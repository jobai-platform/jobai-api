from uuid import UUID

from app.application.billing.dto import CheckoutSessionResult
from app.application.billing.ports import SubscriptionRepository, BillingGateway
from app.application.users.ports import UserRepository
from app.domain.billing.entities import Subscription
from app.domain.billing.enums import SubscriptionPlan, SubscriptionStatus
from app.domain.billing.services import map_stripe_subscription_status


class AssignFreemiumOnSignupUseCase:
    """
    Use case for assigning a freemium subscription to a user on signup.
    """
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def execute(self, user_id: UUID) -> Subscription:
        """
        Execute assignment of freemium subscription to user on signup.
        :param user_id: User ID.
        :return: Subscription.
        """
        existing_subscription = await self.subscription_repository.get_by_user_id(user_id)
        if existing_subscription:
            return existing_subscription

        subscription = Subscription.create_freemium(user_id=user_id)
        return await self.subscription_repository.create(subscription)


class CreateCheckoutSessionUseCase:
    """
    Use case for creating a checkout session.
    """
    def __init__(
        self,
        user_repository: UserRepository,
        billing_gateway: BillingGateway,
    ):
        self.user_repository = user_repository
        self.billing_gateway = billing_gateway

    async def execute(
        self,
        user_id: UUID,
        target_plan: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult:
        """
        Create checkout session.
        :param user_id: User ID.
        :param target_plan: Target plan.
        :param success_url: Success URL.
        :param cancel_url: Cancel URL.
        :return: CheckoutSessionResult.
        """
        if target_plan == SubscriptionPlan.FREEMIUM.value:
            raise ValueError("Cannot create checkout session for freemium plan.")

        try:
            plan = SubscriptionPlan(target_plan)
        except ValueError as exception:
            raise ValueError("Invalid subscription plan.") from exception

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")

        checkout_url = self.billing_gateway.create_checkout_session(
            email=user.email,
            user_id=user.id,
            plan=plan.value,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CheckoutSessionResult(checkout_url=checkout_url)


class HandleStripeWebhookUseCase:
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def execute(self, event: dict) -> None:
        event_type = event.get("type")
        data = event.get("data", {})
        obj = data.get("object", {})

        if event_type == "checkout.session.completed":
            await self._handle_checkout_session_completed(obj)
            return

        if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            await self._handle_subscription_created_or_updated(obj)
            return

        if event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(obj)
            return

    async def _handle_checkout_session_completed(self, obj: dict) -> None:
        metadata = obj.get("metadata", {})
        user_id_raw = metadata.get("user_id")
        plan_raw = metadata.get("plan")

        if not user_id_raw or not plan_raw:
            return

        user_id = UUID(user_id_raw)
        plan = SubscriptionPlan(plan_raw)

        subscription = await self.subscription_repository.get_by_user_id(user_id)
        if not subscription:
            subscription = Subscription.create_freemium(user_id=user_id)
            subscription.assign_paid_plan(
                plan=plan,
                stripe_customer_id=obj.get("customer"),
                stripe_subscription_id=obj.get("subscription"),
                status=SubscriptionStatus.PENDING,
            )
            await self.subscription_repository.create(subscription)
            return

        subscription.assign_paid_plan(
            plan=plan,
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("subscription"),
            status=SubscriptionStatus.PENDING,
        )
        await self.subscription_repository.update(subscription)

    async def _handle_subscription_update(self, obg: dict) -> None:
        stripe_subscription_id = obg.get("id")
        if not stripe_subscription_id:
            return

        subscription = await self.subscription_repository.get_by_stripe_subscription_id(stripe_subscription_id)
        if not subscription:
            return

        stripe_status = obg.get("status", "incomplete")
        subscription.update_status(map_stripe_subscription_status(stripe_status))
        await self.subscription_repository.update(subscription)

    async def _handle_subscription_deleted(self, obj: dict) -> None:
        stripe_subscription_id = obj.get("id")
        if not stripe_subscription_id:
            return

        subscription = await self.subscription_repository.get_by_stripe_subscription_id(stripe_subscription_id)
        if not subscription:
            return

        subscription.update_status(SubscriptionStatus.CANCELED)
        await self.subscription_repository.update(subscription.user_id, subscription)
















