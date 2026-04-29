import logging
from uuid import UUID

from app.application.billing.dto import CheckoutSessionResult
from app.application.billing.ports import BillingGateway, BillingPriceRepository, SubscriptionRepository
from app.domain.billing.entities.billing_price import BillingPrice
from app.application.users.ports import UserRepository
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.billing.services import map_stripe_subscription_status

logger = logging.getLogger(__name__)


class AssignFreemiumOnSignupUseCase:
    """
    Use case for assigning a freemium subscription to a user on signup.
    If the user already has a subscription (e.g. from a previous signup), it will be returned instead of creating a new one.
    - Create Stripe customer
    - Create Stripe Freemium subscription
    - Create local subscription linked to BillingPrice
    """
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        user_repository: UserRepository,
        billing_price_repository: BillingPriceRepository,
        billing_gateway: BillingGateway,
    ):
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.billing_price_repository = billing_price_repository
        self.billing_gateway = billing_gateway

    async def execute(self, user_id: UUID) -> Subscription:
        existing = await self.subscription_repository.get_by_user_id(user_id)
        if existing:
            return existing

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error("User not found for ID: %s. Cannot assign freemium subscription.", user_id)
            raise ValueError("User not found. Cannot assign freemium subscription.")

        freemium_price = await self.billing_price_repository.get_active_by_plan(Plan.FREEMIUM)
        if not freemium_price:
            logger.error("Freemium price not found in database. Cannot assign freemium subscription.")
            raise ValueError("Freemium price not found. Please contact support.")

        stripe_customer_id = await self.billing_gateway.create_customer(
            email=str(user.email),
            user_id=user.id
        )

        stripe_subscription_id = await self.billing_gateway.create_subscription(
            customer_id=stripe_customer_id,
            stripe_price_id=freemium_price.stripe_price_id,
            user_id=user.id,
            plan=Plan.FREEMIUM,
        )


        subscription = Subscription.create_freemium(
            user_id=user.id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            billing_price_id=freemium_price.id,
        )

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
            logger.info("Target plan is freemium. Cannot create checkout session.")
            raise ValueError("Cannot create checkout session for freemium plan.")

        try:
            plan = Plan(target_plan)
        except ValueError as exc:
            logger.error(exc)
            raise ValueError(f"Invalid subscription plan: '{target_plan}.'") from exc

        # Fetch user to get email for Stripe and to verify existence before creating checkout session
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error("User not found for ID: %s. Cannot create checkout session.", user_id)
            raise ValueError("User not found.")

        checkout_url = await self.billing_gateway.create_checkout_session(
            email=str(user.email),
            user_id=user.id,
            plan=plan.value,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CheckoutSessionResult(checkout_url=checkout_url)


class SyncStripePricesUseCase:
    """
    Synchronize Stripe prices into database.
    Stripe Product or Price metadata must contain:
    plan=freemium
    plan=pro
    plan=enterprise
    """
    def __init__(
        self,
        billing_gateway: BillingGateway,
        billing_price_repository: BillingPriceRepository,
    ) -> None:
        self.billing_gateway = billing_gateway
        self.billing_price_repository = billing_price_repository

    async def execute(self) -> int:
        raw_prices = await self.billing_gateway.list_prices()
        synced_count = 0
        for raw_price in raw_prices:
            plan_raw = raw_price.get("plan")

            try:
                plan = Plan(plan_raw)
            except ValueError:
                logger.warning(
                    "Skipping Stripe price with invalid or missing plan metadata: %s",
                    raw_price.get("stripe_price_id"),
                )
                continue

            price = BillingPrice.create(
                plan=plan,
                stripe_price_id=raw_price["stripe_price_id"],
                stripe_product_id=raw_price["stripe_product_id"],
                currency=raw_price["currency"],
                amount=raw_price["amount"],
                interval=raw_price["interval"],
                active=raw_price["active"],
            )

            await self.billing_price_repository.upsert(price)
            synced_count += 1

        return synced_count


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

    async def _handle_subscription_update(self, obj: dict) -> None:
        """
        customer.subscription.created or customer.subscription.updated: the subscription status has changed in Stripe, we update it in our database.
        :param obj: Stripe event object (customer.subscription.created/updated).
        :return: None
        """
        stripe_subscription_id = obj.get("id")
        if not stripe_subscription_id:
            return

        subscription = await self.subscription_repository.get_by_stripe_subscription_id(
            stripe_subscription_id
        )
        if not subscription:
            logger.warning("Subscription update received for unknown subscription: stripe_subscription_id=%s", stripe_subscription_id)
            return

        stripe_status = obj.get("status", "incomplete")
        new_status = map_stripe_subscription_status(stripe_status)
        subscription.update_status(new_status)
        await self.subscription_repository.update(subscription)
        logger.info(
            "Subscription status updated: stripe_subscription_id=%s, new_status=%s",
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
        await self.subscription_repository.update(subscription)
        logger.info("Subscription canceled: stripe_subscription_id=%s, user_id=%s", stripe_subscription_id, subscription.user_id)
