from dataclasses import dataclass


def _normalize(value: str) -> str:
    return value.strip()


@dataclass(slots=True)
class PaymentMethodSnapshot:
    stripe_payment_method_id: str | None
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    holder_name: str | None = None
    country: str | None = None
    funding: str | None = None
    wallet: str | None = None

    def __post_init__(self) -> None:
        self.brand = _normalize(self.brand)
        self.last4 = _normalize(self.last4)
        if self.holder_name is not None:
            self.holder_name = _normalize(self.holder_name)
        if self.country is not None:
            self.country = _normalize(self.country).upper()
        if self.funding is not None:
            self.funding = _normalize(self.funding)
        if self.wallet is not None:
            self.wallet = _normalize(self.wallet)
        if self.stripe_payment_method_id is not None:
            self.stripe_payment_method_id = _normalize(self.stripe_payment_method_id)

        if not self.brand:
            raise ValueError("brand cannot be empty")
        if len(self.last4) != 4 or not self.last4.isdigit():
            raise ValueError("last4 must contain exactly 4 digits")
        if not 1 <= self.exp_month <= 12:
            raise ValueError("exp_month must be between 1 and 12")
        if self.exp_year < 2000:
            raise ValueError("exp_year must be a valid year")

    @property
    def masked_display(self) -> str:
        return f"{self.brand} •••• {self.last4}"

    @property
    def expiry_display(self) -> str:
        return f"{self.exp_month:02d}/{self.exp_year}"
