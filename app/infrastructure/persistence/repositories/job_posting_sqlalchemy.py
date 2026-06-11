import logging
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.job_search.ports import JobPostingRepository
from app.domain.job_search.entities import JobPosting
from app.infrastructure.persistence.models.job_posting import JobPostingModel

logger = logging.getLogger(__name__)


def _to_domain(model: JobPostingModel) -> JobPosting:
    return JobPosting(
        id=UUID(str(model.id)),
        external_id=model.external_id,
        source=model.source,
        title=model.title,
        company=model.company,
        location=model.location,
        description=model.description,
        url=model.url,
        apply_url=model.apply_url,
        company_url=model.company_url,
        posted_at=model.posted_at,
        is_remote=model.is_remote,
        job_type=model.job_type,
        insights=model.insights,
        salary_min=model.salary_min,
        salary_max=model.salary_max,
        salary_currency=model.salary_currency,
        skills=tuple(model.skills_raw.split(",")) if model.skills_raw else (),
        created_at=model.created_at,
    )


def _skills_to_raw(skills: list[str]) -> str | None:
    return ",".join(skills) if skills else None


class JobPostingSQLAlchemyRepository(JobPostingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(
        self,
        external_id: str,
        source: str,
    ) -> JobPosting | None:
        logger.debug(
            "Querying JobPosting by external_id=%s and source=%s",
            external_id,
            source,
        )
        stmt = select(JobPostingModel).where(
            JobPostingModel.external_id == external_id,
            JobPostingModel.source == source,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def get_by_id(self, job_posting_id: UUID) -> JobPosting | None:
        stmt = select(JobPostingModel).where(JobPostingModel.id == job_posting_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def search(
        self,
        *,
        query: str | None = None,
        location: str | None = None,
        limit: int = 20,
    ) -> list[JobPosting]:
        stmt = select(JobPostingModel).order_by(JobPostingModel.posted_at.desc().nullslast())

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    JobPostingModel.title.ilike(pattern),
                    JobPostingModel.company.ilike(pattern),
                    JobPostingModel.description.ilike(pattern),
                    JobPostingModel.skills_raw.ilike(pattern),
                )
            )
        if location:
            stmt = stmt.where(JobPostingModel.location.ilike(f"%{location}%"))

        stmt = stmt.limit(max(1, min(limit, 100)))
        result = await self.session.execute(stmt)
        return [_to_domain(model) for model in result.scalars().all()]

    async def upsert(self, job: JobPosting) -> JobPosting:
        stmt = (
            insert(JobPostingModel)
            .values(
                external_id=job.external_id,
                source=job.source,
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description,
                url=job.url,
                apply_url=job.apply_url,
                company_url=job.company_url,
                posted_at=job.posted_at,
                is_remote=job.is_remote,
                job_type=job.job_type,
                insights=job.insights,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                skills_raw=_skills_to_raw(job.skills),
            )
            .on_conflict_do_update(
                constraint="uq_job_posting_external_id_source",
                set_={
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": job.description,
                    "url": job.url,
                    "apply_url": job.apply_url,
                    "is_remote": job.is_remote,
                    "job_type": job.job_type,
                    "insights": job.insights,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "salary_currency": job.salary_currency,
                    "skills_raw": _skills_to_raw(job.skills),
                    "updated_at": __import__("sqlalchemy").func.now(),
                },
            )
            .returning(JobPostingModel)
        )
        result = await self.session.execute(stmt)
        # Note: commit is handled at the outer layer (dependency)
        model = result.scalar_one()
        logger.info(
            "JobPosting upserted external_id=%s and source=%s",
            job.external_id,
            job.source,
        )
        return _to_domain(model)

    async def list_by_candidate(
        self,
        candidate_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobPosting]:
        # TODO: Need to be reviewed when the candidate search history is implemented
        stmt = (
            select(JobPostingModel)
            .order_by(JobPostingModel.posted_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]

    async def count_new_since_last_search(self, candidate_id: UUID) -> int:
        # TODO: This implementation has been completed with SearchAgent history
        return 0
