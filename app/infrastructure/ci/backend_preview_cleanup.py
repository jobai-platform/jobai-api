from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.infrastructure.ci.neon_branch_lifecycle import sanitize_branch_name

PROTECTED_BRANCH_REFS = frozenset({"main", "develop", "develop-anonymized", "production", "prod"})
PREVIEW_BRANCH_PREFIX = "preview-"
VERCEL_API_BASE_URL = "https://api.vercel.com"
NEON_API_BASE_URL = "https://console.neon.tech/api/v2"


class CleanupSafetyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CleanupTarget:
    branch_ref: str
    neon_branch_name: str


@dataclass(frozen=True, slots=True)
class NeonPreviewBranch:
    branch_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class VercelDeployment:
    uid: str
    url: str
    created_at: datetime
    branch_ref: str


def is_protected_branch_ref(branch_ref: str) -> bool:
    return branch_ref.strip().lower() in PROTECTED_BRANCH_REFS


def build_cleanup_target(branch_ref: str) -> CleanupTarget:
    cleaned = branch_ref.strip()
    if not cleaned:
        raise CleanupSafetyError("Cleanup branch ref is required")
    if is_protected_branch_ref(cleaned):
        raise CleanupSafetyError(f"Refusing to cleanup protected branch ref: {cleaned}")

    neon_branch_name = sanitize_branch_name(cleaned)
    validate_neon_preview_branch_name(neon_branch_name)
    return CleanupTarget(branch_ref=cleaned, neon_branch_name=neon_branch_name)


def validate_neon_preview_branch_name(branch_name: str) -> None:
    cleaned = branch_name.strip().lower()
    if cleaned in PROTECTED_BRANCH_REFS or not cleaned.startswith(PREVIEW_BRANCH_PREFIX):
        raise CleanupSafetyError(f"Refusing to cleanup non-preview Neon branch: {branch_name}")


def parse_timestamp(value: Any) -> datetime:
    if isinstance(value, int | float):
        timestamp = float(value)
        if timestamp > 9_999_999_999:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(UTC)
    raise ValueError(f"Unsupported timestamp value: {value!r}")


def filter_stale_neon_branches(
    branches: list[dict[str, Any]],
    *,
    now: datetime,
    ttl_days: int,
) -> list[NeonPreviewBranch]:
    cutoff = now - timedelta(days=ttl_days)
    stale: list[NeonPreviewBranch] = []
    for branch in branches:
        name = str(branch.get("name") or "")
        if not name.startswith(PREVIEW_BRANCH_PREFIX):
            continue

        created_raw = branch.get("created_at") or branch.get("createdAt") or branch.get("created")
        if created_raw is None:
            continue

        created_at = parse_timestamp(created_raw)
        if created_at >= cutoff:
            continue

        validate_neon_preview_branch_name(name)
        stale.append(
            NeonPreviewBranch(
                branch_id=str(branch["id"]),
                name=name,
                created_at=created_at,
            )
        )
    return stale


def vercel_deployment_branch(deployment: dict[str, Any]) -> str | None:
    direct_branch = deployment.get("branch")
    if isinstance(direct_branch, str) and direct_branch.strip():
        return direct_branch.strip()

    meta = deployment.get("meta")
    if not isinstance(meta, dict):
        return None
    for key in ("githubCommitRef", "gitlabCommitRef", "bitbucketCommitRef", "branch"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def filter_stale_vercel_deployments(
    deployments: list[dict[str, Any]],
    *,
    now: datetime,
    ttl_days: int,
) -> list[VercelDeployment]:
    cutoff = now - timedelta(days=ttl_days)
    stale: list[VercelDeployment] = []
    for deployment in deployments:
        branch_ref = vercel_deployment_branch(deployment)
        if branch_ref is None or is_protected_branch_ref(branch_ref):
            continue
        if str(deployment.get("target") or "").lower() == "production":
            continue

        created_raw = deployment.get("created") or deployment.get("createdAt")
        if created_raw is None:
            continue
        created_at = parse_timestamp(created_raw)
        if created_at >= cutoff:
            continue

        uid = str(deployment.get("uid") or "")
        url = str(deployment.get("url") or "")
        if not uid or not url:
            continue
        stale.append(
            VercelDeployment(
                uid=uid,
                url=url,
                created_at=created_at,
                branch_ref=branch_ref,
            )
        )
    return stale


def _redact_sensitive(value: str) -> str:
    redacted = re.sub(r"postgres(?:ql|ql\+asyncpg)?://\S+", "<redacted-database-url>", value)
    redacted = re.sub(r"(?i)(token|secret|password)=\S+", r"\1=<redacted>", redacted)
    return redacted


def render_cleanup_summary(
    *,
    branch_ref: str,
    neon_branch_name: str,
    neon_deleted: list[str],
    vercel_deleted: list[str],
    env_deleted: list[str],
    skipped: list[str],
) -> str:
    lines = [
        "## Backend preview cleanup",
        "",
        f"- Feature branch: `{branch_ref}`",
        f"- Neon preview branch: `{neon_branch_name}`",
        f"- Neon branches deleted: `{len(neon_deleted)}`",
        f"- Vercel deployments deleted: `{len(vercel_deleted)}`",
        f"- Vercel env vars deleted: `{len(env_deleted)}`",
    ]
    if neon_deleted:
        lines.append(f"- Neon branch ids: `{', '.join(neon_deleted)}`")
    if vercel_deleted:
        lines.append(f"- Vercel deployment ids: `{', '.join(vercel_deleted)}`")
    if env_deleted:
        lines.append(f"- Vercel env ids: `{', '.join(env_deleted)}`")
    if skipped:
        lines.append("- Skipped:")
        lines.extend(f"  - {_redact_sensitive(reason)}" for reason in skipped)
    return "\n".join(lines)


class NeonApiClient:
    def __init__(self, *, api_key: str, project_id: str, base_url: str = NEON_API_BASE_URL) -> None:
        self._api_key = api_key
        self._project_id = project_id
        self._base_url = base_url.rstrip("/")

    def list_branches(self) -> list[dict[str, Any]]:
        payload = self._request_json("GET", f"/projects/{self._project_id}/branches")
        branches = payload.get("branches", [])
        if not isinstance(branches, list):
            return []
        return branches

    def find_branch_by_name(self, branch_name: str) -> dict[str, Any] | None:
        for branch in self.list_branches():
            if branch.get("name") == branch_name:
                return branch
        return None

    def delete_branch(self, branch_id: str) -> None:
        self._request_json("DELETE", f"/projects/{self._project_id}/branches/{branch_id}")

    def _request_json(self, method: str, path: str) -> dict[str, Any]:
        request = Request(
            f"{self._base_url}{path}",
            headers={"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 204:
                return {}
            raise
        return json.loads(body) if body else {}


class VercelApiClient:
    def __init__(
        self,
        *,
        token: str,
        project_id: str,
        team_id: str,
        base_url: str = VERCEL_API_BASE_URL,
    ) -> None:
        self._token = token
        self._project_id = project_id
        self._team_id = team_id
        self._base_url = base_url.rstrip("/")

    def list_deployments(self, *, branch_ref: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "projectId": self._project_id,
            "teamId": self._team_id,
            "limit": 100,
        }
        if branch_ref:
            params["branch"] = branch_ref
        payload = self._request_json("GET", f"/v6/deployments?{urlencode(params)}")
        deployments = payload.get("deployments", [])
        if not isinstance(deployments, list):
            return []
        return deployments

    def delete_deployment(self, deployment_id: str) -> None:
        params = urlencode({"teamId": self._team_id})
        self._request_json("DELETE", f"/v13/deployments/{deployment_id}?{params}")

    def list_branch_env_vars(self, *, branch_ref: str, keys: list[str]) -> list[dict[str, Any]]:
        if not keys:
            return []
        params = urlencode({"teamId": self._team_id, "target": "preview", "gitBranch": branch_ref})
        payload = self._request_json("GET", f"/v9/projects/{self._project_id}/env?{params}")
        envs = payload.get("envs", [])
        if not isinstance(envs, list):
            return []
        wanted = set(keys)
        return [env for env in envs if env.get("key") in wanted]

    def delete_env_var(self, env_id: str) -> None:
        params = urlencode({"teamId": self._team_id})
        self._request_json("DELETE", f"/v9/projects/{self._project_id}/env/{env_id}?{params}")

    def _request_json(self, method: str, path: str) -> dict[str, Any]:
        request = Request(
            f"{self._base_url}{path}",
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            method=method,
        )
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def cleanup_branch(
    *,
    branch_ref: str,
    neon_client: NeonApiClient,
    vercel_client: VercelApiClient,
    env_keys: list[str],
) -> str:
    target = build_cleanup_target(branch_ref)
    neon_deleted: list[str] = []
    vercel_deleted: list[str] = []
    env_deleted: list[str] = []
    skipped: list[str] = []

    neon_branch = neon_client.find_branch_by_name(target.neon_branch_name)
    if neon_branch is None:
        skipped.append(f"Neon branch not found: {target.neon_branch_name}")
    else:
        branch_id = str(neon_branch["id"])
        neon_client.delete_branch(branch_id)
        neon_deleted.append(branch_id)

    for deployment in vercel_client.list_deployments(branch_ref=target.branch_ref):
        deployment_id = str(deployment.get("uid") or "")
        if not deployment_id:
            skipped.append("Vercel deployment without uid")
            continue
        if str(deployment.get("target") or "").lower() == "production":
            skipped.append(f"Skipped production Vercel deployment: {deployment_id}")
            continue
        vercel_client.delete_deployment(deployment_id)
        vercel_deleted.append(deployment_id)

    for env_var in vercel_client.list_branch_env_vars(branch_ref=target.branch_ref, keys=env_keys):
        env_id = str(env_var.get("id") or env_var.get("uid") or "")
        if not env_id:
            skipped.append(f"Vercel env var without id: {env_var.get('key', '<unknown>')}")
            continue
        vercel_client.delete_env_var(env_id)
        env_deleted.append(env_id)

    return render_cleanup_summary(
        branch_ref=target.branch_ref,
        neon_branch_name=target.neon_branch_name,
        neon_deleted=neon_deleted,
        vercel_deleted=vercel_deleted,
        env_deleted=env_deleted,
        skipped=skipped,
    )


def run_janitor(
    *,
    ttl_days: int,
    neon_client: NeonApiClient,
    vercel_client: VercelApiClient,
    now: datetime,
) -> str:
    neon_deleted: list[str] = []
    vercel_deleted: list[str] = []
    skipped: list[str] = []

    for branch in filter_stale_neon_branches(
        neon_client.list_branches(),
        now=now,
        ttl_days=ttl_days,
    ):
        neon_client.delete_branch(branch.branch_id)
        neon_deleted.append(branch.branch_id)

    for deployment in filter_stale_vercel_deployments(
        vercel_client.list_deployments(),
        now=now,
        ttl_days=ttl_days,
    ):
        vercel_client.delete_deployment(deployment.uid)
        vercel_deleted.append(deployment.uid)

    if not neon_deleted and not vercel_deleted:
        skipped.append(f"No stale preview resources older than {ttl_days} days")

    return render_cleanup_summary(
        branch_ref=f"ttl-janitor-{ttl_days}d",
        neon_branch_name="preview-*",
        neon_deleted=neon_deleted,
        vercel_deleted=vercel_deleted,
        env_deleted=[],
        skipped=skipped,
    )


def _write_summary(summary: str) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(f"{summary}\n")
    print(summary)


def _write_multiline_output(name: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    delimiter = f"EOF_{name}"
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def _parse_env_keys(raw: str) -> list[str]:
    return [key.strip() for key in raw.split(",") if key.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup JobAI backend preview resources.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    branch_parser = subparsers.add_parser("branch", help="Cleanup one feature branch")
    branch_parser.add_argument("--branch", required=True, help="Raw Git feature branch ref")

    janitor_parser = subparsers.add_parser("janitor", help="Cleanup stale preview resources by TTL")
    janitor_parser.add_argument("--ttl-days", type=int, default=7, help="Preview TTL in days")

    for mode_parser in (branch_parser, janitor_parser):
        mode_parser.add_argument("--neon-project-id", required=True, help="Neon project id")
        mode_parser.add_argument("--neon-api-key", required=True, help="Neon API key")
        mode_parser.add_argument(
            "--vercel-project-id",
            required=True,
            help="Vercel backend project id",
        )
        mode_parser.add_argument("--vercel-team-id", required=True, help="Vercel team/org id")
        mode_parser.add_argument("--vercel-token", required=True, help="Vercel API token")
        mode_parser.add_argument(
            "--vercel-env-keys",
            default="",
            help="Comma-separated branch-specific Vercel env var keys managed by CI",
        )

    args = parser.parse_args()
    neon_client = NeonApiClient(api_key=args.neon_api_key, project_id=args.neon_project_id)
    vercel_client = VercelApiClient(
        token=args.vercel_token,
        project_id=args.vercel_project_id,
        team_id=args.vercel_team_id,
    )

    if args.mode == "branch":
        summary = cleanup_branch(
            branch_ref=args.branch,
            neon_client=neon_client,
            vercel_client=vercel_client,
            env_keys=_parse_env_keys(args.vercel_env_keys),
        )
    else:
        summary = run_janitor(
            ttl_days=args.ttl_days,
            neon_client=neon_client,
            vercel_client=vercel_client,
            now=datetime.now(tz=UTC),
        )

    _write_multiline_output("cleanup_summary", summary)
    _write_summary(summary)


if __name__ == "__main__":
    main()
