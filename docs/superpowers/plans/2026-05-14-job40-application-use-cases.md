# JOB-40 — Application Use Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 5 core application-layer use cases for the AI Analysis bounded context: match score computation (hybrid cache), analysis polling, candidate/job indexing, and top-K job match retrieval.

**Architecture:** Hexagonal architecture — use cases depend only on ports (ABCs/Protocols), never on infrastructure. All tests use fakes from `tests/fakes/ai_analysis/`. Commands/queries are typed dataclasses. The `AIAnalysis` entity drives state transitions (`start_processing → complete | fail`); a new `reset_for_retry()` mutation handles FAILED re-runs.

**Tech Stack:** Python 3.13, FastAPI (indirectly), SQLAlchemy (infra only), pytest-asyncio strict mode, dataclasses, `uuid.uuid4()`.

---

## Context — What Already Exists

Read these files before starting. Do not re-implement what is already there.

| File | What it contains |
|---|---|
| `app/domain/ai_analysis/entities.py` | `AIAnalysis` entity with `start_processing()`, `complete()`, `fail()` |
| `app/domain/ai_analysis/enums.py` | `AnalysisStatus`, `AnalysisQualityTier` |
| `app/domain/ai_analysis/value_objects.py` | `MatchScore` value object |
| `app/domain/ai_analysis/ports.py` | `EmbeddingPort`, `LLMGatewayPort` (Protocols) |
| `app/application/ai_analysis/ports.py` | `VectorStorePort`, `AIAnalysisPipelinePort`, `AIAnalysisRepository` |
| `app/application/ai_analysis/use_cases.py` | Existing: `GenerateEmbeddingsUseCase`, `GenerateLLMCompletionUseCase`, `AnalyzeJobDescriptionUseCase` — **append** new use cases here |
| `app/application/users/candidate_profile_ports.py` | `CandidateProfileRepository` (needed for indexing) |
| `app/domain/users/candidate_profile.py` | `CandidateProfile` entity |
| `tests/fakes/ai_analysis/in_memory_ai_analysis_repo.py` | `InMemoryAIAnalysisRepository` |
| `tests/fakes/ai_analysis/fake_pipeline_port.py` | `FakeAIPipelinePort` |
| `tests/fakes/ai_analysis/fake_vector_store.py` | `FakeVectorStore` |
| `tests/fakes/ai_analysis/fake_embedding_port.py` | `FakeEmbeddingPort` (returns `[0.1] * 768`) |
| `tests/fakes/users/in_memory_candidate_profile_repo.py` | `InMemoryCandidateProfileRepository` |

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| **Modify** | `app/domain/ai_analysis/entities.py` | Add `reset_for_retry()` method to `AIAnalysis` |
| **Modify** | `app/application/ai_analysis/use_cases.py` | Add 5 use cases + 3 command dataclasses |
| **Create** | `tests/application/ai_analysis/test_get_analysis.py` | Tests for `GetAnalysisUseCase` |
| **Create** | `tests/application/ai_analysis/test_compute_match_score.py` | Tests for `ComputeMatchScoreUseCase` |
| **Create** | `tests/application/ai_analysis/test_index_candidate_profile.py` | Tests for `IndexCandidateProfileUseCase` |
| **Create** | `tests/application/ai_analysis/test_index_job_posting.py` | Tests for `IndexJobPostingUseCase` |
| **Create** | `tests/application/ai_analysis/test_get_candidate_job_matches.py` | Tests for `GetCandidateJobMatchesUseCase` |

---

## Task 1: Domain — Add `reset_for_retry()` to `AIAnalysis`

**Files:**
- Modify: `app/domain/ai_analysis/entities.py`
- Test: `tests/domain/ai_analysis/test_ai_analysis_entity.py` (may already exist — check first; if not, create it)

### Why

`ComputeMatchScoreUseCase` must be able to re-run a FAILED analysis. The entity owns its own state transitions, so the reset logic belongs here.

---

- [ ] **Step 1: Write the failing test**

Check if `tests/domain/ai_analysis/test_ai_analysis_entity.py` exists. If not, create it. Add these tests:

```python
# tests/domain/ai_analysis/test_ai_analysis_entity.py
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore


def _make_analysis(status: AnalysisStatus = AnalysisStatus.PENDING) -> AIAnalysis:
    a = AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=status,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )
    return a


def test_reset_for_retry_from_failed_sets_status_to_pending():
    analysis = _make_analysis(AnalysisStatus.PENDING)
    analysis.status = AnalysisStatus.PROCESSING
    analysis.failure_reason = "timeout"
    analysis.status = AnalysisStatus.FAILED

    # manually set to FAILED without going through fail() to avoid invariant check
    analysis.status = AnalysisStatus.FAILED
    analysis.failure_reason = "timeout"

    analysis.reset_for_retry()

    assert analysis.status == AnalysisStatus.PENDING
    assert analysis.failure_reason is None
    assert analysis.completed_at is None


def test_reset_for_retry_raises_when_status_is_not_failed():
    analysis = _make_analysis(AnalysisStatus.PENDING)
    with pytest.raises(ValueError, match="Cannot retry"):
        analysis.reset_for_retry()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/domain/ai_analysis/test_ai_analysis_entity.py -v
```

Expected: `FAILED` — `AttributeError: 'AIAnalysis' object has no attribute 'reset_for_retry'`

- [ ] **Step 3: Implement `reset_for_retry()`**

Open `app/domain/ai_analysis/entities.py` and add after the `fail()` method:

```python
def reset_for_retry(self) -> None:
    if self.status != AnalysisStatus.FAILED:
        raise ValueError(
            f"Cannot retry from {self.status.name}. Expected status: {AnalysisStatus.FAILED.name}"
        )
    self.status = AnalysisStatus.PENDING
    self.failure_reason = None
    self.completed_at = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/domain/ai_analysis/test_ai_analysis_entity.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domain/ai_analysis/entities.py tests/domain/ai_analysis/test_ai_analysis_entity.py
git commit -m "feat(ai-analysis): add reset_for_retry() to AIAnalysis entity"
```

---

## Task 2: `GetAnalysisUseCase`

**Files:**
- Modify: `app/application/ai_analysis/use_cases.py`
- Create: `tests/application/ai_analysis/test_get_analysis.py`

Simplest use case: polling. Given an `analysis_id`, return the `AIAnalysis` or raise `NotFoundError`.

---

- [ ] **Step 1: Write the failing test**

```python
# tests/application/ai_analysis/test_get_analysis.py
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import GetAnalysisUseCase
from app.application.common.errors import NotFoundError
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from tests.fakes.ai_analysis.in_memory_ai_analysis_repo import InMemoryAIAnalysisRepository


def _make_analysis(status: AnalysisStatus = AnalysisStatus.COMPLETED) -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        candidate_id=uuid4(),
        job_posting_id=uuid4(),
        status=status,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_get_analysis_returns_analysis_when_found():
    repo = InMemoryAIAnalysisRepository()
    analysis = _make_analysis()
    await repo.save(analysis)

    use_case = GetAnalysisUseCase(repo=repo)
    result = await use_case.execute(analysis_id=analysis.id)

    assert result.id == analysis.id
    assert result.status == AnalysisStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_analysis_raises_not_found_when_missing():
    repo = InMemoryAIAnalysisRepository()
    use_case = GetAnalysisUseCase(repo=repo)

    with pytest.raises(NotFoundError, match="AIAnalysis"):
        await use_case.execute(analysis_id=uuid4())
```

- [ ] **Step 2: Check where `NotFoundError` lives**

```bash
grep -r "class NotFoundError" /Users/rsantos/Lab/jobai/backend-api/app --include="*.py" -l
```

Note the exact import path. If it's at `app/application/common/errors.py`, use that. If the file structure is different, adapt the import in the test and implementation accordingly.

- [ ] **Step 3: Run test to verify it fails**

```bash
poetry run pytest tests/application/ai_analysis/test_get_analysis.py -v
```

Expected: `FAILED` — `ImportError` or `AttributeError` for `GetAnalysisUseCase`.

- [ ] **Step 4: Implement `GetAnalysisUseCase`**

Open `app/application/ai_analysis/use_cases.py`. Add at the end of the file (after existing imports, add new ones at top):

Add to imports section at top:
```python
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime, UTC

from app.application.ai_analysis.ports import AIAnalysisRepository, AIAnalysisPipelinePort, VectorStorePort
from app.application.common.errors import NotFoundError
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.domain.ai_analysis.ports import EmbeddingPort
from app.application.users.candidate_profile_ports import CandidateProfileRepository
```

> **Note:** Adjust the import for `NotFoundError` based on where it lives (found in step 2). Do not add duplicate imports if some are already present.

Add the use case class:
```python
class GetAnalysisUseCase:
    def __init__(self, repo: AIAnalysisRepository) -> None:
        self._repo = repo

    async def execute(self, analysis_id: UUID) -> AIAnalysis:
        analysis = await self._repo.find_by_id(analysis_id)
        if analysis is None:
            raise NotFoundError("AIAnalysis", str(analysis_id))
        return analysis
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/application/ai_analysis/test_get_analysis.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/application/ai_analysis/use_cases.py tests/application/ai_analysis/test_get_analysis.py
git commit -m "feat(ai-analysis): add GetAnalysisUseCase"
```

---

## Task 3: `ComputeMatchScoreUseCase`

**Files:**
- Modify: `app/application/ai_analysis/use_cases.py`
- Create: `tests/application/ai_analysis/test_compute_match_score.py`

Hybrid cache pattern:
- **COMPLETED** → return as-is (cache hit, no pipeline call)
- **PENDING / PROCESSING** → return as-is (already in flight)
- **FAILED** → `reset_for_retry()`, then re-run pipeline
- **None (no existing)** → create fresh `AIAnalysis(PENDING)`, run pipeline

The use case always returns the (potentially updated) `AIAnalysis`. The HTTP layer (JOB-41) uses `analysis.status` to decide 200 vs 202.

---

- [ ] **Step 1: Write failing tests**

```python
# tests/application/ai_analysis/test_compute_match_score.py
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import ComputeMatchScoreUseCase, ComputeMatchScoreCommand
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisStatus, AnalysisQualityTier
from app.domain.ai_analysis.value_objects import MatchScore
from tests.fakes.ai_analysis.in_memory_ai_analysis_repo import InMemoryAIAnalysisRepository
from tests.fakes.ai_analysis.fake_pipeline_port import FakeAIPipelinePort


def _make_analysis(status: AnalysisStatus, candidate_id=None, job_posting_id=None) -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        candidate_id=candidate_id or uuid4(),
        job_posting_id=job_posting_id or uuid4(),
        status=status,
        match_score=None,
        quality_tier=AnalysisQualityTier.FAST,
        tokens_consumed=0,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


def _make_completed_analysis(candidate_id=None, job_posting_id=None) -> AIAnalysis:
    score = MatchScore(
        overall=0.9,
        skills_score=0.9,
        experience_score=0.9,
        location_score=0.9,
        salary_score=0.9,
        explanation="cached",
    )
    a = _make_analysis(AnalysisStatus.COMPLETED, candidate_id, job_posting_id)
    a.match_score = score
    return a


@pytest.mark.asyncio
async def test_returns_cached_analysis_when_completed():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()
    cached = _make_completed_analysis(candidate_id=candidate_id, job_posting_id=job_id)
    await repo.save(cached)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.id == cached.id
    assert result.status == AnalysisStatus.COMPLETED
    assert len(pipeline.calls) == 0  # pipeline NOT called for cache hit


@pytest.mark.asyncio
async def test_returns_in_progress_analysis_without_running_pipeline():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()
    in_progress = _make_analysis(AnalysisStatus.PROCESSING, candidate_id, job_id)
    await repo.save(in_progress)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.status == AnalysisStatus.PROCESSING
    assert len(pipeline.calls) == 0


@pytest.mark.asyncio
async def test_creates_new_analysis_and_runs_pipeline_when_no_existing():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(
            candidate_id=candidate_id,
            job_posting_id=job_id,
            tier=AnalysisQualityTier.BALANCED,
        )
    )

    assert result.status == AnalysisStatus.COMPLETED
    assert result.match_score is not None
    assert result.match_score.overall == 0.75  # FakeAIPipelinePort default
    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["tier"] == AnalysisQualityTier.BALANCED


@pytest.mark.asyncio
async def test_resets_failed_analysis_and_reruns_pipeline():
    repo = InMemoryAIAnalysisRepository()
    pipeline = FakeAIPipelinePort()
    candidate_id, job_id = uuid4(), uuid4()

    failed = _make_analysis(AnalysisStatus.FAILED, candidate_id, job_id)
    failed.failure_reason = "timeout"
    await repo.save(failed)

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=pipeline)
    result = await use_case.execute(
        ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
    )

    assert result.status == AnalysisStatus.COMPLETED
    assert result.failure_reason is None
    assert len(pipeline.calls) == 1


@pytest.mark.asyncio
async def test_marks_analysis_as_failed_when_pipeline_raises():
    repo = InMemoryAIAnalysisRepository()
    candidate_id, job_id = uuid4(), uuid4()

    class FailingPipeline(FakeAIPipelinePort):
        async def run(self, candidate_id, job_posting_id, tier, analysis_id):
            raise RuntimeError("LLM unavailable")

    use_case = ComputeMatchScoreUseCase(repo=repo, pipeline=FailingPipeline())

    with pytest.raises(RuntimeError, match="LLM unavailable"):
        await use_case.execute(
            ComputeMatchScoreCommand(candidate_id=candidate_id, job_posting_id=job_id)
        )

    # The analysis should have been saved as FAILED
    saved = await repo.find_by_candidate_and_job(candidate_id, job_id)
    assert saved is not None
    assert saved.status == AnalysisStatus.FAILED
    assert "LLM unavailable" in (saved.failure_reason or "")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/application/ai_analysis/test_compute_match_score.py -v
```

Expected: `FAILED` — `ImportError` for `ComputeMatchScoreUseCase`, `ComputeMatchScoreCommand`.

- [ ] **Step 3: Implement `ComputeMatchScoreCommand` and `ComputeMatchScoreUseCase`**

Append to `app/application/ai_analysis/use_cases.py`:

```python
@dataclass(frozen=True, slots=True)
class ComputeMatchScoreCommand:
    candidate_id: UUID
    job_posting_id: UUID
    tier: AnalysisQualityTier = AnalysisQualityTier.FAST


class ComputeMatchScoreUseCase:
    def __init__(
        self,
        repo: AIAnalysisRepository,
        pipeline: AIAnalysisPipelinePort,
    ) -> None:
        self._repo = repo
        self._pipeline = pipeline

    async def execute(self, command: ComputeMatchScoreCommand) -> AIAnalysis:
        existing = await self._repo.find_by_candidate_and_job(
            command.candidate_id, command.job_posting_id
        )

        if existing is not None:
            if existing.status == AnalysisStatus.COMPLETED:
                return existing
            if existing.status in (AnalysisStatus.PENDING, AnalysisStatus.PROCESSING):
                return existing
            if existing.status == AnalysisStatus.FAILED:
                existing.reset_for_retry()
                await self._repo.save(existing)
                analysis = existing
            else:
                analysis = existing
        else:
            analysis = AIAnalysis(
                id=uuid4(),
                candidate_id=command.candidate_id,
                job_posting_id=command.job_posting_id,
                status=AnalysisStatus.PENDING,
                match_score=None,
                quality_tier=command.tier,
                tokens_consumed=0,
                created_at=datetime.now(UTC),
                completed_at=None,
            )

        analysis.start_processing()
        await self._repo.save(analysis)

        try:
            score = await self._pipeline.run(
                candidate_id=analysis.candidate_id,
                job_posting_id=analysis.job_posting_id,
                tier=command.tier,
                analysis_id=analysis.id,
            )
            analysis.complete(score)
        except Exception as exc:
            analysis.fail(str(exc))
            await self._repo.save(analysis)
            raise

        await self._repo.save(analysis)
        return analysis
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/application/ai_analysis/test_compute_match_score.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/application/ai_analysis/use_cases.py tests/application/ai_analysis/test_compute_match_score.py
git commit -m "feat(ai-analysis): add ComputeMatchScoreUseCase with hybrid cache pattern"
```

---

## Task 4: `IndexCandidateProfileUseCase`

**Files:**
- Modify: `app/application/ai_analysis/use_cases.py`
- Create: `tests/application/ai_analysis/test_index_candidate_profile.py`

Fetches `CandidateProfile` by `candidate_id` (via `user_id` — note: `CandidateProfile.user_id` is the FK), generates an embedding from `title + skills + bio`, and upserts to the vector store.

**Important:** `CandidateProfile` uses `user_id` as the identifier (not a separate `candidate_id`). The use case takes `user_id` (which is the candidate's user account ID).

---

- [ ] **Step 1: Write the failing test**

```python
# tests/application/ai_analysis/test_index_candidate_profile.py
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import IndexCandidateProfileUseCase
from app.application.common.errors import NotFoundError
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
    embedding_port = FakeEmbeddingPort()
    vector_store = FakeVectorStore()

    user_id = uuid4()
    profile = _make_profile(user_id=user_id)
    await profile_repo.save(profile)

    use_case = IndexCandidateProfileUseCase(
        profile_repo=profile_repo,
        embedding=embedding_port,
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

    with pytest.raises(NotFoundError, match="CandidateProfile"):
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/application/ai_analysis/test_index_candidate_profile.py -v
```

Expected: `FAILED` — `ImportError` for `IndexCandidateProfileUseCase`.

- [ ] **Step 3: Implement `IndexCandidateProfileUseCase`**

Append to `app/application/ai_analysis/use_cases.py`:

```python
class IndexCandidateProfileUseCase:
    def __init__(
        self,
        profile_repo: CandidateProfileRepository,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
    ) -> None:
        self._profile_repo = profile_repo
        self._embedding = embedding
        self._vector_store = vector_store

    async def execute(self, user_id: UUID) -> None:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("CandidateProfile", str(user_id))

        parts = []
        if profile.current_title:
            parts.append(profile.current_title)
        if profile.skills:
            parts.append(" ".join(profile.skills))
        if profile.bio:
            parts.append(profile.bio)
        profile_text = " ".join(parts)

        vector = await self._embedding.generate_embedding(profile_text)
        metadata = {
            "title": profile.current_title,
            "skills": profile.skills,
            "years_of_experience": profile.years_of_experience,
        }
        await self._vector_store.upsert_candidate(user_id, vector, metadata)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/application/ai_analysis/test_index_candidate_profile.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/application/ai_analysis/use_cases.py tests/application/ai_analysis/test_index_candidate_profile.py
git commit -m "feat(ai-analysis): add IndexCandidateProfileUseCase"
```

---

## Task 5: `IndexJobPostingUseCase`

**Files:**
- Modify: `app/application/ai_analysis/use_cases.py`
- Create: `tests/application/ai_analysis/test_index_job_posting.py`

Simpler than candidate indexing: takes `job_posting_id` + `description` text directly (no repo lookup needed — the caller already has the description).

---

- [ ] **Step 1: Write the failing test**

```python
# tests/application/ai_analysis/test_index_job_posting.py
from uuid import uuid4

import pytest

from app.application.ai_analysis.use_cases import IndexJobPostingUseCase, IndexJobPostingCommand
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/application/ai_analysis/test_index_job_posting.py -v
```

Expected: `FAILED` — `ImportError`.

- [ ] **Step 3: Implement `IndexJobPostingCommand` and `IndexJobPostingUseCase`**

Append to `app/application/ai_analysis/use_cases.py`:

```python
@dataclass(frozen=True, slots=True)
class IndexJobPostingCommand:
    job_posting_id: UUID
    description: str
    metadata: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        # dataclass frozen=True — use object.__setattr__ to set default
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class IndexJobPostingUseCase:
    def __init__(
        self,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
    ) -> None:
        self._embedding = embedding
        self._vector_store = vector_store

    async def execute(self, command: IndexJobPostingCommand) -> None:
        if not command.description or not command.description.strip():
            raise ValueError("description cannot be empty")
        vector = await self._embedding.generate_embedding(command.description)
        await self._vector_store.upsert_job(command.job_posting_id, vector, command.metadata)
```

> **Note on mutable default in frozen dataclass:** The pattern above sets `metadata` default to `None` and patches it in `__post_init__`. An alternative is to use `field(default_factory=dict)` — but that conflicts with `frozen=True` when the field is a mutable type. The `object.__setattr__` approach is standard for this case in Python.

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/application/ai_analysis/test_index_job_posting.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/application/ai_analysis/use_cases.py tests/application/ai_analysis/test_index_job_posting.py
git commit -m "feat(ai-analysis): add IndexJobPostingUseCase"
```

---

## Task 6: `GetCandidateJobMatchesUseCase`

**Files:**
- Modify: `app/application/ai_analysis/use_cases.py`
- Create: `tests/application/ai_analysis/test_get_candidate_job_matches.py`

Retrieves top-K similar jobs for a candidate using the existing vector embedding. The candidate must have been indexed first via `IndexCandidateProfileUseCase`. Returns `list[SimilarityResult]`.

---

- [ ] **Step 1: Write the failing test**

```python
# tests/application/ai_analysis/test_get_candidate_job_matches.py
from uuid import uuid4

import pytest

from app.application.ai_analysis.ports import SimilarityResult
from app.application.ai_analysis.use_cases import GetCandidateJobMatchesUseCase
from app.application.common.errors import NotFoundError
from tests.fakes.ai_analysis.fake_vector_store import FakeVectorStore


@pytest.mark.asyncio
async def test_returns_top_k_similar_jobs():
    vector_store = FakeVectorStore()
    candidate_id = uuid4()

    # Index candidate
    await vector_store.upsert_candidate(candidate_id, [1.0, 0.0, 0.0], {})

    # Index 3 jobs with different similarity profiles
    job_a = uuid4()
    job_b = uuid4()
    job_c = uuid4()
    await vector_store.upsert_job(job_a, [1.0, 0.0, 0.0], {"title": "Python Dev"})   # most similar
    await vector_store.upsert_job(job_b, [0.5, 0.5, 0.0], {"title": "Full Stack"})   # medium
    await vector_store.upsert_job(job_c, [0.0, 0.0, 1.0], {"title": "DevOps"})       # least similar

    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)
    results = await use_case.execute(candidate_id=candidate_id, top_k=2)

    assert len(results) == 2
    assert results[0].id == job_a  # highest similarity first
    assert results[0].similarity_score > results[1].similarity_score


@pytest.mark.asyncio
async def test_raises_not_found_when_candidate_not_indexed():
    vector_store = FakeVectorStore()
    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)

    with pytest.raises(NotFoundError, match="candidate"):
        await use_case.execute(candidate_id=uuid4(), top_k=10)


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_jobs_indexed():
    vector_store = FakeVectorStore()
    candidate_id = uuid4()
    await vector_store.upsert_candidate(candidate_id, [1.0, 0.0, 0.0], {})

    use_case = GetCandidateJobMatchesUseCase(vector_store=vector_store)
    results = await use_case.execute(candidate_id=candidate_id, top_k=10)

    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/application/ai_analysis/test_get_candidate_job_matches.py -v
```

Expected: `FAILED` — `ImportError`.

- [ ] **Step 3: Implement `GetCandidateJobMatchesUseCase`**

Append to `app/application/ai_analysis/use_cases.py`:

```python
class GetCandidateJobMatchesUseCase:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self._vector_store = vector_store

    async def execute(
        self,
        candidate_id: UUID,
        top_k: int = 10,
    ) -> list[SimilarityResult]:
        candidate_embedding = await self._vector_store.get_candidate(candidate_id)
        if candidate_embedding is None:
            raise NotFoundError("candidate embedding", str(candidate_id))
        return await self._vector_store.search_similar_jobs(
            query_vector=candidate_embedding.vector,
            top_k=top_k,
        )
```

Add missing import at the top of the file (if not already present):
```python
from app.application.ai_analysis.ports import SimilarityResult
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/application/ai_analysis/test_get_candidate_job_matches.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/application/ai_analysis/use_cases.py tests/application/ai_analysis/test_get_candidate_job_matches.py
git commit -m "feat(ai-analysis): add GetCandidateJobMatchesUseCase"
```

---

## Task 7: Full Test Suite + Lint

Run all tests to catch regressions, then fix lint errors.

- [ ] **Step 1: Run the full application test suite**

```bash
poetry run pytest tests/application/ai_analysis/ -v
```

Expected: all PASS (no regressions).

- [ ] **Step 2: Run domain tests to confirm entity change is clean**

```bash
poetry run pytest tests/domain/ -v
```

Expected: all PASS.

- [ ] **Step 3: Run ruff**

```bash
poetry run ruff check app/application/ai_analysis/use_cases.py app/domain/ai_analysis/entities.py
```

Fix any issues reported. Common ones:
- Unused imports
- Missing type annotations on function parameters
- Line length > 120

- [ ] **Step 4: Run mypy on changed files**

```bash
poetry run mypy app/application/ai_analysis/use_cases.py app/domain/ai_analysis/entities.py
```

Fix any type errors. Common one: `EmbeddingPort` is a `Protocol` in `app/domain/ai_analysis/ports.py` — mypy may complain about structural subtyping. If needed, add `# type: ignore[arg-type]` only as a last resort.

- [ ] **Step 5: Run full test suite**

```bash
poetry run pytest -q
```

Expected: all PASS. If anything breaks, fix before committing.

- [ ] **Step 6: Final commit**

```bash
git add -u
git commit -m "chore(ai-analysis): fix lint and type errors in JOB-40 use cases"
```

---

## Self-Review Checklist

### Spec coverage

| JOB-40 requirement | Covered by |
|---|---|
| `ComputeMatchScoreUseCase` — hybrid cache, return cached 200, 202 for in-flight, reset FAILED | Task 3 |
| `GetAnalysisUseCase` — polling find_by_id | Task 2 |
| `IndexCandidateProfileUseCase` — embed CV + skills, upsert vector store | Task 4 |
| `IndexJobPostingUseCase` — embed job description, upsert | Task 5 |
| `GetCandidateJobMatchesUseCase` — top-K RAG search via VectorStorePort | Task 6 |
| Ports: `AIAnalysisPipelinePort`, `VectorStorePort`, `AIAnalysisRepository` | Already exist (no work needed) |
| Ports: `EmbeddingPort`, `LLMGatewayPort` | Already exist in `app/domain/ai_analysis/ports.py` |
| Fakes: `InMemoryAIAnalysisRepo`, `FakeEmbeddingPort`, `FakeVectorStorePort`, `FakeLLMGatewayPort`, `FakeAIPipelinePort` | Already exist (no work needed) |
| Quality tier from `CandidateProfile.preferred_quality_tier` | Accepted as `ComputeMatchScoreCommand.tier` — presentation layer resolves from profile in JOB-41 |

### Notes

- `IndexJobPostingCommand.metadata` uses `object.__setattr__` pattern for mutable default in frozen dataclass. An alternative if this causes issues: change `metadata` to `metadata: dict = dataclasses.field(default_factory=dict)` and drop `frozen=True` (making it a regular `@dataclass(slots=True)` command). Commands don't strictly need to be frozen.
- The `NotFoundError` import path in Tasks 2, 4, 6 must match the actual path in your codebase (step 2 of Task 2 finds it via grep).
