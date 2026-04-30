import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.dependency import (
    BillingGatewayDep,
    CreateCheckoutDep,
    HandleWebhookDep,
    SyncPricesDep,
    SubscriptionRepositoryDep,
)
from app.domain.common.exceptions import NotFoundError
from app.presentation.api.v1.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    StripeWebhookResponse,
    SyncStripePricesResponse,
    SubscriptionRead,
)
from app.presentation.security.deps import get_current_user_id

CurrentUserIdDep = Annotated[UUID, Depends(get_current_user_id)]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stripe", tags=["Stripe"])

@router.get(
    "/subscriptions/me",
    response_model=SubscriptionRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user subscription details",
    description="Retrieve the active subscription plan details for the currently authenticated user."
)
async def get_my_subscription(
    current_user_id: CurrentUserIdDep,
    subscription_repo: SubscriptionRepositoryDep,
):
    sub = await subscription_repo.get_by_user_id(current_user_id)
    if not sub:
        raise NotFoundError(
            code="subscription_not_found",
            details=f"No active subscription found for user {current_user_id}"
        )
    return SubscriptionRead(
        user_id=str(sub.user_id),
        plan=sub.plan.value,
        status=sub.status.value,
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
        billing_price_id=str(sub.billing_price_id) if sub.billing_price_id else None,
    )

@router.post(
    "/checkout-session",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreateCheckoutSessionResponse,
)
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    current_user_id: CurrentUserIdDep,
    use_case: CreateCheckoutDep,
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
    use_case: HandleWebhookDep,
    billing_gateway: BillingGatewayDep,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
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
    summary="Sync Stripe prices to database",
    description="Sync Stripe prices to database",
)
async def sync_stripe_prices(
    use_case: SyncPricesDep,
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
