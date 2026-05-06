from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class JobSearchQuery:
    """
    Value Object representing a job search intent.
    Immutable — passed to JobScraperGateway port.
    """
    keywords: str
    location: str
    limit: int = 25
    remote_only: bool = False
    date_posted_within_days: int | None = 7
    easy_apply_only: bool | None = None  # None = both, True = Easy Apply only, False = external ATS only


@dataclass(frozen=True, slots=True)
class ScrapedJob:
    """
    Value Object representing a normalized job posting
    from any external source (LinkedIn, Indeed, JobUp…).

    Immutable snapshot — source-agnostic.
    Mapped to JobPosting entity for persistence.
    """
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    apply_url: str | None = None
    company_url: str | None = None
    posted_at: date | None = None
    is_remote: bool | None = None
    job_type: str | None = None  # full time, part-time, contract, internship
    insights: str | None = None  # LinkedIn-specific: "42 applicants"
    skills: tuple[str, ...] = field(default_factory=tuple)
