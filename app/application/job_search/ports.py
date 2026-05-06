from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.job_search.entities import JobPosting
from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob


class JobScraperGateway(ABC):
    """
    Interface for job scraper adapters.
    Concrete implementations:
    - LinkedInJobsScraperAdapter  (python-jobspy — LinkedIn internal API, no Selenium)
    - JobSpyAdapter               (LinkedIn + Indeed + Glassdoor + Google)
    - JobUpAdapter                (JobUp.ch — Swiss market)
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


class JobPostingRepository(ABC):
    """
    Interface for job posting persistence.
    Enables deduplication and SearchAgent history tracking.
    """

    @abstractmethod
    async def get_by_external_id(
        self,
        external_id: str,
        source: str
    ) -> Optional["JobPosting"]:
        """
        Get a JobPosting by its external identifier and source platform.
        Used for deduplication before persisting a new scraped job.
        :param external_id: External job identifier (source-specific).
        :param source: Source platform (LinkedIn, Indeed, Glassdoor, Google).
        :return: JobPosting entity or None if not found.
        """
        raise NotImplementedError()


    @abstractmethod
    async def upsert(self, job_posting: "JobPosting") -> "JobPosting":
        """
        Create or update a JobPosting entity in the repository.
        Used to persist new scraped jobs and update existing ones with latest details.
        :param job_posting: JobPosting entity to persist.
        :return: The persisted JobPosting entity (with ID).
        """
        raise NotImplementedError()


    @abstractmethod
    async def list_by_candidate(
        self,
        candidate_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list["JobPosting"]:
        """
        List JobPostings associated with a candidate's search history.
        :param candidate_id: Candidate user ID.
        :param limit: Maximum number of results.
        :param offset: Pagination offset.
        :return: List of JobPosting entities.
        """
        raise NotImplementedError()

    @abstractmethod
    async def count_new_since_last_search(
        self,
        candidate_id: UUID,
    ) -> int:
        """
        Count new job postings found since the candidate's last search.
        Used by SearchAgent to notify candidates of new opportunities.
        :param candidate_id: Candidate user ID.
        :return: Number of new job postings.
        """
        raise NotImplementedError()
