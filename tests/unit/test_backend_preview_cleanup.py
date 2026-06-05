from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.infrastructure.ci.backend_preview_cleanup import (
    CleanupSafetyError,
    build_cleanup_target,
    filter_stale_neon_branches,
    filter_stale_vercel_deployments,
    is_protected_branch_ref,
    render_cleanup_summary,
    vercel_deployment_branch,
)
from app.infrastructure.ci.neon_branch_lifecycle import sanitize_branch_name


def test_build_cleanup_target_reuses_neon_preview_sanitizer() -> None:
    branch_ref = "feature/job-128-09-cicd-cleanup-preview-backend-neon-branch-and-branch"

    target = build_cleanup_target(branch_ref)

    assert target.branch_ref == branch_ref
    assert target.neon_branch_name == sanitize_branch_name(branch_ref)
    assert target.neon_branch_name.startswith("preview-feature-job-128-09-cicd-cleanup-")


@pytest.mark.parametrize("branch_ref", ["main", "develop", "develop-anonymized", "production", "prod"])
def test_build_cleanup_target_rejects_protected_branch_refs(branch_ref: str) -> None:
    with pytest.raises(CleanupSafetyError):
        build_cleanup_target(branch_ref)


def test_is_protected_branch_ref_matches_exact_refs_only() -> None:
    assert is_protected_branch_ref("develop") is True
    assert is_protected_branch_ref("feature/develop-fix") is False


def test_filter_stale_neon_branches_keeps_only_preview_branches_older_than_ttl() -> None:
    now = datetime(2026, 6, 5, tzinfo=UTC)
    branches = [
        {"id": "br_old", "name": "preview-feature-old-aaaaaaaa", "created_at": "2026-05-25T10:00:00Z"},
        {"id": "br_new", "name": "preview-feature-new-bbbbbbbb", "created_at": "2026-06-04T10:00:00Z"},
        {"id": "br_dev", "name": "develop-anonymized", "created_at": "2026-05-01T10:00:00Z"},
        {"id": "br_custom", "name": "custom-preview", "created_at": "2026-05-01T10:00:00Z"},
    ]

    stale = filter_stale_neon_branches(branches, now=now, ttl_days=7)

    assert [branch.name for branch in stale] == ["preview-feature-old-aaaaaaaa"]
    assert stale[0].branch_id == "br_old"


def test_filter_stale_vercel_deployments_skips_missing_or_protected_branch_metadata() -> None:
    now = datetime(2026, 6, 5, tzinfo=UTC)
    old = int((now - timedelta(days=10)).timestamp() * 1000)
    deployments = [
        {
            "uid": "dpl_feature",
            "url": "jobai-api-feature.vercel.app",
            "created": old,
            "readyState": "READY",
            "target": None,
            "meta": {"githubCommitRef": "feature/job-128"},
        },
        {
            "uid": "dpl_develop",
            "url": "jobai-api-develop.vercel.app",
            "created": old,
            "readyState": "READY",
            "target": None,
            "meta": {"githubCommitRef": "develop"},
        },
        {
            "uid": "dpl_unknown",
            "url": "jobai-api-unknown.vercel.app",
            "created": old,
            "readyState": "READY",
            "target": None,
            "meta": {},
        },
    ]

    stale = filter_stale_vercel_deployments(deployments, now=now, ttl_days=7)

    assert [deployment.uid for deployment in stale] == ["dpl_feature"]


def test_vercel_deployment_branch_reads_common_git_metadata_keys() -> None:
    assert vercel_deployment_branch({"meta": {"githubCommitRef": "feature/job-128"}}) == "feature/job-128"
    assert vercel_deployment_branch({"meta": {"gitlabCommitRef": "feature/job-128"}}) == "feature/job-128"
    assert vercel_deployment_branch({"meta": {}, "branch": "feature/job-128"}) == "feature/job-128"


def test_render_cleanup_summary_does_not_include_sensitive_values() -> None:
    summary = render_cleanup_summary(
        branch_ref="feature/job-128",
        neon_branch_name="preview-feature-job-128-aaaaaaaa",
        neon_deleted=["br_123"],
        vercel_deleted=["dpl_123"],
        env_deleted=["env_123"],
        skipped=["DATABASE_URL=postgresql://user:secret@example/db"],
    )

    assert "preview-feature-job-128-aaaaaaaa" in summary
    assert "dpl_123" in summary
    assert "postgresql://" not in summary
    assert "secret" not in summary
