from __future__ import annotations

import logging
from uuid import uuid4
from datetime import UTC, datetime

from fastapi import Request

from backend.services.support import get_application_logger, write_application_exception_log, write_application_log


LOGGING_EXCLUDED_PATHS = {
    "/api/v1/dashboard/logs/clear",
}


async def log_http_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex[:12]}"
    request.state.request_id = request_id
    started_at = datetime.now(UTC)
    try:
        response = await call_next(request)
    except Exception as error:
        logger = get_application_logger(request)
        duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
        write_application_exception_log(
            logger,
            logging.ERROR,
            "http_request_failed",
            error=error,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", ""),
        )
        raise

    logger = get_application_logger(request)
    duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
    if request.url.path not in LOGGING_EXCLUDED_PATHS:
        level = logging.ERROR if response.status_code >= 500 else logging.INFO
        write_application_log(
            logger,
            level,
            "http_request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", ""),
        )
    response.headers["X-Request-Id"] = request_id
    return response
