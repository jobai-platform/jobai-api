import asyncio
import logging
from typing import Optional

from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import Events, EventData
from linkedin_jobs_scraper.query import Query, QueryOptions, QueryFilters
from linkedin_jobs_scraper.filters import TimeFilters, OnSiteOrRemoteFilters

from app.application.job_search.ports import JobScraperGateway
from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob

logger = logging.getLogger(__name__)


class LinkedInJobsScraperAdapter(JobScraperGateway):
    """
    Infrastructure adapter for linkedin-jobs-scraper library.

    Wraps the synchronous Chromium-based scraper in an async interface
    via asyncio.run_in_executor to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        self._scraper = LinkedinScraper(
            headless=True,
            max_workers=1,
            slow_mo=1.5,
            page_load_timeout=40,
        )

    def _build_query(self, query: JobSearchQuery) -> Query:
        """
        Convers a JobSearchQuery Value Object into a linkedin-jobs-scraper Query..
        :param query: JobSearchQuery Value Object.
        :return: Query.
        """
        filters = QueryFilters()

        if query.remote_only:
            filters.on_site_or_remote = OnSiteOrRemoteFilters.REMOTE

        if query.date_posted_within_days == 1:
            filters.time = TimeFilters.DAY
        elif query.date_posted_within_days == 7:
            filters.time = TimeFilters.WEEK
        elif query.date_posted_within_days == 30:
            filters.time = TimeFilters.MONTH

        return Query(
            query=query.keywords,
            options=QueryOptions(
                locations=[query.location],
                limit=query.limit,
                filters=filters,
            )
        )

    def _to_scraped_job(self, data: EventData) -> ScrapedJob:
        """
        Maps a linkedin_jobs_scraper EventData object to a ScrapedJob Value Object.
        :param data: EventData object.
        :return: ScrapedJob Value Object.
        """
        insights_raw = data.insights
        if isinstance(insights_raw, list):
            insights_str = " | ".join(str(i) for i in insights_raw) or None
        else:
            insights_str = str(insights_raw) if insights_raw else None

        return ScrapedJob(
            job_id=data.job_id,
            title=data.title,
            company=data.company,
            location=data.location,
            description=data.description,
            insights=insights_str,
            url=data.link,
            source="LinkedIn",
            apply_url=getattr(data, "apply_link", None),
            company_url=getattr(data, "company_link", None),
            posted_at=data.date if hasattr(data, "date") else None,
        )

    async def scrape_jobs(self, query: JobSearchQuery) -> list[ScrapedJob]:
        """
        Scrapes LinkedIn job posting matching the given query.
        Runs the asynchronous scraper in a thread pool to avoid blocking the event loop.
        :param query: JobSearchQuery Value Object.
        :return: list[ScrapedJob Value Object.]
        """
        results: list[ScrapedJob] = []
        errors: list[Exception] = []

        def on_data(data: EventData):
            try:
                job = self._to_scraped_job(data)
                results.append(job)
                logger.debug(
                    f"LinkedIn job scraped: job_id={job.job_id}, title={job.title}, company={job.company}",
                )
            except Exception as e:
                logger.error("Error mapping LinkedIn EventData: %s", e)

        def on_error(error: Exception) -> None:
            logger.error("LinkedIn scraper error: %s", error)
            errors.append(error)

        def on_end() -> None:
            logger.info(
                "LinkedIn scraper finished: %d jobs found, %d errors",
                len(results), len(errors),
            )

        self._scraper.on(Events.DATA, on_data)
        self._scraper.on(Events.ERROR, on_error)
        self._scraper.on(Events.END, on_end)

        linkedin_query = self._build_query(query)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._scraper.run([linkedin_query])
        )

        logger.info(
            "LinkedInJobScraperAdapter.search_jobs: "
            "Keywords=%r location=%r → %d results",
            query.keywords, query.location, len(results),
        )

        return results

    async def get_job_detail(self, job_id: str) -> Optional[ScrapedJob]:
        """
        Not implemented for LinkedIn scraper since it does not support fetching job details by ID.
        :param job_id: The ID of the job to fetch details for.
        :return: None, as this method is not supported.
        """
        logger.info(
            "get_job_detail not supported by LinkedInJobsScraperAdapter "
            "(job_id=%s). Returning None.",
            job_id,
        )
        return None

