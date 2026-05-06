import pytest
from uuid import uuid4

from app.domain.users.candidate_profile import CandidateProfile, RemotePreference


def _make_profile(**kwargs) -> CandidateProfile:
    defaults = dict(user_id=uuid4())
    return CandidateProfile(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def test_profile_created_with_defaults():
    profile = _make_profile()
    assert profile.skills == []
    assert profile.preferred_locations == []
    assert profile.remote_preference == RemotePreference.ANY
    assert profile.is_complete is False


def test_profile_is_complete_when_title_and_skills_set():
    profile = _make_profile(current_title="Developer", skills=["python"])
    assert profile.is_complete is True


def test_profile_not_complete_without_title():
    profile = _make_profile(skills=["python"])
    assert profile.is_complete is False


def test_profile_not_complete_without_skills():
    profile = _make_profile(current_title="Developer")
    assert profile.is_complete is False


# ---------------------------------------------------------------------------
# Domain rules
# ---------------------------------------------------------------------------

def test_negative_years_of_experience_raises():
    with pytest.raises(ValueError, match="years_of_experience cannot be negative"):
        _make_profile(years_of_experience=-1)


def test_salary_min_greater_than_max_raises():
    with pytest.raises(ValueError, match="desired_salary_min cannot exceed"):
        _make_profile(desired_salary_min=100_000, desired_salary_max=50_000)


def test_salary_min_equal_to_max_is_valid():
    profile = _make_profile(desired_salary_min=50_000, desired_salary_max=50_000)
    assert profile.desired_salary_min == 50_000


def test_zero_years_of_experience_is_valid():
    profile = _make_profile(years_of_experience=0)
    assert profile.years_of_experience == 0


# ---------------------------------------------------------------------------
# Skills normalization
# ---------------------------------------------------------------------------

def test_skills_normalized_to_lowercase():
    profile = _make_profile(skills=["Python", "DJANGO", "FastAPI"])
    assert profile.skills == ["python", "django", "fastapi"]


def test_skills_stripped_of_whitespace():
    profile = _make_profile(skills=["  python  ", " sql "])
    assert profile.skills == ["python", "sql"]


def test_skills_deduplicated():
    profile = _make_profile(skills=["python", "Python", "PYTHON"])
    assert profile.skills == ["python"]


def test_empty_skill_strings_ignored():
    profile = _make_profile(skills=["python", "", "  "])
    assert profile.skills == ["python"]


# ---------------------------------------------------------------------------
# upsert() method
# ---------------------------------------------------------------------------

def test_upsert_updates_title():
    profile = _make_profile()
    profile.upsert(current_title="Senior Engineer")
    assert profile.current_title == "Senior Engineer"


def test_upsert_normalizes_skills():
    profile = _make_profile()
    profile.upsert(skills=["React", "TypeScript", "react"])
    assert profile.skills == ["react", "typescript"]


def test_upsert_validates_salary_constraint():
    profile = _make_profile()
    with pytest.raises(ValueError, match="desired_salary_min cannot exceed"):
        profile.upsert(desired_salary_min=200_000, desired_salary_max=100_000)


def test_upsert_validates_negative_experience():
    profile = _make_profile()
    with pytest.raises(ValueError, match="years_of_experience cannot be negative"):
        profile.upsert(years_of_experience=-5)


def test_upsert_does_not_overwrite_with_none():
    profile = _make_profile(current_title="Engineer", skills=["python"])
    profile.upsert(bio="hello")
    assert profile.current_title == "Engineer"
    assert profile.skills == ["python"]


def test_upsert_updates_timestamp():
    profile = _make_profile()
    before = profile.updated_at
    profile.upsert(bio="updated")
    assert profile.updated_at >= before


# ---------------------------------------------------------------------------
# RemotePreference
# ---------------------------------------------------------------------------

def test_remote_preference_values():
    assert RemotePreference.REMOTE == "remote"
    assert RemotePreference.HYBRID == "hybrid"
    assert RemotePreference.ONSITE == "onsite"
    assert RemotePreference.ANY == "any"
