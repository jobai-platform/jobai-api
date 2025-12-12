import re
from dataclasses import dataclass

_EMAIL_REGEX = re.compile(
    r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
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
