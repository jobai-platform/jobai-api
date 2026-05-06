import re
from dataclasses import dataclass
from typing import Optional

_EMAIL_REGEX = re.compile(
    r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",
)

@dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def from_raw(cls, raw: str) -> "Email":
        if raw is None:
            raise ValueError("Email cannot be None")

        normalized = raw.strip().lower()
        if not normalized:
            raise ValueError("Email cannot be empty or whitespace")

        if not _EMAIL_REGEX.match(normalized):
            raise ValueError(f"Invalid email format: {raw!r}")

        return cls(normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LinkedInProfile:
    """
    Value Object representing a LinkedIn identity returned by the OAuth userinfo endpoint.
    Immutable — created once from the LinkedIn API response, never mutated.
    """
    linkedin_id: str
    email: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.linkedin_id:
            msg = "linkedin_id cannot be empty"
            raise ValueError(msg)
        if not self.email:
            msg = "email cannot be empty"
            raise ValueError(msg)
