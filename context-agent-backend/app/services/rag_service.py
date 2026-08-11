import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.agent import RAGResponse, SourceCitation
from app.schemas.intent import ChatTurn, IntentClassification, QueryIntent
from app.services.cache_service import cache_service
from app.services.context_synthesis import merge_hits, parse_context_sections
from app.services.hybrid_search_service import HybridSearchService
from app.services.intent_classifier import intent_classifier
from app.services.llm_service import llm_service
from app.services.prompt_templates import NO_HISTORY_FOLLOW_UP_NOTE, PROMPTS
from app.services.reranker_service import reranker_service
from app.services.web_fallback_service import web_fallback_service

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, session: AsyncSession) -> None:
        self._search = HybridSearchService(session)

    def _final_limit(self, intent: QueryIntent, requested: int) -> int:
        if intent == QueryIntent.SINGLE_FACT:
            return min(requested, 3)
        if intent == QueryIntent.CONTEXT:
            return min(requested, settings.context_chunk_limit)
        return requested

    def _candidate_limit(self, intent: QueryIntent, final_limit: int) -> int:
        if not settings.reranker_enabled:
            return final_limit
        if intent == QueryIntent.CONTEXT:
            return max(
                settings.rerank_candidate_limit,
                final_limit + settings.background_search_limit,
            )
        return max(settings.rerank_candidate_limit, final_limit)

    async def _apply_rerank(
        self,
        query: str,
        hits: list[dict],
        top_k: int,
    ) -> tuple[list[dict], dict]:
        meta: dict = {
            "rerank_enabled": settings.reranker_enabled,
            "candidate_count": len(hits),
            "rerank_top_k": top_k,
        }
        if not settings.reranker_enabled or len(hits) <= top_k:
            return hits[:top_k], meta

        try:
            reranked = await asyncio.to_thread(reranker_service.rerank, query, hits, top_k)
            meta["reranked"] = True
            return reranked, meta
        except Exception:
            logger.exception("Reranking failed, using RRF order")
            meta["reranked"] = False
            meta["rerank_error"] = True
            return hits[:top_k], meta

    async def _maybe_web_fallback(
        self,
        query: str,
        hits: list[dict],
        limit: int,
    ) -> tuple[list[dict], dict]:
        should_use, reason = web_fallback_service.should_fallback(hits)
        meta: dict = {
            "web_fallback_enabled": web_fallback_service.is_enabled(),
            "web_fallback_used": False,
        }
        if not should_use:
            return hits, meta

        meta["web_fallback_reason"] = reason
        meta["web_fallback_attempted"] = True
        web_hits = await asyncio.to_thread(
            web_fallback_service.search,
            query,
            settings.web_fallback_max_results,
        )
        if not web_hits:
            return hits, meta

        if not hits:
            merged = web_hits[:limit]
        else:
            merged = merge_hits(
                web_hits,
                hits,
                max_total=max(limit, len(hits) + len(web_hits)),
            )

        meta["web_fallback_used"] = True
        meta["web_fallback_count"] = len(web_hits)
        logger.info(
            "Web fallback applied reason=%s local_hits=%s web_hits=%s merged=%s",
            reason,
            len(hits),
            len(web_hits),
            len(merged),
        )
        return merged, meta

    async def _retrieve_hits(
        self,
        query: str,
        classification: IntentClassification,
        limit: int,
        prior_sources: list[dict] | None = None,
    ) -> tuple[list[dict], dict]:
        final_limit = self._final_limit(classification.intent, limit)
        candidate_limit = self._candidate_limit(classification.intent, final_limit)

        cached = await asyncio.to_thread(
            cache_service.get_rag_retrieval,
            query,
            classification.intent.value,
            limit,
        )
        from_cache = cached is not None
        if cached is not None:
            hits, retrieval = cached
        else:
            retrieval = await self._search.hybrid_search(query, limit=candidate_limit)
            hits = retrieval["results"]

            if classification.intent == QueryIntent.CONTEXT:
                background_query = f"{query} background history context earlier developments"
                background_hits = await self._search.semantic_search(
                    background_query,
                    settings.background_search_limit,
                )
                for hit in background_hits:
                    hit["from_background_search"] = True
                hits = merge_hits(
                    hits,
                    background_hits,
                    max_total=candidate_limit + settings.background_search_limit,
                )
                retrieval = {
                    **retrieval,
                    "background_query": background_query,
                    "background_count": len(background_hits),
                }
                logger.info(
                    "Context retrieval candidates=%s background=%s merged=%s",
                    candidate_limit,
                    len(background_hits),
                    len(hits),
                )

        # Filter local hits by score thresholds before checking for web fallback
        hits = [
            hit for hit in hits
            if hit.get("from_web_fallback")
            or (hit.get("semantic_score") is not None and hit.get("semantic_score") >= settings.semantic_similarity_threshold)
            or (hit.get("score") is not None and hit.get("score") >= settings.semantic_similarity_threshold)
            or (hit.get("bm25_score") is not None and hit.get("bm25_score") >= settings.bm25_relevance_threshold)
        ]

        # Merge relevant prior sources into candidates before web fallback/reranking
        if prior_sources:
            seen_urls = {hit.get("url") for hit in hits if hit.get("url")}
            import re
            def calculate_overlap_score(q: str, t: str) -> float:
                qw = set(re.findall(r"\w+", q.lower()))
                tw = set(re.findall(r"\w+", t.lower()))
                if not qw:
                    return 0.0
                return len(qw.intersection(tw)) / len(qw)

            for src in prior_sources:
                if src.get("url") not in seen_urls:
                    overlap = calculate_overlap_score(query, f"{src.get('title', '')} {src.get('chunk', '')}")
                    if overlap >= 0.1 or settings.reranker_enabled:
                        hits.append(src)

        # Classify source types for bias tracking
        from urllib.parse import urlparse
        def classify_source_type(url: str, source_name: str = "") -> str:
            domain = ""
            if url:
                try:
                    domain = urlparse(url).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                except Exception:
                    pass
            name = (source_name or "").lower()
            if domain.endswith((".gov", ".mil", ".gov.in", ".gov.uk")) or "government" in name or "official" in name:
                return "government/official"
            advocacy_keywords = {"afsc", "amnesty", "hrw", "greenpeace", "oxfam", "aclu", "sierra", "opinion", "advocacy"}
            if any(kw in domain or kw in name for kw in advocacy_keywords):
                return "advocacy/opinion"
            return "wire/news"

        for hit in hits:
            hit["source_type"] = classify_source_type(hit.get("url"), hit.get("source"))

        local_hits_snapshot = list(hits)
        local_retrieval_snapshot = dict(retrieval)

        hits, web_meta = await self._maybe_web_fallback(query, hits, final_limit)

        # Classify any new web fallback hits that were added
        for hit in hits:
            if "source_type" not in hit:
                hit["source_type"] = classify_source_type(hit.get("url"), hit.get("source"))

        hits, rerank_meta = await self._apply_rerank(query, hits, final_limit)
        
        # Filter final hits one last time to ensure absolute relevance
        hits = [
            hit for hit in hits
            if hit.get("from_web_fallback")
            or hit.get("from_prior_turn")
            or (hit.get("semantic_score") is not None and hit.get("semantic_score") >= settings.semantic_similarity_threshold)
            or (hit.get("score") is not None and hit.get("score") >= settings.semantic_similarity_threshold)
            or (hit.get("bm25_score") is not None and hit.get("bm25_score") >= settings.bm25_relevance_threshold)
        ]

        retrieval = {
            **retrieval,
            **web_meta,
            **rerank_meta,
            "fused_count": len(hits),
            "from_cache": from_cache,
        }
        if not from_cache:
            await asyncio.to_thread(
                cache_service.set_rag_retrieval,
                query,
                classification.intent.value,
                limit,
                local_hits_snapshot,
                {**local_retrieval_snapshot, "fused_count": len(local_hits_snapshot)},
            )
        return hits, retrieval

    def _build_prompt(
        self,
        query: str,
        hits: list[dict],
        classification: IntentClassification,
        history: list[ChatTurn],
    ) -> str:
        system = PROMPTS[classification.intent]
        parts: list[str] = [system]

        if classification.intent == QueryIntent.FOLLOW_UP and not history:
            parts.append(NO_HISTORY_FOLLOW_UP_NOTE)
        elif history:
            turns = "\n".join(f"{turn.role}: {turn.text}" for turn in history[-6:])
            parts.append(f"Recent conversation:\n{turns}")

        if not hits:
            parts.append("Context:\nNo relevant news excerpts were found.")
        else:
            from datetime import datetime, timezone
            from app.services.web_fallback_service import _parse_publish_date

            def get_dt(h):
                ds = h.get("publish_date")
                if not ds:
                    return datetime.min.replace(tzinfo=timezone.utc)
                parsed = _parse_publish_date(ds)
                return parsed if parsed is not None else datetime.min.replace(tzinfo=timezone.utc)

            sorted_hits = sorted(hits, key=get_dt, reverse=True)
            split_idx = max(2, len(sorted_hits) // 2) if len(sorted_hits) > 2 else len(sorted_hits)
            most_recent = sorted_hits[:split_idx]
            earlier = sorted_hits[split_idx:]

            blocks: list[str] = []

            def format_block(hit: dict) -> str:
                original_idx = hits.index(hit) + 1
                tag = ""
                if hit.get("from_background_search"):
                    tag = " [background-related]"
                elif hit.get("from_web_fallback"):
                    tag = " [live web source]"

                src_type = hit.get("source_type", "wire/news")
                tag += f" [source type: {src_type}]"

                return (
                    f"[{original_idx}] {hit.get('title', 'Untitled')} ({hit.get('source', 'unknown')}, "
                    f"{hit.get('publish_date', 'unknown date')}){tag}\n"
                    f"{hit.get('chunk', '')}\n"
                    f"URL: {hit.get('url', '')}"
                )

            if most_recent:
                blocks.append("--- MOST RECENT UPDATES (Use these for the latest developments) ---")
                for hit in most_recent:
                    blocks.append(format_block(hit))
            if earlier:
                blocks.append("--- EARLIER COVERAGE & BACKGROUND (Use these for historical context) ---")
                for hit in earlier:
                    blocks.append(format_block(hit))

            parts.append("Context:\n" + "\n\n".join(blocks))

        parts.append(f"Question: {query}\n\nAnswer:")
        return "\n\n".join(parts)

    async def query(
        self,
        query: str,
        *,
        limit: int = 6,
        history: list[ChatTurn] | None = None,
        prior_sources: list[dict] | None = None,
        track_trending: bool = True,
    ) -> RAGResponse:
        history = history or []
        logger.info("RAG query=%r limit=%s history_turns=%s prior_sources=%s", query, limit, len(history), len(prior_sources) if prior_sources else 0)

        if not history and not web_fallback_service.is_enabled():
            cached_response = await asyncio.to_thread(cache_service.get_rag_response, query, limit)
            if cached_response is not None:
                if track_trending:
                    logger.debug("Skipping trending increment for cached RAG response")
                cached_response.setdefault("retrieval", {})["from_cache"] = True
                return RAGResponse(**cached_response)

        classification = intent_classifier.classify(query, history)
        hits, retrieval = await self._retrieve_hits(query, classification, limit, prior_sources=prior_sources)

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
            prompt = self._build_prompt(query, hits, classification, history)
            answer = llm_service.generate(prompt)

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
            import re
            cited_indices = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
            sources = [s for s in sources if s.index in cited_indices]

        logger.info(
            "RAG complete intent=%s sources=%s sections=%s reranked=%s cached=%s",
            classification.intent,
            len(sources),
            len(sections),
            retrieval.get("reranked"),
            retrieval.get("from_cache"),
        )
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

        if not history and not web_fallback_service.is_enabled():
            await asyncio.to_thread(
                cache_service.set_rag_response,
                query,
                limit,
                response.model_dump(mode="json"),
            )

        if track_trending and hits:
            await asyncio.to_thread(cache_service.increment_trending, query)

        return response

    async def query_stream(
        self,
        query: str,
        *,
        limit: int = 6,
        history: list[ChatTurn] | None = None,
        prior_sources: list[dict] | None = None,
        track_trending: bool = True,
    ):
        history = history or []
        logger.info("RAG query_stream query=%r limit=%s history_turns=%s prior_sources=%s", query, limit, len(history), len(prior_sources) if prior_sources else 0)

        classification = intent_classifier.classify(query, history)
        hits, retrieval = await self._retrieve_hits(query, classification, limit, prior_sources=prior_sources)

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

        metadata = {
            "type": "metadata",
            "intent": classification.intent.value if hasattr(classification.intent, "value") else classification.intent,
            "sources": [s.model_dump(mode="json") for s in sources],
            "retrieval": {
                "semantic_count": retrieval.get("semantic_count"),
                "bm25_count": retrieval.get("bm25_count"),
                "fused_count": retrieval.get("fused_count", len(hits)),
                "web_fallback_used": retrieval.get("web_fallback_used"),
            }
        }
        yield f"data: {orjson.dumps(metadata).decode('utf-8')}\n\n"

        if not hits:
            refusal = (
                "I could not find any relevant news articles in the local database "
                "or via live web search matching your question. Because strict grounding "
                "is enabled, I cannot synthesize a response without verified sources to "
                "prevent hallucination."
            )
            yield f"data: {orjson.dumps({'type': 'token', 'text': refusal}).decode('utf-8')}\n\n"
            yield "data: [DONE]\n\n"
            return

        prompt = self._build_prompt(query, hits, classification, history)
        full_text = []
        try:
            loop = asyncio.get_running_loop()
            def fetch_stream():
                return list(llm_service.generate_stream(prompt))
            chunks = await loop.run_in_executor(None, fetch_stream)
            for chunk in chunks:
                full_text.append(chunk)
                yield f"data: {orjson.dumps({'type': 'token', 'text': chunk}).decode('utf-8')}\n\n"
        except Exception as exc:
            logger.error("Error during streaming generation: %s", exc)
            yield f"data: {orjson.dumps({'type': 'error', 'message': str(exc)}).decode('utf-8')}\n\n"

        if track_trending and hits:
            await asyncio.to_thread(cache_service.increment_trending, query)

        yield "data: [DONE]\n\n"

    def classify_only(self, query: str, history: list[ChatTurn] | None = None) -> IntentClassification:
        return intent_classifier.classify(query, history or [])
