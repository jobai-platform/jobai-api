from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class JobSearchQuery:
    """
    Value Object representing a job search intent.
    Immutable — passed to JobScraperGateway port.
    Encapsulates all search criteria for a job search operation.

    Ubiquitous Language:
    - keywords              : job title, skills or any search term
    - location              : target city, region or country
    - remote_only           : filter for remote positions only
    - date_posted_within_days : recency filter (1=today, 7=this week…)
    """
    keywords: str
    location: str
    limit: int = 25
    remote_only: bool = False
    date_posted_within_days: Optional[int] = 7


@dataclass(frozen=True, slots=True)
class ScrapedJob:
    """
    Value Object representing a normalized job posting
    from any external source (LinkedIn, Indeed, JobUp…).

    Immutable snapshot — source-agnostic.
    Mapped to JobPosting entity for persistence.

    Ubiquitous Language:
    - job_id    : external identifier from the source platform
    - source    : origin platform (LinkedIn, Indeed, JobUp…)
    - insights  : platform-specific metadata (ex: "42 applicants")
    """
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    apply_url: Optional[str] = None
    company_url: Optional[str] = None
    posted_at: Optional[date] = None
    is_remote: Optional[bool] = None
    job_type: Optional[str] = None # full time, part-time, contract, internship
    insights: Optional[str] = None # LinkedIn-specific: "42 applicants"
    skills: tuple[str, ...] = field(default_factory=tuple)
