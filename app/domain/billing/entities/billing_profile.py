from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class BillingProfile:
    user_id: UUID
    stripe_customer_id: str | None = None
    contact_first_name: str | None = None
    contact_last_name: str | None = None
    contact_email: str | None = None
    billing_address: BillingAddress | None = None
    payment_method_snapshot: PaymentMethodSnapshot | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        self._normalize_contact_fields()
        self._validate()

    def _normalize_contact_fields(self) -> None:
        if self.contact_first_name is not None:
            self.contact_first_name = self.contact_first_name.strip()
        if self.contact_last_name is not None:
            self.contact_last_name = self.contact_last_name.strip()
        if self.contact_email is not None:
            self.contact_email = self.contact_email.strip().lower()
        if self.stripe_customer_id is not None:
            self.stripe_customer_id = self.stripe_customer_id.strip()

    def _validate(self) -> None:
        if self.contact_first_name is not None and not self.contact_first_name:
            raise ValueError("contact_first_name cannot be empty")
        if self.contact_last_name is not None and not self.contact_last_name:
            raise ValueError("contact_last_name cannot be empty")
        if self.contact_email is not None and not self.contact_email:
            raise ValueError("contact_email cannot be empty")

    @property
    def contact_full_name(self) -> str | None:
        names = [name for name in [self.contact_first_name, self.contact_last_name] if name]
        if not names:
            return None
        return " ".join(names)

    def update_contact_info(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> None:
        if first_name is not None:
            self.contact_first_name = first_name.strip()
        if last_name is not None:
            self.contact_last_name = last_name.strip()
        if email is not None:
            self.contact_email = email.strip().lower()
        self.updated_at = _utcnow()
        self._validate()

    def update_billing_address(self, address: BillingAddress | None) -> None:
        self.billing_address = address
        self.updated_at = _utcnow()

    def update_payment_method(self, snapshot: PaymentMethodSnapshot | None) -> None:
        self.payment_method_snapshot = snapshot
        self.updated_at = _utcnow()
