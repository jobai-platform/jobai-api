from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.application.ai_analysis.ports import SimilarityResult
from app.domain.job_search.entities import JobPosting
from app.domain.users.candidate_profile import CandidateProfile


def serialize_candidate_profile(profile: CandidateProfile) -> dict[str, Any]:
    return {
        "id": str(profile.id) if profile.id else None,
        "user_id": str(profile.user_id),
        "current_title": profile.current_title,
        "years_of_experience": profile.years_of_experience,
        "skills": profile.skills,
        "desired_salary_min": profile.desired_salary_min,
        "desired_salary_max": profile.desired_salary_max,
        "preferred_locations": profile.preferred_locations,
        "remote_preference": profile.remote_preference.value,
        "bio": profile.bio,
        "cv_url": profile.cv_url,
        "is_complete": profile.is_complete,
        "created_at": _format_temporal(profile.created_at),
        "updated_at": _format_temporal(profile.updated_at),
    }


def serialize_cv_text(profile: CandidateProfile) -> dict[str, Any]:
    return {
        "user_id": str(profile.user_id),
        "cv_url": profile.cv_url,
        "text": None,
        "status": "not_uploaded" if profile.cv_url is None else "external_document",
    }


def serialize_job_posting(job: JobPosting) -> dict[str, Any]:
    return {
        "id": str(job.id) if job.id else None,
        "external_id": job.external_id,
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "url": job.url,
        "apply_url": job.apply_url,
        "company_url": job.company_url,
        "posted_at": _format_temporal(job.posted_at),
        "is_remote": job.is_remote,
        "job_type": job.job_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "insights": job.insights,
        "skills": list(job.skills),
        "created_at": _format_temporal(job.created_at),
    }


def serialize_similarity_result(result: SimilarityResult) -> dict[str, Any]:
    return {
        "id": str(result.id),
        "similarity_score": round(result.similarity_score, 12),
        "metadata": result.metadata,
    }


def _format_temporal(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
