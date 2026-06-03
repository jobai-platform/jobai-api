from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import os
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.infrastructure.persistence.models.ai_analysis import AIAnalysisModel
from app.infrastructure.persistence.models.billing_price import BillingPriceModel
from app.infrastructure.persistence.models.candidate_profile import CandidateProfileModel
from app.infrastructure.persistence.models.embeddings import (
    CandidateEmbeddingModel,
    JobEmbeddingModel,
)
from app.infrastructure.persistence.models.job_posting import JobPostingModel
from app.infrastructure.persistence.models.search_agent import SearchAgentModel
from app.infrastructure.persistence.models.subscription import SubscriptionModel
from app.infrastructure.persistence.models.user import UserModel

logger = logging.getLogger(__name__)

SEED_NAMESPACE = UUID("f9ce15a8-8f22-4f69-8619-4cbdfc164f6a")
SEED_TIMESTAMP = datetime(2026, 6, 3, 8, 30, tzinfo=UTC)
VECTOR_SIZE = 768

TRUNCATE_SQL = text(
    """
    TRUNCATE TABLE
        public.ai_analyses,
        public.candidate_embeddings,
        public.job_embeddings,
        public.search_agents,
        public.subscriptions,
        public.refresh_tokens,
        public.candidate_profiles,
        public.job_postings,
        public.billing_prices,
        public.users
    RESTART IDENTITY CASCADE
    """
)


def _seed_uuid(label: str) -> UUID:
    return uuid5(SEED_NAMESPACE, label)


def _vector(primary: float, secondary: float) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    vector[0] = primary
    vector[1] = secondary
    return vector


def _time() -> datetime:
    return SEED_TIMESTAMP


@dataclass(frozen=True, slots=True)
class AnonymizedDevelopSeed:
    users: tuple[UserModel, ...]
    candidate_profiles: tuple[CandidateProfileModel, ...]
    billing_prices: tuple[BillingPriceModel, ...]
    subscriptions: tuple[SubscriptionModel, ...]
    search_agents: tuple[SearchAgentModel, ...]
    job_postings: tuple[JobPostingModel, ...]
    candidate_embeddings: tuple[CandidateEmbeddingModel, ...]
    job_embeddings: tuple[JobEmbeddingModel, ...]
    ai_analyses: tuple[AIAnalysisModel, ...]

    def model_batches(self) -> tuple[tuple[Any, ...], ...]:
        return (
            self.users,
            self.candidate_profiles,
            self.billing_prices,
            self.subscriptions,
            self.search_agents,
            self.job_postings,
            self.candidate_embeddings,
            self.job_embeddings,
            self.ai_analyses,
        )


def build_anonymized_develop_seed() -> AnonymizedDevelopSeed:
    user_id = _seed_uuid("user-anon-001")
    candidate_profile_id = _seed_uuid("candidate-profile-anon-001")
    billing_price_id = _seed_uuid("billing-price-freemium-anon")
    subscription_id = _seed_uuid("subscription-freemium-anon")
    search_agent_id = _seed_uuid("search-agent-anon-001")
    job_backend_id = _seed_uuid("job-backend-anon-001")
    job_frontend_id = _seed_uuid("job-frontend-anon-001")
    candidate_embedding_id = _seed_uuid("candidate-embedding-anon-001")
    backend_embedding_id = _seed_uuid("job-embedding-backend-anon-001")
    frontend_embedding_id = _seed_uuid("job-embedding-frontend-anon-001")
    analysis_id = _seed_uuid("analysis-anon-backend-001")

    users = (
        UserModel(
            id=user_id,
            email="candidate.001@example.test",
            username="candidate_001",
            first_name="Anon",
            last_name="Candidate",
            hashed_password="$2b$12$anonymized.seed.placeholder",
            role="user",
            is_active=True,
            stripe_customer_id=None,
            linkedin_id=None,
            avatar_url=None,
            is_deleted=False,
            deleted_at=None,
            scheduled_purge_at=None,
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    candidate_profiles = (
        CandidateProfileModel(
            id=candidate_profile_id,
            user_id=user_id,
            current_title="Backend Engineer",
            years_of_experience=6,
            skills=["python", "fastapi", "postgresql", "docker"],
            desired_salary_min=120000,
            desired_salary_max=140000,
            preferred_locations=["Zurich", "Remote"],
            remote_preference="hybrid",
            bio="Synthetic anonymized profile used to validate the develop Neon branch.",
            cv_url=None,
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    billing_prices = (
        BillingPriceModel(
            id=billing_price_id,
            plan="freemium",
            stripe_price_id="price_freemium_anonymized",
            stripe_product_id="prod_freemium_anonymized",
            currency="chf",
            amount=0,
            interval="month",
            active=True,
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    subscriptions = (
        SubscriptionModel(
            id=subscription_id,
            user_id=user_id,
            billing_price_id=billing_price_id,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            plan="freemium",
            status="active",
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    search_agents = (
        SearchAgentModel(
            id=search_agent_id,
            candidate_id=user_id,
            keywords="python fastapi postgresql",
            location="Zurich, Switzerland",
            remote_only=False,
            date_posted_within_days=14,
            limit=10,
            easy_apply_only=None,
            is_active=True,
            last_run_at=None,
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    job_postings = (
        JobPostingModel(
            id=job_backend_id,
            external_id="li_anonymized_backend_001",
            source="linkedin",
            title="Backend Engineer",
            company="Northwind Labs",
            location="Zurich, Switzerland",
            description=(
                "Synthetic anonymized backend role for validating search, "
                "embeddings, and AI analysis flows."
            ),
            url="https://example.test/jobs/backend-engineer-001",
            apply_url="https://example.test/apply/backend-engineer-001",
            company_url="https://example.test/company/northwind-labs",
            posted_at=datetime(2026, 6, 1).date(),
            is_remote=False,
            job_type="fulltime",
            insights="Synthetic seed job",
            salary_min=120000.0,
            salary_max=145000.0,
            salary_currency="CHF",
            skills_raw="python,fastapi,postgresql,docker",
            created_at=_time(),
            updated_at=_time(),
        ),
        JobPostingModel(
            id=job_frontend_id,
            external_id="li_anonymized_frontend_001",
            source="linkedin",
            title="Frontend Engineer",
            company="Northwind Labs",
            location="Bern, Switzerland",
            description="Synthetic anonymized frontend role used as a contrast job posting.",
            url="https://example.test/jobs/frontend-engineer-001",
            apply_url="https://example.test/apply/frontend-engineer-001",
            company_url="https://example.test/company/northwind-labs",
            posted_at=datetime(2026, 5, 30).date(),
            is_remote=True,
            job_type="fulltime",
            insights="Synthetic seed job",
            salary_min=110000.0,
            salary_max=135000.0,
            salary_currency="CHF",
            skills_raw="typescript,react,nextjs,graphql",
            created_at=_time(),
            updated_at=_time(),
        ),
    )

    candidate_embeddings = (
        CandidateEmbeddingModel(
            id=candidate_embedding_id,
            candidate_id=candidate_profile_id,
            vector=_vector(0.93, 0.35),
            extra_metadata={
                "source": "develop-anonymized-seed",
                "profile": "backend-candidate",
            },
            indexed_at=_time(),
        ),
    )

    job_embeddings = (
        JobEmbeddingModel(
            id=backend_embedding_id,
            job_posting_id=job_backend_id,
            vector=_vector(0.95, 0.31),
            extra_metadata={
                "source": "develop-anonymized-seed",
                "title": "backend-engineer",
            },
            indexed_at=_time(),
        ),
        JobEmbeddingModel(
            id=frontend_embedding_id,
            job_posting_id=job_frontend_id,
            vector=_vector(0.09, 0.99),
            extra_metadata={
                "source": "develop-anonymized-seed",
                "title": "frontend-engineer",
            },
            indexed_at=_time(),
        ),
    )

    ai_analyses = (
        AIAnalysisModel(
            id=analysis_id,
            candidate_id=candidate_profile_id,
            job_posting_id=job_backend_id,
            status=AnalysisStatus.COMPLETED.value,
            quality_tier=AnalysisQualityTier.BALANCED.value,
            overall_score=0.94,
            skills_score=0.96,
            experience_score=0.90,
            location_score=0.92,
            salary_score=0.88,
            explanation="Synthetic anonymized match used to validate the develop branch seed.",
            failure_reason=None,
            tokens_consumed=256,
            created_at=_time(),
            completed_at=_time(),
        ),
    )

    return AnonymizedDevelopSeed(
        users=users,
        candidate_profiles=candidate_profiles,
        billing_prices=billing_prices,
        subscriptions=subscriptions,
        search_agents=search_agents,
        job_postings=job_postings,
        candidate_embeddings=candidate_embeddings,
        job_embeddings=job_embeddings,
        ai_analyses=ai_analyses,
    )


async def seed_anonymized_develop(session: AsyncSession) -> None:
    seed = build_anonymized_develop_seed()
    await session.execute(TRUNCATE_SQL)
    for batch in seed.model_batches():
        session.add_all(batch)
        await session.flush()
    await session.commit()
    logger.info(
        "Seeded develop-anonymized branch with %d users, %d candidate profiles, %d jobs",
        len(seed.users),
        len(seed.candidate_profiles),
        len(seed.job_postings),
    )


async def _run(database_url: str) -> None:
    engine = create_async_engine(database_url, future=True, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with session_factory() as session:
            await seed_anonymized_develop(session)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset and seed the develop-anonymized Neon branch with anonymized data.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Async SQLAlchemy database URL. Defaults to DATABASE_URL.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    import asyncio

    asyncio.run(_run(args.database_url))


if __name__ == "__main__":
    main()
