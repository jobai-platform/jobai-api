from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.application.ai_analysis.use_cases import ComputeMatchScoreCommand, IndexJobPostingCommand
from app.core.dependency import (
    ComputeMatchScoreDep,
    GetAnalysisDep,
    GetCandidateJobMatchesDep,
    IndexCandidateProfileDep,
    IndexJobPostingDep,
)
from app.core.rate_limiting import limiter
from app.domain.ai_analysis.enums import AnalysisStatus
from app.presentation.api.v1.schemas.ai_analysis import (
    AnalysisResponse,
    ComputeMatchRequest,
    IndexJobPostingRequest,
    JobMatchResponse,
)
from app.presentation.security.deps import get_current_user_id

router = APIRouter(tags=["AI Analysis"])

CurrentUserIdDep = Annotated[UUID, Depends(get_current_user_id)]


def _status_code_for(analysis_status: AnalysisStatus) -> int:
    if analysis_status in {AnalysisStatus.PENDING, AnalysisStatus.PROCESSING}:
        return status.HTTP_202_ACCEPTED
    return status.HTTP_200_OK


@router.post(
    "/analyses/",
    response_model=AnalysisResponse,
    summary="Compute a candidate/job matching score",
)
@limiter.limit("10/hour")
async def compute_match_score(
    request: Request,
    response: Response,
    body: ComputeMatchRequest,
    current_user_id: CurrentUserIdDep,
    use_case: ComputeMatchScoreDep,
) -> AnalysisResponse:
    analysis = await use_case.execute(
        ComputeMatchScoreCommand(
            candidate_id=body.candidate_id,
            job_posting_id=body.job_posting_id,
        )
    )
    response.status_code = _status_code_for(analysis.status)
    response.headers["Location"] = f"/api/v1/analyses/{analysis.id}"
    return AnalysisResponse.from_domain(analysis)


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an AI analysis by ID",
)
async def get_analysis(
    analysis_id: UUID,
    current_user_id: CurrentUserIdDep,
    use_case: GetAnalysisDep,
) -> AnalysisResponse:
    analysis = await use_case.execute(analysis_id)
    return AnalysisResponse.from_domain(analysis)


@router.get(
    "/candidates/{candidate_id}/analyses/",
    response_model=list[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="List analyses for a candidate",
)
async def list_candidate_analyses(
    candidate_id: UUID,
    current_user_id: CurrentUserIdDep,
    use_case: GetAnalysisDep,
) -> list[AnalysisResponse]:
    analyses = await use_case.find_by_candidate(candidate_id)
    return [AnalysisResponse.from_domain(analysis) for analysis in analyses]


@router.get(
    "/candidates/{candidate_id}/job-matches/",
    response_model=list[JobMatchResponse],
    status_code=status.HTTP_200_OK,
    summary="Get ranked job matches for a candidate",
)
async def get_candidate_job_matches(
    candidate_id: UUID,
    current_user_id: CurrentUserIdDep,
    use_case: GetCandidateJobMatchesDep,
    top_k: int = 20,
) -> list[JobMatchResponse]:
    matches = await use_case.execute(candidate_id=candidate_id, top_k=top_k)
    return [JobMatchResponse.from_domain(match) for match in matches]


@router.post(
    "/candidates/{candidate_id}/index",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index a candidate profile for matching",
)
async def index_candidate_profile(
    candidate_id: UUID,
    current_user_id: CurrentUserIdDep,
    use_case: IndexCandidateProfileDep,
) -> dict[str, str]:
    await use_case.execute(candidate_id)
    return {"message": "indexing started"}


@router.post(
    "/job-postings/{job_posting_id}/index",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index a job posting for matching",
)
async def index_job_posting(
    job_posting_id: UUID,
    body: IndexJobPostingRequest,
    current_user_id: CurrentUserIdDep,
    use_case: IndexJobPostingDep,
) -> dict[str, str]:
    await use_case.execute(
        IndexJobPostingCommand(
            job_posting_id=job_posting_id,
            description=body.description,
        )
    )
    return {"message": "indexing started"}
