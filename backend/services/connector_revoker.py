"""Provider-specific connector revoke lifecycle service.

Owns the full revoke-connector workflow: record lookup, credential extraction,
provider-specific upstream token revocation, credential clearing, persistence,
and sanitized result.  Routes should call `revoke_connector` and return the
result directly.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from starlette import status

from backend.services.connector_catalog import (
    _provider_display_name,
    canonicalize_connector_provider,
)
from backend.services.connector_google_oauth_client import revoke_google_token
from backend.services.connector_oauth_provider_clients import (
    revoke_notion_token,
    revoke_trello_token,
)
from backend.services.connector_secrets import extract_connector_secret_map
from backend.services.connectors import (
    find_stored_connector_record,
    sanitize_connector_record_for_response,
    save_connector_record,
)
from backend.services.utils import utc_now_iso

DatabaseConnection = Any

# Fields to clear when revoking any connector.
_CLEARED_CREDENTIAL_FIELDS: dict[str, Any] = {
    "access_token_input": None,
    "refresh_token_input": None,
    "client_secret_input": None,
    "api_key_input": None,
    "password_input": None,
    "header_value_input": None,
    "has_refresh_token": False,
    "clear_credentials": True,
}


def revoke_connector(
    *,
    connection: DatabaseConnection,
    connector_id: str,
    protection_secret: str,
) -> tuple[str, dict[str, Any]]:
    """Revoke a connector's upstream token and clear local credentials.

    Looks up the connector record, attempts to revoke the upstream token via the
    provider's API, clears all credential fields, marks the record as ``revoked``,
    persists the changes, and returns ``(message, sanitized_record_dict)``.

    Raises:
        HTTPException 404: Connector not found.
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

    message = f"{provider_name} connector revoked and credentials cleared."

    if provider == "google":
        token = secret_map.get("access_token") or secret_map.get("refresh_token") or ""
        if token:
            revoke_google_token(token=token)
    elif provider == "github":
        message = "GitHub credentials cleared locally. Save a new personal access token to reconnect."
    elif provider == "notion":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if token and client_id and client_secret:
            revoke_notion_token(token=token, client_id=client_id, client_secret=client_secret)
        else:
            message = (
                "Notion credentials cleared locally. "
                "Configure a client secret to revoke the upstream token as well."
            )
    elif provider == "trello":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        if token and client_id:
            revoke_trello_token(token=token, client_id=client_id)
            message = "Trello connector revoked and credentials cleared."
        else:
            message = (
                "Trello credentials cleared locally. "
                "Configure a client ID to revoke the upstream token as well."
            )

    now = utc_now_iso()
    record["status"] = "revoked"
    record["updated_at"] = now
    record["auth_config"] = {
        **record.get("auth_config", {}),
        **_CLEARED_CREDENTIAL_FIELDS,
    }
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    if isinstance(record.get("auth_config"), dict):
        record["auth_config"]["has_refresh_token"] = False
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return message, sanitized


__all__ = ["revoke_connector"]
