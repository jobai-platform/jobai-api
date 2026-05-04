from dataclasses import dataclass

from app.domain.job_search.value_objects import ScrapedJob


@dataclass(frozen=True)
class JobSearchResult:
    """
    Represents an individual job search result.
    """
    jobs: list[ScrapedJob]
    total: int
    keywords: str
    location: str
    source: str

    @property
    def has_results(self) -> bool:
        return self.total > 0
