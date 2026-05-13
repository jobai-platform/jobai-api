from uuid import uuid4

from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.infrastructure.ai.pipeline.state import PipelineState, make_initial_state


def test_make_initial_state_sets_defaults():
    """GIVEN valid IDs and tier
    WHEN make_initial_state is called
    THEN state has None for all computed fields and retry_count=0
    """
    candidate_id = uuid4()
    job_posting_id = uuid4()
    analysis_id = uuid4()

    state = make_initial_state(
        candidate_id=candidate_id,
        job_posting_id=job_posting_id,
        tier=AnalysisQualityTier.FAST,
        analysis_id=analysis_id,
    )

    assert state["candidate_id"] == candidate_id
    assert state["job_posting_id"] == job_posting_id
    assert state["tier"] == AnalysisQualityTier.FAST
    assert state["analysis_id"] == analysis_id
    assert state["structured_profile"] is None
    assert state["structured_job"] is None
    assert state["context_jobs"] == []
    assert state["raw_scores"] is None
    assert state["match_score"] is None
    assert state["retry_count"] == 0
    assert state["error"] is None
