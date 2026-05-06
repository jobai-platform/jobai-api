from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    """Request schema for job search."""
    keywords: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)
    remote_only: bool = Field(default=False)
    date_posted_within_days: Optional[int] = Field(default=7, ge=1, le=30)
    easy_apply_only: Optional[bool] = Field(default=None)


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


# ---------------------------------------------------------------------------
# SearchAgent schemas
# ---------------------------------------------------------------------------

class SearchAgentCreateRequest(BaseModel):
    keywords: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    remote_only: bool = Field(default=False)
    date_posted_within_days: int = Field(default=7, ge=1, le=30)
    limit: int = Field(default=25, ge=1, le=100)
    easy_apply_only: Optional[bool] = Field(
        default=None,
        description="null = both, true = Easy Apply only, false = external ATS only",
    )


class SearchAgentUpdateRequest(BaseModel):
    keywords: Optional[str] = Field(default=None, min_length=1, max_length=255)
    location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    remote_only: Optional[bool] = None
    date_posted_within_days: Optional[int] = Field(default=None, ge=1, le=30)
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    easy_apply_only: Optional[bool] = None


class SearchAgentResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    keywords: str
    location: str
    remote_only: bool
    date_posted_within_days: int
    limit: int
    easy_apply_only: Optional[bool] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunSearchAgentResponse(BaseModel):
    agent: SearchAgentResponse
    jobs_found: int
