from pydantic import BaseModel, HttpUrl


class CreateCheckoutSessionRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: HttpUrl


class StripeWebhookResponse(BaseModel):
    received: bool


class SubscriptionRead(BaseModel):
    """
    DTO for subscription read - used for the frontend Dashboard
    """
    user_id: str
    plan: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None

    model_config = {
        "from_attributes": True,
    }
