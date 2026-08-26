from datetime import datetime

from pydantic import BaseModel, HttpUrl


class BillingAddressRead(BaseModel):
    line1: str
    line2: str | None = None
    city: str
    state: str | None = None
    postal_code: str
    country: str

    model_config = {
        "from_attributes": True,
    }


class PaymentMethodSnapshotRead(BaseModel):
    stripe_payment_method_id: str | None = None
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    holder_name: str | None = None
    country: str | None = None
    funding: str | None = None
    wallet: str | None = None
    masked_display: str
    expiry_display: str

    model_config = {
        "from_attributes": True,
    }


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


class InvoiceRead(BaseModel):
    date: datetime | None = None
    amount: int | None = None
    currency: str | None = None
    status: str | None = None
    stripe_invoice_id: str | None = None
    stripe_payment_id: str | None = None
    description: str | None = None
    hosted_invoice_url: str | None = None

    model_config = {
        "from_attributes": True,
    }


class BillingHistoryRead(BaseModel):
    items: list[InvoiceRead]
    total: int
    limit: int
    offset: int
    has_more: bool

    model_config = {
        "from_attributes": True,
    }


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


class BillingProfileRead(BaseModel):
    user_id: str
    stripe_customer_id: str | None = None
    contact_first_name: str | None = None
    contact_last_name: str | None = None
    contact_email: str | None = None
    contact_full_name: str | None = None
    billing_address: BillingAddressRead | None = None
    payment_method_snapshot: PaymentMethodSnapshotRead | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }
