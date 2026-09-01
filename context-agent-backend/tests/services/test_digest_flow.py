import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.models.article import Article
from app.models.watch import Watch
from app.services.digest_service import (
    DigestService,
    build_digest_prompt,
    find_matching_articles,
    resolve_canonical_entity,
)


class TestDigestFlow(unittest.IsolatedAsyncioTestCase):
    def test_build_digest_prompt(self):
        art1 = MagicMock(
            spec=Article,
            title="ISRO launches new earth observation satellite",
            summary="A major milestone for the space agency.",
            source="The Hindu",
            cleaned_text="",
        )
        prompt = build_digest_prompt("ISRO", [art1])
        self.assertIn("ISRO", prompt)
        self.assertIn("ISRO launches new earth observation satellite", prompt)
        self.assertIn("The Hindu", prompt)

    @patch("app.services.digest_service.select")
    async def test_resolve_canonical_entity_case_insensitive(self, mock_select):
        mock_session = AsyncMock()
        mock_entity = MagicMock(id=uuid.uuid4(), canonical_name="ISRO")
        mock_session.scalar.return_value = mock_entity

        result = await resolve_canonical_entity("isro", mock_session)
        self.assertEqual(result, mock_entity)
        mock_session.scalar.assert_called_once()

    @patch("app.services.digest_service.AsyncSessionLocal")
    @patch("app.services.digest_service.get_sync_redis")
    @patch("app.services.digest_service.WatchRepository")
    @patch("app.services.digest_service.DigestRepository")
    @patch("app.services.digest_service.find_matching_articles")
    @patch("app.services.digest_service.llm_service")
    async def test_run_daily_digests_deduplicates_llm_and_is_idempotent(
        self,
        mock_llm,
        mock_find_articles,
        mock_digest_repo_cls,
        mock_watch_repo_cls,
        mock_get_redis,
        mock_session_local,
    ):
        # 1. Setup Redis Mock
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # lock acquired
        mock_get_redis.return_value = mock_redis

        # 2. Setup Watches (2 different users watching the same keyword "isro" / "ISRO")
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        watch1 = Watch(
            id=uuid.uuid4(),
            user_id=user1_id,
            keyword="ISRO",
            entity_id=entity_id,
            is_active=True,
        )
        watch1.user = MagicMock(email="user1@example.com")
        watch2 = Watch(
            id=uuid.uuid4(),
            user_id=user2_id,
            keyword="isro",
            entity_id=entity_id,
            is_active=True,
        )
        watch2.user = MagicMock(email="user2@example.com")

        mock_watch_repo = MagicMock()
        mock_watch_repo.list_all_active = AsyncMock(return_value=[watch1, watch2])
        mock_watch_repo_cls.return_value = mock_watch_repo

        # 3. Setup Digest Repository Mock (initially no digests exist for today)
        mock_digest_repo = MagicMock()
        mock_digest_repo.get_by_watch_and_date = AsyncMock(return_value=None)
        mock_digest_repo.create_or_skip = AsyncMock(return_value=(MagicMock(), True))
        mock_digest_repo_cls.return_value = mock_digest_repo

        # 4. Setup Matching Articles Mock
        art = MagicMock(
            id=uuid.uuid4(),
            title="ISRO mission successful",
            summary="New satellite in orbit.",
            source="BBC",
            cleaned_text="Article text",
        )
        mock_find_articles.return_value = [art]

        # 5. Setup LLM Mock
        mock_llm.generate.return_value = (
            "Executive summary on ISRO.\n\nKey Updates:\n- Mission launch successful."
        )

        # 6. Execute Run
        today = date(2026, 9, 1)
        with patch("app.services.digest_service.EmailService.send_daily_digest_notification", new_callable=AsyncMock) as mock_send_email:
            result = await DigestService.run_daily_digests(digest_date=today)

            # 7. Assertions
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["unique_keywords_checked"], 1)
            self.assertEqual(result["digests_created"], 2)  # 2 user digests created
            self.assertEqual(result["digests_skipped"], 0)

            # CRITICAL VERIFICATION: LLM was called only ONCE for both users!
            mock_llm.generate.assert_called_once()

            # Both user digests were saved
            self.assertEqual(mock_digest_repo.create_or_skip.call_count, 2)
            mock_redis.delete.assert_called_once_with("lock:digest:daily")

            # Notification emails were dispatched to both users
            self.assertEqual(mock_send_email.call_count, 2)

    @patch("app.services.digest_service.AsyncSessionLocal")
    @patch("app.services.digest_service.get_sync_redis")
    @patch("app.services.digest_service.WatchRepository")
    @patch("app.services.digest_service.DigestRepository")
    @patch("app.services.digest_service.ArticleRepository")
    @patch("app.services.digest_service.find_matching_articles")
    @patch("app.services.digest_service.web_fallback_service")
    @patch("app.services.digest_service.llm_service")
    async def test_run_daily_digests_web_search_fallback(
        self,
        mock_llm,
        mock_web_service,
        mock_find_articles,
        mock_article_repo_cls,
        mock_digest_repo_cls,
        mock_watch_repo_cls,
        mock_get_redis,
        mock_session_local,
    ):
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_get_redis.return_value = mock_redis

        user_id = uuid.uuid4()
        watch = Watch(
            id=uuid.uuid4(),
            user_id=user_id,
            keyword="Quantum Computing",
            entity_id=None,
            is_active=True,
        )
        watch.user = MagicMock(email="user@example.com")

        mock_watch_repo = MagicMock()
        mock_watch_repo.list_all_active = AsyncMock(return_value=[watch])
        mock_watch_repo_cls.return_value = mock_watch_repo

        mock_digest_repo = MagicMock()
        mock_digest_repo.get_by_watch_and_date = AsyncMock(return_value=None)
        mock_digest_repo.create_or_skip = AsyncMock(return_value=(MagicMock(), True))
        mock_digest_repo_cls.return_value = mock_digest_repo

        # 0 local articles found
        mock_find_articles.return_value = []

        # Web fallback enabled with hits
        mock_web_service.is_enabled.return_value = True
        mock_web_service.search.return_value = [
            {
                "title": "Quantum chip sets record",
                "chunk": "Breakthrough in qubit coherence.",
                "url": "https://example.com/quantum",
                "source": "web:tech",
                "publish_date": "2026-09-01T12:00:00Z",
            }
        ]

        saved_art = MagicMock(id=uuid.uuid4())
        mock_article_repo = MagicMock()
        mock_article_repo.upsert = AsyncMock(return_value=(saved_art, True, False))
        mock_article_repo_cls.return_value = mock_article_repo

        mock_llm.generate.return_value = "Quantum computing updates summary."

        with patch("app.services.digest_service.EmailService.send_daily_digest_notification", new_callable=AsyncMock) as mock_send_email:
            result = await DigestService.run_daily_digests()

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["digests_created"], 1)
            mock_web_service.search.assert_called_once_with("Quantum Computing news", 5)
            mock_article_repo.upsert.assert_called_once()
            mock_send_email.assert_called_once()

    @patch("app.services.digest_service.get_sync_redis")
    async def test_run_daily_digests_locked(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.set.return_value = False  # Lock already held
        mock_get_redis.return_value = mock_redis

        result = await DigestService.run_daily_digests()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "already_running")
        mock_redis.delete.assert_not_called()
