from abc import ABC, abstractmethod

from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob


class JobScraperGateway(ABC):
    """
    Interface for job scraper adapters.
    Each implementation (LinkedIn, Indeed, etc.) must implement this method.
    """

    @abstractmethod
    async def search_jobs(self, query: JobSearchQuery) -> list[ScrapedJob]:
        """Search for job postings matching the given query."""

    @abstractmethod
    async def get_job_detail(self, job_id: str) -> ScrapedJob | None:
        """Retrieve full details for a specific job posting by its external ID."""
