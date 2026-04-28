from pydantic import BaseModel, HttpUrl


class CreateCheckoutSessionRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    checkout_url: HttpUrl


class StripeWebhookResponse(BaseModel):
    received: bool
