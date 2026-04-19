from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, status

from backend.database import fetch_one
from backend.schemas.platform import FrontendSessionSummary
from backend.services.utils import utc_now_iso

DEFAULT_PLATFORM_SCOPES = ("platform:read", "platform:embed:read")


def get_frontend_bootstrap_token() -> str:
    return os.getenv("MALCOM_FRONTEND_BOOTSTRAP_TOKEN", "").strip()


def get_frontend_access_ttl_minutes() -> int:
    raw_value = os.getenv("MALCOM_FRONTEND_ACCESS_TOKEN_TTL_MINUTES", "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 15
    return max(5, min(parsed or 15, 24 * 60))


def get_frontend_refresh_ttl_days() -> int:
    raw_value = os.getenv("MALCOM_FRONTEND_REFRESH_TOKEN_TTL_DAYS", "").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 7
    return max(1, min(parsed or 7, 180))


def ensure_frontend_bootstrap_token(expected_token: str) -> None:
    configured_token = get_frontend_bootstrap_token()
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hosted frontend auth is not configured. Set MALCOM_FRONTEND_BOOTSTRAP_TOKEN and try again.",
        )
    if not secrets.compare_digest(configured_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid hosted frontend bootstrap token.")


def create_frontend_session(
    connection: Any,
    *,
    operator_name: str,
    bootstrap_token: str,
    client_name: str,
    requested_origin: str | None,
    requested_scopes: list[str] | None,
) -> tuple[FrontendSessionSummary, str, str]:
    ensure_frontend_bootstrap_token(bootstrap_token)
    now = _utc_now()
    access_expires_at = now + timedelta(minutes=get_frontend_access_ttl_minutes())
    refresh_expires_at = now + timedelta(days=get_frontend_refresh_ttl_days())
    access_token = _generate_token("malcom_at")
    refresh_token = _generate_token("malcom_rt")
    session_id = f"frontend_session_{uuid4().hex[:16]}"
    scopes = _normalize_scopes(requested_scopes)
    metadata = {
        "session_type": "hosted-frontend",
        "requested_scopes": scopes,
        "session_lifecycle": {
            "session_mode": "refreshable",
            "rotation_strategy": "rolling",
            "access_token_ttl_minutes": get_frontend_access_ttl_minutes(),
            "refresh_token_ttl_days": get_frontend_refresh_ttl_days(),
            "bootstrap_token_required": True,
        },
    }
    if requested_origin:
        metadata["requested_origin"] = requested_origin

    connection.execute(
        """
        INSERT INTO frontend_sessions (
            id,
            operator_name,
            client_name,
            status,
            scopes_json,
            access_token_hash,
            refresh_token_hash,
            metadata_json,
            issued_at,
            access_expires_at,
            refresh_expires_at,
            last_used_at,
            revoked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            operator_name.strip(),
            client_name.strip(),
            "active",
            json.dumps(scopes),
            _hash_token(access_token),
            _hash_token(refresh_token),
            json.dumps(metadata),
            now.isoformat(),
            access_expires_at.isoformat(),
            refresh_expires_at.isoformat(),
            now.isoformat(),
            None,
        ),
    )
    connection.commit()
    return (
        FrontendSessionSummary(
            id=session_id,
            operator_name=operator_name.strip(),
            client_name=client_name.strip(),
            status="active",
            session_type="hosted-frontend",
            requested_origin=requested_origin,
            requested_scopes=scopes,
            scopes=scopes,
            issued_at=now.isoformat(),
            access_expires_at=access_expires_at.isoformat(),
            refresh_expires_at=refresh_expires_at.isoformat(),
            last_used_at=now.isoformat(),
            metadata=metadata,
        ),
        access_token,
        refresh_token,
    )


def refresh_frontend_session(
    connection: Any,
    *,
    refresh_token: str,
    client_name: str | None,
) -> tuple[FrontendSessionSummary, str, str]:
    session_row = _load_session_by_refresh_token(connection, refresh_token)
    _assert_session_refreshable(session_row)
    if client_name and client_name.strip() and client_name.strip() != session_row["client_name"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Refresh token is not valid for this client.")

    now = _utc_now()
    access_token = _generate_token("malcom_at")
    next_refresh_token = _generate_token("malcom_rt")
    next_access_expires_at = now + timedelta(minutes=get_frontend_access_ttl_minutes())
    next_refresh_expires_at = now + timedelta(days=get_frontend_refresh_ttl_days())
    metadata = _load_json_object(session_row.get("metadata_json"))
    metadata["session_type"] = metadata.get("session_type") or "hosted-frontend"
    metadata["last_refreshed_at"] = now.isoformat()
    metadata.setdefault("requested_scopes", _load_json_list(session_row.get("scopes_json")))
    connection.execute(
        """
        UPDATE frontend_sessions
        SET access_token_hash = ?,
            refresh_token_hash = ?,
            access_expires_at = ?,
            refresh_expires_at = ?,
            metadata_json = ?,
            last_used_at = ?,
            status = 'active'
        WHERE id = ?
        """,
        (
            _hash_token(access_token),
            _hash_token(next_refresh_token),
            next_access_expires_at.isoformat(),
            next_refresh_expires_at.isoformat(),
            json.dumps(metadata),
            now.isoformat(),
            session_row["id"],
        ),
    )
    connection.commit()
    updated_row = fetch_one(connection, "SELECT * FROM frontend_sessions WHERE id = ?", (session_row["id"],))
    if updated_row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Frontend session disappeared during refresh.")
    return _session_summary_from_row(updated_row), access_token, next_refresh_token


def revoke_frontend_session(connection: Any, *, refresh_token: str) -> FrontendSessionSummary:
    session_row = _load_session_by_refresh_token(connection, refresh_token)
    revoked_at = utc_now_iso()
    metadata = _load_json_object(session_row.get("metadata_json"))
    metadata["session_type"] = metadata.get("session_type") or "hosted-frontend"
    metadata["revoked_at"] = revoked_at
    connection.execute(
        """
        UPDATE frontend_sessions
        SET status = 'revoked',
            revoked_at = ?,
            metadata_json = ?,
            last_used_at = ?
        WHERE id = ?
        """,
        (revoked_at, json.dumps(metadata), revoked_at, session_row["id"]),
    )
    connection.commit()
    updated_row = fetch_one(connection, "SELECT * FROM frontend_sessions WHERE id = ?", (session_row["id"],))
    if updated_row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Frontend session disappeared during revoke.")
    return _session_summary_from_row(updated_row)


def require_platform_session(request: Request) -> FrontendSessionSummary:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token for hosted frontend platform access.")
    access_token = authorization.split(" ", 1)[1].strip()
    session_row = _load_session_by_access_token(request.app.state.connection, access_token)
    _assert_session_accessible(session_row)
    now = utc_now_iso()
    request.app.state.connection.execute(
        "UPDATE frontend_sessions SET last_used_at = ? WHERE id = ?",
        (now, session_row["id"]),
    )
    request.app.state.connection.commit()
    refreshed_row = fetch_one(request.app.state.connection, "SELECT * FROM frontend_sessions WHERE id = ?", (session_row["id"],))
    if refreshed_row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Frontend session disappeared during authentication.")
    return _session_summary_from_row(refreshed_row)


def _load_session_by_access_token(connection: Any, access_token: str) -> dict[str, Any]:
    session_row = fetch_one(
        connection,
        "SELECT * FROM frontend_sessions WHERE access_token_hash = ?",
        (_hash_token(access_token),),
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend access token is invalid.")
    return dict(session_row)


def _load_session_by_refresh_token(connection: Any, refresh_token: str) -> dict[str, Any]:
    session_row = fetch_one(
        connection,
        "SELECT * FROM frontend_sessions WHERE refresh_token_hash = ?",
        (_hash_token(refresh_token),),
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend refresh token is invalid.")
    return dict(session_row)


def _assert_session_accessible(session_row: dict[str, Any]) -> None:
    if session_row.get("status") == "revoked" or session_row.get("revoked_at"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend session has been revoked.")
    if _parse_iso(session_row["access_expires_at"]) <= _utc_now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend access token has expired.")


def _assert_session_refreshable(session_row: dict[str, Any]) -> None:
    if session_row.get("status") == "revoked" or session_row.get("revoked_at"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend session has been revoked.")
    if _parse_iso(session_row["refresh_expires_at"]) <= _utc_now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hosted frontend refresh token has expired.")


def _session_summary_from_row(row: dict[str, Any]) -> FrontendSessionSummary:
    status_value = row.get("status") or "active"
    if row.get("revoked_at"):
        status_value = "revoked"
    elif _parse_iso(row["access_expires_at"]) <= _utc_now():
        status_value = "expired"
    return FrontendSessionSummary(
        id=row["id"],
        operator_name=row["operator_name"],
        client_name=row["client_name"],
        status=status_value,
        session_type=str(_load_json_object(row.get("metadata_json")).get("session_type") or "hosted-frontend"),
        requested_origin=_load_json_object(row.get("metadata_json")).get("requested_origin"),
        requested_scopes=_load_json_list(row.get("scopes_json")),
        scopes=_load_json_list(row.get("scopes_json")),
        issued_at=row["issued_at"],
        access_expires_at=row["access_expires_at"],
        refresh_expires_at=row["refresh_expires_at"],
        last_used_at=row.get("last_used_at"),
        metadata=_load_json_object(row.get("metadata_json")),
    )


def _normalize_scopes(requested_scopes: list[str] | None) -> list[str]:
    normalized = {scope.strip() for scope in (requested_scopes or []) if scope and scope.strip()}
    normalized.update(DEFAULT_PLATFORM_SCOPES)
    return sorted(normalized)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _parse_iso(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _load_json_object(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return value


__all__ = [
    "create_frontend_session",
    "get_frontend_access_ttl_minutes",
    "get_frontend_bootstrap_token",
    "get_frontend_refresh_ttl_days",
    "require_platform_session",
    "refresh_frontend_session",
    "revoke_frontend_session",
]
