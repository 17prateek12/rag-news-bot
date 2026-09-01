import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.core.security import (
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
)
from app.core.user_auth import get_current_user
from app.main import app
from app.models.user import User


class TestPasswordRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.raw_password = "CurrentPassword123!"
        self.hashed_password = hash_password(self.raw_password)
        self.user = User(
            id=uuid.uuid4(),
            email="testuser@example.com",
            hashed_password=self.hashed_password,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_token_helpers(self):
        token = create_password_reset_token("user@example.com", expire_minutes=15)
        payload = decode_password_reset_token(token)
        self.assertEqual(payload["sub"], "user@example.com")
        self.assertEqual(payload["token_type"], "password_reset")

    @patch("app.api.routes.auth.UserRepository")
    def test_change_password_success(self, mock_repo_cls):
        app.dependency_overrides[get_current_user] = lambda: self.user
        mock_repo = MagicMock()
        mock_repo.update_password = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "CurrentPassword123!",
                "new_password": "NewSecretPassword456!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password changed successfully.")
        mock_repo.update_password.assert_called_once()

    @patch("app.api.routes.auth.UserRepository")
    def test_change_password_incorrect_current_password(self, mock_repo_cls):
        app.dependency_overrides[get_current_user] = lambda: self.user
        mock_repo = MagicMock()
        mock_repo.update_password = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewSecretPassword456!",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Incorrect current password", response.json()["error"]["message"])
        mock_repo.update_password.assert_not_called()

    @patch("app.api.routes.auth.EmailService.send_password_reset_email")
    @patch("app.api.routes.auth.UserRepository")
    def test_forgot_password_registered_user(self, mock_repo_cls, mock_send_email):
        mock_repo = MagicMock()
        mock_repo.get_by_email = AsyncMock(return_value=self.user)
        mock_repo_cls.return_value = mock_repo
        mock_send_email.return_value = True

        response = self.client.post(
            "/auth/forgot-password",
            json={"email": "testuser@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("password reset link has been sent", data["message"])
        # Verify token is NEVER returned in response
        self.assertNotIn("reset_token", data)
        mock_send_email.assert_called_once()

    @patch("app.api.routes.auth.EmailService.send_password_reset_email")
    @patch("app.api.routes.auth.UserRepository")
    def test_forgot_password_unregistered_user(self, mock_repo_cls, mock_send_email):
        mock_repo = MagicMock()
        mock_repo.get_by_email = AsyncMock(return_value=None)
        mock_repo_cls.return_value = mock_repo

        response = self.client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("password reset link has been sent", data["message"])
        self.assertNotIn("reset_token", data)
        mock_send_email.assert_not_called()

    @patch("app.api.routes.auth.UserRepository")
    def test_reset_password_success(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo.get_by_email = AsyncMock(return_value=self.user)
        mock_repo.update_password = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        token = create_password_reset_token(self.user.email)
        response = self.client.post(
            "/auth/reset-password",
            json={
                "token": token,
                "new_password": "BrandNewPassword789!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password reset successfully", response.json()["message"])
        mock_repo.update_password.assert_called_once()

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            "/auth/reset-password",
            json={
                "token": "invalid.jwt.token",
                "new_password": "BrandNewPassword789!",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid or expired", response.json()["error"]["message"])
