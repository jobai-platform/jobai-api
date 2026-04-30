from dataclasses import dataclass

from app.domain.job_search.value_objects import ScrapedJob


@dataclass(frozen=True)
class JobSearchResult:
    """
    DTO returned by SearchJobsUseCase to the presentation layer.
    Equivalent to CheckoutSessionResult in the billing bounded context.

    Carries scraped jobs and search metadata.
    """
    jobs: list[ScrapedJob]
    total: int
    keywords: str
    location: str
    source: str

    @property
    def has_results(self) -> bool:
        return self.total > 0
