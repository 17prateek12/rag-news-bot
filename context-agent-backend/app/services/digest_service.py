import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_sync_redis
from app.core.tracing import traceable
from app.models.article import Article
from app.models.trending import TrendingEntity, article_entities
from app.models.watch import Watch
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.watch_repository import WatchRepository
from app.schemas.article import NormalizedArticleDTO
from app.services.email_service import EmailService
from app.services.llm_service import llm_service
from app.services.web_fallback_service import web_fallback_service
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DigestSummarySchema(BaseModel):
    overview: str = Field(description="2-3 sentence executive summary")
    bullets: list[str] = Field(default_factory=list, description="List of key factual update bullet points")


def _parse_digest_summary_rules(raw_text: str) -> DigestSummarySchema:
    import json
    import re

    if not raw_text or not raw_text.strip():
        return DigestSummarySchema(overview="", bullets=[])

    raw_text = raw_text.strip()

    # 1. Try JSON parse
    if (raw_text.startswith("{") and raw_text.endswith("}")) or ("```json" in raw_text):
        cleaned_json = raw_text
        if "```json" in raw_text:
            match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                cleaned_json = match.group(1)
        try:
            data = json.loads(cleaned_json)
            if isinstance(data, dict):
                overview = str(data.get("overview") or data.get("summary") or "").strip()
                bullets_raw = data.get("bullets") or data.get("key_updates") or data.get("highlights") or []
                bullets = [str(b).strip() for b in bullets_raw if str(b).strip()]
                if overview or bullets:
                    return DigestSummarySchema(overview=overview, bullets=bullets)
        except Exception:
            pass

    # 2. Rule-based line-by-line parsing
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    overview_lines = []
    bullets = []
    in_bullets = False

    header_patterns = (
        "key updates",
        "key findings",
        "key takeaways",
        "key developments",
        "highlights",
        "bullet points",
        "updates:",
        "summary:",
    )

    bullet_regex = re.compile(r"^(?:[-*•]|\d+[\.\)])\s*(.+)$")

    for line in lines:
        lower_line = line.lower()
        if any(lower_line.startswith(hp) for hp in header_patterns):
            in_bullets = True
            continue

        match = bullet_regex.match(line)
        if match:
            in_bullets = True
            bullets.append(match.group(1).strip())
        elif in_bullets:
            cleaned = line.lstrip("-*• ").strip()
            if cleaned:
                bullets.append(cleaned)
        else:
            overview_lines.append(line)

    overview = " ".join(overview_lines).strip()
    return DigestSummarySchema(overview=overview, bullets=bullets)


def parse_digest_summary_langchain(raw_text: str) -> DigestSummarySchema:
    """Parse digest raw LLM text into structured overview and bullets using LangChain PydanticOutputParser with fallback."""
    try:
        from langchain_core.output_parsers import PydanticOutputParser

        parser = PydanticOutputParser(pydantic_object=DigestSummarySchema)
        return parser.parse(raw_text)
    except Exception as exc:
        logger.debug("LangChain digest parser failed (%s), using rule-based parsing", exc)
        return _parse_digest_summary_rules(raw_text)


def parse_digest_summary(raw_text: str) -> DigestSummarySchema:
    """Parse digest raw LLM text into structured overview and bullets."""
    if settings.use_langchain_output_parsing:
        return parse_digest_summary_langchain(raw_text)
    return _parse_digest_summary_rules(raw_text)



async def resolve_canonical_entity(
    keyword: str, session: AsyncSession
) -> TrendingEntity | None:
    """Case-insensitive lookup for matching existing TrendingEntity."""
    stmt = select(TrendingEntity).where(
        func.lower(TrendingEntity.canonical_name) == func.lower(keyword.strip())
    )
    return await session.scalar(stmt)


async def find_matching_articles(
    keyword: str,
    entity_id: UUID | None,
    since: datetime,
    session: AsyncSession,
    limit: int = 10,
) -> list[Article]:
    """Find articles ingested (created_at) since the given timestamp matching keyword or entity."""
    stmt = (
        select(Article)
        .where(Article.created_at >= since)
        .options(selectinload(Article.source_relation))
        .order_by(Article.published_at.desc())
        .limit(limit)
    )

    if entity_id:
        stmt = stmt.join(
            article_entities, Article.id == article_entities.c.article_id
        ).where(article_entities.c.entity_id == entity_id)
    else:
        escaped_kw = (
            keyword.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped_kw}%"
        stmt = stmt.where(
            or_(
                Article.title.ilike(pattern, escape="\\"),
                Article.cleaned_text.ilike(pattern, escape="\\"),
            )
        )

    return list((await session.scalars(stmt)).all())


def build_digest_prompt(keyword: str, articles: list[Article]) -> str:
    articles_context = []
    for idx, art in enumerate(articles, start=1):
        source_name = art.source if art.source else "News"
        summary_or_snippet = (
            art.summary
            if art.summary
            else (art.cleaned_text[:300] if art.cleaned_text else "")
        )
        articles_context.append(
            f"[{idx}] Title: {art.title}\nSource: {source_name}\nSummary: {summary_or_snippet}"
        )

    joined_articles = "\n\n".join(articles_context)

    return f"""You are an expert news analyst creating a concise daily intelligence brief for a user tracking the topic/entity: "{keyword}".

Below are the news articles published in the last 24 hours regarding "{keyword}":

{joined_articles}

Instructions:
1. Synthesize the key developments into a clear, engaging 2-3 sentence overview.
2. Follow with 2-3 concise bullet points highlighting specific facts, decisions, or figures.
3. Maintain an objective, informative tone. Do not use generic filler phrases like "In today's news".
4. If articles cover multiple aspects, synthesize them coherently.

Output format:
[2-3 sentence executive summary]

Key Updates:
- [Bullet 1]
- [Bullet 2]
- [Bullet 3 (optional)]
"""


class DigestService:
    @classmethod
    @traceable(name="daily_digests_run", run_type="chain")
    async def run_daily_digests(
        cls,
        digest_date: date | None = None,
        since: datetime | None = None,
    ) -> dict:
        """Run daily digests generation for all active user watches.

        Groups watches by keyword/entity to ensure LLM summaries are generated
        only ONCE per unique topic, and writes idempotent Digest records per user.
        Dispatches web fallback if no local articles match, and sends email notifications.
        """
        redis_client = get_sync_redis()
        lock_key = "lock:digest:daily"

        # 1-hour Redis lock
        if not redis_client.set(lock_key, "true", ex=3600, nx=True):
            logger.warning("Daily digest job is already running. Skipping execution.")
            return {
                "status": "skipped",
                "reason": "already_running",
                "message": "Another digest job is already running.",
            }

        target_date = digest_date or datetime.now(timezone.utc).date()
        since_time = since or (datetime.now(timezone.utc) - timedelta(hours=24))

        logger.info(
            "Starting daily digest run for date=%s since=%s",
            target_date.isoformat(),
            since_time.isoformat(),
        )

        digests_created = 0
        digests_skipped = 0
        unique_keywords_checked = 0

        try:
            async with AsyncSessionLocal() as session:
                watch_repo = WatchRepository(session)
                digest_repo = DigestRepository(session)
                article_repo = ArticleRepository(session)

                active_watches = await watch_repo.list_all_active()
                if not active_watches:
                    logger.info("No active watches found.")
                    return {
                        "status": "completed",
                        "digest_date": target_date.isoformat(),
                        "unique_keywords_checked": 0,
                        "digests_created": 0,
                        "digests_skipped": 0,
                        "message": "No active watches to process.",
                    }

                # Group watches by (keyword_lower, entity_id)
                keyword_groups: dict[tuple[str, UUID | None], list[Watch]] = {}
                user_subscribed_topics: dict[UUID, tuple[str, list[str]]] = {}

                for w in active_watches:
                    key = (w.keyword.strip().lower(), w.entity_id)
                    keyword_groups.setdefault(key, []).append(w)

                    # Track user topics for notification email
                    if w.user and w.user.email:
                        if w.user_id not in user_subscribed_topics:
                            user_subscribed_topics[w.user_id] = (w.user.email, [])
                        if w.keyword not in user_subscribed_topics[w.user_id][1]:
                            user_subscribed_topics[w.user_id][1].append(w.keyword)

                unique_keywords_checked = len(keyword_groups)
                logger.info(
                    "Processing %s active watches across %s unique topic groups",
                    len(active_watches),
                    unique_keywords_checked,
                )

                for (kw_lower, entity_id), watches in keyword_groups.items():
                    canonical_keyword = watches[0].keyword
                    watch_ids = [w.id for w in watches]

                    # Batch check if watches in this group already have digests for target_date
                    existing_watch_ids = await digest_repo.get_existing_watch_ids_for_date(
                        watch_ids, target_date
                    )
                    pending_watches = [w for w in watches if w.id not in existing_watch_ids]
                    digests_skipped += len(existing_watch_ids)

                    if not pending_watches:
                        logger.debug(
                            "All %s watches for topic '%s' already have digests for %s",
                            len(watches),
                            canonical_keyword,
                            target_date,
                        )
                        continue

                    # 1. Query matching articles in local database
                    matched_articles = await find_matching_articles(
                        canonical_keyword, entity_id, since_time, session
                    )

                    # 2. Web Fallback if 0 local articles found
                    if not matched_articles and web_fallback_service.is_enabled():
                        logger.info(
                            "0 local articles for '%s'. Attempting web search fallback via Tavily.",
                            canonical_keyword,
                        )
                        try:
                            web_hits = await asyncio.to_thread(
                                web_fallback_service.search, f"{canonical_keyword} news", 5
                            )
                            if web_hits:
                                fallback_articles = []
                                for hit in web_hits:
                                    try:
                                        pub_date = (
                                            datetime.fromisoformat(
                                                hit["publish_date"].replace("Z", "+00:00")
                                            )
                                            if hit.get("publish_date")
                                            else datetime.now(timezone.utc)
                                        )
                                    except Exception:
                                        pub_date = datetime.now(timezone.utc)

                                    dto = NormalizedArticleDTO(
                                        title=hit["title"],
                                        summary=hit.get("chunk", "")[:500],
                                        url=hit["url"],
                                        source=hit.get("source", "web"),
                                        published_at=pub_date,
                                        cleaned_text=hit.get("chunk", ""),
                                        categories=[],
                                    )
                                    saved_art, _, _ = await article_repo.upsert(dto)
                                    fallback_articles.append(saved_art)
                                matched_articles = fallback_articles
                        except Exception as web_err:
                            logger.warning(
                                "Web fallback search failed for '%s': %s",
                                canonical_keyword,
                                web_err,
                            )

                    if not matched_articles:
                        logger.debug(
                            "Zero matching articles found locally and on web for topic '%s'",
                            canonical_keyword,
                        )
                        continue

                    article_ids = [a.id for a in matched_articles]

                    # 3. Generate LLM summary ONCE for this unique topic
                    prompt = build_digest_prompt(canonical_keyword, matched_articles)
                    try:
                        summary_text = await asyncio.to_thread(
                            llm_service.generate, prompt
                        )
                    except Exception as llm_err:
                        logger.error(
                            "LLM digest generation failed for topic '%s': %s",
                            canonical_keyword,
                            llm_err,
                        )
                        continue

                    # 4. Batch persist digest records across all users watching this topic
                    count = await digest_repo.create_batch_for_watches(
                        pending_watches,
                        digest_date=target_date,
                        summary_text=summary_text,
                        article_ids=article_ids,
                    )
                    digests_created += count

                # 5. Send email notification to each user who has subscribed topics
                if digests_created > 0 and user_subscribed_topics:
                    for user_id, (user_email, topics) in user_subscribed_topics.items():
                        try:
                            await EmailService.send_daily_digest_notification(
                                to_email=user_email,
                                topics=topics,
                                app_url=settings.frontend_url,
                            )
                            logger.info("Sent daily digest email notification to %s", user_email)
                        except Exception as email_err:
                            logger.error(
                                "Failed to send daily digest email to %s: %s",
                                user_email,
                                email_err,
                            )

                logger.info(
                    "Daily digest run complete: date=%s keywords=%s created=%s skipped=%s",
                    target_date.isoformat(),
                    unique_keywords_checked,
                    digests_created,
                    digests_skipped,
                )

                return {
                    "status": "completed",
                    "digest_date": target_date.isoformat(),
                    "unique_keywords_checked": unique_keywords_checked,
                    "digests_created": digests_created,
                    "digests_skipped": digests_skipped,
                    "message": f"Successfully generated {digests_created} digest(s).",
                }

        finally:
            redis_client.delete(lock_key)
