import pytest

from app.domain.common.exceptions import ConflictError
from app.domain.users.entities import Candidate
from app.domain.users.value_objects import Email, LinkedInProfile


def _make_user(**kwargs) -> Candidate:
    defaults = {
        "id": None,
        "email": Email.from_raw("alice@example.com"),
        "first_name": "Alice",
        "last_name": "Smith",
    }
    return Candidate(**{**defaults, **kwargs})


def _make_profile(**kwargs) -> LinkedInProfile:
    defaults = {
        "linkedin_id": "li_abc123",
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "avatar_url": "https://cdn.linkedin.com/alice.jpg",
    }
    return LinkedInProfile(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# LinkedInProfile value object
# ---------------------------------------------------------------------------

def test_linkedin_profile_is_immutable():
    profile = _make_profile()
    with pytest.raises((AttributeError, TypeError)):
        profile.linkedin_id = "other"  # type: ignore[misc]


def test_linkedin_profile_raises_on_empty_linkedin_id():
    with pytest.raises(ValueError, match="linkedin_id cannot be empty"):
        LinkedInProfile(linkedin_id="", email="a@b.com", first_name="A", last_name="B")


def test_linkedin_profile_raises_on_empty_email():
    with pytest.raises(ValueError, match="email cannot be empty"):
        LinkedInProfile(linkedin_id="li_x", email="", first_name="A", last_name="B")


def test_linkedin_profile_avatar_url_is_optional():
    profile = LinkedInProfile(
        linkedin_id="li_x", email="a@b.com", first_name="A", last_name="B"
    )
    assert profile.avatar_url is None


# ---------------------------------------------------------------------------
# User.attach_linkedin()
# ---------------------------------------------------------------------------

def test_attach_linkedin_sets_linkedin_id_and_avatar():
    user = _make_user()
    profile = _make_profile()

    user.attach_linkedin(profile)

    assert user.linkedin_id == "li_abc123"
    assert user.avatar_url == "https://cdn.linkedin.com/alice.jpg"


def test_attach_linkedin_is_idempotent_same_id():
    user = _make_user(linkedin_id="li_abc123")
    profile = _make_profile(linkedin_id="li_abc123")

    user.attach_linkedin(profile)  # should not raise

    assert user.linkedin_id == "li_abc123"


def test_attach_linkedin_raises_if_different_id_already_attached():
    user = _make_user(linkedin_id="li_OTHER")
    profile = _make_profile(linkedin_id="li_abc123")

    with pytest.raises(ConflictError, match="different LinkedIn account"):
        user.attach_linkedin(profile)


def test_attach_linkedin_updates_avatar_url():
    user = _make_user(linkedin_id="li_abc123", avatar_url="https://old.jpg")
    profile = _make_profile(linkedin_id="li_abc123", avatar_url="https://new.jpg")

    user.attach_linkedin(profile)

    assert user.avatar_url == "https://new.jpg"
