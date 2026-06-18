import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status

from app.core.dependency import (
    BillingGatewayDep,
    CreateCheckoutDep,
    GetBillingHistoryDep,
    HandleWebhookDep,
    SubscriptionRepositoryDep,
    SyncPricesDep,
)
from app.domain.common.exceptions import NotFoundError
from app.presentation.api.v1.schemas.billing import (
    BillingHistoryRead,
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    InvoiceRead,
    StripeWebhookResponse,
    SubscriptionRead,
    SyncStripePricesResponse,
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
    description=(
        "Retrieve the active subscription plan details for the currently authenticated user."
    ),
)
async def get_my_subscription(
    current_user_id: CurrentUserIdDep,
    subscription_repo: SubscriptionRepositoryDep,
):
    sub = await subscription_repo.get_by_user_id(current_user_id)
    if not sub:
        raise NotFoundError(
            code="subscription_not_found",
            details=f"No active subscription found for user {current_user_id}",
        )
    return SubscriptionRead(
        user_id=str(sub.user_id),
        plan=sub.plan.value,
        status=sub.status.value,
        stripe_customer_id=sub.stripe_customer_id,
        stripe_subscription_id=sub.stripe_subscription_id,
        billing_price_id=str(sub.billing_price_id) if sub.billing_price_id else None,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at,
        amount=sub.amount,
        currency=sub.currency,
    )


@router.get(
    "/billing-history",
    response_model=BillingHistoryRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user billing history",
    description=(
        "Retrieve the paginated Stripe billing history for the currently authenticated user."
    ),
)
async def get_billing_history(
    current_user_id: CurrentUserIdDep,
    use_case: GetBillingHistoryDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    result = await use_case.execute(
        user_id=current_user_id,
        limit=limit,
        offset=offset,
    )
    return BillingHistoryRead(
        items=[InvoiceRead.model_validate(item) for item in result.items],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
        has_more=result.has_more,
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


@router.get(
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
