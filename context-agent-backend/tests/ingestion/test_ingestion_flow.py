import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.ingestion_service import run_ingestion
from app.worker.tasks import ingest_all_feeds


class TestIngestionFlow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.services.ingestion_service.get_sync_redis")
    @patch("app.services.ingestion_service.AsyncSessionLocal")
    @patch("app.services.ingestion_service.IngestOrchestrator")
    async def test_run_ingestion_success(self, mock_orchestrator, mock_session_local, mock_get_redis):
        # Setup Redis mock
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # Lock successfully acquired
        mock_get_redis.return_value = mock_redis

        # Setup orchestrator mock
        mock_orch_instance = mock_orchestrator.return_value
        mock_res = MagicMock(saved=5, updated=2, embedded=7, errors=[])
        mock_orch_instance.run_all = AsyncMock(return_value=[mock_res])

        # Run the shared ingestion function
        result = await run_ingestion()

        # Assertions
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["feeds_processed"], 1)
        self.assertEqual(result["saved"], 5)
        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["embedded"], 7)
        self.assertEqual(result["errors"], 0)

        # Verify lock interactions
        mock_redis.set.assert_called_once_with("lock:ingest:all", "true", ex=7200, nx=True)
        mock_redis.delete.assert_called_once_with("lock:ingest:all")
        mock_redis.publish.assert_called_once()

    @patch("app.services.ingestion_service.get_sync_redis")
    async def test_run_ingestion_already_running(self, mock_get_redis):
        # Setup Redis mock to simulate that lock acquisition failed
        mock_redis = MagicMock()
        mock_redis.set.return_value = False
        mock_get_redis.return_value = mock_redis

        # Run the shared ingestion function
        result = await run_ingestion()

        # Assertions
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "already_running")
        
        # Verify lock was not cleared and orchestrator not run
        mock_redis.delete.assert_not_called()

    @patch("app.worker.tasks.run_ingestion")
    def test_celery_task_calls_shared_function(self, mock_run_ingestion):
        # Patch the async runner in task
        with patch("app.worker.tasks._run_async") as mock_run_async:
            mock_run_async.return_value = {"status": "completed", "saved": 2}
            
            # Execute Celery task
            result = ingest_all_feeds()
            
            # Assertions
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["saved"], 2)
            mock_run_async.assert_called_once()

    @patch("app.api.routes.admin.ingest.run_ingestion")
    def test_fastapi_endpoint_calls_shared_function(self, mock_run_ingestion):
        # Override admin authentication dependency in FastAPI
        from app.core.admin_auth import get_current_admin
        from app.models.admin import Admin
        
        mock_admin = MagicMock(spec=Admin)
        app.dependency_overrides[get_current_admin] = lambda: mock_admin
        
        # Mock the run_ingestion return payload
        mock_run_ingestion.return_value = {
            "status": "completed",
            "feeds_processed": 1,
            "saved": 3,
            "updated": 0,
            "embedded": 3,
            "errors": 0,
            "message": "Global feed ingestion has completed."
        }

        # Make synchronous request to endpoint using TestClient
        response = self.client.post("/admin/ingest/run")

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["saved"], 3)
        mock_run_ingestion.assert_called_once()
