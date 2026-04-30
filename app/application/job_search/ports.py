from abc import ABC, abstractmethod
from typing import Optional

from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob


class JobScraperGateway(ABC):
    """
    Interface for job scraper adapters.
    Each implementation (LinkedIn, Indeed, etc.) must implement this method.
    Implements :
    - LinkedInJobsScraperAdapter (linkedin-jobs-scraper)
    - JobSpyAdapter              (LinkedIn + Indeed + Glassdoor + Google)
    - JobUpAdapter               (JobUp.ch — Swiss market)
    All business logic depends on this port,
    never directly on a concrete implementation.
    """

    @abstractmethod
    async def search_jobs(self, query: JobSearchQuery) -> list[ScrapedJob]:
        """
        Search for job postings matching the given query.
        :param query: JobSearchQuery value object with search criteria.
        :return: List of normalized ScrapedJob value objects.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_job_detail(self, job_id: str) -> Optional[ScrapedJob]:
        """
        Retrieve full details for a specific job posting by its external ID.
        Returns None if the job is no longer available on the source platform.
        :param job_id: External job identifier (source-specific).
        :return: ScrapedJob value object or None.
        """
        raise NotImplementedError()
