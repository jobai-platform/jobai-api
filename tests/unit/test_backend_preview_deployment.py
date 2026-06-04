from app.infrastructure.ci.backend_preview_deployment import (
    build_preview_metadata,
    render_pr_comment,
)


def test_build_preview_metadata_derives_deterministic_url_and_image() -> None:
    metadata = build_preview_metadata(
        preview_slug="preview-feature-job-125-abcdef12",
        repository="jobai-platform/jobai-api",
        commit_sha="1234567890abcdef",
        base_domain="preview-api.sovrum.dev",
    )

    assert metadata.preview_host == "preview-feature-job-125-abcdef12.preview-api.sovrum.dev"
    assert metadata.preview_url == "https://preview-feature-job-125-abcdef12.preview-api.sovrum.dev"
    assert metadata.image_ref == "ghcr.io/jobai-platform/jobai-api/jobai-backend:sha-1234567"
    assert metadata.compose_project == "jobai-preview-preview-feature-job-125-abcdef12"


def test_build_preview_metadata_normalizes_base_domain() -> None:
    metadata = build_preview_metadata(
        preview_slug="preview-feature-job-125-abcdef12",
        repository="jobai-platform/jobai-api",
        commit_sha="1234567890abcdef",
        base_domain="https://preview-api.sovrum.dev/",
    )

    assert metadata.preview_url == "https://preview-feature-job-125-abcdef12.preview-api.sovrum.dev"


def test_render_pr_comment_contains_stable_marker_and_preview_context() -> None:
    metadata = build_preview_metadata(
        preview_slug="preview-feature-job-125-abcdef12",
        repository="jobai-platform/jobai-api",
        commit_sha="1234567890abcdef",
        base_domain="preview-api.sovrum.dev",
    )

    comment = render_pr_comment(metadata, branch_ref="feature/job-125", neon_branch_name="preview-feature-job-125-abcdef12")

    assert "<!-- jobai-backend-preview -->" in comment
    assert "https://preview-feature-job-125-abcdef12.preview-api.sovrum.dev" in comment
    assert "preview-feature-job-125-abcdef12" in comment
    assert "feature/job-125" in comment
