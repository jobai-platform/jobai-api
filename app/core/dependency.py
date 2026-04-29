from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.billing.ports import BillingGateway, BillingPriceRepository, SubscriptionRepository
from app.application.billing.use_cases import (
    AssignFreemiumOnSignupUseCase,
    CreateCheckoutSessionUseCase,
    HandleStripeWebhookUseCase,
    SyncStripePricesUseCase,
)
from app.application.users.ports import UserRepository
from app.application.users.use_cases import UserService
from app.infrastructure.billing.stripe_gateway import StripeGateway
from app.infrastructure.config.database import get_async_session
from app.infrastructure.persistence.repositories.billing_price_sqlalchemy import BillingPriceSQLAlchemyRepository
from app.infrastructure.persistence.repositories.subscription_sqlalchemy import SubscriptionSQLAlchemyRepository
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.password_service import PasswordServiceAdapter

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def get_user_repository(
    session: DbSession,
) -> UserRepository:
    return SqlAlchemyUserRepository(session=session)

def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    pwd_hasher = PasswordServiceAdapter()
    return UserService(user_repo=repo, pwd_hasher=pwd_hasher)

# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------
def get_subscription_repository(
    session: DbSession,
) -> SubscriptionRepository:
    return SubscriptionSQLAlchemyRepository(session=session)

def get_billing_price_repository(
    session: DbSession,
) -> BillingPriceRepository:
    return BillingPriceSQLAlchemyRepository(session=session)

def get_billing_gateway() -> BillingGateway:
    return StripeGateway()

def get_assign_freemium_on_signup_use_case(
    subscription_repository: SubscriptionRepository = Depends(get_subscription_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    billing_price_repository: BillingPriceRepository = Depends(get_billing_price_repository),
    billing_gateway: BillingGateway = Depends(get_billing_gateway),
) -> AssignFreemiumOnSignupUseCase:
    return AssignFreemiumOnSignupUseCase(
        subscription_repository=subscription_repository,
        user_repository=user_repository,
        billing_price_repository=billing_price_repository,
        billing_gateway=billing_gateway,
    )

def get_create_checkout_session_use_case(
    user_repository: UserRepository = Depends(get_user_repository),
    billing_gateway: BillingGateway = Depends(get_billing_gateway),
) -> CreateCheckoutSessionUseCase:
    return CreateCheckoutSessionUseCase(
        user_repository=user_repository,
        billing_gateway=billing_gateway,
    )

def get_handle_stripe_webhook_use_case(
    subscription_repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> HandleStripeWebhookUseCase:
    return HandleStripeWebhookUseCase(subscription_repository=subscription_repository)

def get_sync_stripe_prices_use_case(
    billing_gateway: BillingGateway = Depends(get_billing_gateway),
    billing_price_repository: BillingPriceRepository = Depends(get_billing_price_repository),
) -> SyncStripePricesUseCase:
    return SyncStripePricesUseCase(
        billing_gateway=billing_gateway,
        billing_price_repository=billing_price_repository,
    )
