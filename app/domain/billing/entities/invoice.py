from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Invoice:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    stripe_customer_id: str | None = None
    stripe_invoice_id: str | None = None
    stripe_payment_id: str | None = None
    amount: int = 0
    currency: str = ""
    status: str = ""
    date: datetime = field(default_factory=lambda: datetime.now(UTC))
    due_date: datetime | None = None
    paid_at: datetime | None = None
    description: str | None = None
    hosted_invoice_url: str | None = None

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be a positive integer")
        if not self.currency or len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be an ISO 4217 code")
        if self.date.tzinfo is None or self.date.utcoffset() is None:
            raise ValueError("date must be timezone-aware")
        if self.due_date is not None and (self.due_date.tzinfo is None or self.due_date.utcoffset() is None):
            raise ValueError("due_date must be timezone-aware")
        if self.paid_at is not None and (self.paid_at.tzinfo is None or self.paid_at.utcoffset() is None):
            raise ValueError("paid_at must be timezone-aware")

    def is_paid(self) -> bool:
        return self.status.lower() == "paid"

    def days_since_issue(self, reference: datetime | None = None) -> int:
        ref = reference or datetime.now(self.date.tzinfo or UTC)
        return (ref.date() - self.date.date()).days

    def get_display_amount(self) -> float:
        return self.amount / 100
