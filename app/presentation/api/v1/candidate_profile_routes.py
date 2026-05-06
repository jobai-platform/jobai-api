import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.application.users.candidate_profile_use_cases import UpsertProfileCommand
from app.application.users.cv_use_cases import UploadCVCommand
from app.core.dependency import (
    DeleteCVDep,
    GetCandidateProfileDep,
    UploadCVDep,
    UpsertCandidateProfileDep,
)
from app.domain.common.exceptions import BadRequestError, NotFoundError
from app.domain.users.candidate_profile import CandidateProfile
from app.presentation.api.v1.schemas.candidate_profile import (
    CVUploadResponse,
    CandidateProfileResponse,
    UpsertCandidateProfileRequest,
)
from app.presentation.security.deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/candidates", tags=["Candidate Profile"])

CurrentUserIdDep = Annotated[UUID, Depends(get_current_user_id)]


def _to_response(profile: CandidateProfile) -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        current_title=profile.current_title,
        years_of_experience=profile.years_of_experience,
        skills=profile.skills,
        desired_salary_min=profile.desired_salary_min,
        desired_salary_max=profile.desired_salary_max,
        preferred_locations=profile.preferred_locations,
        remote_preference=profile.remote_preference,
        bio=profile.bio,
        cv_url=profile.cv_url,
        is_complete=profile.is_complete,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/me/profile",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get my candidate profile",
)
async def get_my_profile(
    current_user_id: CurrentUserIdDep,
    use_case: GetCandidateProfileDep,
) -> CandidateProfileResponse:
    profile = await use_case.execute(current_user_id)
    return _to_response(profile)


@router.put(
    "/me/profile",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update my candidate profile",
)
async def upsert_my_profile(
    body: UpsertCandidateProfileRequest,
    current_user_id: CurrentUserIdDep,
    use_case: UpsertCandidateProfileDep,
) -> CandidateProfileResponse:
    profile = await use_case.execute(UpsertProfileCommand(
        user_id=current_user_id,
        current_title=body.current_title,
        years_of_experience=body.years_of_experience,
        skills=body.skills,
        desired_salary_min=body.desired_salary_min,
        desired_salary_max=body.desired_salary_max,
        preferred_locations=body.preferred_locations,
        remote_preference=body.remote_preference,
        bio=body.bio,
        cv_url=body.cv_url,
    ))
    return _to_response(profile)


@router.post(
    "/me/cv",
    response_model=CVUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload my CV",
    description="Upload a PDF or Word document (max 5 MB). Replaces any existing CV.",
    responses={
        201: {"description": "CV uploaded successfully"},
        400: {"description": "Invalid file (empty, too large, or wrong type)"},
        401: {"description": "Authentication required"},
        404: {"description": "Candidate profile not found"},
    },
)
async def upload_cv(
    file: UploadFile,
    current_user_id: CurrentUserIdDep,
    use_case: UploadCVDep,
) -> CVUploadResponse:
    data = await file.read()
    try:
        result = await use_case.execute(UploadCVCommand(
            user_id=current_user_id,
            filename=file.filename or "cv",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        ))
    except BadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from None
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.code) from None
    return CVUploadResponse(key=result.key, url=result.url, size=result.size, content_type=result.content_type)


@router.delete(
    "/me/cv",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my CV",
    responses={
        204: {"description": "CV deleted"},
        400: {"description": "No CV to delete"},
        401: {"description": "Authentication required"},
        404: {"description": "Candidate profile not found"},
    },
)
async def delete_cv(
    current_user_id: CurrentUserIdDep,
    use_case: DeleteCVDep,
) -> Response:
    try:
        await use_case.execute(current_user_id)
    except BadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from None
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.code) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
