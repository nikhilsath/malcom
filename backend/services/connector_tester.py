from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Tuple

from backend.services.support import canonicalize_connector_provider, extract_connector_secret_map, utc_now_iso
from backend.services.connector_health import (
    _probe_google_access_token,
    _probe_github_access_token,
    _probe_notion_access_token,
    _probe_trello_credentials,
    _inspect_github_scopes_from_payload,
)
from backend.services.connector_postgres import probe_postgres_connection


def test_connector_record(record: dict[str, Any], protection_secret: str | None = None) -> Tuple[bool, str, dict[str, Any]]:
    """Perform provider-specific connector testing logic.

    Returns (ok, message, updated_record).
    """
    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = provider or "connector"

    if record.get("status") == "revoked":
        record["status"] = "revoked"
        message = f"{provider_name} connector is revoked."
        ok = False
    elif record.get("auth_config", {}).get("expires_at") and record.get("auth_config", {}).get("expires_at") and parse_expiry(record["auth_config"]["expires_at"]):
        record["status"] = "expired"
        message = f"{provider_name} token has expired."
        ok = False
    else:
        if provider == "google":
            access_token = secret_map.get("access_token")
            if not access_token:
                record["status"] = "needs_attention"
                message = "Google connector is missing an access token. Reconnect Google to continue."
                ok = False
            else:
                ok, message = _probe_google_access_token(access_token=access_token)
                record["status"] = "connected" if ok else "needs_attention"
        elif provider == "github":
            access_token = secret_map.get("access_token")
            if not access_token:
                record["status"] = "needs_attention"
                message = "GitHub connector is missing an access token. Reconnect GitHub to continue."
                ok = False
            else:
                ok, message, detected_scopes = _probe_github_access_token(access_token=access_token)
                if detected_scopes:
                    record["scopes"] = detected_scopes
                record["status"] = "connected" if ok else "needs_attention"
        elif provider == "notion":
            access_token = secret_map.get("access_token")
            if not access_token:
                record["status"] = "needs_attention"
                message = "Notion connector is missing an access token. Reconnect Notion to continue."
                ok = False
            else:
                ok, message = _probe_notion_access_token(access_token=access_token)
                record["status"] = "connected" if ok else "needs_attention"
        elif provider == "trello":
            api_key = secret_map.get("api_key") or auth_config.get("client_id")
            access_token = secret_map.get("access_token")
            if not api_key or not access_token:
                record["status"] = "needs_attention"
                message = "Trello connector is missing its client ID or access token. Reconnect Trello and try again."
                ok = False
            else:
                ok, message = _probe_trello_credentials(api_key=api_key, token=access_token)
                record["status"] = "connected" if ok else "needs_attention"
        elif provider == "cpanel_postgres" or str(record.get("provider") or "") in ("cpanel_postgres", "cpanel-postgres"):
            # Extract host/port/database/username and protected password
            host = secret_map.get("host") or auth_config.get("host")
            port = secret_map.get("port") or auth_config.get("port")
            database = secret_map.get("database") or auth_config.get("database")
            username = secret_map.get("username") or auth_config.get("username")
            password = secret_map.get("password") or auth_config.get("password_input") or auth_config.get("password")

            if not host or not database or not username or not password:
                record["status"] = "needs_attention"
                message = "cPanel PostgreSQL connector is missing required connection details."
                ok = False
            else:
                try:
                    ok, message = probe_postgres_connection(
                        {
                            "host": host,
                            "port": port,
                            "database": database,
                            "username": username,
                            "password": password,
                        }
                    )
                except Exception:
                    # Let probe raise HTTPException for network errors; surface as needs_attention here
                    raise
                record["status"] = "connected" if ok else "needs_attention"
        elif any(secret_map.values()) or record.get("auth_type") == "oauth2":
            record["status"] = "connected"
            message = "Connector credentials look complete."
            ok = True
        else:
            record["status"] = "needs_attention"
            message = "Connector is missing credential material."
            ok = False

    record["last_tested_at"] = utc_now_iso()
    record["updated_at"] = record["last_tested_at"]
    return ok, message, record


def parse_expiry(value: str) -> bool:
    try:
        # returns True if expired
        from datetime import datetime, timezone

        dt = datetime.fromisoformat(value)
        return dt <= datetime.now(timezone.utc)
    except Exception:
        return False
