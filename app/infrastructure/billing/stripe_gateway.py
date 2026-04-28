from uuid import UUID

import stripe

from app.application.billing.ports import BillingGateway
from app.core.config import settings


class StripeGateway(BillingGateway):
    """
    Stripe billing gateway implementation.
    """
    def __init__(self, stripe_client) -> None:
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
        :param email: User email.
        :param user_id: User ID.
        :param plan: Target plan.
        :param success_url: Success URL.
        :param cancel_url: Cancel URL.
        :return: Checkout session URL.
        """
        lookup_key = self.plan_lookup_keys.get(plan)
        if not lookup_key:
            raise ValueError(f"Unsupported plan: {plan}")

        prices = stripe.Price.list(
            lookup_key=[lookup_key],
            active=True,
            limit=1,
        )
        if not prices.data:
            raise ValueError(f"No active price found for plan: {plan}")

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=email,
                line_items=[{
                    "price": prices.data[0].id,
                    "quantity": 1,
                }],
                metadata={
                    "user_id": str(user_id),
                    "plan": plan,
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session.url
        except Exception as e:
            raise RuntimeError(f"Failed to create Stripe checkout session: {str(e)}")

    async def verify_and_construct_event(self, payload: bytes, signature: str) -> dict:
        """
        Verify the Stripe webhook signature and construct the event.
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
            return event
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid Stripe webhook signature: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to construct Stripe event: {str(e)}")
