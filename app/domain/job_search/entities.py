from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID


@dataclass(slots=True)
class JobPosting:
    """
    Domain entity representing a job posting.
    Sourced from external scrapers (LinkedIn, Indeed, JobUp…).
    Immutable after creation — updates create new instances.

    Ubiquitous Language:
    - JobPosting  : une offre d'emploi publique
    - external_id : identifiant côté source (LinkedIn job_id, etc.)
    - source      : plateforme d'origine (linkedin, indeed, jobup…)
    """
    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str

    # Optional enrichment
    apply_url: Optional[str] = None
    company_url: Optional[str] = None
    posted_at: Optional[date] = None
    is_remote: Optional[bool] = None
    job_type: Optional[str] = None       # full time, part-time, contract, internship
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    insights: Optional[str] = None       # Ex: "42 candidats" (LinkedIn-specific)
    skills: list[str] = field(default_factory=list)

    # Internal tracking
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    def is_salary_available(self) -> bool:
        """Returns True if at least a min or max salary is specified."""
        return self.salary_min is not None or self.salary_max is not None

    def salary_range_label(self) -> Optional[str]:
        """
        Human-readable salary range.
        Ex: 'CHF 80,000 – 120,000' or 'CHF 80,000+'
        """
        if not self.is_salary_available():
            return None

        currency = self.salary_currency or "CHF"

        if self.salary_min and self.salary_max:
            return f"{currency} {self.salary_min:,.0f} – {self.salary_max:,.0f}"
        if self.salary_min:
            return f"{currency} {self.salary_min:,.0f}+"
        return f"Up to {currency} {self.salary_max:,.0f}"
