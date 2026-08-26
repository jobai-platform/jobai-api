from uuid import uuid4

import pytest

from app.application.billing.use_cases import GetBillingProfileUseCase
from app.domain.billing.entities.billing_address import BillingAddress
from app.domain.billing.entities.billing_profile import BillingProfile
from app.domain.billing.entities.payment_method_snapshot import PaymentMethodSnapshot
from tests.fakes.billing.in_memory_billing_profile_repo import InMemoryBillingProfileRepository


@pytest.mark.asyncio
async def test_get_billing_profile_returns_profile_when_present() -> None:
    user_id = uuid4()
    profile = BillingProfile(
        user_id=user_id,
        stripe_customer_id="cus_123",
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
            holder_name="Ada Lovelace",
            country="GB",
            funding="credit",
        ),
    )

    repo = InMemoryBillingProfileRepository()
    await repo.upsert(profile)
    use_case = GetBillingProfileUseCase(billing_profile_repository=repo)

    result = await use_case.execute(user_id=user_id)

    assert result is not None
    assert result.stripe_customer_id == "cus_123"
    assert result.payment_method_snapshot is not None
    assert result.payment_method_snapshot.masked_display == "visa •••• 4242"


@pytest.mark.asyncio
async def test_get_billing_profile_returns_none_when_missing() -> None:
    use_case = GetBillingProfileUseCase(billing_profile_repository=InMemoryBillingProfileRepository())

    result = await use_case.execute(user_id=uuid4())

    assert result is None
