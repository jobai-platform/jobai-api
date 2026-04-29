import logging
from uuid import UUID

from app.application.billing.dto import CheckoutSessionResult
from app.application.billing.ports import SubscriptionRepository, BillingGateway
from app.application.users.ports import UserRepository
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.billing.services import map_stripe_subscription_status

logger = logging.getLogger(__name__)


class AssignFreemiumOnSignupUseCase:
    """
    Use case for assigning a freemium subscription to a user on signup.
    If the user already has a subscription (e.g. from a previous signup), it will be returned instead of creating a new one.
    """
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def execute(self, user_id: UUID) -> Subscription:
        existing = await self.subscription_repository.get_by_user_id(user_id)
        if existing:
            return existing

        subscription = Subscription.create_freemium(user_id=user_id)
        return await self.subscription_repository.create(subscription)


class CreateCheckoutSessionUseCase:
    """
    Create a checkout session for a user to upgrade to a paid plan.
    """
    def __init__(
        self,
        user_repository: UserRepository,
        billing_gateway: BillingGateway,
    ) -> None:
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
        if target_plan == Plan.FREEMIUM.value:
            raise ValueError("Cannot create checkout session for freemium plan.")

        try:
            plan = Plan(target_plan)
        except ValueError as exc:
            raise ValueError(f"Invalid subscription plan: '{target_plan}.'") from exc

        # Fetch user to get email for Stripe and to verify existence before creating checkout session
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")

        checkout_url = await self.billing_gateway.create_checkout_session(
            email=str(user.email),
            user_id=user.id,
            plan=plan.value,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CheckoutSessionResult(checkout_url=checkout_url)


class HandleStripeWebhookUseCase:
    """
    Handle Stripe webhook requests.
    Managed events:
    - checkout.session.completed      → assign_paid_plan (PENDING)
    - customer.subscription.created   → update_status depuis Stripe
    - customer.subscription.updated   → update_status depuis Stripe
    - customer.subscription.deleted   → CANCELED
    """
    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    async def execute(self, event: dict) -> None:
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})

        logger.info(f"Handling Stripe webhook event: type={event_type} object_id={obj.get('id')}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_session_completed(obj)

        elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            await self._handle_subscription_update(obj)

        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(obj)
        else:
            logger.debug("Stripe webhook event ignored: type=%s", event_type)

    # -------------------------------------------------------------------------
    # Private handlers
    # -------------------------------------------------------------------------
    async def _handle_checkout_session_completed(self, obj: dict) -> None:
        """
        checkout.session.completed: the initial payment has ok.
        In this event, we assign the paid plan to the user with a PENDING status, waiting for the subscription.created or subscription.updated event from Stripe to update the status to ACTIVE or other.
        :param obj: Stripe event object (checkout.session.completed).
        :return: None
        """
        metadata = obj.get("metadata", {})
        user_id_raw = metadata.get("user_id")
        plan_raw = metadata.get("plan")

        if not user_id_raw or not plan_raw:
            logger.warning(
                "checkout.session.completed: missing metadata: user_id=%s, plan=%s",
                user_id_raw,
                plan_raw,
            )
            return

        user_id = UUID(user_id_raw)
        try:
            plan = Plan(plan_raw)
        except ValueError:
            logger.error("checkout.session.completed: invalid plan in metadata: %s", plan_raw)
            return

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
            logger.info("Subscription created for user_id=%s, plan=%s", user_id, plan)
        else:
            subscription.assign_paid_plan(
                plan=plan,
                stripe_customer_id=obj.get("customer"),
                stripe_subscription_id=obj.get("subscription"),
                status=SubscriptionStatus.PENDING,
            )
            await self.subscription_repository.update(subscription)
            logger.info("Subscription updated for user_id=%s, plan=%s", user_id, plan)

    async def _handle_subscription_update(self, obg: dict) -> None:
        """
        customer.subscription.created or customer.subscription.updated: the subscription status has changed in Stripe, we update it in our database.
        :param obg: Stripe event object (checkout.session.completed).
        :return: None
        """
        stripe_subscription_id = obg.get("id")
        if not stripe_subscription_id:
            return

        subscription = await self.subscription_repository.get_by_stripe_subscription_id(
            stripe_subscription_id
        )
        if not subscription:
            logger.warning("Subscription update received for unknown subscription: stripe_subscription_id=%s", stripe_subscription_id)
            return

        stripe_status = obg.get("status", "incomplete")
        new_status = map_stripe_subscription_status(stripe_status)
        subscription.update_status(new_status)
        await self.subscription_repository.update(subscription)
        logger.info(
            "Subscription updated for user_id=%s, plan=%s, status=%s",
            stripe_subscription_id,
            new_status,
        )

    async def _handle_subscription_deleted(self, obj: dict) -> None:
        """
        customer.subscription.deleted: the subscription status has changed in Stripe, we update it in our database.
        :param obj: Stripe event object (customer.subscription.deleted).
        :return: None
        """
        stripe_subscription_id = obj.get("id")
        if not stripe_subscription_id:
            return

        subscription = await self.subscription_repository.get_by_stripe_subscription_id(
            stripe_subscription_id
        )
        if not subscription:
            logger.warning("Subscription deletion received for unknown subscription: stripe_subscription_id=%s", stripe_subscription_id)
            return

        subscription.update_status(SubscriptionStatus.CANCELED)
        await self.subscription_repository.update(subscription.user_id, subscription)
        logger.info("Subscription updated for user_id=%s, plan=%s", stripe_subscription_id, subscription.plan)
