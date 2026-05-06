import logging

from app.application.job_search.dto import JobSearchResult
from app.application.job_search.ports import JobScraperGateway, JobPostingRepository
from app.domain.job_search.entities import JobPosting
from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob

logger = logging.getLogger(__name__)


def _to_job_posting(scraped: ScrapedJob) -> JobPosting:
    """Maps a ScrapedJob Value Object to a JobPosting Entity."""
    return JobPosting(
        external_id=scraped.job_id,
        title=scraped.title,
        company=scraped.company,
        location=scraped.location,
        description=scraped.description,
        url=scraped.url,
        source=scraped.source,
        apply_url=scraped.apply_url,
        company_url=scraped.company_url,
        posted_at=scraped.posted_at,
        is_remote=scraped.is_remote,
        job_type=scraped.job_type,
        insights=scraped.insights,
        skills=scraped.skills,
    )


class SearchJobsUseCase:
    """
    Orchestrates Job Search for a candidate.
    Source-agnostic: delegates to JobScraperGateway
    Future: cross-reference with existing applications to avoid duplicate.
    """

    def __init__(
        self,
        scraper: JobScraperGateway,
        job_posting_repo: JobPostingRepository,
    ) -> None:
        self.scraper = scraper
        self.job_posting_repo = job_posting_repo

    async def execute(
        self,
        *,
        keywords: str,
        location: str,
        limit: int = 25,
        remote_only: bool = False,
        date_posted_within_days: int | None = 7,
    ) -> JobSearchResult:
        """
        Search for job postings matching the given parameters.
        :param keywords: Job title or skills to search for.
        :param location: Location to search for jobs.
        :param limit: Maximum number of jobs to return.
        :param remote_only: Whether to only include remote jobs.
        :param date_posted_within_days: Number of days back to consider when searching for jobs.
        :return: A list of job postings matching the criteria.
        """
        query = JobSearchQuery(
            keywords=keywords,
            location=location,
            limit=limit,
            remote_only=remote_only,
            date_posted_within_days=date_posted_within_days,
        )
        jobs = await self.scraper.search_jobs(query)

        persisted: list[JobPosting] = []
        for job in jobs:
            job_entity = _to_job_posting(job)
            saved = await self.job_posting_repo.upsert(job_entity)
            persisted.append(saved)

        logger.info(
            "SearchJobsUseCase: scraped=%d persisted=%d "
            "keywords='%s' location='%s'",
            len(jobs), len(persisted), keywords, location,
        )

        return JobSearchResult(
            jobs=jobs,
            total=len(jobs),
            keywords=keywords,
            location=location,
            source=jobs[0].source if jobs else "unknown",
        )

    async def get_detail(self, *, job_id: str) -> ScrapedJob | None:
        """
        Retrieve full details for a specific job posting.
        :param job_id: External job identifier.
        :return: ScrapedJob or None if not found.
        """
        try:
            return await self.scraper.get_job_detail(job_id)
        except Exception:
            logger.exception("Error retrieving job detail for job_id '%s'", job_id)
            return None
