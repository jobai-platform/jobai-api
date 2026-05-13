import logging
from functools import partial
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.application.ai_analysis.ports import AIAnalysisPipelinePort, VectorStorePort
from app.domain.ai_analysis.enums import AnalysisQualityTier
from app.domain.ai_analysis.ports import EmbeddingPort
from app.domain.ai_analysis.value_objects import MatchScore
from app.infrastructure.ai.pipeline.nodes import (
    job_extractor_node,
    profile_extractor_node,
    reporter_node,
    scorer_node,
    semantic_retriever_node,
)
from app.infrastructure.ai.pipeline.state import PipelineState, make_initial_state

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _should_retry_retriever(state: PipelineState) -> str:
    """Conditional edge: loop back when retry_count increased (low confidence); else go to scorer."""
    if state.get("error"):
        return "error"
    prev = state.get("_prev_retry_count", 0)
    current = state.get("retry_count", 0)
    if current > prev and current <= _MAX_RETRIES:
        return "retry"
    return "scorer"


class LangGraphMatchingPipeline(AIAnalysisPipelinePort):
    """Implements AIAnalysisPipelinePort using a 5-node LangGraph DAG."""

    def __init__(
        self,
        llm: object,
        embedding_port: EmbeddingPort,
        vector_store: VectorStorePort,
        candidate_text: str,
        job_text: str,
    ) -> None:
        self._llm = llm
        self._embedding_port = embedding_port
        self._vector_store = vector_store
        self._candidate_text = candidate_text
        self._job_text = job_text
        self._graph = self._build_graph()

    def _build_graph(self) -> object:
        graph = StateGraph(PipelineState)

        graph.add_node("profile_extractor", partial(profile_extractor_node, llm=self._llm))
        graph.add_node("job_extractor", partial(job_extractor_node, llm=self._llm))
        graph.add_node(
            "semantic_retriever",
            partial(
                semantic_retriever_node,
                embedding_port=self._embedding_port,
                vector_store=self._vector_store,
            ),
        )
        graph.add_node("scorer", partial(scorer_node, llm=self._llm))
        graph.add_node("reporter", partial(reporter_node, llm=self._llm))

        graph.set_entry_point("profile_extractor")
        graph.add_edge("profile_extractor", "job_extractor")
        graph.add_edge("job_extractor", "semantic_retriever")
        graph.add_conditional_edges(
            "semantic_retriever",
            _should_retry_retriever,
            {"retry": "semantic_retriever", "scorer": "scorer", "error": END},
        )
        graph.add_edge("scorer", "reporter")
        graph.add_edge("reporter", END)

        return graph.compile()

    async def run(
        self,
        candidate_id: UUID,
        job_posting_id: UUID,
        tier: AnalysisQualityTier,
        analysis_id: UUID,
    ) -> MatchScore:
        from app.infrastructure.ai.langfuse_callback import get_langfuse_callback

        initial_state = make_initial_state(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            tier=tier,
            analysis_id=analysis_id,
            candidate_text=self._candidate_text,
            job_text=self._job_text,
        )

        callbacks = []
        langfuse_handler = get_langfuse_callback()
        if langfuse_handler:
            callbacks.append(langfuse_handler)

        config = {"callbacks": callbacks} if callbacks else {}

        final_state: PipelineState = await self._graph.ainvoke(initial_state, config=config)

        if final_state.get("error"):
            raise RuntimeError(f"Pipeline failed: {final_state['error']}")

        score = final_state.get("match_score")
        if score is None:
            raise RuntimeError("Pipeline completed without producing a MatchScore")

        logger.info(
            "Pipeline completed: analysis_id=%s overall=%.3f",
            analysis_id,
            score.overall,
        )
        return score
