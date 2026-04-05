"""Connector secret protection, provider catalog, and auth normalization helpers.

Primary identifiers: connector protection constants, ``DEFAULT_CONNECTOR_CATALOG``,
secret masking/protection helpers, and connector storage/response normalization functions.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from backend.database import fetch_all, fetch_one
from backend.schemas import OutgoingAuthConfig
from backend.services.settings import (
    delete_stored_settings_section,
    read_stored_settings_section,
)
from backend.services.utils import utc_now_iso

from backend.services.connector_secrets import (
    CONNECTOR_NONCE_BYTES,
    CONNECTOR_PROTECTION_VERSION,
    CONNECTOR_SECRET_FIELD_INPUTS,
    CONNECTOR_SIGNATURE_BYTES,
    build_connector_keystream,
    derive_connector_protection_key,
    extract_connector_secret_map,
    get_connector_protection_secret,
    mask_connector_secret,
    protect_connector_secret_value,
    unprotect_connector_secret_value,
)
from backend.services.connector_catalog import (
    ACTIVE_STORAGE_CONNECTOR_STATUSES,
    CONNECTOR_AUTH_POLICY_ROW_ID,
    CONNECTOR_AUTH_POLICY_SETTINGS_KEY,
    CONNECTOR_CREDENTIAL_VISIBILITY_OPTIONS,
    CONNECTOR_PROVIDER_CANONICAL_MAP,
    CONNECTOR_REQUEST_AUTH_TYPE_MAP,
    CONNECTOR_ROTATION_INTERVAL_OPTIONS,
    CONNECTOR_STATUS_OPTIONS,
    DEFAULT_CONNECTOR_CATALOG,
    DEFAULT_CONNECTOR_PROVIDER_METADATA,
    GITHUB_AVAILABLE_SCOPES,
    GOOGLE_RECOMMENDED_SCOPES,
    LEGACY_GOOGLE_CONNECTOR_PROVIDER_IDS,
    SUPPORTED_CONNECTOR_AUTH_TYPES,
    SUPPORTED_CONNECTOR_PROVIDERS,
    SUPPORTED_CONNECTOR_STATUSES,
    _clone_connector_catalog_defaults,
    _get_default_connector_preset,
    _provider_display_name,
    _provider_metadata,
    _row_to_connector_preset,
    build_connector_catalog,
    build_connector_response_metadata,
    canonicalize_connector_provider,
    get_connector_preset,
    get_connector_provider_metadata,
    get_default_connector_settings,
    normalize_connector_auth_policy,
    normalize_connector_request_auth_type,
)
from backend.services.connector_migrations import (
    _migrate_legacy_connector_auth_policy_setting,
    _migrate_legacy_connectors_from_settings,
    _read_connector_auth_policy_row,
    _read_connector_auth_policy_setting,
    ensure_legacy_connector_storage_migrated,
)

DatabaseConnection = Any
DatabaseRow = dict[str, Any]


def sanitize_connector_auth_config_response(auth_config: dict[str, Any], protection_secret: str) -> dict[str, Any]:
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    return {
        "client_id": auth_config.get("client_id"),
        "username": auth_config.get("username"),
        "header_name": auth_config.get("header_name"),
        "scope_preset": auth_config.get("scope_preset"),
        "redirect_uri": auth_config.get("redirect_uri"),
        "expires_at": auth_config.get("expires_at"),
        "has_refresh_token": bool(secret_map.get("refresh_token")) or bool(auth_config.get("has_refresh_token")),
        "client_secret_masked": mask_connector_secret(secret_map.get("client_secret")),
        "access_token_masked": mask_connector_secret(secret_map.get("access_token")),
        "refresh_token_masked": mask_connector_secret(secret_map.get("refresh_token")),
        "api_key_masked": mask_connector_secret(secret_map.get("api_key")),
        "password_masked": mask_connector_secret(secret_map.get("password")),
        "header_value_masked": mask_connector_secret(secret_map.get("header_value")),
    }


def normalize_connector_auth_config_for_storage(
    auth_config: dict[str, Any] | None,
    existing_auth_config: dict[str, Any] | None,
    protection_secret: str,
) -> dict[str, Any]:
    next_auth_config = dict(existing_auth_config or {})
    incoming_auth_config = auth_config or {}
    existing_secret_map = extract_connector_secret_map(existing_auth_config or {}, protection_secret)
    incoming_protected_secrets = incoming_auth_config.get("protected_secrets") or {}
    protected_secrets: dict[str, str] = {}

    clear_credentials = bool(incoming_auth_config.get("clear_credentials"))

    if clear_credentials:
        next_auth_config = {}
        next_auth_config["protected_secrets"] = {}
        for field_name in ("client_id", "username", "header_name", "scope_preset", "redirect_uri", "expires_at"):
            if field_name in incoming_auth_config:
                next_auth_config[field_name] = incoming_auth_config.get(field_name)
        next_auth_config["has_refresh_token"] = False
        return next_auth_config

    for field_name, input_key in CONNECTOR_SECRET_FIELD_INPUTS.items():
        next_value = None if clear_credentials else incoming_auth_config.get(input_key)
        if next_value:
            protected_secrets[field_name] = protect_connector_secret_value(next_value, protection_secret)
        elif not clear_credentials and isinstance(incoming_protected_secrets.get(field_name), str) and incoming_protected_secrets.get(field_name):
            protected_secrets[field_name] = incoming_protected_secrets[field_name]
        elif not clear_credentials and field_name in existing_secret_map:
            protected_secrets[field_name] = protect_connector_secret_value(existing_secret_map[field_name], protection_secret)

    next_auth_config["protected_secrets"] = protected_secrets

    for field_name in ("client_id", "username", "header_name", "scope_preset", "redirect_uri", "expires_at"):
        if field_name in incoming_auth_config:
            next_auth_config[field_name] = incoming_auth_config.get(field_name)

    if "has_refresh_token" in incoming_auth_config and incoming_auth_config.get("has_refresh_token") is not None:
        next_auth_config["has_refresh_token"] = bool(incoming_auth_config.get("has_refresh_token"))
    else:
        next_auth_config["has_refresh_token"] = bool(protected_secrets.get("refresh_token")) or bool(next_auth_config.get("has_refresh_token"))

    return next_auth_config


def normalize_connector_record_for_storage(
    record: dict[str, Any],
    *,
    existing_record: dict[str, Any] | None,
    connection: DatabaseConnection | None = None,
    protection_secret: str,
    timestamp: str,
) -> dict[str, Any]:
    provider = canonicalize_connector_provider(record.get("provider") or ((existing_record or {}).get("provider")))
    preset = get_connector_preset(provider, connection=connection) if provider else None
    if provider == "generic_http":
        preset = None
    elif preset is None:
        provider = "generic_http"
    preset = preset or {
        "name": "Generic HTTP",
        "base_url": None,
        "docs_url": None,
        "default_scopes": [],
        "auth_types": ["bearer", "api_key", "basic", "header"],
    }
    auth_type = record.get("auth_type") or (existing_record or {}).get("auth_type") or preset["auth_types"][0]
    if auth_type not in SUPPORTED_CONNECTOR_AUTH_TYPES:
        auth_type = preset["auth_types"][0]
    status_value = record.get("status") or (existing_record or {}).get("status") or "draft"
    if status_value not in SUPPORTED_CONNECTOR_STATUSES:
        status_value = "draft"

    scopes = [
        item.strip()
        for item in record.get("scopes", (existing_record or {}).get("scopes", [])) or []
        if isinstance(item, str) and item.strip()
    ]

    return {
        "id": record.get("id") or (existing_record or {}).get("id") or f"connector_{uuid4().hex[:10]}",
        "provider": provider,
        "name": record.get("name") or (existing_record or {}).get("name") or preset["name"],
        "status": status_value,
        "auth_type": auth_type,
        "scopes": scopes or list(preset.get("default_scopes", [])),
        "base_url": record.get("base_url") or (existing_record or {}).get("base_url") or preset.get("base_url"),
        "owner": record.get("owner") or (existing_record or {}).get("owner") or "Workspace",
        "docs_url": record.get("docs_url") or (existing_record or {}).get("docs_url") or preset.get("docs_url"),
        "credential_ref": record.get("credential_ref") or (existing_record or {}).get("credential_ref") or f"connector/{record.get('id') or (existing_record or {}).get('id') or 'pending'}",
        "created_at": record.get("created_at") or (existing_record or {}).get("created_at") or timestamp,
        "updated_at": timestamp,
        "last_tested_at": record.get("last_tested_at") if "last_tested_at" in record else (existing_record or {}).get("last_tested_at"),
        "auth_config": normalize_connector_auth_config_for_storage(
            record.get("auth_config"),
            (existing_record or {}).get("auth_config"),
            protection_secret,
        ),
    }


def sanitize_connector_record_for_response(record: dict[str, Any], protection_secret: str) -> dict[str, Any]:
    request_auth_type = normalize_connector_request_auth_type(record.get("auth_type"))
    return {
        **record,
        "request_auth_type": request_auth_type,
        "auth_config": sanitize_connector_auth_config_response(record.get("auth_config") or {}, protection_secret),
    }


def normalize_connector_settings_for_storage(
    value: dict[str, Any] | None,
    *,
    existing_settings: dict[str, Any] | None,
    connection: DatabaseConnection | None = None,
    protection_secret: str,
) -> dict[str, Any]:
    defaults = get_default_connector_settings()
    current_settings = existing_settings or defaults
    payload = value or {}
    now = utc_now_iso()
    existing_records = {
        item["id"]: item
        for item in current_settings.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }
    next_records = [
        normalize_connector_record_for_storage(
            item,
            existing_record=existing_records.get(item.get("id")),
            connection=connection,
            protection_secret=protection_secret,
            timestamp=now,
        )
        for item in payload.get("records", current_settings.get("records", [])) or []
        if isinstance(item, dict)
    ]

    return {
        "catalog": build_connector_catalog(connection),
        "records": next_records,
        "auth_policy": normalize_connector_auth_policy(payload.get("auth_policy") or current_settings.get("auth_policy")),
    }


def sanitize_connector_settings_for_response(
    value: dict[str, Any] | None,
    protection_secret: str,
    *,
    connection: DatabaseConnection | None = None,
) -> dict[str, Any]:
    defaults = get_default_connector_settings()
    current = value or defaults
    return {
        "catalog": build_connector_catalog(connection),
        "records": [
            sanitize_connector_record_for_response(item, protection_secret)
            for item in current.get("records", [])
            if isinstance(item, dict)
        ],
        "auth_policy": normalize_connector_auth_policy(current.get("auth_policy")),
        "metadata": build_connector_response_metadata(),
    }


def _decode_json_text(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return fallback


def _serialize_connector_row(row: DatabaseRow) -> dict[str, Any]:
    provider = canonicalize_connector_provider(row.get("provider")) or "generic_http"
    status_value = str(row.get("status") or "draft")
    if status_value not in SUPPORTED_CONNECTOR_STATUSES:
        status_value = "draft"

    auth_type = str(row.get("auth_type") or "bearer")
    if auth_type not in SUPPORTED_CONNECTOR_AUTH_TYPES:
        auth_type = "bearer"

    scopes = _decode_json_text(row.get("scopes_json"), [])
    auth_config = _decode_json_text(row.get("auth_config_json"), {})

    return {
        "id": str(row.get("id") or "").strip(),
        "provider": provider,
        "name": row.get("name") or str(row.get("id") or ""),
        "status": status_value,
        "auth_type": auth_type,
        "scopes": [item for item in scopes if isinstance(item, str)],
        "base_url": row.get("base_url"),
        "owner": row.get("owner"),
        "docs_url": row.get("docs_url"),
        "credential_ref": row.get("credential_ref"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "last_tested_at": row.get("last_tested_at"),
        "auth_config": auth_config if isinstance(auth_config, dict) else {},
    }


def _build_connector_record_for_upsert(record: dict[str, Any]) -> dict[str, Any]:
    connector_id = str(record.get("id") or "").strip()
    if not connector_id:
        raise ValueError("Connector id is required for persistence.")

    provider = canonicalize_connector_provider(record.get("provider")) or "generic_http"
    status_value = str(record.get("status") or "draft")
    if status_value not in SUPPORTED_CONNECTOR_STATUSES:
        status_value = "draft"

    auth_type = str(record.get("auth_type") or "bearer")
    if auth_type not in SUPPORTED_CONNECTOR_AUTH_TYPES:
        auth_type = "bearer"

    preset = get_connector_preset(provider)
    scopes = [item for item in (record.get("scopes") or []) if isinstance(item, str)]
    auth_config = record.get("auth_config") if isinstance(record.get("auth_config"), dict) else {}

    return {
        "id": connector_id,
        "provider": provider,
        "name": str(record.get("name") or connector_id),
        "status": status_value,
        "auth_type": auth_type,
        "scopes_json": json.dumps(scopes),
        "base_url": record.get("base_url") or (preset or {}).get("base_url") or "",
        "owner": record.get("owner") or "Workspace",
        "docs_url": record.get("docs_url") or (preset or {}).get("docs_url") or "",
        "credential_ref": record.get("credential_ref"),
        "created_at": record.get("created_at") or utc_now_iso(),
        "updated_at": record.get("updated_at") or utc_now_iso(),
        "auth_config_json": json.dumps(auth_config),
        "last_tested_at": record.get("last_tested_at"),
    }


def list_stored_connector_records(connection: DatabaseConnection) -> list[dict[str, Any]]:
    rows = fetch_all(
        connection,
        """
        SELECT
            id,
            provider,
            name,
            status,
            auth_type,
            scopes_json,
            base_url,
            owner,
            docs_url,
            credential_ref,
            created_at,
            updated_at,
            auth_config_json,
            last_tested_at
        FROM connectors
        ORDER BY name ASC, id ASC
        """,
    )
    return [item for item in (_serialize_connector_row(row) for row in rows) if item.get("id")]


def _fetch_stored_connector_record_row(connection: DatabaseConnection, connector_id: str) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT
            id,
            provider,
            name,
            status,
            auth_type,
            scopes_json,
            base_url,
            owner,
            docs_url,
            credential_ref,
            created_at,
            updated_at,
            auth_config_json,
            last_tested_at
        FROM connectors
        WHERE id = ?
        """,
        (connector_id,),
    )
    if row is None:
        return None
    return _serialize_connector_row(row)


def replace_stored_connector_records(connection: DatabaseConnection, records: list[dict[str, Any]]) -> None:
    normalized_records = [_build_connector_record_for_upsert(record) for record in records if isinstance(record, dict)]
    record_ids = [record["id"] for record in normalized_records]

    for record in normalized_records:
        connection.execute(
            """
            INSERT INTO connectors (
                id,
                provider,
                name,
                status,
                auth_type,
                scopes_json,
                base_url,
                owner,
                docs_url,
                credential_ref,
                created_at,
                updated_at,
                auth_config_json,
                last_tested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider = excluded.provider,
                name = excluded.name,
                status = excluded.status,
                auth_type = excluded.auth_type,
                scopes_json = excluded.scopes_json,
                base_url = excluded.base_url,
                owner = excluded.owner,
                docs_url = excluded.docs_url,
                credential_ref = excluded.credential_ref,
                updated_at = excluded.updated_at,
                auth_config_json = excluded.auth_config_json,
                last_tested_at = excluded.last_tested_at
            """,
            (
                record["id"],
                record["provider"],
                record["name"],
                record["status"],
                record["auth_type"],
                record["scopes_json"],
                record["base_url"],
                record["owner"],
                record["docs_url"],
                record["credential_ref"],
                record["created_at"],
                record["updated_at"],
                record["auth_config_json"],
                record["last_tested_at"],
            ),
        )

    if record_ids:
        placeholders = ", ".join("?" for _ in record_ids)
        connection.execute(f"DELETE FROM connectors WHERE id NOT IN ({placeholders})", tuple(record_ids))
    else:
        connection.execute("DELETE FROM connectors")

    connection.commit()


def _sort_connector_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [record for record in records if isinstance(record, dict)],
        key=lambda record: (str(record.get("name") or "").lower(), str(record.get("id") or "")),
    )


def create_connector_record(
    connection: DatabaseConnection,
    record: dict[str, Any],
    *,
    protection_secret: str,
) -> dict[str, Any]:
    requested_id = str(record.get("id") or "").strip()
    if requested_id and find_stored_connector_record(connection, requested_id) is not None:
        raise ValueError("Connector already exists.")

    timestamp = str(record.get("updated_at") or utc_now_iso())
    next_record = normalize_connector_record_for_storage(
        record,
        existing_record=None,
        connection=connection,
        protection_secret=protection_secret,
        timestamp=timestamp,
    )
    if find_stored_connector_record(connection, next_record["id"]) is not None:
        raise ValueError("Connector already exists.")

    current_records = list_stored_connector_records(connection)
    replace_stored_connector_records(connection, _sort_connector_records([*current_records, next_record]))
    return next_record


def save_connector_record(
    connection: DatabaseConnection,
    record: dict[str, Any],
    *,
    protection_secret: str,
) -> dict[str, Any]:
    connector_id = str(record.get("id") or "").strip()
    if not connector_id:
        raise ValueError("Connector id is required.")

    existing_record = find_stored_connector_record(connection, connector_id)
    if existing_record is None:
        raise FileNotFoundError(connector_id)

    timestamp = str(record.get("updated_at") or utc_now_iso())
    next_record = normalize_connector_record_for_storage(
        record,
        existing_record=existing_record,
        connection=connection,
        protection_secret=protection_secret,
        timestamp=timestamp,
    )
    remaining_records = [item for item in list_stored_connector_records(connection) if item.get("id") != connector_id]
    replace_stored_connector_records(connection, _sort_connector_records([*remaining_records, next_record]))
    return next_record


def update_connector_record(
    connection: DatabaseConnection,
    connector_id: str,
    updates: dict[str, Any],
    *,
    protection_secret: str,
) -> dict[str, Any]:
    existing_record = find_stored_connector_record(connection, connector_id)
    if existing_record is None:
        raise FileNotFoundError(connector_id)

    next_record = dict(existing_record)
    for field_name in (
        "provider",
        "name",
        "status",
        "auth_type",
        "scopes",
        "base_url",
        "owner",
        "docs_url",
        "credential_ref",
        "last_tested_at",
        "created_at",
        "updated_at",
    ):
        if field_name in updates:
            next_record[field_name] = updates.get(field_name)

    if "auth_config" in updates:
        next_record["auth_config"] = updates.get("auth_config") or {}

    return save_connector_record(connection, next_record, protection_secret=protection_secret)


def delete_connector_record(connection: DatabaseConnection, connector_id: str) -> dict[str, Any]:
    existing_record = find_stored_connector_record(connection, connector_id)
    if existing_record is None:
        raise FileNotFoundError(connector_id)

    remaining_records = [item for item in list_stored_connector_records(connection) if item.get("id") != connector_id]
    replace_stored_connector_records(connection, _sort_connector_records(remaining_records))
    return existing_record


def write_connector_auth_policy(connection: DatabaseConnection, auth_policy: dict[str, Any]) -> dict[str, Any]:
    normalized_policy = normalize_connector_auth_policy(auth_policy)
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO connector_auth_policies (policy_id, auth_policy_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(policy_id) DO UPDATE SET
            auth_policy_json = excluded.auth_policy_json,
            updated_at = excluded.updated_at
        """,
        (CONNECTOR_AUTH_POLICY_ROW_ID, json.dumps(normalized_policy), now, now),
    )
    connection.execute("DELETE FROM settings WHERE key = ?", (CONNECTOR_AUTH_POLICY_SETTINGS_KEY,))
    connection.commit()
    return normalized_policy


def persist_connector_settings(connection: DatabaseConnection, settings_value: dict[str, Any]) -> None:
    records = [item for item in settings_value.get("records", []) if isinstance(item, dict)]
    replace_stored_connector_records(connection, records)

    auth_policy = normalize_connector_auth_policy(settings_value.get("auth_policy"))
    write_connector_auth_policy(connection, auth_policy)


def get_stored_connector_settings(connection: DatabaseConnection) -> dict[str, Any]:
    policy_payload = _read_connector_auth_policy_setting(connection)
    records = list_stored_connector_records(connection)

    return {
        "catalog": build_connector_catalog(connection),
        "records": records,
        "auth_policy": normalize_connector_auth_policy((policy_payload or {}).get("auth_policy")),
    }


def find_stored_connector_record(connection: DatabaseConnection, connector_id: str) -> dict[str, Any] | None:
    return _fetch_stored_connector_record_row(connection, connector_id)


def build_outgoing_auth_config_from_connector(record: dict[str, Any], protection_secret: str) -> OutgoingAuthConfig:
    auth_config = record.get("auth_config") or {}
    secrets_map = extract_connector_secret_map(auth_config, protection_secret)
    connector_auth_type = record.get("auth_type") or "none"

    if connector_auth_type in {"oauth2", "bearer"}:
        return OutgoingAuthConfig(token=secrets_map.get("access_token") or secrets_map.get("api_key"))
    if connector_auth_type == "api_key":
        return OutgoingAuthConfig(
            header_name=auth_config.get("header_name") or "X-API-Key",
            header_value=secrets_map.get("api_key"),
        )
    if connector_auth_type == "basic":
        return OutgoingAuthConfig(
            username=auth_config.get("username"),
            password=secrets_map.get("password"),
        )
    if connector_auth_type == "header":
        return OutgoingAuthConfig(
            header_name=auth_config.get("header_name"),
            header_value=secrets_map.get("header_value"),
        )

    return OutgoingAuthConfig()


def merge_outgoing_auth_config(
    base_config: OutgoingAuthConfig,
    override_config: OutgoingAuthConfig | None,
) -> OutgoingAuthConfig:
    return OutgoingAuthConfig(
        token=override_config.token if override_config and override_config.token else base_config.token,
        username=override_config.username if override_config and override_config.username else base_config.username,
        password=override_config.password if override_config and override_config.password else base_config.password,
        header_name=override_config.header_name if override_config and override_config.header_name else base_config.header_name,
        header_value=override_config.header_value if override_config and override_config.header_value else base_config.header_value,
    )


def hydrate_outgoing_configuration_from_connector(
    connection: DatabaseConnection,
    *,
    connector_id: str | None,
    destination_url: str,
    auth_type: str,
    auth_config: OutgoingAuthConfig | None,
    protection_secret: str,
) -> tuple[str, str, OutgoingAuthConfig | None]:
    if not connector_id:
        return destination_url, auth_type, auth_config

    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")
    if record.get("status") == "revoked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is revoked.")

    connector_auth_type = record.get("auth_type") or "none"
    connector_request_auth_type = normalize_connector_request_auth_type(connector_auth_type)
    base_config = build_outgoing_auth_config_from_connector(record, protection_secret)
    next_auth_type = auth_type if auth_type != "none" else connector_request_auth_type
    next_auth_config = merge_outgoing_auth_config(base_config, auth_config)
    next_destination = destination_url or record.get("base_url") or ""
    return next_destination, next_auth_type, next_auth_config


def build_pkce_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_connector_oauth_authorization_url(
    provider: str,
    *,
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: str,
    code_challenge: str,
) -> str:
    if provider == "google" or provider.startswith("google_"):
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    elif provider == "github":
        base_url = "https://github.com/login/oauth/authorize"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    elif provider == "notion":
        base_url = "https://api.notion.com/v1/oauth/authorize"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    elif provider == "trello":
        parsed_redirect = urllib.parse.urlparse(redirect_uri)
        redirect_query = dict(urllib.parse.parse_qsl(parsed_redirect.query, keep_blank_values=True))
        redirect_query["state"] = state
        base_url = "https://trello.com/1/authorize"
        query = {
            "key": client_id,
            "name": "Malcom",
            "scope": ",".join(scopes or ["read", "write"]),
            "expiration": "never",
            "response_type": "token",
            "return_url": urllib.parse.urlunparse(
                parsed_redirect._replace(query=urllib.parse.urlencode(redirect_query))
            ),
        }
    else:
        base_url = "https://example.invalid/oauth/authorize"
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

    return f"{base_url}?{urllib.parse.urlencode(query)}"


def _resolve_token_expiry(token_payload: dict[str, Any], *, default_seconds: int | None = None) -> str | None:
    expires_in = token_payload.get("expires_in")
    if isinstance(expires_in, int):
        return (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()
    if default_seconds is not None:
        return (datetime.now(UTC) + timedelta(seconds=default_seconds)).isoformat()
    return None


__all__ = [
    "CONNECTOR_PROTECTION_VERSION",
    "CONNECTOR_SECRET_FIELD_INPUTS",
    "DEFAULT_CONNECTOR_CATALOG",
    "DEFAULT_CONNECTOR_PROVIDER_METADATA",
    "SUPPORTED_CONNECTOR_AUTH_TYPES",
    "SUPPORTED_CONNECTOR_PROVIDERS",
    "SUPPORTED_CONNECTOR_STATUSES",
    "build_connector_catalog",
    "build_connector_response_metadata",
    "build_connector_keystream",
    "build_connector_oauth_authorization_url",
    "build_outgoing_auth_config_from_connector",
    "build_pkce_code_challenge",
    "canonicalize_connector_provider",
    "create_connector_record",
    "delete_connector_record",
    "derive_connector_protection_key",
    "ensure_legacy_connector_storage_migrated",
    "extract_connector_secret_map",
    "find_stored_connector_record",
    "get_connector_preset",
    "get_connector_provider_metadata",
    "get_connector_protection_secret",
    "get_default_connector_settings",
    "get_stored_connector_settings",
    "hydrate_outgoing_configuration_from_connector",
    "mask_connector_secret",
    "merge_outgoing_auth_config",
    "normalize_connector_auth_config_for_storage",
    "normalize_connector_auth_policy",
    "normalize_connector_record_for_storage",
    "normalize_connector_request_auth_type",
    "normalize_connector_settings_for_storage",
    "protect_connector_secret_value",
    "persist_connector_settings",
    "replace_stored_connector_records",
    "list_stored_connector_records",
    "save_connector_record",
    "sanitize_connector_auth_config_response",
    "sanitize_connector_record_for_response",
    "sanitize_connector_settings_for_response",
    "_provider_display_name",
    "_provider_metadata",
    "_resolve_token_expiry",
    "unprotect_connector_secret_value",
    "update_connector_record",
    "write_connector_auth_policy",
]
