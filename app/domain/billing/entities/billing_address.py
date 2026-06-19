from dataclasses import dataclass


def _normalize(value: str) -> str:
    return value.strip()


@dataclass(slots=True)
class BillingAddress:
    line1: str
    city: str
    postal_code: str
    country: str
    line2: str | None = None
    state: str | None = None

    def __post_init__(self) -> None:
        self.line1 = _normalize(self.line1)
        self.city = _normalize(self.city)
        self.postal_code = _normalize(self.postal_code)
        self.country = _normalize(self.country).upper()
        if self.line2 is not None:
            self.line2 = _normalize(self.line2)
        if self.state is not None:
            self.state = _normalize(self.state)

        if not self.line1:
            raise ValueError("line1 cannot be empty")
        if not self.city:
            raise ValueError("city cannot be empty")
        if not self.postal_code:
            raise ValueError("postal_code cannot be empty")
        if not self.country:
            raise ValueError("country cannot be empty")
        if len(self.country) not in {2, 3}:
            raise ValueError("country must be a valid ISO country code")

    def as_single_line(self) -> str:
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        parts.extend([self.postal_code, self.city, self.country])
        return ", ".join(parts)
