import pytest

from app.application.billing.use_cases import SyncStripePricesUseCase
from app.domain.billing.entities.billing_price import BillingPrice
from app.domain.billing.enums import Plan


class FakeBillingGateway:
    def __init__(self, prices=None):
        self.prices = prices or []
        self.list_prices_called = False

    async def list_prices(self):
        self.list_prices_called = True
        return self.prices


class FakeBillingPriceRepository:
    def __init__(self):
        self.upserted = []

    async def upsert(self, price: BillingPrice) -> BillingPrice:
        self.upserted.append(price)
        return price

    async def get_active_by_plan(self, plan: Plan):
        return None


@pytest.mark.asyncio
async def test_sync_stripe_prices_upserts_valid_prices():
    gateway = FakeBillingGateway(
        prices=[
            {
                "stripe_price_id": "price_free",
                "stripe_product_id": "prod_free",
                "plan": "freemium",
                "currency": "chf",
                "amount": 0,
                "interval": "month",
                "active": True,
            },
            {
                "stripe_price_id": "price_pro",
                "stripe_product_id": "prod_pro",
                "plan": "pro",
                "currency": "chf",
                "amount": 2900,
                "interval": "month",
                "active": True,
            },
        ]
    )
    repo = FakeBillingPriceRepository()

    use_case = SyncStripePricesUseCase(
        billing_gateway=gateway,
        billing_price_repository=repo,
    )

    result = await use_case.execute()

    assert gateway.list_prices_called is True
    assert result == 2
    assert len(repo.upserted) == 2
    assert repo.upserted[0].plan == Plan.FREEMIUM
    assert repo.upserted[0].stripe_price_id == "price_free"
    assert repo.upserted[1].plan == Plan.PRO
    assert repo.upserted[1].stripe_price_id == "price_pro"


@pytest.mark.asyncio
async def test_sync_stripe_prices_ignores_unknown_plan():
    gateway = FakeBillingGateway(
        prices=[
            {
                "stripe_price_id": "price_unknown",
                "stripe_product_id": "prod_unknown",
                "plan": "unknown",
                "currency": "chf",
                "amount": 1000,
                "interval": "month",
                "active": True,
            }
        ]
    )
    repo = FakeBillingPriceRepository()

    use_case = SyncStripePricesUseCase(
        billing_gateway=gateway,
        billing_price_repository=repo,
    )

    result = await use_case.execute()

    assert result == 0
    assert repo.upserted == []
