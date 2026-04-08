"""Postgres connection probe helper for connector health checks.

Exposes `probe_postgres_connection(auth_config)` which attempts a short-lived
connection to a PostgreSQL server using `psycopg` and returns a tuple of
(ok: bool, message: str). Network/unreachable errors raise `HTTPException` with
502 to match other connector probe behaviors.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from starlette import status

import psycopg


def probe_postgres_connection(auth_config: dict[str, Any]) -> tuple[bool, str]:
    host = str(auth_config.get("host") or auth_config.get("hostname") or "").strip()
    port = int(auth_config.get("port") or 0) or 5432
    database = str(auth_config.get("database") or auth_config.get("dbname") or "").strip()
    user = str(auth_config.get("username") or auth_config.get("user") or "").strip()
    password = auth_config.get("password") or auth_config.get("password_input") or ""
    sslmode = auth_config.get("sslmode")

    dsn_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "dbname": database,
        "user": user,
        "password": password,
        "connect_timeout": 5,
    }
    if sslmode:
        dsn_kwargs["sslmode"] = sslmode

    try:
        # Use a short-lived connection to verify credentials and reachability.
        with psycopg.connect(**dsn_kwargs) as conn:
            # Simple lightweight server-side check: open and close the connection.
            pass
    except psycopg.OperationalError as error:
        msg = str(error)
        lowered = msg.lower()
        # Authentication failures
        if "password authentication failed" in lowered or "authentication failed" in lowered or "password" in lowered and "authentication" in lowered:
            return False, "PostgreSQL rejected the saved credentials. Verify username and password."
        # Database not found
        if "does not exist" in lowered or "database \"" in lowered and "\" does not exist" in lowered:
            return False, "Database not found. Verify the database name and try again."
        # Network / host resolution / connection refused -> surface as 502
        if (
            "could not connect to server" in lowered
            or "connection refused" in lowered
            or "name or service not known" in lowered
            or "timed out" in lowered
            or "timeout" in lowered
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach PostgreSQL server while checking the connector: {msg}",
            ) from error
        # Fallback to a user-facing message
        return False, f"PostgreSQL reported an error: {msg}"
    except Exception as error:  # pragma: no cover - defensive
        msg = str(error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach PostgreSQL server while checking the connector: {msg}",
        ) from error

    return True, "PostgreSQL connection verified."
