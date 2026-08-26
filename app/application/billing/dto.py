from dataclasses import dataclass

from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.invoice import Invoice
from app.domain.billing.entities.subscription import Subscription


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


@dataclass(frozen=True)
class BillingAccountOverviewResult:
    subscription: Subscription
    billing_profile: BillingProfile | None
    billing_history: BillingHistoryResult
