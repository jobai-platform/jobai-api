import logging
from uuid import UUID

import stripe

from app.application.billing.ports import BillingGateway
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeGateway(BillingGateway):
    """
    Adapt Stripe for the BillingGateway port.

    Stripe is the source of truth for pricing:
    Price IDs are resolved dynamically via lookup keys
    configured in the Stripe Dashboard (and mapped via environment variables).
    This allows you to switch environments (test ↔ production) solely
    via the .env file without modifying the code.
    """
    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_API_KEY
        self.webhook_secret =  settings.STRIPE_WEBHOOK_SECRET
        self.plan_lookup_keys = {
            "pro": settings.STRIPE_PRO_PLAN_LOOKUP_KEY,
            "enterprise": settings.STRIPE_ENTERPRISE_PLAN_LOOKUP_KEY,
        }

    async def create_checkout_session(
        self,
        *,
        email: str,
        user_id: UUID,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe checkout session.

        The prices as fetched from the Stripe API.
        This guarantees that the correct price is always used based on the lookup key, and allows switching environments without code changes.
        :param email: User email.
        :param user_id: User ID.
        :param plan: Target plan.
        :param success_url: Success URL.
        :param cancel_url: Cancel URL.
        :return: Checkout session URL.
        """
        lookup_key = self.plan_lookup_keys.get(plan)
        if not lookup_key:
            raise ValueError(f"Unsupported plan: '{plan}'. Supported plans: {list(self.plan_lookup_keys.keys())}")

        # Dynamic price from Stripe
        prices = stripe.Price.list(
            lookup_key=[lookup_key],
            active=True,
            limit=1,
        )
        if not prices.data:
            raise ValueError(
                f"No active price found for plan: {plan}",
                f"(lookup_key {lookup_key}) has no active prices)",
                f"Verify the Dashboard Stripe."
            )

        price_id = prices.data[0].id
        logger.info(f"Stripe price resolved: plan=%s lookup_key=%s price_id=%s", plan, lookup_key, price_id)

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=email,
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                metadata={
                    "user_id": str(user_id),
                    "plan": plan,
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except stripe.StripeError as exc:
            logger.error("Stripe checkout session creation failed: %s", exc)
            raise RuntimeError(f"Failed to create Stripe checkout session: {exc}") from exc

        return session.url


    async def create_customer(self, email: str, user_id: UUID) -> str:
        """
        Create a Stripe customer.
        :param email: User email.
        :param user_id: User ID.
        :return: Stripe customer ID.
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={
                    "user_id": str(user_id),
                },
            )
            return customer.id
        except Exception as e:
            raise RuntimeError(f"Failed to create Stripe customer: {str(e)}")


    async def verify_and_construct_event(self, payload: bytes, signature: str) -> dict:
        """
        Verify the Stripe webhook signature and construct the event.
        If invalid signature is found, raise an exception.
        :param payload: Raw request body.
        :param signature: Stripe signature from headers.
        :return: Constructed event dictionary.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self.webhook_secret,
            )
            return dict(event)
        except stripe.SignatureVerificationError as exc:
            logger.error("Stripe webhook signature verification failed: %s", exc)
            raise RuntimeError("Invalid Stripe webhook signature") from exc
        except Exception as exc:
            logger.error("Failed to construct Stripe event: %s", exc)
            raise RuntimeError(f"Failed to construct Stripe event: {exc}") from exc
