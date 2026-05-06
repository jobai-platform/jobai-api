import pytest
from uuid import uuid4

from app.application.users.candidate_profile_use_cases import (
    UpsertCandidateProfileUseCase,
    GetCandidateProfileUseCase,
    UpsertProfileCommand,
)
from app.domain.users.candidate_profile import CandidateProfile, RemotePreference
from tests.fakes.users.in_memory_candidate_profile_repo import InMemoryCandidateProfileRepository


def _make_use_cases() -> tuple[UpsertCandidateProfileUseCase, GetCandidateProfileUseCase, InMemoryCandidateProfileRepository]:
    repo = InMemoryCandidateProfileRepository()
    return UpsertCandidateProfileUseCase(repo), GetCandidateProfileUseCase(repo), repo


# ---------------------------------------------------------------------------
# GetCandidateProfileUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_profile_auto_creates_empty_profile():
    _, get_uc, repo = _make_use_cases()
    user_id = uuid4()

    profile = await get_uc.execute(user_id)

    assert profile.user_id == user_id
    assert profile.id is not None
    assert profile.is_complete is False
    assert await repo.get_by_user_id(user_id) is not None


@pytest.mark.asyncio
async def test_get_profile_returns_existing_profile():
    _, get_uc, repo = _make_use_cases()
    user_id = uuid4()
    existing = CandidateProfile(user_id=user_id, current_title="Engineer", skills=["python"])
    await repo.save(existing)

    profile = await get_uc.execute(user_id)

    assert profile.current_title == "Engineer"
    assert profile.skills == ["python"]


# ---------------------------------------------------------------------------
# UpsertCandidateProfileUseCase
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_creates_profile_when_none_exists():
    upsert_uc, _, repo = _make_use_cases()
    user_id = uuid4()

    profile = await upsert_uc.execute(UpsertProfileCommand(
        user_id=user_id,
        current_title="Backend Developer",
        skills=["python", "fastapi"],
    ))

    assert profile.id is not None
    assert profile.current_title == "Backend Developer"
    assert profile.skills == ["python", "fastapi"]
    assert profile.is_complete is True


@pytest.mark.asyncio
async def test_upsert_updates_existing_profile():
    upsert_uc, _, repo = _make_use_cases()
    user_id = uuid4()
    existing = CandidateProfile(user_id=user_id, current_title="Junior Dev")
    await repo.save(existing)

    profile = await upsert_uc.execute(UpsertProfileCommand(
        user_id=user_id,
        current_title="Senior Dev",
        skills=["python"],
        years_of_experience=5,
    ))

    assert profile.current_title == "Senior Dev"
    assert profile.years_of_experience == 5
    assert profile.is_complete is True


@pytest.mark.asyncio
async def test_upsert_normalizes_skills():
    upsert_uc, _, _ = _make_use_cases()
    user_id = uuid4()

    profile = await upsert_uc.execute(UpsertProfileCommand(
        user_id=user_id,
        skills=["Python", "PYTHON", "  FastAPI  "],
    ))

    assert profile.skills == ["python", "fastapi"]


@pytest.mark.asyncio
async def test_upsert_raises_on_invalid_salary_range():
    upsert_uc, _, _ = _make_use_cases()

    with pytest.raises(ValueError, match="desired_salary_min cannot exceed"):
        await upsert_uc.execute(UpsertProfileCommand(
            user_id=uuid4(),
            desired_salary_min=100_000,
            desired_salary_max=50_000,
        ))


@pytest.mark.asyncio
async def test_upsert_raises_on_negative_experience():
    upsert_uc, _, _ = _make_use_cases()

    with pytest.raises(ValueError, match="years_of_experience cannot be negative"):
        await upsert_uc.execute(UpsertProfileCommand(
            user_id=uuid4(),
            years_of_experience=-1,
        ))


@pytest.mark.asyncio
async def test_upsert_preserves_existing_fields_when_not_provided():
    upsert_uc, _, repo = _make_use_cases()
    user_id = uuid4()
    existing = CandidateProfile(
        user_id=user_id,
        current_title="Engineer",
        skills=["python"],
        bio="Hello world",
    )
    await repo.save(existing)

    profile = await upsert_uc.execute(UpsertProfileCommand(
        user_id=user_id,
        years_of_experience=3,
    ))

    assert profile.current_title == "Engineer"
    assert profile.skills == ["python"]
    assert profile.bio == "Hello world"
    assert profile.years_of_experience == 3


@pytest.mark.asyncio
async def test_upsert_sets_remote_preference():
    upsert_uc, _, _ = _make_use_cases()

    profile = await upsert_uc.execute(UpsertProfileCommand(
        user_id=uuid4(),
        remote_preference=RemotePreference.REMOTE,
    ))

    assert profile.remote_preference == RemotePreference.REMOTE
