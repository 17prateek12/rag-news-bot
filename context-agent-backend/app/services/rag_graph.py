import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import traceable
from app.schemas.agent import RAGResponse, SourceCitation
from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent
from app.services.cache_service import cache_service
from app.services.context_synthesis import parse_context_sections
from app.services.intent_classifier import intent_classifier
from app.services.llm_service import llm_service
from app.services.query_rewriter import lcel_query_rewriter

logger = logging.getLogger(__name__)


def _extract_cited_indices(text: str) -> set[int]:
    import re
    indices: set[int] = set()
    for group in re.findall(r"\[([\d,\s]+)\]", text):
        for part in group.split(","):
            part = part.strip()
            if part.isdigit():
                indices.add(int(part))
    return indices


class RAGGraphState(TypedDict, total=False):
    rag_service: Any
    query: str
    limit: int
    history: list[ChatTurn]
    prior_sources: list[dict]
    track_trending: bool
    classification: IntentClassification
    retrieval_query: str
    hits: list[dict]
    retrieval: dict
    retry_count: int
    prompt: str
    answer: str
    sections: list[str]
    sources: list[SourceCitation]
    response: RAGResponse


async def classify_node(state: RAGGraphState) -> dict:
    query = state["query"]
    history = state.get("history", [])
    loop = asyncio.get_running_loop()
    classification = await loop.run_in_executor(None, intent_classifier.classify, query, history)
    logger.info("LangGraph [classify_node] intent=%s confidence=%s", classification.intent, classification.confidence)
    return {"classification": classification}


async def rewrite_node(state: RAGGraphState) -> dict:
    query = state["query"]
    history = state.get("history", [])
    if history:
        rewritten = await lcel_query_rewriter.rewrite(query, history)
        logger.info("LangGraph [rewrite_node] %r -> %r", query, rewritten)
        return {"retrieval_query": rewritten}
    return {"retrieval_query": query}


async def retrieve_node(state: RAGGraphState) -> dict:
    rag_service = state["rag_service"]
    retrieval_query = state.get("retrieval_query", state["query"])
    classification = state["classification"]
    limit = state.get("limit", 6)
    prior_sources = state.get("prior_sources", [])

    hits, retrieval = await rag_service._retrieve_hits(
        retrieval_query,
        classification,
        limit,
        prior_sources=prior_sources,
        bypass_single_fact_limit=False,
    )
    return {"hits": hits, "retrieval": retrieval, "retry_count": 0}


async def retry_retrieve_node(state: RAGGraphState) -> dict:
    rag_service = state["rag_service"]
    retrieval_query = state.get("retrieval_query", state["query"])
    classification = state["classification"]
    limit = state.get("limit", 6)
    prior_sources = state.get("prior_sources", [])

    logger.info("LangGraph [retry_retrieve_node] retrying with wider candidate window for single_fact")
    hits, retrieval = await rag_service._retrieve_hits(
        retrieval_query,
        classification,
        limit,
        prior_sources=prior_sources,
        bypass_single_fact_limit=True,
    )
    return {"hits": hits, "retrieval": retrieval, "retry_count": 1}


def should_retry_retrieval(state: RAGGraphState) -> str:
    hits = state.get("hits", [])
    classification = state.get("classification")
    retry_count = state.get("retry_count", 0)

    if not hits and classification and classification.intent == QueryIntent.SINGLE_FACT and retry_count == 0:
        return "retry_retrieve"
    return "generate"


async def generate_node(state: RAGGraphState) -> dict:
    rag_service = state["rag_service"]
    query = state["query"]
    history = state.get("history", [])
    classification = state["classification"]
    hits = state.get("hits", [])
    retrieval = state.get("retrieval", {})
    limit = state.get("limit", 6)
    track_trending = state.get("track_trending", True)

    if not hits:
        answer = (
            "I could not find any relevant news articles in the local database "
            "or via live web search matching your question. Because strict grounding "
            "is enabled, I cannot synthesize a response without verified sources to "
            "prevent hallucination."
        )
        sections = []
        sources = []
    else:
        prompt = rag_service._build_prompt(query, hits, classification, history)
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(None, llm_service.generate, prompt)

        # Reactive web fallback: if local articles lacked the specific answer, fetch live web sources and regenerate
        ungrounded_indicators = (
            "provided excerpts do not",
            "provided context does not",
            "provided text does not",
            "excerpts do not contain",
            "excerpts do not name",
            "excerpts do not mention",
            "excerpts do not provide",
            "excerpts do not state",
            "context does not contain",
            "context does not name",
            "context does not mention",
            "context does not provide",
            "context does not state",
            "do not name",
            "does not name",
            "do not mention",
            "does not mention",
        )
        lower_ans = answer.lower()
        from app.services.web_fallback_service import web_fallback_service
        from app.config import settings
        from app.services.context_synthesis import merge_hits
        if (
            not retrieval.get("web_fallback_used")
            and web_fallback_service.is_enabled()
            and any(ind in lower_ans for ind in ungrounded_indicators)
        ):
            logger.info("LangGraph [generate_node] Local excerpts insufficient for %r. Triggering reactive web fallback.", query)
            web_hits = await asyncio.to_thread(
                web_fallback_service.search,
                query,
                settings.web_fallback_max_results,
            )
            if web_hits:
                hits = merge_hits(web_hits, hits, max_total=max(limit, len(hits) + len(web_hits)))
                hits, rerank_meta = await rag_service._apply_rerank(query, hits, max(limit, 4))
                retrieval["web_fallback_used"] = True
                retrieval["web_fallback_reason"] = "insufficient_local_context"
                retrieval["web_fallback_count"] = len(web_hits)
                retrieval.update(rerank_meta)

                prompt = rag_service._build_prompt(query, hits, classification, history)
                answer = await loop.run_in_executor(None, llm_service.generate, prompt)

        sections = (
            parse_context_sections(answer)
            if classification.intent == QueryIntent.CONTEXT
            else []
        )

        sources = [
            SourceCitation(
                index=idx,
                title=hit.get("title", "Untitled"),
                source=hit.get("source", "unknown"),
                url=hit.get("url", ""),
                publish_date=hit.get("publish_date"),
                excerpt=(hit.get("chunk") or "")[:300],
            )
            for idx, hit in enumerate(hits, start=1)
        ]
        cited_indices = _extract_cited_indices(answer)
        sources = [s for s in sources if s.index in cited_indices]

    response = RAGResponse(
        query=query,
        intent=classification.intent,
        intent_confidence=classification.confidence,
        intent_reason=classification.reason,
        answer=answer,
        sections=sections,
        sources=sources,
        retrieval={
            "semantic_count": retrieval.get("semantic_count"),
            "bm25_count": retrieval.get("bm25_count"),
            "background_count": retrieval.get("background_count"),
            "background_query": retrieval.get("background_query"),
            "candidate_count": retrieval.get("candidate_count"),
            "rerank_enabled": retrieval.get("rerank_enabled"),
            "reranked": retrieval.get("reranked"),
            "fused_count": retrieval.get("fused_count", len(hits)),
            "from_cache": retrieval.get("from_cache", False),
            "web_fallback_enabled": retrieval.get("web_fallback_enabled"),
            "web_fallback_used": retrieval.get("web_fallback_used"),
            "web_fallback_reason": retrieval.get("web_fallback_reason"),
            "web_fallback_count": retrieval.get("web_fallback_count"),
            "hits": hits,
        },
    )

    if not history:
        await asyncio.to_thread(
            cache_service.set_rag_response,
            query,
            limit,
            response.model_dump(mode="json"),
        )

    if track_trending and hits:
        try:
            from app.worker.tasks import track_query_trending
            track_query_trending.delay(query)
        except Exception:
            pass

    return {"response": response}


def build_rag_graph():
    """Build and compile the LangGraph StateGraph workflow for RAG intent routing."""
    workflow = StateGraph(RAGGraphState)

    workflow.add_node("classify", classify_node)
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("retry_retrieve", retry_retrieve_node)
    workflow.add_node("generate", generate_node)

    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "rewrite")
    workflow.add_edge("rewrite", "retrieve")

    workflow.add_conditional_edges(
        "retrieve",
        should_retry_retrieval,
        {
            "retry_retrieve": "retry_retrieve",
            "generate": "generate",
        },
    )
    workflow.add_edge("retry_retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


_rag_graph_app = None


def get_rag_graph():
    global _rag_graph_app
    if _rag_graph_app is None:
        _rag_graph_app = build_rag_graph()
    return _rag_graph_app


@traceable(name="langgraph_rag_query", run_type="chain")
async def execute_rag_graph(
    rag_service: Any,
    query: str,
    *,
    limit: int = 6,
    history: list[ChatTurn] | None = None,
    prior_sources: list[dict] | None = None,
    track_trending: bool = True,
) -> RAGResponse:
    """Execute the compiled LangGraph StateGraph pipeline returning an exact RAGResponse."""
    history = history or []

    if not history:
        cached_response = await asyncio.to_thread(cache_service.get_rag_response, query, limit)
        if cached_response is not None:
            logger.info("Serving LangGraph RAG response from cache query=%r", query)
            cached_response.setdefault("retrieval", {})["from_cache"] = True
            response = RAGResponse(**cached_response)
            if track_trending and response.sources:
                try:
                    from app.worker.tasks import track_query_trending
                    track_query_trending.delay(query)
                except Exception as entity_exc:
                    logger.exception("Failed to enqueue query trending from cache: %s", entity_exc)
            return response

    graph = get_rag_graph()
    initial_state: RAGGraphState = {
        "rag_service": rag_service,
        "query": query,
        "limit": limit,
        "history": history,
        "prior_sources": prior_sources or [],
        "track_trending": track_trending,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state["response"]
