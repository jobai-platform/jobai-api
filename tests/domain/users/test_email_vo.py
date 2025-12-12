import pytest

from app.domain.users.value_objects import Email


def test_email_is_normalized_add_lowercased():
    email = Email.from_raw("USER@Example.COM")
    assert email.value == "user@example.com"
    assert str(email) == "user@example.com"


@pytest.mark.parametrize(
    "raw",
    ["", "  ", "not-an-email", "user@", "@example.com", "user@example", "user@@example.com"]
)
def test_email_rejects_invalid_values(raw: str):
    with pytest.raises(ValueError):
        Email.from_raw(raw)
