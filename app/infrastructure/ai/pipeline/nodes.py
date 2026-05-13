import json
import logging

from langchain_core.language_models import BaseLLM

from app.application.ai_analysis.ports import SimilarityResult, VectorStorePort
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.ai.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

_PROFILE_EXTRACTION_PROMPT = """Extract structured information from this candidate profile.
Return ONLY a valid JSON object with these exact keys:
- "skills": list of technical skills (strings)
- "experience_years": integer or null
- "locations": list of preferred locations (strings)
- "salary_range": {{"min": int, "max": int}} or null

Candidate profile:
{text}"""

_JOB_EXTRACTION_PROMPT = """Extract structured information from this job posting.
Return ONLY a valid JSON object with these exact keys:
- "required_skills": list of required technical skills (strings)
- "seniority": one of "Junior", "Mid", "Senior", "Lead" or null
- "location": location string or "Remote" or null
- "salary_range": {{"min": int, "max": int}} or null

Job posting:
{text}"""

_SCORING_PROMPT = """You are a job matching expert. Score the compatibility between this candidate and job.

CANDIDATE:
{profile}

JOB REQUIREMENT:
{job}

SIMILAR JOBS FOR CONTEXT:
{context}

Return ONLY a valid JSON object with these exact keys (float values between 0.0 and 1.0):
{{"skills": <float>, "experience": <float>, "location": <float>, "salary": <float>}}"""

_EXPLANATION_PROMPT = """Write a 2-3 sentence explanation of this job match in a professional tone.
Be specific about strengths and gaps.

Scores: skills={skills}, experience={experience}, location={location}, salary={salary}
Candidate profile: {profile}
Job requirements: {job}

Write the explanation in the same language as the job description."""

_CONFIDENCE_THRESHOLD = 0.6
_MAX_RETRIES = 3


def _parse_llm_json(response: str, context: str) -> dict | None:
    clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("Node %s: LLM did not return valid JSON: %.100s", context, response)
        return None


async def profile_extractor_node(state: PipelineState, llm: BaseLLM) -> dict:
    text = state.get("_candidate_text", "")
    if not text:
        return {"error": "profile_extractor: no candidate text provided", "structured_profile": None}

    prompt = _PROFILE_EXTRACTION_PROMPT.format(text=text)
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "profile_extractor")

    if parsed is None:
        return {"error": "profile_extractor: LLM did not return valid JSON", "structured_profile": None}

    return {"structured_profile": parsed, "error": None}


async def job_extractor_node(state: PipelineState, llm: BaseLLM) -> dict:
    text = state.get("_job_text", "")
    if not text:
        return {"error": "job_extractor: no job text provided", "structured_job": None}

    prompt = _JOB_EXTRACTION_PROMPT.format(text=text)
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "job_extractor")

    if parsed is None:
        return {"error": "job_extractor: LLM did not return valid JSON", "structured_job": None}

    return {"structured_job": parsed, "error": None}


async def semantic_retriever_node(
    state: PipelineState,
    embedding_port: EmbeddingPort,
    vector_store: VectorStorePort,
) -> dict:
    profile = state.get("structured_profile")
    if not profile:
        return {"error": "semantic_retriever: no structured_profile available"}

    profile_text = " ".join(str(v) for v in profile.values() if v)
    vector = await embedding_port.generate_embedding(profile_text)
    results: list[SimilarityResult] = await vector_store.search_similar_jobs(
        query_vector=vector, top_k=5
    )

    max_score = max((r.similarity_score for r in results), default=0.0)
    retry_count = state.get("retry_count", 0)

    if max_score < _CONFIDENCE_THRESHOLD and retry_count < _MAX_RETRIES:
        return {"retry_count": retry_count + 1}

    context_jobs = [{"similarity_score": r.similarity_score, **r.metadata} for r in results]
    return {"context_jobs": context_jobs, "error": None}


async def scorer_node(state: PipelineState, llm: BaseLLM) -> dict:
    profile = state.get("structured_profile", {})
    job = state.get("structured_job", {})
    context = state.get("context_jobs", [])

    prompt = _SCORING_PROMPT.format(
        profile=json.dumps(profile, ensure_ascii=False),
        job=json.dumps(job, ensure_ascii=False),
        context=json.dumps(context[:3], ensure_ascii=False),
    )
    response = await llm.ainvoke(prompt)
    parsed = _parse_llm_json(str(response), "scorer")

    if parsed is None:
        return {"error": "scorer: LLM did not return valid JSON", "raw_scores": None}

    required = {"skills", "experience", "location", "salary"}
    if not required.issubset(parsed.keys()):
        return {"error": f"scorer: missing keys in response: {required - parsed.keys()}", "raw_scores": None}

    return {"raw_scores": parsed, "error": None}


async def reporter_node(state: PipelineState, llm: BaseLLM) -> dict:
    raw = state.get("raw_scores", {}) or {}
    profile = state.get("structured_profile", {})
    job = state.get("structured_job", {})

    skills = float(raw.get("skills", 0.0))
    experience = float(raw.get("experience", 0.0))
    location = float(raw.get("location", 0.0))
    salary = float(raw.get("salary", 0.0))

    prompt = _EXPLANATION_PROMPT.format(
        skills=skills,
        experience=experience,
        location=location,
        salary=salary,
        profile=json.dumps(profile, ensure_ascii=False),
        job=json.dumps(job, ensure_ascii=False),
    )
    explanation = str(await llm.ainvoke(prompt)).strip()

    overall = round(skills * 0.4 + experience * 0.3 + location * 0.2 + salary * 0.1, 3)

    try:
        score = MatchScore(
            overall=overall,
            skills_score=skills,
            experience_score=experience,
            location_score=location,
            salary_score=salary,
            explanation=explanation,
        )
    except (ValueError, TypeError) as exc:
        return {"error": f"reporter: invalid scores — {exc}", "match_score": None}

    return {"match_score": score, "error": None}
