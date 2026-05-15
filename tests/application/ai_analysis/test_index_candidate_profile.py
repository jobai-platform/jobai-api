from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import IndexCandidateProfileUseCase
from app.domain.common.exceptions import NotFoundError
from app.domain.users.candidate_profile import CandidateProfile
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore
from tests.fakes.users.in_memory_candidate_profile_repo import InMemoryCandidateProfileRepository


def _make_profile(user_id=None) -> CandidateProfile:
    return CandidateProfile(
        user_id=user_id or uuid4(),
        current_title="Senior Python Developer",
        skills=["python", "fastapi", "postgresql"],
        bio="Backend engineer with 8 years experience.",
    )


@pytest.mark.asyncio
async def test_index_candidate_profile_upserts_embedding_to_vector_store():
    profile_repo = InMemoryCandidateProfileRepository()
    vector_store = FakeVectorStore()
    user_id = uuid4()
    profile = _make_profile(user_id=user_id)
    await profile_repo.save(profile)

    use_case = IndexCandidateProfileUseCase(
        profile_repo=profile_repo,
        embedding=FakeEmbeddingPort(),
        vector_store=vector_store,
    )
    await use_case.execute(user_id=user_id)

    stored = await vector_store.get_candidate(user_id)
    assert stored is not None
    assert stored.candidate_id == user_id
    assert len(stored.vector) == 768  # FakeEmbeddingPort returns [0.1] * 768


@pytest.mark.asyncio
async def test_index_candidate_profile_raises_not_found_when_no_profile():
    profile_repo = InMemoryCandidateProfileRepository()
    use_case = IndexCandidateProfileUseCase(
        profile_repo=profile_repo,
        embedding=FakeEmbeddingPort(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(NotFoundError):
        await use_case.execute(user_id=uuid4())


@pytest.mark.asyncio
async def test_index_candidate_profile_stores_metadata():
    profile_repo = InMemoryCandidateProfileRepository()
    vector_store = FakeVectorStore()
    user_id = uuid4()
    profile = _make_profile(user_id=user_id)
    await profile_repo.save(profile)

    use_case = IndexCandidateProfileUseCase(
        profile_repo=profile_repo,
        embedding=FakeEmbeddingPort(),
        vector_store=vector_store,
    )
    await use_case.execute(user_id=user_id)

    stored = await vector_store.get_candidate(user_id)
    assert stored.metadata["skills"] == ["python", "fastapi", "postgresql"]
    assert stored.metadata["title"] == "Senior Python Developer"
    assert "years_of_experience" in stored.metadata
