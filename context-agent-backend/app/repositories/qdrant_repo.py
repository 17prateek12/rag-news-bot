import logging
import uuid
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.core.exceptions import QdrantError

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        logger.info("Connecting to Qdrant url=%s", settings.qdrant_url)
        try:
            _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)
        except Exception as exc:
            raise QdrantError(
                "Failed to connect to Qdrant",
                details={"url": settings.qdrant_url},
                cause=exc,
            ) from exc
    return _client


class QdrantRepository:
    def __init__(self) -> None:
        self._client = get_qdrant_client()
        self._collection = settings.qdrant_collection
        self._entity_collection = "trending_entities"

    def ensure_collection(self) -> None:
        try:
            collections = {item.name for item in self._client.get_collections().collections}
            if self._collection not in collections:
                logger.info("Creating Qdrant collection: %s", self._collection)
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimensions,
                        distance=Distance.COSINE,
                    ),
                )
            else:
                logger.info("Qdrant collection exists: %s", self._collection)

            if self._entity_collection not in collections:
                logger.info("Creating Qdrant entity collection: %s", self._entity_collection)
                self._client.create_collection(
                    collection_name=self._entity_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimensions,
                        distance=Distance.COSINE,
                    ),
                )
            else:
                logger.info("Qdrant entity collection exists: %s", self._entity_collection)

            # Ensure payload index for article_id exists
            try:
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name="article_id",
                    field_schema="keyword",
                )
                logger.info("Ensured keyword payload index for 'article_id' on collection %s", self._collection)
            except Exception as index_exc:
                logger.debug("Payload index creation skipped: %s", index_exc)
        except Exception as exc:
            raise QdrantError(
                "Failed to ensure Qdrant collections",
                details={"collection": self._collection, "entity_collection": self._entity_collection},
                cause=exc,
            ) from exc

    def collection_info(self) -> dict[str, Any]:
        try:
            info = self._client.get_collection(self._collection)
            return {
                "name": self._collection,
                "points_count": info.points_count,
                "status": str(info.status),
                "vector_size": settings.embedding_dimensions,
            }
        except Exception as exc:
            raise QdrantError(
                "Failed to read Qdrant collection info",
                details={"collection": self._collection},
                cause=exc,
            ) from exc

    def delete_points(self, point_ids: list[uuid.UUID]) -> None:
        if not point_ids:
            return
        logger.debug("Deleting %s Qdrant points", len(point_ids))
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=[str(point_id) for point_id in point_ids],
            )
        except Exception as exc:
            raise QdrantError(
                "Failed to delete Qdrant points",
                details={"count": len(point_ids)},
                cause=exc,
            ) from exc

    def delete_by_article_id(self, article_id: uuid.UUID) -> None:
        logger.debug("Deleting Qdrant points for article_id=%s", article_id)
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=Filter(
                    must=[FieldCondition(key="article_id", match=MatchValue(value=str(article_id)))]
                ),
            )
        except Exception as exc:
            raise QdrantError(
                "Failed to delete Qdrant points by article",
                details={"article_id": str(article_id)},
                cause=exc,
            ) from exc

    def upsert_chunks(
        self,
        *,
        article_id: uuid.UUID,
        title: str,
        source: str,
        url: str,
        published_at: datetime,
        categories: list[str],
        chunks: list[str],
        vectors: list[list[float]],
    ) -> list[uuid.UUID]:
        point_ids: list[uuid.UUID] = []
        points: list[PointStruct] = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            point_id = uuid.uuid4()
            point_ids.append(point_id)
            points.append(
                PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload={
                        "article_id": str(article_id),
                        "title": title,
                        "chunk": chunk,
                        "source": source,
                        "source_type": "rss",
                        "url": url,
                        "publish_date": published_at.isoformat(),
                        "categories": categories,
                        "chunk_index": idx,
                    },
                )
            )
        logger.info(
            "Upserting %s chunks to Qdrant article_id=%s source=%s",
            len(points),
            article_id,
            source,
        )
        try:
            self._client.upsert(collection_name=self._collection, points=points)
        except Exception as exc:
            raise QdrantError(
                "Failed to upsert chunks to Qdrant",
                details={"article_id": str(article_id), "chunk_count": len(points)},
                cause=exc,
            ) from exc
        return point_ids

    def search(self, query_vector: list[float], limit: int = 6) -> list[dict[str, Any]]:
        logger.info("Qdrant search limit=%s", limit)
        try:
            response = self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            hits = response.points
        except Exception as exc:
            raise QdrantError(
                "Qdrant search failed",
                details={"limit": limit},
                cause=exc,
            ) from exc
        return [
            {
                "score": hit.score,
                "article_id": hit.payload.get("article_id"),
                "title": hit.payload.get("title"),
                "chunk": hit.payload.get("chunk"),
                "source": hit.payload.get("source"),
                "url": hit.payload.get("url"),
                "publish_date": hit.payload.get("publish_date"),
                "categories": hit.payload.get("categories", []),
                "chunk_index": hit.payload.get("chunk_index"),
            }
            for hit in hits
            if hit.payload
        ]

    def list_chunks_for_article(self, article_id: uuid.UUID) -> list[dict[str, Any]]:
        try:
            records, _ = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="article_id", match=MatchValue(value=str(article_id)))]
                ),
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            raise QdrantError(
                "Failed to list Qdrant chunks for article",
                details={"article_id": str(article_id)},
                cause=exc,
            ) from exc
        return [
            {
                "point_id": str(record.id),
                "chunk_index": record.payload.get("chunk_index"),
                "chunk": record.payload.get("chunk"),
            }
            for record in records
            if record.payload
        ]

    def search_entities(self, query_vector: list[float], limit: int = 1) -> list[dict[str, Any]]:
        try:
            response = self._client.query_points(
                collection_name=self._entity_collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            hits = response.points
        except Exception as exc:
            raise QdrantError(
                "Qdrant entity search failed",
                cause=exc,
            ) from exc
        return [
            {
                "score": hit.score,
                "entity_id": uuid.UUID(hit.id) if isinstance(hit.id, str) else hit.id,
                "canonical_name": hit.payload.get("canonical_name"),
                "entity_type": hit.payload.get("entity_type"),
            }
            for hit in hits
            if hit.payload
        ]

    def upsert_entity(self, entity_id: uuid.UUID, vector: list[float], canonical_name: str, entity_type: str) -> None:
        try:
            self._client.upsert(
                collection_name=self._entity_collection,
                points=[
                    PointStruct(
                        id=str(entity_id),
                        vector=vector,
                        payload={
                            "canonical_name": canonical_name,
                            "entity_type": entity_type,
                            "created_at": datetime.utcnow().isoformat(),
                        }
                    )
                ]
            )
        except Exception as exc:
            raise QdrantError(
                "Failed to upsert entity to Qdrant",
                details={"entity_id": str(entity_id), "canonical_name": canonical_name},
                cause=exc,
            ) from exc


qdrant_repository = QdrantRepository()
