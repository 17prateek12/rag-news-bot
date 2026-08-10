import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.request_context import get_request_id

logger = logging.getLogger(__name__)


def _error_payload(
    *,
    code: str,
    message: str,
    details: dict | None = None,
) -> dict:
    payload = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    request_id = get_request_id()
    if request_id:
        payload["error"]["request_id"] = request_id
    if details:
        payload["error"]["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError [%s] %s %s -> %s",
            exc.code,
            request.method,
            request.url.path,
            exc.message,
            extra={"details": exc.details},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details or None,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        logger.warning(
            "HTTPException %s %s -> %s",
            request.method,
            request.url.path,
            exc.detail,
        )
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message", str(detail))
            details = detail
        else:
            message = str(detail)
            details = None
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code="HTTP_ERROR",
                message=message,
                details=details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "ValidationError %s %s -> %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                code="REQUEST_VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            ),
        )
