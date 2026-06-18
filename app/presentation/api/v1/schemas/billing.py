from datetime import datetime

from pydantic import BaseModel, HttpUrl


class CreateCheckoutSessionRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: HttpUrl


class StripeWebhookResponse(BaseModel):
    received: bool


class SyncStripePricesResponse(BaseModel):
    synced_count: int


class SubscriptionRead(BaseModel):
    """
    DTO for subscription read - used for the frontend Dashboard
    """

    user_id: str
    plan: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_price_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    canceled_at: datetime | None = None
    amount: int | None = None
    currency: str | None = None

    model_config = {
        "from_attributes": True,
    }
