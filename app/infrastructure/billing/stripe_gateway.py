import asyncio
import logging
from typing import List
from uuid import UUID

import stripe

from app.application.billing.ports import BillingGateway
from app.core.config import settings
from app.domain.billing.enums import Plan

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

        try:
            price_id = await self._resolve_price_id_by_lookup_key(lookup_key)

            def _create_session():
                return stripe.checkout.Session.create(
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
                    subscription_data={
                        "metadata": {
                            "user_id": str(user_id),
                            "plan": plan,
                        }
                    },
                    success_url=success_url,
                    cancel_url=cancel_url,
                )

            session = await asyncio.to_thread(_create_session)

        except stripe.error.CardError as exc:
            logger.error(f"Failed to create Stripe checkout session: {exc}")
            raise RuntimeError(f"Failed to create Stripe checkout session: {exc}") from exc

        if not session.url:
            logger.error("Stripe checkout session created but no URL returned: %s", session)
            raise RuntimeError("Stripe checkout session created but no URL returned")

        return session.url

    async def create_customer(
        self,
        *,
        email: str,
        user_id: UUID
    ) -> str:
        """
        Create a Stripe customer.
        :param email: User email.
        :param user_id: User ID.
        :return: Stripe customer ID.
        """
        try:
            def _create_customer():
                return stripe.Customer.create(
                    email=email,
                    metadata={
                        "user_id": str(user_id)
                    },
                )
            customer = await asyncio.to_thread(_create_customer)
            return customer.id
        except stripe.StripeError as exc:
            logger.error("Stripe customer creation failed: %s", exc)
            raise RuntimeError(f"Failed to create Stripe customer: {exc}") from exc


    async def create_subscription(
        self,
        *,
        customer_id: str,
        stripe_price_id: str,
        user_id: UUID,
        plan: Plan,
    ) -> str:
        """
        Create a Stripe subscription.
        :param customer_id: Stripe customer ID.
        :param stripe_price_id: Stripe price ID.
        :param user_id: User ID.
        :param plan: Target plan.
        :return: Stripe subscription ID.
        """
        try:
            def _create_subscription():
                return stripe.Subscription.create(
                    customer=customer_id,
                    items=[{
                        "price": stripe_price_id,
                        "quantity": 1,
                    }],
                    metadata={
                        "user_id": str(user_id),
                        "plan": plan.value,
                        "source": "jobai_signup",
                    }
                )
            subscription = await asyncio.to_thread(_create_subscription)
            return subscription.id
        except stripe.StripeError as exc:
            logger.error("Stripe subscription creation failed: %s", exc)
            raise RuntimeError(f"Failed to create Stripe subscription: {exc}") from exc

    async def list_prices(self) -> list[dict]:
        """
        List active Stripe prices.
        :return: List of price dictionaries.
        """
        try:
            def _list_prices():
                return stripe.Price.list(
                    active=True,
                    expand=["data.product"],
                    limit=20,
                )
            response = await asyncio.to_thread(_list_prices)
        except stripe.StripeError as exc:
            logger.error("Stripe price listing failed: %s", exc)
            raise RuntimeError(f"Failed to list Stripe prices: {exc}") from exc

        prices: List[dict] = []

        for price in response.data:
            product = price.product

            product_metadata = getattr(product, "metadata", {}) or {}
            price_metadata = getattr(price, "metadata", {}) or {}

            plan = price_metadata.get("plan") or product_metadata.get("plan")

            recurring = getattr(price, "recurring", None)
            interval = recurring.get("interval") or price_metadata.get("interval")

            stripe_product_id = product.id if hasattr(product, "id") else price.product

            prices.append({
                "stripe_price_id": price.id,
                "stripe_product_id": stripe_product_id,
                "plan": plan,
                "currency": price.currency,
                "amount": price.unit_amount or 0,
                "interval": interval,
                "active": price.active,
            })

        return prices


    async def verify_and_construct_event(
        self,
        payload: bytes,
        signature: str
    ) -> dict:
        """
        Verify the Stripe webhook signature and construct the event.
        If invalid signature is found, raise an exception.
        :param payload: Raw request body.
        :param signature: Stripe signature from headers.
        :return: Constructed event dictionary.
        """
        try:
            def _construct_event():
                return stripe.Webhook.construct_event(
                    payload=payload,
                    sig_header=signature,
                    secret=self.webhook_secret,
                )

            event = await asyncio.to_thread(_construct_event)
            return dict(event)

        except stripe.error.SignatureVerificationError as exc:
            logger.error("Stripe webhook signature verification failed: %s", exc)
            raise RuntimeError(f"Invalid Stripe webhook signature: {exc}") from exc
        except stripe.StripeError as exc:
            logger.error("Failed to construct Stripe event: %s", exc)
            raise RuntimeError(f"Failed to construct Stripe event: {exc}") from exc

    async def _resolve_price_id_by_lookup_key(self, lookup_key: str) -> str:
        def _list_prices():
            return stripe.Price.list(
                lookup_keys=[lookup_key],
                active=True,
                limit=1,
            )

        prices = await asyncio.to_thread(_list_prices)

        if not prices.data:
            raise ValueError(
                f"No active price found for lookup_key={lookup_key}. "
                "Verify the Stripe Dashboard."
            )

        price_id = prices.data[0].id
        logger.info(
            "Stripe price resolved: lookup_key=%s price_id=%s",
            lookup_key,
            price_id,
        )
        return price_id
