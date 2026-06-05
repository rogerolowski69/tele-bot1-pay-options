import logging
from typing import Any

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.config import settings
from apps.api.exceptions import AppError
from packages.telegram_auth import InitDataError

logger = logging.getLogger("apps.api.errors")


def _error_body(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.warning("AppError code=%s message=%s", exc.code, exc.message, extra={"request_id": request_id})
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code=exc.code, message=exc.message, request_id=request_id, details=exc.details),
        )

    @app.exception_handler(InitDataError)
    async def init_data_error_handler(request: Request, exc: InitDataError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        return JSONResponse(
            status_code=401,
            content=_error_body(code="unauthorized", message=str(exc), request_id=request_id),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code="http_error", message=detail, request_id=request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        return JSONResponse(
            status_code=422,
            content=_error_body(
                code="validation_error",
                message="Request validation failed",
                request_id=request_id,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(httpx.HTTPStatusError)
    async def httpx_error_handler(request: Request, exc: httpx.HTTPStatusError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.error("Upstream HTTP error: %s", exc, extra={"request_id": request_id})
        return JSONResponse(
            status_code=502,
            content=_error_body(
                code="upstream_error",
                message="External service request failed",
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        message = str(exc) if settings.debug else "Internal server error"
        return JSONResponse(
            status_code=500,
            content=_error_body(code="internal_error", message=message, request_id=request_id),
        )
