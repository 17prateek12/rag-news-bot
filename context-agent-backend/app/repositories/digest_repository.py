from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.watch import Digest, Watch


class DigestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_watch_and_date(
        self, watch_id: UUID, digest_date: date
    ) -> Digest | None:
        stmt = select(Digest).where(
            Digest.watch_id == watch_id, Digest.digest_date == digest_date
        )
        return await self._session.scalar(stmt)

    async def get_existing_watch_ids_for_date(
        self, watch_ids: list[UUID], digest_date: date
    ) -> set[UUID]:
        """Batch fetch watch IDs that already have a digest generated for digest_date."""
        if not watch_ids:
            return set()
        stmt = select(Digest.watch_id).where(
            Digest.watch_id.in_(watch_ids),
            Digest.digest_date == digest_date,
        )
        return set((await self._session.scalars(stmt)).all())

    async def create_batch_for_watches(
        self,
        watches: list[Watch],
        digest_date: date,
        summary_text: str,
        article_ids: list[UUID],
    ) -> list[Digest]:
        """Batch create digests for multiple subscriber watches with a single commit."""
        if not watches:
            return []

        watch_ids = [w.id for w in watches]

        # 1. Prune older previous digests for these watches (keep only single latest digest per watch)
        await self._session.execute(
            delete(Digest).where(
                Digest.watch_id.in_(watch_ids),
                Digest.digest_date < digest_date,
            )
        )

        # 2. Add all new digest entities
        new_digests = []
        for w in watches:
            digest = Digest(
                user_id=w.user_id,
                watch_id=w.id,
                digest_date=digest_date,
                summary_text=summary_text,
                article_ids=article_ids,
            )
            self._session.add(digest)
            new_digests.append(digest)

        # 3. Single atomic commit for the entire subscriber batch
        await self._session.commit()
        for d in new_digests:
            await self._session.refresh(d)
        return new_digests

    async def create_or_skip(
        self,
        user_id: UUID,
        watch_id: UUID,
        digest_date: date,
        summary_text: str,
        article_ids: list[UUID],
    ) -> tuple[Digest | None, bool]:
        existing = await self.get_by_watch_and_date(watch_id, digest_date)
        if existing:
            return existing, False

        # Delete any older previous digests for this watch (keep only single latest digest per watch)
        await self._session.execute(
            delete(Digest).where(
                Digest.watch_id == watch_id,
                Digest.digest_date < digest_date,
            )
        )

        digest = Digest(
            user_id=user_id,
            watch_id=watch_id,
            digest_date=digest_date,
            summary_text=summary_text,
            article_ids=article_ids,
        )
        self._session.add(digest)
        await self._session.commit()
        await self._session.refresh(digest)
        return digest, True

    async def list_recent_for_user(self, user_id: UUID) -> list[dict]:
        # Since only the single latest digest per watch is preserved in the DB,
        # we fetch all active watch digests without an artificial date cutoff filter.
        # This prevents digests from silently vanishing if the daily cron fails.
        stmt = (
            select(Digest)
            .join(Watch, Digest.watch_id == Watch.id)
            .where(
                Digest.user_id == user_id,
            )
            .options(selectinload(Digest.watch))
            .order_by(Digest.digest_date.desc(), Digest.created_at.desc())
        )
        digests = list((await self._session.scalars(stmt)).all())

        if not digests:
            return []

        # Collect all unique article IDs across these digests to fetch in a single query
        all_article_ids: set[UUID] = set()
        for d in digests:
            if d.article_ids:
                all_article_ids.update(d.article_ids)

        articles_by_id: dict[UUID, Article] = {}
        if all_article_ids:
            article_stmt = (
                select(Article)
                .where(Article.id.in_(all_article_ids))
                .options(selectinload(Article.source_relation))
            )
            loaded_articles = list((await self._session.scalars(article_stmt)).all())
            articles_by_id = {a.id: a for a in loaded_articles}

        results = []
        for d in digests:
            matched_articles = [
                {
                    "id": a_id,
                    "title": articles_by_id[a_id].title if a_id in articles_by_id else "Article",
                    "url": articles_by_id[a_id].url if a_id in articles_by_id else "",
                    "source": articles_by_id[a_id].source if a_id in articles_by_id else None,
                    "published_at": (
                        articles_by_id[a_id].published_at if a_id in articles_by_id else None
                    ),
                }
                for a_id in d.article_ids
                if a_id in articles_by_id
            ]

            from app.services.digest_service import parse_digest_summary
            overview, bullets = parse_digest_summary(d.summary_text)

            results.append(
                {
                    "id": d.id,
                    "watch_id": d.watch_id,
                    "keyword": d.watch.keyword if d.watch else "Watch",
                    "digest_date": d.digest_date,
                    "summary_text": d.summary_text,
                    "overview": overview,
                    "bullets": bullets,
                    "article_ids": d.article_ids,
                    "articles": matched_articles,
                    "created_at": d.created_at,
                }
            )

        return results
