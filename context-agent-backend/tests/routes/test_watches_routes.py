import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.core.admin_auth import get_current_admin
from app.core.user_auth import get_current_user
from app.main import app
from app.models.admin import Admin
from app.models.trending import TrendingEntity
from app.models.user import User
from app.models.watch import Watch


class TestWatchesRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = User(
            id=uuid.uuid4(),
            email="testuser@example.com",
            hashed_password="hashed_password",
        )
        self.admin = Admin(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password="admin_hashed_password",
        )
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_current_admin] = lambda: self.admin

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.api.routes.watches.resolve_canonical_entity")
    @patch("app.api.routes.watches.WatchRepository")
    def test_create_watch_links_entity_case_insensitively(
        self, mock_repo_cls, mock_resolve_entity
    ):
        mock_repo = MagicMock()
        mock_repo.count_for_user = AsyncMock(return_value=2)
        mock_repo.get_by_user_and_keyword = AsyncMock(return_value=None)
        
        entity_id = uuid.uuid4()
        mock_entity = TrendingEntity(id=entity_id, canonical_name="ISRO")
        mock_resolve_entity.return_value = mock_entity

        created_watch = Watch(
            id=uuid.uuid4(),
            user_id=self.user.id,
            keyword="isro",
            entity_id=entity_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_repo.create = AsyncMock(return_value=created_watch)
        mock_repo_cls.return_value = mock_repo

        response = self.client.post("/watches", json={"keyword": "isro"})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["keyword"], "isro")
        self.assertEqual(data["entity_id"], str(entity_id))
        mock_resolve_entity.assert_called_once()

    @patch("app.api.routes.watches.WatchRepository")
    def test_create_watch_limit_exceeded(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo.count_for_user = AsyncMock(return_value=5)  # limit reached
        mock_repo_cls.return_value = mock_repo

        response = self.client.post("/watches", json={"keyword": "RBI"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum watch limit", response.json()["error"]["message"])

    @patch("app.api.routes.watches.check_watch_update_rate_limit")
    @patch("app.api.routes.watches.WatchRepository")
    def test_create_watch_duplicate_keyword(self, mock_repo_cls, mock_rate_limit):
        mock_repo = MagicMock()
        mock_repo.count_for_user = AsyncMock(return_value=1)
        mock_repo.get_by_user_and_keyword = AsyncMock(return_value=MagicMock())  # already exists
        mock_repo_cls.return_value = mock_repo

        response = self.client.post("/watches", json={"keyword": "ISRO"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("already watching", response.json()["error"]["message"])

    @patch("app.api.routes.watches.check_watch_update_rate_limit")
    def test_create_watch_rate_limit_exceeded(self, mock_rate_limit):
        from fastapi import HTTPException, status
        mock_rate_limit.side_effect = HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily watch modification limit reached (5 changes allowed per day). Please try again tomorrow.",
        )

        response = self.client.post("/watches", json={"keyword": "Tesla"})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Daily watch modification limit reached", response.json()["error"]["message"])


    @patch("app.api.routes.watches.WatchRepository")
    def test_list_watches(self, mock_repo_cls):
        mock_repo = MagicMock()
        watch = Watch(
            id=uuid.uuid4(),
            user_id=self.user.id,
            keyword="Apple",
            entity_id=None,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_repo.list_for_user = AsyncMock(return_value=[watch])
        mock_repo_cls.return_value = mock_repo

        response = self.client.get("/watches")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["keyword"], "Apple")

    @patch("app.api.routes.watches.WatchRepository")
    def test_delete_watch_success(self, mock_repo_cls):
        mock_repo = MagicMock()
        watch = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=watch)
        mock_repo.delete = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        watch_id = uuid.uuid4()
        response = self.client.delete(f"/watches/{watch_id}")
        self.assertEqual(response.status_code, 204)
        mock_repo.delete.assert_called_once_with(watch)

    @patch("app.api.routes.digests.DigestRepository")
    def test_list_digests(self, mock_repo_cls):
        mock_repo = MagicMock()
        digest_item = {
            "id": uuid.uuid4(),
            "watch_id": uuid.uuid4(),
            "keyword": "ISRO",
            "digest_date": date(2026, 9, 1),
            "summary_text": "Launch successful today.",
            "article_ids": [uuid.uuid4()],
            "articles": [
                {
                    "id": uuid.uuid4(),
                    "title": "ISRO Success",
                    "url": "https://example.com/isro",
                    "source": "BBC",
                    "published_at": datetime.now(timezone.utc),
                }
            ],
            "created_at": datetime.now(timezone.utc),
        }
        mock_repo.list_recent_for_user = AsyncMock(return_value=[digest_item])
        mock_repo_cls.return_value = mock_repo

        response = self.client.get("/digests")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["keyword"], "ISRO")

    @patch("app.api.routes.admin.digests.DigestService")
    def test_admin_run_digests(self, mock_service):
        mock_service.run_daily_digests = AsyncMock(
            return_value={
                "status": "completed",
                "digest_date": "2026-09-01",
                "unique_keywords_checked": 2,
                "digests_created": 3,
                "digests_skipped": 0,
                "message": "Successfully generated 3 digest(s).",
            }
        )

        response = self.client.post("/admin/digests/run")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["digests_created"], 3)
        mock_service.run_daily_digests.assert_called_once()
