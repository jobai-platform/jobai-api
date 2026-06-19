from dataclasses import dataclass
from app.domain.billing.entities.invoice import Invoice


@dataclass(frozen=True)
class CheckoutSessionResult:
    checkout_url: str


@dataclass(frozen=True)
class BillingHistoryResult:
    items: list[Invoice]
    total: int
    limit: int
    offset: int
    has_more: bool
