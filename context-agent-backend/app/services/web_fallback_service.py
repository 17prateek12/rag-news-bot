import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import settings
from app.ingestion.hasher import content_hash
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

_client: TavilyClient | None = None


def _get_client() -> TavilyClient | None:
    global _client
    if not settings.tavily_api_key:
        return None
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def _parse_publish_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _source_label(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "web"


def _newest_publish_date(hits: list[dict[str, Any]]) -> datetime | None:
    newest: datetime | None = None
    for hit in hits:
        if hit.get("from_web_fallback"):
            continue
        published = _parse_publish_date(hit.get("publish_date"))
        if published and (newest is None or published > newest):
            newest = published
    return newest


class WebFallbackService:
    def is_enabled(self) -> bool:
        return settings.web_fallback_enabled and bool(settings.tavily_api_key)

    def should_fallback(self, hits: list[dict[str, Any]]) -> tuple[bool, str]:
        if not self.is_enabled():
            return False, ""

        if not hits:
            return True, "no_local_hits"

        if len(hits) < settings.web_fallback_min_hits:
            return True, "insufficient_hits"

        best_semantic = max((float(hit.get("semantic_score") or 0) for hit in hits), default=0.0)
        has_strong_bm25 = any(float(hit.get("bm25_score") or 0) > 0.05 for hit in hits)
        if best_semantic < settings.web_fallback_min_semantic_score and not has_strong_bm25:
            return True, "low_relevance"

        newest = _newest_publish_date(hits)
        if newest is None:
            return False, ""

        age_hours = (datetime.now(timezone.utc) - newest).total_seconds() / 3600
        if age_hours > settings.web_fallback_stale_hours:
            return True, "stale_coverage"

        return False, ""

    def _to_hit(self, result: dict[str, Any], rank: int) -> dict[str, Any]:
        url = result.get("url") or ""
        content = (result.get("content") or result.get("raw_content") or "").strip()
        title = (result.get("title") or "Untitled").strip()
        published = result.get("published_date") or result.get("published_at")
        return {
            "article_id": f"web:{content_hash(url or title)}",
            "chunk_index": 0,
            "chunk": content or title,
            "title": title,
            "source": f"web:{_source_label(url)}",
            "url": url,
            "publish_date": published,
            "categories": [],
            "from_web_fallback": True,
            "web_score": float(result.get("score") or 0.0),
            "web_rank": rank,
        }

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return []

        result_limit = limit or settings.web_fallback_max_results
        cached = cache_service.get_web_fallback(query, result_limit)
        if cached is not None:
            return cached

        client = _get_client()
        if client is None:
            return []

        try:
            response = client.search(
                query,
                topic="news",
                search_depth=settings.web_fallback_search_depth,
                max_results=result_limit,
                include_answer=False,
            )
        except Exception as exc:
            logger.warning("Tavily search failed query=%r: %s", query, exc)
            return []

        hits = [
            self._to_hit(result, rank)
            for rank, result in enumerate(response.get("results") or [], start=1)
            if result.get("url") or result.get("title")
        ]
        cache_service.set_web_fallback(query, result_limit, hits)
        logger.info("Web fallback returned %s hits for query=%r", len(hits), query)
        return hits


web_fallback_service = WebFallbackService()
