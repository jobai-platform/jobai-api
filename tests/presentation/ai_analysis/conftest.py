from collections.abc import AsyncGenerator, Callable
from uuid import UUID

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai_analysis.use_cases import (
    ComputeMatchScoreUseCase,
    GetAnalysisUseCase,
    GetCandidateJobMatchesUseCase,
    IndexCandidateProfileUseCase,
    IndexJobPostingUseCase,
)
from app.core.dependency import (
    get_billing_gateway,
    get_compute_match_score_use_case,
    get_get_analysis_use_case,
    get_get_candidate_job_matches_use_case,
    get_index_candidate_profile_use_case,
    get_index_job_posting_use_case,
)
from app.domain.users.candidate_profile import CandidateProfile
from app.infrastructure.config.database import get_async_session
from app.infrastructure.security.jwt_service import JWTService
from app.main import app
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_pipeline_port import FakeAIPipelinePort
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore
from tests.fakes.ai_analysis.in_memory_ai_analysis_repo import InMemoryAIAnalysisRepository
from tests.fakes.billing.fake_billing_gateway import FakeBillingGateway
from tests.fakes.users.in_memory_candidate_profile_repo import InMemoryCandidateProfileRepository


@pytest.fixture()
def fake_analysis_repo() -> InMemoryAIAnalysisRepository:
    return InMemoryAIAnalysisRepository()


@pytest.fixture()
def fake_pipeline() -> FakeAIPipelinePort:
    return FakeAIPipelinePort()


@pytest.fixture()
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture()
def fake_embedding() -> FakeEmbeddingPort:
    return FakeEmbeddingPort()


@pytest.fixture()
def fake_profile_repo() -> InMemoryCandidateProfileRepository:
    return InMemoryCandidateProfileRepository()


@pytest_asyncio.fixture()
async def ai_client(
    db_session: AsyncSession,
    fake_analysis_repo: InMemoryAIAnalysisRepository,
    fake_pipeline: FakeAIPipelinePort,
    fake_vector_store: FakeVectorStore,
    fake_embedding: FakeEmbeddingPort,
    fake_profile_repo: InMemoryCandidateProfileRepository,
) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = _override_get_async_session
    app.dependency_overrides[get_billing_gateway] = FakeBillingGateway
    app.dependency_overrides[get_compute_match_score_use_case] = lambda: ComputeMatchScoreUseCase(
        repo=fake_analysis_repo,
        pipeline=fake_pipeline,
    )
    app.dependency_overrides[get_get_analysis_use_case] = lambda: GetAnalysisUseCase(repo=fake_analysis_repo)
    app.dependency_overrides[get_index_candidate_profile_use_case] = lambda: IndexCandidateProfileUseCase(
        profile_repo=fake_profile_repo,
        embedding=fake_embedding,
        vector_store=fake_vector_store,
    )
    app.dependency_overrides[get_index_job_posting_use_case] = lambda: IndexJobPostingUseCase(
        embedding=fake_embedding,
        vector_store=fake_vector_store,
    )
    app.dependency_overrides[get_get_candidate_job_matches_use_case] = lambda: GetCandidateJobMatchesUseCase(
        vector_store=fake_vector_store,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers_for(jwt_service: JWTService) -> Callable[[UUID, str], dict[str, str]]:
    def _headers(user_id: UUID, role: str = "user") -> dict[str, str]:
        token = jwt_service.create_access_token(
            subject=str(user_id),
            extra={"role": role, "email": "candidate@test.com"},
        )
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest_asyncio.fixture()
async def candidate_profile_factory(
    fake_profile_repo: InMemoryCandidateProfileRepository,
) -> Callable[[UUID], object]:
    async def _factory(user_id: UUID) -> CandidateProfile:
        profile = CandidateProfile(
            user_id=user_id,
            current_title="Backend Engineer",
            years_of_experience=5,
            skills=["python", "fastapi"],
            bio="Builds APIs.",
        )
        return await fake_profile_repo.save(profile)

    return _factory
