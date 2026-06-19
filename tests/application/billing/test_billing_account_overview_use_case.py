from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.billing.dto import BillingAccountOverviewResult
from app.application.billing.use_cases import GetBillingAccountOverviewUseCase
from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.invoice import Invoice
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.common.exceptions import NotFoundError
from tests.fakes.billing.in_memory_billing_profile_repo import InMemoryBillingProfileRepository
from tests.fakes.billing.in_memory_subscription_repo import InMemorySubscriptionRepository


@dataclass
class _User:
    id: object
    stripe_customer_id: str | None


class FakeUserRepo:
    def __init__(self, user: _User | None):
        self.user = user

    async def get_by_id(self, user_id):
        return self.user


class FakeInvoiceRepo:
    def __init__(self, invoices: list[Invoice] | None = None):
        self.invoices = invoices or []

    async def get_by_stripe_customer_id(self, stripe_customer_id: str, limit: int = 50, offset: int = 0):
        invoices = [invoice for invoice in self.invoices if invoice.stripe_customer_id == stripe_customer_id]
        return invoices[offset : offset + limit]

    async def count_by_stripe_customer_id(self, stripe_customer_id: str) -> int:
        return sum(1 for invoice in self.invoices if invoice.stripe_customer_id == stripe_customer_id)


@pytest.mark.asyncio
async def test_get_billing_account_overview_returns_subscription_profile_and_history():
    user_id = uuid4()
    customer_id = "cus_123"
    issued_at = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)

    subscription = Subscription.create_freemium(
        user_id=user_id,
        stripe_customer_id=customer_id,
        stripe_subscription_id="sub_123",
    )
    profile = BillingProfile(
        user_id=user_id,
        stripe_customer_id=customer_id,
        contact_first_name="Ada",
        contact_last_name="Lovelace",
        contact_email="ada@example.com",
        billing_address=BillingAddress(
            line1="10 Downing St",
            city="London",
            postal_code="SW1A",
            country="GB",
        ),
        payment_method_snapshot=PaymentMethodSnapshot(
            stripe_payment_method_id="pm_123",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2027,
        ),
    )
    invoices = [
        Invoice(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_invoice_id="in_2",
            stripe_payment_id="pi_2",
            amount=2900,
            currency="eur",
            status="paid",
            date=issued_at,
            description="June invoice",
        ),
        Invoice(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_invoice_id="in_1",
            stripe_payment_id="pi_1",
            amount=1900,
            currency="eur",
            status="paid",
            date=issued_at.replace(hour=10),
            description="May invoice",
        ),
    ]

    uc = GetBillingAccountOverviewUseCase(
        user_repository=FakeUserRepo(_User(id=user_id, stripe_customer_id=customer_id)),
        subscription_repository=InMemorySubscriptionRepository(),
        billing_profile_repository=InMemoryBillingProfileRepository(),
        invoice_repository=FakeInvoiceRepo(invoices=invoices),
    )

    await uc.subscription_repository.create(subscription)
    await uc.billing_profile_repository.upsert(profile)

    result = await uc.execute(user_id=user_id, history_limit=1, history_offset=0)

    assert isinstance(result, BillingAccountOverviewResult)
    assert result.subscription.plan == Plan.FREEMIUM
    assert result.subscription.status == SubscriptionStatus.ACTIVE
    assert result.billing_profile is not None
    assert result.billing_profile.contact_full_name == "Ada Lovelace"
    assert result.billing_profile.payment_method_snapshot is not None
    assert result.billing_profile.payment_method_snapshot.masked_display == "visa •••• 4242"
    assert result.billing_history.total == 2
    assert result.billing_history.has_more is True
    assert result.billing_history.items[0].stripe_invoice_id == "in_2"


@pytest.mark.asyncio
async def test_get_billing_account_overview_returns_empty_history_without_customer_id():
    user_id = uuid4()
    subscription = Subscription.create_freemium(user_id=user_id)
    profile = BillingProfile(user_id=user_id)

    uc = GetBillingAccountOverviewUseCase(
        user_repository=FakeUserRepo(_User(id=user_id, stripe_customer_id=None)),
        subscription_repository=InMemorySubscriptionRepository(),
        billing_profile_repository=InMemoryBillingProfileRepository(),
        invoice_repository=FakeInvoiceRepo(),
    )

    await uc.subscription_repository.create(subscription)
    await uc.billing_profile_repository.upsert(profile)

    result = await uc.execute(user_id=user_id)

    assert result.billing_history.items == []
    assert result.billing_history.total == 0
    assert result.billing_history.has_more is False


@pytest.mark.asyncio
async def test_get_billing_account_overview_raises_when_user_missing():
    uc = GetBillingAccountOverviewUseCase(
        user_repository=FakeUserRepo(None),
        subscription_repository=InMemorySubscriptionRepository(),
        billing_profile_repository=InMemoryBillingProfileRepository(),
        invoice_repository=FakeInvoiceRepo(),
    )

    with pytest.raises(NotFoundError, match="User not found"):
        await uc.execute(user_id=uuid4())
