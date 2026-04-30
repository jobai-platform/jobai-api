from datetime import date
from typing import Optional

from app.domain.job_search.value_objects import JobSearchQuery, ScrapedJob
from app.application.job_search.ports import JobScraperGateway


def make_scraped_job(**kwargs) -> ScrapedJob:
    """Factory helper — overridable defaults for tests."""
    defaults = {
        "job_id": "job_001",
        "title": "Senior Python Developer",
        "company": "Acme Corp",
        "location": "Geneva, Switzerland",
        "description": "We are looking for a senior Python developer...",
        "url": "https://linkedin.com/jobs/view/001",
        "source": "linkedin",
        "apply_url": "https://linkedin.com/jobs/apply/001",
        "company_url": "https://linkedin.com/company/acme",
        "posted_at": date(2026, 4, 28),
        "is_remote": False,
        "job_type": "fulltime",
    }
    return ScrapedJob(**{**defaults, **kwargs})


class FakeJobScraperGateway(JobScraperGateway):
    """
    In-memory fake implementation for unit tests.
    Controllable: inject expected results via constructor.
    Tracks calls for assertion in tests.
    """
    def __init__(self, jobs: list[ScrapedJob] | None = None) -> None:
        self._jobs = jobs or []
        self.search_calls: list[JobSearchQuery] = []
        self.detail_calls: list[str] = []

    async def search_jobs(self, query: JobSearchQuery) -> list[ScrapedJob]:
        self.search_calls.append(query)
        return self._jobs

    async def get_job_detail(self, job_id: str) -> Optional[ScrapedJob]:
        self.detail_calls.append(job_id)
        return next((j for j in self._jobs if j.job_id == job_id), None)
