from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    """Request schema for job search."""
    keywords: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)
    remote_only: bool = Field(default=False)
    date_posted_within_days: Optional[int] = Field(default=7, ge=1, le=30)


class ScrapedJobSchema(BaseModel):
    """Response schema for a single job posting."""
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
    job_type: Optional[str] = None
    insights: Optional[str] = None
    skills: list[str] = []

    model_config = {"from_attributes": True}


class JobSearchResponse(BaseModel):
    """Response schema for job search endpoint."""
    jobs: list[ScrapedJobSchema]
    total: int
    keywords: str
    location: str
    source: str
    has_results: bool
