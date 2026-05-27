import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import SubscriptionRepository
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.infrastructure.persistence.models.subscription import SubscriptionModel

logger = logging.getLogger(__name__)


def _to_domain(model: SubscriptionModel) -> Subscription:
    return Subscription(
        user_id=UUID(str(model.user_id)),
        plan=Plan(model.plan),
        status=SubscriptionStatus(model.status),
        stripe_customer_id=model.stripe_customer_id,
        stripe_subscription_id=model.stripe_subscription_id,
        billing_price_id=UUID(str(model.billing_price_id)) if model.billing_price_id else None,
    )


class SubscriptionSQLAlchemyRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == str(user_id))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.stripe_subscription_id == stripe_subscription_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def create(self, subscription: Subscription) -> Subscription:
        model = SubscriptionModel(
            user_id=str(subscription.user_id),
            plan=subscription.plan.value,
            status=subscription.status.value,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_subscription_id=subscription.stripe_subscription_id,
            billing_price_id=str(subscription.billing_price_id) if subscription.billing_price_id else None,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return _to_domain(model)

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.user_id == str(subscription.user_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            logger.warning("Subscription update failed: not found for user_id=%s", subscription.user_id)
            return None

        model.plan = subscription.plan.value
        model.status = subscription.status.value
        model.stripe_customer_id = subscription.stripe_customer_id
        model.stripe_subscription_id = subscription.stripe_subscription_id
        model.billing_price_id = str(subscription.billing_price_id) if subscription.billing_price_id else None
        await self.session.commit()
        await self.session.refresh(model)
        logger.info(
            "Subscription updated: user_id=%s, plan=%s, status=%s",
            subscription.user_id,
            subscription.plan,
            subscription.status,
        )
        return _to_domain(model)
