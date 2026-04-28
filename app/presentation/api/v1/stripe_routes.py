import logging

from fastapi import APIRouter, status, Depends, HTTPException, Header, Request

from app.application.billing.ports import BillingGateway
from app.application.billing.use_cases import CreateCheckoutSessionUseCase, HandleStripeWebhookUseCase
from app.core.dependency import get_create_checkout_session_use_case, get_handle_stripe_webhook_use_case, \
    get_billing_gateway
from app.presentation.api.v1.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    StripeWebhookResponse,
)
from uuid import UUID
from app.presentation.security.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["Stripe"])

@router.post(
    "/checkout-session",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Stripe checkout session",
    description="Stripe checkout session",
    response_model=CreateCheckoutSessionResponse,
    response_description="Checkout session created",
)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    use_case: CreateCheckoutSessionUseCase = Depends(get_create_checkout_session_use_case),
):
    try:
        result = await use_case.execute(
            user_id=current_user_id,
            target_plan=payload.plan,
            success_url=str(payload.success_url),
            cancel_url=str(payload.cancel_url),
        )
        return CreateCheckoutSessionResponse(checkout_url=result.checkout_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        logger.error(f"Error creating checkout session for user {current_user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with billing gateway. Please try again later."
        ) from exc

@router.post(
    "/webhook",
    summary="Stripe webhook",
    description=(
        "Stripe webhook endpoint"
        "The signature has verified using the Stripe library to ensure authenticity. The payload is then processed by the HandleStripeWebhookUseCase, which updates subscription statuses based on the event type (e.g., payment succeeded, subscription updated)."
        "customer.subscription.created/updated/deleted."
    ),
    response_model=StripeWebhookResponse,
    response_description="Stripe webhook created",
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    billing_gateway: BillingGateway = Depends(get_billing_gateway),
    use_case: HandleStripeWebhookUseCase = Depends(get_handle_stripe_webhook_use_case),
):
    try:
        event = await billing_gateway.verify_and_construct_event(payload, stripe_signature)
    except ValueError as exc:
        """Signature invalid or bad payload received."""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe payload."
        ) from exc
    try:
        await use_case.execute(event)
    except Exception as exc:
        logger.error(f"Error processing Stripe webhook event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing Stripe webhook event."
        ) from exc

    return StripeWebhookResponse(received=True)
