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
from app.application.job_search.ports import JobScraperGateway, JobPostingRepository
from app.application.job_search.use_cases import SearchJobsUseCase
from app.application.users.ports import UserRepository
from app.application.users.use_cases import UserService
from app.infrastructure.billing.stripe_gateway import StripeGateway
from app.infrastructure.config.database import get_async_session
from app.infrastructure.job_search.linkedin_scraper_adapter import LinkedInJobsScraperAdapter
from app.infrastructure.persistence.repositories.billing_price_sqlalchemy import BillingPriceSQLAlchemyRepository
from app.infrastructure.persistence.repositories.job_posting_sqlalchemy import JobPostingSQLAlchemyRepository
from app.infrastructure.persistence.repositories.subscription_sqlalchemy import SubscriptionSQLAlchemyRepository
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.password_service import PasswordServiceAdapter


DbSession = Annotated[AsyncSession, Depends(get_async_session)]


# ---------------------------------------------------------------------------
# Users - factories
# ---------------------------------------------------------------------------
def get_user_repository(
    session: DbSession,
) -> UserRepository:
    return SqlAlchemyUserRepository(session=session)

def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(user_repo=repo, pwd_hasher=PasswordServiceAdapter())

# ---------------------------------------------------------------------------
# Billing - factories
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
    subscription_repository: Annotated[SubscriptionRepository, Depends(get_subscription_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    billing_price_repository: Annotated[BillingPriceRepository, Depends(get_billing_price_repository)],
    billing_gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
) -> AssignFreemiumOnSignupUseCase:
    return AssignFreemiumOnSignupUseCase(
        subscription_repository=subscription_repository,
        user_repository=user_repository,
        billing_price_repository=billing_price_repository,
        billing_gateway=billing_gateway,
    )

def get_create_checkout_session_use_case(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    billing_gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
) -> CreateCheckoutSessionUseCase:
    return CreateCheckoutSessionUseCase(
        user_repository=user_repository,
        billing_gateway=billing_gateway,
    )

def get_handle_stripe_webhook_use_case(
    subscription_repository: Annotated[SubscriptionRepository, Depends(get_subscription_repository)],
) -> HandleStripeWebhookUseCase:
    return HandleStripeWebhookUseCase(subscription_repository=subscription_repository)

def get_sync_stripe_prices_use_case(
    billing_gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
    billing_price_repository: Annotated[BillingPriceRepository, Depends(get_billing_price_repository)],
) -> SyncStripePricesUseCase:
    return SyncStripePricesUseCase(
        billing_gateway=billing_gateway,
        billing_price_repository=billing_price_repository,
    )

# ---------------------------------------------------------------------------
# Job Search - factories
# ---------------------------------------------------------------------------
def get_job_scraper_gateway() -> JobScraperGateway:
    return LinkedInJobsScraperAdapter()

def get_job_posting_repository(session: DbSession) -> JobPostingRepository:
    return JobPostingSQLAlchemyRepository(session=session)

def get_search_jobs_use_case(
    scraper: Annotated[JobScraperGateway, Depends(get_job_scraper_gateway)],
    job_posting_repository: Annotated[JobPostingRepository, Depends(get_job_posting_repository)],
) -> SearchJobsUseCase:
    return SearchJobsUseCase(
        scraper=scraper,
        job_posting_repo=job_posting_repository,
    )


# ---------------------------------------------------------------------------
# Annotated aliases - to be imported in the routes
# ---------------------------------------------------------------------------
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
SubscriptionRepositoryDep = Annotated[SubscriptionRepository, Depends(get_subscription_repository)]
AssignFreemiumDep = Annotated[AssignFreemiumOnSignupUseCase, Depends(get_assign_freemium_on_signup_use_case)]
CreateCheckoutDep = Annotated[CreateCheckoutSessionUseCase, Depends(get_create_checkout_session_use_case)]
HandleWebhookDep = Annotated[HandleStripeWebhookUseCase, Depends(get_handle_stripe_webhook_use_case)]
SyncPricesDep = Annotated[SyncStripePricesUseCase, Depends(get_sync_stripe_prices_use_case)]
BillingGatewayDep = Annotated[BillingGateway, Depends(get_billing_gateway)]
SearchJobsDep = Annotated[SearchJobsUseCase, Depends(get_search_jobs_use_case)]

