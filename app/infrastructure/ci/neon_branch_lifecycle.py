from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

NEON_DB_NAME = "neondb"
NEON_ROLE_NAME = "neondb_owner"
PREVIEW_BRANCH_PREFIX = "preview"
MAX_NEON_BRANCH_NAME_LENGTH = 63


@dataclass(frozen=True, slots=True)
class PreviewBranchResult:
    branch_name: str
    branch_id: str
    created: bool
    database_url: str


def sanitize_branch_name(raw_branch: str, *, prefix: str = PREVIEW_BRANCH_PREFIX) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw_branch.strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-") or "branch"
    digest = hashlib.sha1(raw_branch.encode("utf-8")).hexdigest()[:8]
    fixed = len(prefix) + 1 + 1 + len(digest)
    max_slug_len = MAX_NEON_BRANCH_NAME_LENGTH - fixed
    slug = normalized[:max_slug_len].rstrip("-") or "branch"
    return f"{prefix}-{slug}-{digest}"


def to_asyncpg_url(connection_string: str) -> str:
    cleaned = connection_string.strip()
    cleaned = cleaned.replace("postgresql://", "postgresql+asyncpg://", 1)
    cleaned = cleaned.replace("?sslmode=require&channel_binding=require", "?ssl=require")
    cleaned = cleaned.replace("?sslmode=require", "?ssl=require")
    return cleaned


def _run_neonctl_json(args: list[str], *, project_id: str, api_key: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "npx",
            "neonctl",
            *args,
            "--project-id",
            project_id,
            "--api-key",
            api_key,
            "--output",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _run_neonctl_text(args: list[str], *, project_id: str, api_key: str) -> str:
    completed = subprocess.run(
        [
            "npx",
            "neonctl",
            *args,
            "--project-id",
            project_id,
            "--api-key",
            api_key,
            "--output",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _branch_payload(payload: dict[str, Any]) -> dict[str, Any]:
    branch = payload.get("branch")
    if isinstance(branch, dict):
        return branch
    return payload


def _wait_for_branch_ready(*, branch_name: str, project_id: str, api_key: str) -> dict[str, Any]:
    last_payload: dict[str, Any] | None = None
    for _ in range(24):
        payload = _run_neonctl_json(
            ["branches", "get", branch_name],
            project_id=project_id,
            api_key=api_key,
        )
        last_payload = payload
        branch = _branch_payload(payload)
        state = str(branch.get("current_state") or branch.get("state") or "").lower()
        if state in {"ready", "active"}:
            return branch
        time.sleep(5)

    branch = _branch_payload(last_payload or {})
    raise RuntimeError(
        f"Neon branch {branch_name} did not become ready (state={branch.get('current_state')!r})"
    )


def ensure_preview_branch(
    *,
    branch_ref: str,
    project_id: str,
    api_key: str,
    parent_branch: str,
) -> PreviewBranchResult:
    branch_name = sanitize_branch_name(branch_ref)

    created = False
    try:
        branch_payload = _run_neonctl_json(
            ["branches", "get", branch_name],
            project_id=project_id,
            api_key=api_key,
        )
        branch = _branch_payload(branch_payload)
    except subprocess.CalledProcessError:
        branch_payload = _run_neonctl_json(
            ["branches", "create", "--name", branch_name, "--parent", parent_branch],
            project_id=project_id,
            api_key=api_key,
        )
        branch = _branch_payload(branch_payload)
        created = True

    branch = _wait_for_branch_ready(
        branch_name=branch_name,
        project_id=project_id,
        api_key=api_key,
    )

    connection_string = _run_neonctl_text(
        [
            "connection-string",
            branch_name,
            "--role-name",
            NEON_ROLE_NAME,
            "--database-name",
            NEON_DB_NAME,
        ],
        project_id=project_id,
        api_key=api_key,
    )
    database_url = to_asyncpg_url(connection_string)

    return PreviewBranchResult(
        branch_name=branch["name"],
        branch_id=branch["id"],
        created=created,
        database_url=database_url,
    )


def _write_github_output(name: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _write_github_env(name: str, value: str) -> None:
    env_path = os.getenv("GITHUB_ENV")
    if not env_path:
        return
    with Path(env_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _write_summary(
    result: PreviewBranchResult,
    *,
    branch_ref: str,
    commit_sha: str,
    parent_branch: str,
) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    created_label = "created" if result.created else "reused"
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write("## Neon preview branch lifecycle\n")
        handle.write(f"- Feature branch: `{branch_ref}`\n")
        handle.write(f"- Commit SHA: `{commit_sha}`\n")
        handle.write(f"- Parent branch: `{parent_branch}`\n")
        handle.write(f"- Neon preview branch: `{result.branch_name}`\n")
        handle.write(f"- Neon branch id: `{result.branch_id}`\n")
        handle.write(f"- Result: `{created_label}`\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or reuse a Neon preview branch for feature previews.",
    )
    parser.add_argument("--branch", required=True, help="Git branch name from GitHub Actions")
    parser.add_argument("--commit-sha", required=True, help="Git commit SHA")
    parser.add_argument("--project-id", required=True, help="Neon project id")
    parser.add_argument("--api-key", required=True, help="Neon API key")
    parser.add_argument(
        "--parent-branch",
        default="develop-anonymized",
        help="Parent Neon branch used for preview branching",
    )
    args = parser.parse_args()

    result = ensure_preview_branch(
        branch_ref=args.branch,
        project_id=args.project_id,
        api_key=args.api_key,
        parent_branch=args.parent_branch,
    )

    _write_github_output("preview_branch_name", result.branch_name)
    _write_github_output("preview_branch_id", result.branch_id)
    _write_github_output("preview_branch_created", "true" if result.created else "false")
    _write_github_env("DATABASE_URL", result.database_url)
    _write_summary(
        result,
        branch_ref=args.branch,
        commit_sha=args.commit_sha,
        parent_branch=args.parent_branch,
    )

    print(
        json.dumps(
            {
                "branch_name": result.branch_name,
                "branch_id": result.branch_id,
                "created": result.created,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
