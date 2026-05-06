import asyncio
import logging
from datetime import date
from typing import Optional

from app.application.job_search.ports import JobScraperGateway
from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob

logger = logging.getLogger(__name__)


class LinkedInJobsScraperAdapter(JobScraperGateway):
    """
    Infrastructure adapter using python-jobspy (no Selenium/Chrome).
    Calls LinkedIn's internal search API via httpx.
    """

    def _build_site_name(self) -> list[str]:
        return ["linkedin"]

    def _map_hours_old(self, days: int | None) -> int | None:
        if days is None:
            return None
        return days * 24

    async def search_jobs(self, query: JobSearchQuery) -> list[ScrapedJob]:
        logger.info(
            "JobSpyAdapter.search_jobs: keywords=%r location=%r limit=%d remote_only=%s",
            query.keywords,
            query.location,
            query.limit,
            query.remote_only,
        )

        loop = asyncio.get_event_loop()
        try:
            jobs_df = await loop.run_in_executor(
                None,
                lambda: self._run_scrape(query),
            )
        except Exception as exc:
            logger.error("JobSpyAdapter.search_jobs: scrape failed — %s", exc)
            raise RuntimeError(f"Job scraper failed: {exc}") from exc

        results: list[ScrapedJob] = []
        for _, row in jobs_df.iterrows():
            try:
                results.append(self._row_to_scraped_job(row))
            except Exception as exc:
                logger.warning("JobSpyAdapter: skipping row due to mapping error — %s", exc)

        logger.info(
            "JobSpyAdapter.search_jobs: %d jobs returned for keywords=%r location=%r",
            len(results),
            query.keywords,
            query.location,
        )
        return results

    def _run_scrape(self, query: JobSearchQuery):
        from jobspy import scrape_jobs  # local import — heavy dep

        return scrape_jobs(
            site_name=self._build_site_name(),
            search_term=query.keywords,
            location=query.location,
            results_wanted=query.limit,
            is_remote=query.remote_only,
            hours_old=self._map_hours_old(query.date_posted_within_days),
            linkedin_fetch_description=True,
        )

    def _row_to_scraped_job(self, row) -> ScrapedJob:
        posted_at: date | None = None
        raw_date = row.get("date_posted")
        if raw_date is not None:
            try:
                posted_at = raw_date.date() if hasattr(raw_date, "date") else date.fromisoformat(str(raw_date))
            except Exception:
                posted_at = None

        skills_raw = row.get("skills") or []
        if isinstance(skills_raw, str):
            skills: tuple[str, ...] = tuple(s.strip() for s in skills_raw.split(",") if s.strip())
        elif hasattr(skills_raw, "__iter__"):
            skills = tuple(str(s) for s in skills_raw if s)
        else:
            skills = ()

        job_type_raw = row.get("job_type")
        job_type = str(job_type_raw) if job_type_raw else None

        return ScrapedJob(
            job_id=str(row.get("id") or row.get("job_url") or ""),
            title=str(row.get("title") or ""),
            company=str(row.get("company") or ""),
            location=str(row.get("location") or ""),
            description=str(row.get("description") or ""),
            url=str(row.get("job_url") or ""),
            source="LinkedIn",
            apply_url=str(row["job_url_direct"]) if row.get("job_url_direct") else None,
            company_url=str(row["company_url"]) if row.get("company_url") else None,
            posted_at=posted_at,
            is_remote=bool(row.get("is_remote")) if row.get("is_remote") is not None else None,
            job_type=job_type,
            insights=None,
            skills=skills,
        )

    async def get_job_detail(self, job_id: str) -> Optional[ScrapedJob]:
        logger.info(
            "JobSpyAdapter.get_job_detail: not supported (job_id=%s), returning None",
            job_id,
        )
        return None
