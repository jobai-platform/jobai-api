import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException

from app.core.dependency import SearchJobsDep
from app.presentation.api.mappers.job_search_mapper import to_job_search_response
from app.presentation.api.v1.schemas.job_search import JobSearchResponse, JobSearchRequest
from app.presentation.security.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs Search"])

CurrentUserIdDep = Annotated[UUID, Depends(get_current_user_id)]


@router.post(
    "/search",
    response_model=JobSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for Jobs postings",
    description=(
        "Search for job postings on LinkedIn matching the given criteria."
        "Results are scraped in real-time and persisted for deduplication."
        "Requires authentication"
    ),
    responses={
        200: {"description": "Job search results"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
        502: {"description": "Scraper unavailable"},
    },
)
async def search_jobs(
    payload: JobSearchRequest,
    current_user_id: CurrentUserIdDep,
    use_case: SearchJobsDep,
) -> JobSearchResponse:
    """
    Search for jobs postings matching the given criteria.
    Scrape LinkedIn and persists results for deduplication.
    :param payload: Job search payload
    :param current_user_id: Current user ID
    :param use_case: UseCase instance
    :return: Job search results
    """
    try:
        result = await use_case.execute(
            keywords=payload.keywords,
            location=payload.location,
            limit=payload.limit,
            remote_only=payload.remote_only,
            date_posted_within_days=payload.date_posted_within_days,
            easy_apply_only=payload.easy_apply_only,
        )
        return to_job_search_response(result)
    except RuntimeError as exc:
        logger.error("Scraper unavailable for user_id=%s: %s", current_user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Job scraper temporarily unavailable. Please try again later.",
        )
