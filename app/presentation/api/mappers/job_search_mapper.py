from app.application.job_search.dto import JobSearchResult
from app.domain.job_search.value_objects import ScrapedJob
from app.presentation.api.v1.schemas.job_search import (
    JobSearchResponse,
    ScrapedJobSchema,
)


def to_scraped_job_schema(job: ScrapedJob) -> ScrapedJobSchema:
    """Maps a ScrapedJob Value Object to a ScrapedJobSchema DTO."""
    return ScrapedJobSchema(
        job_id=job.job_id,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        url=job.url,
        source=job.source,
        apply_url=job.apply_url,
        company_url=job.company_url,
        posted_at=job.posted_at,
        is_remote=job.is_remote,
        job_type=job.job_type,
        insights=job.insights,
        skills=list(job.skills),
    )


def to_job_search_response(result: JobSearchResult) -> JobSearchResponse:
    """Maps a JobSearchResult DTO to a JobSearchResponse schema."""
    return JobSearchResponse(
        jobs=[to_scraped_job_schema(job) for job in result.jobs],
        total=result.total,
        keywords=result.keywords,
        location=result.location,
        source=result.source,
        has_results=result.has_results,
    )
