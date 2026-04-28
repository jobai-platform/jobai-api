from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import SubscriptionRepository
from app.domain.billing.entities import Subscription
from app.domain.billing.enums import SubscriptionPlan, SubscriptionStatus
from app.infrastructure.persistence.models.subscription import SubscriptionModel


class SubscriptionSQLAlchemyRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)


    @staticmethod
    def _to_domain(model: SubscriptionModel) -> Subscription:
        return Subscription(
            user_id=UUID(model.user_id),
            plan=SubscriptionPlan(model.plan),
            status=SubscriptionStatus(model.status),
            stripe_customer_id=model.stripe_customer_id,
            stripe_subscription_id=model.stripe_subscription_id,
        )
