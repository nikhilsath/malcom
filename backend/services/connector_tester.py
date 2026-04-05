"""Provider-specific connector health-test lifecycle service.

Owns the full test-connector workflow: record lookup, credential extraction,
provider-specific probing, status update, persistence, and sanitized result.
Routes should call `test_connector` and return the result directly.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from starlette import status

from backend.runtime import parse_iso_datetime
from backend.services.connector_catalog import (
    _provider_display_name,
    canonicalize_connector_provider,
)
from backend.services.connector_health import (
    _probe_github_access_token,
    _probe_google_access_token,
    _probe_notion_access_token,
    _probe_trello_credentials,
)
from backend.services.connector_secrets import extract_connector_secret_map
from backend.services.connectors import (
    find_stored_connector_record,
    sanitize_connector_record_for_response,
    save_connector_record,
)
from backend.services.utils import utc_now_iso

DatabaseConnection = Any


def test_connector(
    *,
    connection: DatabaseConnection,
    connector_id: str,
    protection_secret: str,
) -> tuple[bool, str, dict[str, Any]]:
    """Test a connector by probing its upstream service.

    Looks up the connector record, extracts credentials, runs the appropriate
    provider probe, updates the record status/timestamps, persists the result,
    and returns ``(ok, message, sanitized_record_dict)``.

    Raises:
        HTTPException 404: Connector not found.
        HTTPException 502: Upstream provider unreachable (propagated from probe).
    """
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found.",
        )

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = _provider_display_name(provider)

    if record.get("status") == "revoked":
        record["status"] = "revoked"
        message = f"{provider_name} connector is revoked."
        ok = False
    elif (
        record.get("auth_config", {}).get("expires_at")
        and parse_iso_datetime(record["auth_config"]["expires_at"])
        and parse_iso_datetime(record["auth_config"]["expires_at"]) <= datetime.now(UTC)
    ):
        record["status"] = "expired"
        message = f"{provider_name} token has expired."
        ok = False
    elif provider == "google":
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
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ok, message, sanitized


__all__ = ["test_connector"]

# Prevent pytest from collecting this function as a test case.
test_connector.__test__ = False  # type: ignore[attr-defined]
