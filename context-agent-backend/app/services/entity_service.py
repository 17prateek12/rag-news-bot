import asyncio
import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trending import TrendingEntity
from app.repositories.embedding_service import embedding_service
from app.repositories.qdrant_repo import qdrant_repository
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

NER_PROMPT = """You are an expert Named Entity Recognition (NER) system.
Extract all distinct named entities (such as people, organizations, locations, events, or technologies) from the following text.

Format the output strictly as a JSON list of objects, each containing:
- "name": The exact name of the entity as it appears or slightly normalized (e.g. "Narendra Modi", "United Nations", "SpaceX", "Bihar").
- "type": One of "person", "organization", "location", "event", "technology", or "other".

Do not return any extra markdown styling, notes, or wrapper text. Only return the valid JSON array.

Text: {text}
JSON:"""


class EntityService:
    def _normalize_name(self, name: str) -> str:
        # Clean extra spaces, lowercase first, but capitalize words for canonical names
        cleaned = " ".join(name.strip().split())
        # Make it title case for standard presentation
        return cleaned.title() if cleaned else ""

    async def extract_entities(self, text: str) -> list[dict[str, str]]:
        if not text or not text.strip():
            return []
        prompt = NER_PROMPT.format(text=text)
        try:
            loop = asyncio.get_running_loop()
            def run_gen():
                return llm_service.generate(prompt)
            raw = await loop.run_in_executor(None, run_gen)
            
            # Clean markdown code blocks from response
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # strip out ```json and ```
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
                cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                entities = []
                for item in parsed:
                    if isinstance(item, dict) and "name" in item:
                        entities.append({
                            "name": str(item["name"]).strip(),
                            "type": str(item.get("type", "other")).strip().lower()
                        })
                return entities
        except Exception as exc:
            logger.warning("NER extraction failed for text: %s. Error: %s", text[:100], exc)
        return []

    async def get_or_create_canonical_entity(
        self, name: str, entity_type: str, db: AsyncSession
    ) -> TrendingEntity:
        normalized_name = self._normalize_name(name)
        if not normalized_name:
            # Fallback if empty name
            normalized_name = "Unknown Entity"

        # 1. Check if the entity already exists in Postgres
        stmt = select(TrendingEntity).filter(TrendingEntity.canonical_name == normalized_name)
        result = await db.execute(stmt)
        entity = result.scalars().first()
        if entity:
            return entity

        # 2. Generate embedding for vector space comparison
        try:
            loop = asyncio.get_running_loop()
            def embed():
                return embedding_service.embed_text(normalized_name)
            vector = await loop.run_in_executor(None, embed)
        except Exception as exc:
            logger.error("Failed to generate embedding for entity %s: %s", normalized_name, exc)
            # Fallback to direct DB create without Qdrant embedding on error
            entity = TrendingEntity(
                id=uuid.uuid4(),
                canonical_name=normalized_name,
                entity_type=entity_type
            )
            db.add(entity)
            await db.commit()
            await db.refresh(entity)
            return entity

        # 3. Query Qdrant for a nearby canonical alias
        try:
            loop = asyncio.get_running_loop()
            def qdrant_search():
                return qdrant_repository.search_entities(vector, limit=1)
            hits = await loop.run_in_executor(None, qdrant_search)
            
            if hits and hits[0]["score"] >= 0.85:
                canonical_name = hits[0]["canonical_name"]
                stmt = select(TrendingEntity).filter(TrendingEntity.canonical_name == canonical_name)
                result = await db.execute(stmt)
                entity = result.scalars().first()
                if entity:
                    logger.info("Canonicalized entity: %r -> %r (score: %s)", normalized_name, canonical_name, hits[0]["score"])
                    return entity
        except Exception as exc:
            logger.warning("Qdrant lookup failed during canonicalization for %s: %s", normalized_name, exc)

        # 4. Create a new canonical entity in Postgres and Qdrant
        entity_id = uuid.uuid4()
        entity = TrendingEntity(
            id=entity_id,
            canonical_name=normalized_name,
            entity_type=entity_type
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)

        # Upsert point to Qdrant trending_entities collection
        try:
            loop = asyncio.get_running_loop()
            def qdrant_upsert():
                return qdrant_repository.upsert_entity(entity_id, vector, normalized_name, entity_type)
            await loop.run_in_executor(None, qdrant_upsert)
        except Exception as exc:
            logger.error("Failed to upsert entity %s to Qdrant: %s", normalized_name, exc)

        return entity


entity_service = EntityService()
