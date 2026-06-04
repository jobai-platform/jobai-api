from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path

PREVIEW_COMMENT_MARKER = "<!-- jobai-backend-preview -->"
PREVIEW_IMAGE_NAME = "jobai-backend"


@dataclass(frozen=True, slots=True)
class BackendPreviewMetadata:
    preview_slug: str
    preview_host: str
    preview_url: str
    image_ref: str
    compose_project: str


def _normalize_base_domain(base_domain: str) -> str:
    normalized = base_domain.strip().removeprefix("https://").removeprefix("http://").strip("/")
    if not normalized:
        raise ValueError("Preview backend base domain is required")
    return normalized


def build_preview_metadata(
    *,
    preview_slug: str,
    repository: str,
    commit_sha: str,
    base_domain: str,
) -> BackendPreviewMetadata:
    normalized_domain = _normalize_base_domain(base_domain)
    short_sha = commit_sha[:7]
    preview_host = f"{preview_slug}.{normalized_domain}"
    return BackendPreviewMetadata(
        preview_slug=preview_slug,
        preview_host=preview_host,
        preview_url=f"https://{preview_host}",
        image_ref=f"ghcr.io/{repository}/{PREVIEW_IMAGE_NAME}:sha-{short_sha}",
        compose_project=f"jobai-preview-{preview_slug}",
    )


def render_pr_comment(
    metadata: BackendPreviewMetadata,
    *,
    branch_ref: str,
    neon_branch_name: str,
) -> str:
    return "\n".join(
        [
            PREVIEW_COMMENT_MARKER,
            "## Backend preview ready",
            "",
            f"- Preview URL: {metadata.preview_url}",
            f"- Health check: {metadata.preview_url}/health",
            f"- Feature branch: `{branch_ref}`",
            f"- Neon branch: `{neon_branch_name}`",
            f"- Docker image: `{metadata.image_ref}`",
            f"- Compose project: `{metadata.compose_project}`",
        ]
    )


def _write_github_output(name: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _write_multiline_github_output(name: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    delimiter = f"EOF_{name}"
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def _write_github_env(name: str, value: str) -> None:
    env_path = os.getenv("GITHUB_ENV")
    if not env_path:
        return
    with Path(env_path).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare backend preview deployment metadata.")
    parser.add_argument(
        "--preview-slug",
        required=True,
        help="Sanitized branch slug used for preview resources",
    )
    parser.add_argument("--branch", required=True, help="Git branch ref name")
    parser.add_argument("--repository", required=True, help="GitHub repository in owner/name form")
    parser.add_argument(
        "--commit-sha",
        required=True,
        help="Git commit SHA used to tag the Docker image",
    )
    parser.add_argument("--base-domain", required=True, help="Base domain for backend previews")
    parser.add_argument(
        "--neon-branch-name",
        required=True,
        help="Matching Neon preview branch name",
    )
    args = parser.parse_args()

    metadata = build_preview_metadata(
        preview_slug=args.preview_slug,
        repository=args.repository,
        commit_sha=args.commit_sha,
        base_domain=args.base_domain,
    )
    comment = render_pr_comment(
        metadata,
        branch_ref=args.branch,
        neon_branch_name=args.neon_branch_name,
    )

    _write_github_output("preview_slug", metadata.preview_slug)
    _write_github_output("preview_host", metadata.preview_host)
    _write_github_output("preview_url", metadata.preview_url)
    _write_github_output("image_ref", metadata.image_ref)
    _write_github_output("compose_project", metadata.compose_project)
    _write_multiline_github_output("pr_comment_body", comment)

    _write_github_env("PREVIEW_SLUG", metadata.preview_slug)
    _write_github_env("PREVIEW_HOST", metadata.preview_host)
    _write_github_env("PREVIEW_URL", metadata.preview_url)
    _write_github_env("IMAGE_REF", metadata.image_ref)
    _write_github_env("COMPOSE_PROJECT_NAME", metadata.compose_project)


if __name__ == "__main__":
    main()
