from typing import Any


class AppError(Exception):
    """Base application error with a stable code for API clients and logs."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if cause is not None:
            self.__cause__ = cause

    def to_dict(self, *, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if request_id:
            payload["request_id"] = request_id
        return payload


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400


class AuthenticationError(AppError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class AuthorizationError(AppError):
    code = "AUTHORIZATION_FAILED"
    status_code = 403


class ConfigurationError(AppError):
    code = "CONFIGURATION_ERROR"
    status_code = 500


class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    status_code = 500


class ExternalServiceError(AppError):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502


class FetchError(ExternalServiceError):
    code = "FEED_FETCH_FAILED"


class EmbeddingError(ExternalServiceError):
    code = "EMBEDDING_FAILED"


class QdrantError(ExternalServiceError):
    code = "QDRANT_ERROR"


class IngestError(AppError):
    code = "INGEST_FAILED"
    status_code = 500


class RedisError(ExternalServiceError):
    code = "REDIS_ERROR"


class SearchError(AppError):
    code = "SEARCH_FAILED"
    status_code = 502


class LLMError(ExternalServiceError):
    code = "LLM_GENERATION_FAILED"


class SpeechToTextError(ExternalServiceError):
    code = "SPEECH_TO_TEXT_FAILED"
