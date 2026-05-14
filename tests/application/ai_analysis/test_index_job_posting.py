from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import IndexJobPostingCommand, IndexJobPostingUseCase
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore


@pytest.mark.asyncio
async def test_index_job_posting_upserts_embedding():
    vector_store = FakeVectorStore()
    job_id = uuid4()

    use_case = IndexJobPostingUseCase(
        embedding=FakeEmbeddingPort(),
        vector_store=vector_store,
    )
    await use_case.execute(
        IndexJobPostingCommand(
            job_posting_id=job_id,
            description="Senior Python developer needed. FastAPI, PostgreSQL required.",
        )
    )

    stored = await vector_store.get_job(job_id)
    assert stored is not None
    assert stored.job_posting_id == job_id
    assert len(stored.vector) == 768


@pytest.mark.asyncio
async def test_index_job_posting_raises_on_empty_description():
    use_case = IndexJobPostingUseCase(
        embedding=FakeEmbeddingPort(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="description"):
        await use_case.execute(
            IndexJobPostingCommand(job_posting_id=uuid4(), description="   ")
        )


@pytest.mark.asyncio
async def test_index_job_posting_stores_metadata():
    vector_store = FakeVectorStore()
    job_id = uuid4()

    use_case = IndexJobPostingUseCase(
        embedding=FakeEmbeddingPort(),
        vector_store=vector_store,
    )
    await use_case.execute(
        IndexJobPostingCommand(
            job_posting_id=job_id,
            description="Python backend role",
            metadata={"title": "Backend Engineer", "company": "Acme"},
        )
    )

    stored = await vector_store.get_job(job_id)
    assert stored.metadata["title"] == "Backend Engineer"
    assert stored.metadata["company"] == "Acme"
