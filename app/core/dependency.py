from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.ports import (
    AIAnalysisPipelinePort,
    AIAnalysisRepository,
    VectorStorePort,
)
from app.application.ai_analysis.use_cases import (
    AnalyzeJobDescriptionUseCase,
    ComputeMatchScoreUseCase,
    GenerateEmbeddingsUseCase,
    GenerateLLMCompletionUseCase,
    GetAnalysisUseCase,
    GetCandidateJobMatchesUseCase,
    IndexCandidateProfileUseCase,
    IndexJobPostingUseCase,
)
from app.application.auth.linkedin_oauth_use_case import LinkedInOAuthUseCase
from app.application.billing.ports import (
    BillingGateway,
    BillingPriceRepository,
    SubscriptionRepository,
)
from app.application.billing.use_cases import (
    AssignFreemiumOnSignupUseCase,
    CreateCheckoutSessionUseCase,
    HandleStripeWebhookUseCase,
    SyncStripePricesUseCase,
)
from app.application.job_search.ports import (
    JobPostingRepository,
    JobScraperGateway,
    SearchAgentRepository,
)
from app.application.job_search.search_agent_use_cases import (
    CreateSearchAgentUseCase,
    DeleteSearchAgentUseCase,
    GetSearchAgentUseCase,
    RunSearchAgentUseCase,
    UpdateSearchAgentUseCase,
)
from app.application.job_search.use_cases import SearchJobsUseCase
from app.application.storage.ports import StorageGateway
from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.application.users.candidate_profile_use_cases import (
    GetCandidateProfileUseCase,
    UpsertCandidateProfileUseCase,
)
from app.application.users.cv_use_cases import DeleteCVUseCase, UploadCVUseCase
from app.application.users.ports import UserRepository
from app.application.users.use_cases import UserService
from app.core.config import settings
from app.domain.ai_analysis.ports import EmbeddingPort, LLMGatewayPort
from app.domain.ai_analysis.services.model_router import ModelRouter
from app.domain.ai_analysis.value_objects import ProviderConfig
from app.infrastructure.ai.langgraph_pipeline_adapter import LangGraphPipelineAdapter
from app.infrastructure.ai.ollama_embedding_adapter import OllamaEmbeddingAdapter
from app.infrastructure.ai.ollama_llm_gateway import OllamaLLMGateway
from app.infrastructure.ai.timescale_vector_store import TimescaleVectorStoreAdapter
from app.infrastructure.billing.stripe_gateway import StripeGateway
from app.infrastructure.config.database import get_async_session
from app.infrastructure.job_search.linkedin_scraper_adapter import LinkedInJobsScraperAdapter
from app.infrastructure.persistence.repositories.ai_analysis_sqlalchemy import (
    SQLAlchemyAIAnalysisRepository,
)
from app.infrastructure.persistence.repositories.billing_price_sqlalchemy import (
    BillingPriceSQLAlchemyRepository,
)
from app.infrastructure.persistence.repositories.candidate_profile_sqlalchemy import (
    SQLAlchemyCandidateProfileRepository,
)
from app.infrastructure.persistence.repositories.job_posting_sqlalchemy import (
    JobPostingSQLAlchemyRepository,
)
from app.infrastructure.persistence.repositories.search_agent_sqlalchemy import (
    SQLAlchemySearchAgentRepository,
)
from app.infrastructure.persistence.repositories.subscription_sqlalchemy import (
    SubscriptionSQLAlchemyRepository,
)
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository
from app.infrastructure.security.jwt_service import JWTTokenServiceAdapter
from app.infrastructure.security.linkedin_oauth_adapter import LinkedInOAuthAdapter
from app.infrastructure.security.password_service import PasswordServiceAdapter
from app.infrastructure.storage.s3_gateway import S3StorageGateway

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


# ---------------------------------------------------------------------------
# Users - factories
# ---------------------------------------------------------------------------
def get_user_repository(
    session: DbSession,
) -> UserRepository:
    return SqlAlchemyUserRepository(session=session)

# ---------------------------------------------------------------------------
# Candidate Profile - factories
# ---------------------------------------------------------------------------
def get_candidate_profile_repository(session: DbSession) -> CandidateProfileRepository:
    return SQLAlchemyCandidateProfileRepository(session=session)

def get_candidate_profile_use_case(
    repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
) -> GetCandidateProfileUseCase:
    return GetCandidateProfileUseCase(repo=repo)

def get_upsert_candidate_profile_use_case(
    repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
) -> UpsertCandidateProfileUseCase:
    return UpsertCandidateProfileUseCase(repo=repo)

def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    profile_repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
) -> UserService:
    return UserService(
        user_repo=repo,
        pwd_hasher=PasswordServiceAdapter(),
        profile_repo=profile_repo,
    )

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
    subscription_repository: Annotated[
        SubscriptionRepository,
        Depends(get_subscription_repository),
    ],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    billing_price_repository: Annotated[
        BillingPriceRepository,
        Depends(get_billing_price_repository),
    ],
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
    subscription_repository: Annotated[
        SubscriptionRepository,
        Depends(get_subscription_repository),
    ],
) -> HandleStripeWebhookUseCase:
    return HandleStripeWebhookUseCase(subscription_repository=subscription_repository)

def get_sync_stripe_prices_use_case(
    billing_gateway: Annotated[BillingGateway, Depends(get_billing_gateway)],
    billing_price_repository: Annotated[
        BillingPriceRepository,
        Depends(get_billing_price_repository),
    ],
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

def get_search_agent_repository(session: DbSession) -> SearchAgentRepository:
    return SQLAlchemySearchAgentRepository(session=session)

def get_create_search_agent_use_case(
    repo: Annotated[SearchAgentRepository, Depends(get_search_agent_repository)],
) -> CreateSearchAgentUseCase:
    return CreateSearchAgentUseCase(repo=repo)

def get_get_search_agent_use_case(
    repo: Annotated[SearchAgentRepository, Depends(get_search_agent_repository)],
) -> GetSearchAgentUseCase:
    return GetSearchAgentUseCase(repo=repo)

def get_update_search_agent_use_case(
    repo: Annotated[SearchAgentRepository, Depends(get_search_agent_repository)],
) -> UpdateSearchAgentUseCase:
    return UpdateSearchAgentUseCase(repo=repo)

def get_delete_search_agent_use_case(
    repo: Annotated[SearchAgentRepository, Depends(get_search_agent_repository)],
) -> DeleteSearchAgentUseCase:
    return DeleteSearchAgentUseCase(repo=repo)

def get_run_search_agent_use_case(
    repo: Annotated[SearchAgentRepository, Depends(get_search_agent_repository)],
    search_uc: Annotated[SearchJobsUseCase, Depends(get_search_jobs_use_case)],
) -> RunSearchAgentUseCase:
    return RunSearchAgentUseCase(agent_repo=repo, search_jobs_use_case=search_uc)

# ---------------------------------------------------------------------------
# Storage — factories
# ---------------------------------------------------------------------------
def get_storage_gateway() -> StorageGateway:
    return S3StorageGateway()

def get_upload_cv_use_case(
    profile_repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
    storage: Annotated[StorageGateway, Depends(get_storage_gateway)],
) -> UploadCVUseCase:
    return UploadCVUseCase(profile_repo=profile_repo, storage=storage)

def get_delete_cv_use_case(
    profile_repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
    storage: Annotated[StorageGateway, Depends(get_storage_gateway)],
) -> DeleteCVUseCase:
    return DeleteCVUseCase(profile_repo=profile_repo, storage=storage)

# ---------------------------------------------------------------------------
# LinkedIn OAuth — factories
# ---------------------------------------------------------------------------
def get_linkedin_oauth_adapter() -> LinkedInOAuthAdapter:
    return LinkedInOAuthAdapter(
        client_id=settings.LINKEDIN_CLIENT_ID,
        client_secret=settings.LINKEDIN_CLIENT_SECRET,
    )

def get_linkedin_oauth_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    freemium: Annotated[
        AssignFreemiumOnSignupUseCase,
        Depends(get_assign_freemium_on_signup_use_case),
    ],
    profile_repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
) -> LinkedInOAuthUseCase:
    return LinkedInOAuthUseCase(
        oauth_gateway=get_linkedin_oauth_adapter(),
        user_repo=user_repo,
        token_service=JWTTokenServiceAdapter(),
        freemium_use_case=freemium,
        profile_repo=profile_repo,
    )
# ---------------------------------------------------------------------------
# AI Analysis — composition root
# ---------------------------------------------------------------------------
def get_model_router() -> ModelRouter:
    config = ProviderConfig(
        embedding_provider=settings.EMBEDDING_PROVIDER,
        llm_provider=settings.LLM_PROVIDER,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
        ollama_llm_model=settings.OLLAMA_LLM_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    providers: dict[str, EmbeddingPort | LLMGatewayPort] = {
        "embedding_ollama": OllamaEmbeddingAdapter(
            base_url=config.ollama_base_url,
            model=config.ollama_embedding_model,
        ),
        "llm_ollama": OllamaLLMGateway(
            base_url=config.ollama_base_url,
            model=config.ollama_llm_model,
            timeout=settings.OLLAMA_TIMEOUT,
        ),
    }

    return ModelRouter(config=config, providers=providers)


def get_generate_embeddings_use_case(
    router: Annotated[ModelRouter, Depends(get_model_router)],
) -> GenerateEmbeddingsUseCase:
    return GenerateEmbeddingsUseCase(router=router)


def get_generate_llm_completion_use_case(
    router: Annotated[ModelRouter, Depends(get_model_router)],
) -> GenerateLLMCompletionUseCase:
    return GenerateLLMCompletionUseCase(router=router)


def get_analyze_job_description_use_case(
    router: Annotated[ModelRouter, Depends(get_model_router)],
) -> AnalyzeJobDescriptionUseCase:
    return AnalyzeJobDescriptionUseCase(router=router)


def get_ai_analysis_repository(session: DbSession) -> AIAnalysisRepository:
    return SQLAlchemyAIAnalysisRepository(session=session)


def get_vector_store(session: DbSession) -> VectorStorePort:
    return TimescaleVectorStoreAdapter(session=session)


def get_embedding_port() -> EmbeddingPort:
    return OllamaEmbeddingAdapter(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBEDDING_MODEL,
    )


def get_langgraph_pipeline(session: DbSession) -> AIAnalysisPipelinePort:
    llm = OllamaLLMGateway(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_LLM_MODEL,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    embedding = OllamaEmbeddingAdapter(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBEDDING_MODEL,
    )
    return LangGraphPipelineAdapter(session=session, llm=llm, embedding_port=embedding)


def get_compute_match_score_use_case(
    repo: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
    pipeline: Annotated[AIAnalysisPipelinePort, Depends(get_langgraph_pipeline)],
) -> ComputeMatchScoreUseCase:
    return ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)


def get_get_analysis_use_case(
    repo: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
) -> GetAnalysisUseCase:
    return GetAnalysisUseCase(repo=repo)


def get_index_candidate_profile_use_case(
    profile_repo: Annotated[CandidateProfileRepository, Depends(get_candidate_profile_repository)],
    embedding: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
) -> IndexCandidateProfileUseCase:
    return IndexCandidateProfileUseCase(
        profile_repo=profile_repo,
        embedding=embedding,
        vector_store=vector_store,
    )


def get_index_job_posting_use_case(
    embedding: Annotated[EmbeddingPort, Depends(get_embedding_port)],
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
) -> IndexJobPostingUseCase:
    return IndexJobPostingUseCase(embedding=embedding, vector_store=vector_store)


def get_get_candidate_job_matches_use_case(
    vector_store: Annotated[VectorStorePort, Depends(get_vector_store)],
) -> GetCandidateJobMatchesUseCase:
    return GetCandidateJobMatchesUseCase(vector_store=vector_store)


# ---------------------------------------------------------------------------
# Annotated aliases - to be imported in the routes
# ---------------------------------------------------------------------------
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
SubscriptionRepositoryDep = Annotated[SubscriptionRepository, Depends(get_subscription_repository)]
AssignFreemiumDep = Annotated[
    AssignFreemiumOnSignupUseCase,
    Depends(get_assign_freemium_on_signup_use_case),
]
CreateCheckoutDep = Annotated[
    CreateCheckoutSessionUseCase,
    Depends(get_create_checkout_session_use_case),
]
HandleWebhookDep = Annotated[
    HandleStripeWebhookUseCase,
    Depends(get_handle_stripe_webhook_use_case),
]
SyncPricesDep = Annotated[SyncStripePricesUseCase, Depends(get_sync_stripe_prices_use_case)]
BillingGatewayDep = Annotated[BillingGateway, Depends(get_billing_gateway)]
SearchJobsDep = Annotated[SearchJobsUseCase, Depends(get_search_jobs_use_case)]
CreateSearchAgentDep = Annotated[
    CreateSearchAgentUseCase,
    Depends(get_create_search_agent_use_case),
]
GetSearchAgentDep = Annotated[GetSearchAgentUseCase, Depends(get_get_search_agent_use_case)]
UpdateSearchAgentDep = Annotated[
    UpdateSearchAgentUseCase,
    Depends(get_update_search_agent_use_case),
]
DeleteSearchAgentDep = Annotated[
    DeleteSearchAgentUseCase,
    Depends(get_delete_search_agent_use_case),
]
RunSearchAgentDep = Annotated[RunSearchAgentUseCase, Depends(get_run_search_agent_use_case)]
LinkedInOAuthUseCaseDep = Annotated[LinkedInOAuthUseCase, Depends(get_linkedin_oauth_use_case)]
GetCandidateProfileDep = Annotated[
    GetCandidateProfileUseCase,
    Depends(get_candidate_profile_use_case),
]
UpsertCandidateProfileDep = Annotated[
    UpsertCandidateProfileUseCase,
    Depends(get_upsert_candidate_profile_use_case),
]
UploadCVDep = Annotated[UploadCVUseCase, Depends(get_upload_cv_use_case)]
DeleteCVDep = Annotated[DeleteCVUseCase, Depends(get_delete_cv_use_case)]
ModelRouterDep = Annotated[ModelRouter, Depends(get_model_router)]
GenerateEmbeddingsDep = Annotated[
    GenerateEmbeddingsUseCase,
    Depends(get_generate_embeddings_use_case),
]
GenerateLLMCompletionDep = Annotated[
    GenerateLLMCompletionUseCase,
    Depends(get_generate_llm_completion_use_case),
]
AnalyzeJobDescriptionDep = Annotated[
    AnalyzeJobDescriptionUseCase,
    Depends(get_analyze_job_description_use_case),
]
ComputeMatchScoreDep = Annotated[
    ComputeMatchScoreUseCase,
    Depends(get_compute_match_score_use_case),
]
GetAnalysisDep = Annotated[GetAnalysisUseCase, Depends(get_get_analysis_use_case)]
IndexCandidateProfileDep = Annotated[
    IndexCandidateProfileUseCase,
    Depends(get_index_candidate_profile_use_case),
]
IndexJobPostingDep = Annotated[IndexJobPostingUseCase, Depends(get_index_job_posting_use_case)]
GetCandidateJobMatchesDep = Annotated[
    GetCandidateJobMatchesUseCase,
    Depends(get_get_candidate_job_matches_use_case),
]
