import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FetchError, NotFoundError, ValidationError
from app.ingestion.content_builder import build_cleaned_text
from app.ingestion.feed_context import FeedContext
from app.ingestion.fetcher import FeedFetcher
from app.ingestion.parsers.registry import ParserRegistry
from app.ingestion.vector_loader import VectorLoader
from app.models.rss_source import RssSource
from app.repositories.article_repository import ArticleRepository
from app.repositories.rss_source_repository import RssSourceRepository
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


@dataclass
class IngestErrorDetail:
    stage: str
    code: str
    message: str
    article_url: str | None = None


@dataclass
class IngestResult:
    feed_url: str
    source: str
    fetched: int
    saved: int
    updated: int
    skipped: int
    embedded: int
    embed_skipped: int
    embed_errors: list[str]
    errors: list[str]
    error_details: list[dict] = field(default_factory=list)


class IngestOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._fetcher = FeedFetcher()
        self._rss_repo = RssSourceRepository(session)
        self._article_repo = ArticleRepository(session)
        self._vector_loader = VectorLoader(session)

    async def run_all(self) -> list[IngestResult]:
        sources = await self._rss_repo.list_active()
        logger.info("Starting ingest for %s active feeds", len(sources))
        results: list[IngestResult] = []
        for source in sources:
            results.append(await self.run_source(source))
        logger.info("Completed ingest for %s feeds", len(results))
        return results

    async def run_by_id(self, source_id: int) -> IngestResult:
        source = await self._rss_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(
                "RSS source not found",
                details={"source_id": source_id},
            )
        if not source.is_active:
            raise ValidationError(
                "RSS source is inactive",
                details={"source_id": source_id},
            )
        return await self.run_source(source)

    def _record_error(
        self,
        result: IngestResult,
        *,
        stage: str,
        code: str,
        message: str,
        article_url: str | None = None,
    ) -> None:
        detail = IngestErrorDetail(
            stage=stage,
            code=code,
            message=message,
            article_url=article_url,
        )
        result.error_details.append(detail.__dict__)
        if stage == "embed":
            if message not in result.embed_errors:
                result.embed_errors.append(message)
        else:
            if message not in result.errors:
                result.errors.append(message)
        logger.error(
            "Ingest error stage=%s code=%s source=%s url=%s message=%s",
            stage,
            code,
            result.source,
            article_url,
            message,
        )

    async def run_source(self, rss_source: RssSource) -> IngestResult:
        result = IngestResult(
            feed_url=rss_source.feed_url,
            source=rss_source.source,
            fetched=0,
            saved=0,
            updated=0,
            skipped=0,
            embedded=0,
            embed_skipped=0,
            embed_errors=[],
            errors=[],
        )

        logger.info(
            "Ingest start source=%s parser=%s url=%s",
            rss_source.source,
            rss_source.parse_key,
            rss_source.feed_url,
        )

        try:
            feed = await self._fetcher.fetch(rss_source.feed_url)
        except FetchError as exc:
            self._record_error(
                result,
                stage="fetch",
                code=exc.code,
                message=exc.message,
            )
            logger.error("Ingest aborted for source=%s due to fetch failure", rss_source.source)
            return result

        parser = ParserRegistry.get(rss_source.parse_key)
        context = FeedContext(
            source=rss_source.source,
            feed_url=rss_source.feed_url,
            default_category=rss_source.category.name,
        )

        entries = getattr(feed, "entries", []) or []
        result.fetched = len(entries)
        logger.info("Processing %s entries for source=%s", result.fetched, rss_source.source)

        for entry in entries:
            article_url = getattr(entry, "link", None)
            try:
                normalized = parser.parse_entry(entry, context)
                if not normalized:
                    result.skipped += 1
                    logger.debug("Skipped unparsable entry url=%s", article_url)
                    continue

                normalized.cleaned_text = build_cleaned_text(normalized)
                article, created, content_changed = await self._article_repo.upsert(normalized)
                if created:
                    result.saved += 1
                    logger.info("Saved article url=%s", article.url)
                else:
                    result.updated += 1
                    logger.debug("Updated article url=%s content_changed=%s", article.url, content_changed)

                needs_embed = content_changed or (article.embedded_at is None)
                if needs_embed:
                    embed_result = await self._vector_loader.embed_article(article)
                    if embed_result.embedded:
                        result.embedded += 1
                        try:
                            from app.services.entity_service import entity_service
                            from app.services.trending_service import trending_service
                            
                            entities = await entity_service.extract_entities(article.title + " " + (article.summary or ""))
                            for entity_info in entities:
                                entity_obj = await entity_service.get_or_create_canonical_entity(
                                    entity_info["name"], entity_info["type"], self._session
                                )
                                if entity_obj not in article.entities_relation:
                                    article.entities_relation.append(entity_obj)
                                    self._session.add(article)
                                await trending_service.increment_news_count(entity_obj.id, self._session)
                            await self._session.commit()
                        except Exception as entity_exc:
                            await self._session.rollback()
                            logger.exception("Failed to extract and link entities during ingestion for article %s: %s", article.id, entity_exc)
                    elif embed_result.skipped:
                        result.embed_skipped += 1
                        logger.info(
                            "Embed skipped article_id=%s code=%s reason=%s",
                            article.id,
                            embed_result.error_code,
                            embed_result.error,
                        )
                    elif embed_result.error:
                        self._record_error(
                            result,
                            stage="embed",
                            code=embed_result.error_code or "EMBEDDING_FAILED",
                            message=embed_result.error,
                            article_url=article.url,
                        )
                else:
                    result.embed_skipped += 1
                    logger.debug("Embed skipped unchanged article_id=%s", article.id)
            except Exception as exc:
                await self._session.rollback()
                self._record_error(
                    result,
                    stage="parse",
                    code="ARTICLE_PROCESSING_FAILED",
                    message=str(exc),
                    article_url=article_url,
                )
                result.skipped += 1

        logger.info(
            "Ingest complete source=%s fetched=%s saved=%s updated=%s embedded=%s "
            "embed_skipped=%s errors=%s embed_errors=%s",
            result.source,
            result.fetched,
            result.saved,
            result.updated,
            result.embedded,
            result.embed_skipped,
            len(result.errors),
            len(result.embed_errors),
        )
        if result.embedded > 0 or result.saved > 0:
            cache_service.invalidate_search_cache()
        return result
