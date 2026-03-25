import stripe
from fastapi import APIRouter, status, Depends, HTTPException, Header, Request

from app.application.billing.use_cases import CreateCheckoutSessionUseCase, HandleStripeWebhookUseCase
from app.core.dependency import get_create_checkout_session_use_case, get_handle_stripe_webhook_use_case, \
    get_billing_gateway
from app.presentation.api.v1.schemas.billing import CreateCheckoutSessionResponse, StripeWebhookResponse
from uuid import UUID
from app.presentation.security.deps import get_current_user_id

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
    payload: CreateCheckoutSessionResponse,
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post(
    "/webhook",
    summary="Stripe webhook",
    description="Stripe webhook",
    response_model=StripeWebhookResponse,
    response_description="Stripe webhook created",
)

async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    billing_gateway = Depends(get_billing_gateway),
    use_case: HandleStripeWebhookUseCase = Depends(get_handle_stripe_webhook_use_case),
):
    payload = await request.body()
    try:
        event = await billing_gateway.verify_and_construct_event(payload, stripe_signature)
        await use_case.execute(event)
        return StripeWebhookResponse(received=True)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe webhook signature verification failed.",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe payload."
        )
