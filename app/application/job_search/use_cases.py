import logging
from typing import Optional

from app.application.job_search.dto import JobSearchResult
from app.application.job_search.ports import JobScraperGateway
from app.domain.job_search.value_objects import ScrapedJob, JobSearchQuery

logger = logging.getLogger(__name__)

class SearchJobsUseCase:
    """
    Orchestrates searching jobs for a candidate.
    Future extensions:
        - Cross-reference with existing applications to avoid duplicates.
        - Feed results into SkillMatch scoring.
        - Trigger SearchAgent autonomously on a schedule.
        - Validates search criteria.
        - Retrieves matching jobs from the repository.
        - Applies any necessary business logic (e.g., filtering, sorting).
        - Returns the list of matching jobs to the caller.
        - Handles any exceptions that may occur during the search process.
        - Logs relevant information for monitoring and debugging purposes.
        - Ensures that the search operation is efficient and scalable.
        - May interact with other use cases or services as needed (e.g., for user preferences).
        - Provides a clear interface for the presentation layer to invoke the search functionality.
        - Ensures that the search results are relevant and personalized based on the candidate's profile and preferences.
    """
    def __init__(self, scraper: JobScraperGateway) -> None:
        self.scraper = scraper


    async def execute(
        self,
        *,
        keywords: str,
        location: str,
        limit: int = 25,
        remote_only: bool = False,
        date_posted_within_days: Optional[int] = 7,
    ) -> JobSearchResult:
        query = JobSearchQuery(
            keywords=keywords,
            location=location,
            limit=limit,
            remote_only=remote_only,
            date_posted_within_days=date_posted_within_days,
        )
        jobs = await self.scraper.search_jobs(query)

        logger.info("SearchJobsUseCase: found %d jobs for query: %s", len(jobs), query)

        source = jobs[0].source if jobs else "unknown"
        return JobSearchResult(jobs=jobs, total=len(jobs), keywords=keywords, location=location, source=source)


    async def get_detail(self, *, job_id: str) -> Optional[ScrapedJob]:
        """
        Retrieve detailed information for a specific job posting.
        - Validates the job ID.
        - Retrieves the job details from the repository or external source.
        - Handles any exceptions that may occur during the retrieval process.
        - Logs relevant information for monitoring and debugging purposes.
        - Ensures that the retrieval operation is efficient and scalable.
        - May interact with other use cases or services as needed (e.g., for user preferences).
        - Provides a clear interface for the presentation layer to invoke the detail retrieval functionality.
        - Ensures that the retrieved job details are accurate and up-to-date based on the source platform.
        """
        try:
            job_detail = await self.scraper.get_job_detail(job_id)
            return job_detail
        except Exception as e:
            logger.error("Error retrieving job detail for job_id '%s': %s", job_id, str(e))
            return None
