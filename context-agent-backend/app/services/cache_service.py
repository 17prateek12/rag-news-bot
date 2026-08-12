import logging
from datetime import date
from hashlib import sha256
from typing import Any

import orjson

from app.config import settings
from app.core.redis_client import get_sync_redis


logger = logging.getLogger(__name__)

SEARCH_VERSION_KEY = "cache:search:version"
TRENDING_KEY = "trending:queries"


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def query_fingerprint(query: str) -> str:
    return sha256(normalize_query(query).encode("utf-8")).hexdigest()[:16]


class CacheService:
    def _redis(self):
        return get_sync_redis()

    def _enabled(self) -> bool:
        return settings.cache_enabled

    def _get_search_version(self) -> int:
        if not self._enabled():
            return 0
        try:
            value = self._redis().get(SEARCH_VERSION_KEY)
            return int(value) if value is not None else 0
        except Exception as exc:
            logger.warning("Redis search version read failed: %s", exc)
            return 0

    def invalidate_search_cache(self) -> None:
        if not self._enabled():
            return
        try:
            self._redis().incr(SEARCH_VERSION_KEY)
            logger.info("Search cache invalidated (version bumped)")
        except Exception as exc:
            logger.warning("Redis search cache invalidation failed: %s", exc)

    def _get_json(self, key: str) -> Any | None:
        if not self._enabled():
            return None
        try:
            raw = self._redis().get(key)
            if raw is None:
                return None
            return orjson.loads(raw)
        except Exception as exc:
            logger.warning("Redis cache read failed key=%s: %s", key, exc)
            return None

    def _set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self._enabled():
            return
        try:
            self._redis().setex(key, ttl_seconds, orjson.dumps(value))
        except Exception as exc:
            logger.warning("Redis cache write failed key=%s: %s", key, exc)

    def _delete(self, *keys: str) -> None:
        if not self._enabled() or not keys:
            return
        try:
            self._redis().delete(*keys)
        except Exception as exc:
            logger.warning("Redis cache delete failed keys=%s: %s", keys, exc)

    def hybrid_search_key(self, query: str, limit: int) -> str:
        version = self._get_search_version()
        return f"search:hybrid:{version}:{query_fingerprint(query)}:{limit}"

    def get_hybrid_search(self, query: str, limit: int) -> dict[str, Any] | None:
        payload = self._get_json(self.hybrid_search_key(query, limit))
        if payload is not None:
            logger.debug("Hybrid search cache hit query=%r limit=%s", query, limit)
        return payload

    def set_hybrid_search(self, query: str, limit: int, payload: dict[str, Any]) -> None:
        self._set_json(
            self.hybrid_search_key(query, limit),
            payload,
            settings.cache_search_ttl_seconds,
        )

    def bm25_search_key(self, query: str, limit: int) -> str:
        version = self._get_search_version()
        return f"search:bm25:{version}:{query_fingerprint(query)}:{limit}"

    def get_bm25_search(self, query: str, limit: int) -> dict[str, Any] | None:
        payload = self._get_json(self.bm25_search_key(query, limit))
        if payload is not None:
            logger.debug("BM25 search cache hit query=%r limit=%s", query, limit)
        return payload

    def set_bm25_search(self, query: str, limit: int, payload: dict[str, Any]) -> None:
        self._set_json(
            self.bm25_search_key(query, limit),
            payload,
            600,  # 10-minute retention
        )

    def rag_retrieval_key(self, query: str, intent: str, limit: int) -> str:
        version = self._get_search_version()
        return f"rag:retrieval:{version}:{query_fingerprint(query)}:{intent}:{limit}"

    def get_rag_retrieval(
        self,
        query: str,
        intent: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
        payload = self._get_json(self.rag_retrieval_key(query, intent, limit))
        if payload is None:
            return None
        logger.debug("RAG retrieval cache hit query=%r intent=%s", query, intent)
        return payload.get("hits", []), payload.get("retrieval", {})

    def set_rag_retrieval(
        self,
        query: str,
        intent: str,
        limit: int,
        hits: list[dict[str, Any]],
        retrieval: dict[str, Any],
    ) -> None:
        self._set_json(
            self.rag_retrieval_key(query, intent, limit),
            {"hits": hits, "retrieval": retrieval},
            settings.cache_search_ttl_seconds,
        )

    def rag_response_key(self, query: str, limit: int) -> str:
        version = self._get_search_version()
        return f"rag:response:{version}:{query_fingerprint(query)}:{limit}"

    def get_rag_response(self, query: str, limit: int) -> dict[str, Any] | None:
        payload = self._get_json(self.rag_response_key(query, limit))
        if payload is not None:
            logger.debug("RAG response cache hit query=%r limit=%s", query, limit)
        return payload

    def set_rag_response(self, query: str, limit: int, payload: dict[str, Any]) -> None:
        self._set_json(
            self.rag_response_key(query, limit),
            payload,
            settings.cache_rag_ttl_seconds,
        )

    def web_fallback_key(self, query: str, limit: int) -> str:
        version = self._get_search_version()
        return f"web:tavily:{version}:{query_fingerprint(query)}:{limit}"

    def get_web_fallback(self, query: str, limit: int) -> list[dict[str, Any]] | None:
        payload = self._get_json(self.web_fallback_key(query, limit))
        if payload is not None:
            logger.debug("Web fallback cache hit query=%r", query)
        return payload

    def set_web_fallback(self, query: str, limit: int, hits: list[dict[str, Any]]) -> None:
        self._set_json(
            self.web_fallback_key(query, limit),
            hits,
            settings.web_fallback_cache_ttl_seconds,
        )



    def session_messages_key(self, session_id: str) -> str:
        return f"chat:session:{session_id}:msgs"

    def user_sessions_key(self, user_id: str) -> str:
        return f"chat:user:{user_id}:sessions"

    def get_session_messages(self, session_id: str) -> list[dict[str, Any]] | None:
        payload = self._get_json(self.session_messages_key(session_id))
        if payload is not None:
            logger.debug("Session messages cache hit session_id=%s", session_id)
        return payload

    def set_session_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        self._set_json(
            self.session_messages_key(session_id),
            messages,
            settings.cache_session_ttl_seconds,
        )

    def get_user_sessions(self, user_id: str) -> list[dict[str, Any]] | None:
        payload = self._get_json(self.user_sessions_key(user_id))
        if payload is not None:
            logger.debug("User sessions cache hit user_id=%s", user_id)
        return payload

    def set_user_sessions(self, user_id: str, sessions: list[dict[str, Any]]) -> None:
        self._set_json(
            self.user_sessions_key(user_id),
            sessions,
            settings.cache_session_ttl_seconds,
        )

    def invalidate_session(self, session_id: str, user_id: str | None = None) -> None:
        keys = [self.session_messages_key(session_id)]
        if user_id:
            keys.append(self.user_sessions_key(user_id))
        self._delete(*keys)

    def ping(self) -> bool:
        try:
            return bool(self._redis().ping())
        except Exception:
            return False


cache_service = CacheService()
