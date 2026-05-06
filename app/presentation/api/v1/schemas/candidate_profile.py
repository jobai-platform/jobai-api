from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.domain.users.candidate_profile import RemotePreference


class UpsertCandidateProfileRequest(BaseModel):
    current_title: Optional[str] = Field(default=None, max_length=255)
    years_of_experience: Optional[int] = Field(default=None, ge=0)
    skills: Optional[list[str]] = None
    desired_salary_min: Optional[int] = Field(default=None, ge=0)
    desired_salary_max: Optional[int] = Field(default=None, ge=0)
    preferred_locations: Optional[list[str]] = None
    remote_preference: Optional[RemotePreference] = None
    bio: Optional[str] = Field(default=None, max_length=2000)
    cv_url: Optional[str] = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_salary_range(self) -> "UpsertCandidateProfileRequest":
        if (
            self.desired_salary_min is not None
            and self.desired_salary_max is not None
            and self.desired_salary_min > self.desired_salary_max
        ):
            raise ValueError("desired_salary_min cannot exceed desired_salary_max")
        return self


class CVUploadResponse(BaseModel):
    key: str
    url: str
    size: int
    content_type: str


class CandidateProfileResponse(BaseModel):
    id: Optional[UUID]
    user_id: UUID
    current_title: Optional[str]
    years_of_experience: Optional[int]
    skills: list[str]
    desired_salary_min: Optional[int]
    desired_salary_max: Optional[int]
    preferred_locations: list[str]
    remote_preference: RemotePreference
    bio: Optional[str]
    cv_url: Optional[str]
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
