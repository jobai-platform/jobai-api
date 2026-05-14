import json
import logging
from uuid import UUID

from app.application.ai_analysis.ports import AIAnalysisRepository
from app.domain.ai_analysis.entities import AIAnalysis
from app.domain.ai_analysis.services.model_router import ModelRouter
from app.domain.common.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class GenerateEmbeddingsUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        port = self._router.get_embedding_port()
        return await port.generate_embedding(text)


class GenerateLLMCompletionUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, prompt: str, **kwargs: object) -> str:
        port = self._router.get_llm_port()
        return await port.complete(prompt, **kwargs)


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
            raise ValueError("job_description cannot be empty")

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
        clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            return json.loads(clean)  # json.loads() parses a str — not json.load() which needs a file
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
