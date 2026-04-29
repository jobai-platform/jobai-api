import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.application.billing.ports import BillingGateway
from app.application.billing.use_cases import (
    CreateCheckoutSessionUseCase,
    HandleStripeWebhookUseCase,
    SyncStripePricesUseCase,
)
from app.core.dependency import (
    get_billing_gateway,
    get_create_checkout_session_use_case,
    get_handle_stripe_webhook_use_case,
    get_sync_stripe_prices_use_case,
)
from app.presentation.api.v1.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    StripeWebhookResponse,
    SyncStripePricesResponse,
)
from app.presentation.security.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post(
    "/checkout-session",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreateCheckoutSessionResponse,
)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    use_case: CreateCheckoutSessionUseCase = Depends(
        get_create_checkout_session_use_case
    ),
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
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        logger.error(
            "Error creating checkout session for user %s: %s",
            current_user_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with billing gateway.",
        ) from exc


@router.post(
    "/webhook",
    response_model=StripeWebhookResponse,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    billing_gateway: BillingGateway = Depends(get_billing_gateway),
    use_case: HandleStripeWebhookUseCase = Depends(
        get_handle_stripe_webhook_use_case
    ),
):
    payload = await request.body()

    try:
        event = await billing_gateway.verify_and_construct_event(
            payload,
            stripe_signature,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe payload.",
        ) from exc

    try:
        await use_case.execute(event)

    except Exception as exc:
        logger.error("Error processing Stripe webhook event: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing Stripe webhook event.",
        ) from exc

    return StripeWebhookResponse(received=True)


@router.post(
    "/sync-prices",
    status_code=status.HTTP_200_OK,
    response_model=SyncStripePricesResponse,
)
async def sync_stripe_prices(
    use_case: SyncStripePricesUseCase = Depends(get_sync_stripe_prices_use_case),
):
    try:
        synced_count = await use_case.execute()
        return SyncStripePricesResponse(synced_count=synced_count)

    except Exception as exc:
        logger.error("Error syncing Stripe prices: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error syncing Stripe prices.",
        ) from exc
