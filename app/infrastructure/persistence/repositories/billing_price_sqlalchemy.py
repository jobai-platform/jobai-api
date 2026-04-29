import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import BillingPriceRepository
from app.domain.billing.entities.billing_price import BillingPrice
from app.domain.billing.enums import Plan
from app.infrastructure.persistence.models.billing_price import BillingPriceModel

logger = logging.getLogger(__name__)


def _to_domain(model: BillingPriceModel) -> BillingPrice:
    return BillingPrice(
        id=UUID(str(model.id)),
        plan=Plan(model.plan),
        stripe_price_id=model.stripe_price_id,
        stripe_product_id=model.stripe_product_id,
        currency=model.currency,
        amount=float(model.amount),
        interval=model.interval,
        active=model.active,
    )


class BillingPriceSQLAlchemyRepository(BillingPriceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, price: BillingPrice) -> BillingPrice:
        stmt = (
            insert(BillingPriceModel)
            .values(
                plan=price.plan.value,
                stripe_price_id=price.stripe_price_id,
                stripe_product_id=price.stripe_product_id,
                currency=price.currency,
                amount=int(price.amount),
                interval=price.interval,
                active=price.active,
            )
            .on_conflict_do_update(
                constraint="uq_billing_prices_stripe_price_id",
                set_={
                    "plan": price.plan.value,
                    "stripe_product_id": price.stripe_product_id,
                    "currency": price.currency,
                    "amount": int(price.amount),
                    "interval": price.interval,
                    "active": price.active,
                    "updated_at": "now()",
                },
            )
            .returning(BillingPriceModel)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        model = result.scalar_one()
        logger.info("BillingPrice upserted: stripe_price_id=%s, plan=%s", price.stripe_price_id, price.plan)
        return _to_domain(model)

    async def get_active_by_plan(self, plan: Plan) -> Optional[BillingPrice]:
        stmt = select(BillingPriceModel).where(
            BillingPriceModel.plan == plan.value,
            BillingPriceModel.active.is_(True),
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None
