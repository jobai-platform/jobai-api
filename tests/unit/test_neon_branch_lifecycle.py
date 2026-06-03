from app.infrastructure.ci.neon_branch_lifecycle import sanitize_branch_name, to_asyncpg_url


def test_sanitize_branch_name_is_deterministic_and_neon_safe() -> None:
    branch_name = sanitize_branch_name("feature/job-124-06-cicd-add-neon-branch-lifecycle-workflow-for-feature")

    assert branch_name.startswith("preview-feature-job-124-06-cicd-add-neon-branch-")
    assert branch_name == sanitize_branch_name("feature/job-124-06-cicd-add-neon-branch-lifecycle-workflow-for-feature")
    assert len(branch_name) <= 63
    assert "/" not in branch_name
    assert "_" not in branch_name


def test_sanitize_branch_name_changes_with_input() -> None:
    a = sanitize_branch_name("feature/job-124-a")
    b = sanitize_branch_name("feature/job-124-b")

    assert a != b


def test_to_asyncpg_url_converts_neon_connection_string() -> None:
    url = to_asyncpg_url(
        "postgresql://neondb_owner:secret@ep-example.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )

    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in url
