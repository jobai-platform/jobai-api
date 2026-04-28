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
    """
    MMapping ORM model to domain entity.
    :param model: Subscription model.
    :return: Subscription domain entity.
    """
    return Subscription(
        user_id=UUID(model.user_id),
        plan=Plan(model.plan),
        status=SubscriptionStatus(model.status),
        stripe_customer_id=model.stripe_customer_id,
        stripe_subscription_id=model.stripe_subscription_id,
    )


class SubscriptionSQLAlchemyRepository(SubscriptionRepository):
    """
    Implementation of SQLAlchemy subscription repository.
    """
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_stripe_customer_id(self, user_id: UUID) -> Optional[Subscription]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
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
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_domain(model)

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        """
        Update subscription status and stripe_customer_id.
        :param subscription: Subscription model.
        :return: Updated subscription domain entity or None if not found.
        """
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.user_id == str(subscription.user_id)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            logger.warning("Subscription update failed: subscription not found for user_id=%s", subscription.user_id)
            return None

        model.plan = subscription.plan.value
        model.status = subscription.status.value
        model.stripe_customer_id = subscription.stripe_customer_id
        model.stripe_subscription_id = subscription.stripe_subscription_id
        await self.session.commit()
        await self.session.refresh(model)
        logger.info(
            "Subscription updated: user_id=%s, plan=%s, status=%s, stripe_customer_id=%s",
            subscription.user_id,
            subscription.plan,
            subscription.status,
            subscription.stripe_customer_id,
        )
        return _to_domain(model)

    # async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
    #     stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
    #     result = await self.session.execute(stmt)
    #     model = result.scalar_one_or_none()
    #     if not model:
    #         return None
    #     return self._to_domain(model)
