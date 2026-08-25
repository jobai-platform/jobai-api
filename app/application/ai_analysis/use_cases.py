from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
from uuid import UUID, uuid4

from app.application.ai_analysis.ports import (
    AIAnalysisPipelinePort,
    AIAnalysisRepository,
    SimilarityResult,
    VectorStorePort,
)
from app.application.users.candidate_profile_ports import CandidateProfileRepository
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.enums import AnalysisQualityTier, AnalysisStatus
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.services.model_router import ModelRouter
from app.domain.common.exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)


class GenerateEmbeddingsUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise BadRequestError(
                code="empty_embedding_input",
                details="Text cannot be empty",
            )
        port = self._router.get_embedding_port()
        return await port.generate_embedding(text)


class GenerateLLMCompletionUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        port = self._router.get_llm_port()
        return await port.complete(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )


class AnalyzeJobDescriptionUseCase:
    """Extracts structured information from a raw job description using an LLM."""

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, job_description: str) -> dict[str, object]:
        """Analyse a job description and return a structured dict.

        Returns a dict with keys: skills, seniority, remote_policy, raw_analysis.
        Falls back to {"raw_analysis": <text>} if the LLM does not return valid JSON.
        """
        if not job_description or not job_description.strip():
            raise BadRequestError(
                code="empty_job_description",
                details="job_description cannot be empty",
            )

        llm_port = self._router.get_llm_port()

        system_prompt = (
            "You are a job description analyzer. "
            "Extract structured information from the job description provided by the user. "
            "Respond ONLY with a valid JSON object — no prose, no markdown, no code fences."
        )

        prompt = (
            "Analyze the following job description and return a JSON object with these fields:\n"
            '- "skills": list of required technical skills\n'
            '- "seniority": one of "Junior", "Mid", "Senior", "Lead" or null\n'
            '- "remote_policy": one of "Remote", "Hybrid", "On-site" or null\n'
            '- "industry": company industry if mentioned, or null\n\n'
            f"Job description:\n{job_description}"
        )

        response = await llm_port.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # low temperature for deterministic structured output
            max_tokens=1000,
        )

        # Strip markdown code fences if the LLM wraps JSON in ```json ... ```
        clean = (
            response.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        try:
            # json.loads() parses a str — not json.load() which needs a file
            return json.loads(clean)
        except json.JSONDecodeError:
            logger.error("LLM did not return valid JSON, falling back to raw: %s", response[:200])
            return {"raw_analysis": response}


class GetAnalysisUseCase:
    """Returns an AIAnalysis aggregate by ID, or raises NotFoundError."""

    def __init__(self, repo: AIAnalysisRepository) -> None:
        self._repo = repo

    async def execute(self, analysis_id: UUID) -> AIAnalysis:
        analysis = await self._repo.find_by_id(analysis_id)
        if analysis is None:
            raise NotFoundError(
                code="ai_analysis_not_found",
                details=f"AIAnalysis {analysis_id} not found.",
            )
        return analysis

    async def find_by_candidate(self, candidate_id: UUID, limit: int = 20) -> list[AIAnalysis]:
        return await self._repo.find_by_candidate(candidate_id, limit=limit)


@dataclass(frozen=True, slots=True)
class ComputeMatchScoreCommand:
    candidate_id: UUID
    job_posting_id: UUID
    tier: AnalysisQualityTier = AnalysisQualityTier.FAST


class ComputeMatchScoreUseCase:
    """Hybrid cache pattern: return cached result, queue in-flight, retry failed, or start fresh."""

    def __init__(self, repo: AIAnalysisRepository, pipeline: AIAnalysisPipelinePort) -> None:
        self._repo = repo
        self._pipeline = pipeline

    async def execute(self, command: ComputeMatchScoreCommand) -> AIAnalysis:
        existing = await self._repo.find_by_candidate_and_job(
            command.candidate_id, command.job_posting_id
        )

        _terminal_or_inflight = (
            AnalysisStatus.COMPLETED,
            AnalysisStatus.PENDING,
            AnalysisStatus.PROCESSING,
        )
        if existing is not None:
            if existing.status in _terminal_or_inflight:
                return existing
            # FAILED — reset and retry
            existing.reset_for_retry()
            await self._repo.save(existing)
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
            await self._repo.save(analysis)

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


class IndexCandidateProfileUseCase:
    """Fetches a CandidateProfile, generates its embedding, and upserts it to the vector store."""

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
            raise NotFoundError(
                code="candidate_profile_not_found",
                details=f"CandidateProfile {user_id} not found.",
            )

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


@dataclass(frozen=True, slots=True)
class IndexJobPostingCommand:
    job_posting_id: UUID
    description: str
    metadata: dict = field(default_factory=dict)


class IndexJobPostingUseCase:
    """Generates an embedding for the given job description and upserts it to the vector store."""

    def __init__(
        self,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
    ) -> None:
        self._embedding = embedding
        self._vector_store = vector_store

    async def execute(self, command: IndexJobPostingCommand) -> None:
        if not command.description or not command.description.strip():
            raise BadRequestError(
                code="empty_job_description",
                details="description cannot be empty",
            )
        vector = await self._embedding.generate_embedding(command.description)
        await self._vector_store.upsert_job(command.job_posting_id, vector, command.metadata)


class GetCandidateJobMatchesUseCase:
    """Returns the top-K most similar jobs for a candidate using their existing vector embedding."""

    def __init__(self, vector_store: VectorStorePort) -> None:
        self._vector_store = vector_store

    async def execute(
        self,
        candidate_id: UUID,
        top_k: int = 10,
    ) -> list[SimilarityResult]:
        candidate_embedding = await self._vector_store.get_candidate(candidate_id)
        if candidate_embedding is None:
            raise NotFoundError(
                code="candidate_embedding_not_found",
                details=(
                    f"Candidate {candidate_id} has no indexed embedding. "
                    "Call IndexCandidateProfileUseCase first."
                ),
            )
        return await self._vector_store.search_similar_jobs(
            query_vector=candidate_embedding.vector,
            top_k=top_k,
        )
