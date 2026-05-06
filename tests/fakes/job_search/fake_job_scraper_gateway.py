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


class FakeJobPostingRepository:
    """
    In-memory fake for JobPostingRepository.
    Use in application-layer tests — no DB needed.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], "JobPosting"] = {}
        self.upserted: list = []

    async def upsert(self, job) -> "JobPosting":
        key = (job.external_id, job.source)
        self._store[key] = job
        self.upserted.append(job)
        return job

    async def get_by_external_id(
        self, external_id: str, source: str
    ) -> Optional["JobPosting"]:
        return self._store.get((external_id, source))

    async def list_by_candidate(
        self, candidate_id, limit: int = 50, offset: int = 0
    ) -> list:
        return list(self._store.values())[offset: offset + limit]

    async def count_new_since_last_search(self, candidate_id) -> int:
        return 0
