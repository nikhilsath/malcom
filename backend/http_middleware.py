from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import Request

from backend.services.support import get_application_logger, write_application_log


async def log_http_requests(request: Request, call_next):
    started_at = datetime.now(UTC)
    try:
        response = await call_next(request)
    except Exception as error:
        logger = get_application_logger(request)
        duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
        write_application_log(
            logger,
            logging.ERROR,
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            error=str(error),
        )
        raise

    logger = get_application_logger(request)
    duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
    level = logging.ERROR if response.status_code >= 500 else logging.INFO
    write_application_log(
        logger,
        level,
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else None,
    )
    return response
