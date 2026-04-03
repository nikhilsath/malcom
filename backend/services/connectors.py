"""Connector secret protection, provider catalog, and auth normalization helpers.

Primary identifiers: connector protection constants, ``DEFAULT_CONNECTOR_CATALOG``,
secret masking/protection helpers, and connector storage/response normalization functions.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import urllib.parse
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from backend.database import fetch_all, fetch_one
from backend.schemas import OutgoingAuthConfig
from backend.services.settings import read_stored_settings_section, write_settings_section
from backend.services.utils import utc_now_iso

DatabaseConnection = Any
DatabaseRow = dict[str, Any]

CONNECTOR_PROTECTION_VERSION = "enc_v1"
CONNECTOR_NONCE_BYTES = 16
CONNECTOR_SIGNATURE_BYTES = 32
CONNECTOR_OAUTH_STATE_TTL_SECONDS = 600
LEGACY_GOOGLE_CONNECTOR_PROVIDER_IDS = {
    "google_calendar",
    "google_gmail",
    "google_sheets",
}
CONNECTOR_PROVIDER_CANONICAL_MAP = {
    "google_calendar": "google",
    "google_gmail": "google",
    "google_sheets": "google",
}
SUPPORTED_CONNECTOR_PROVIDERS = {
    "google",
    *LEGACY_GOOGLE_CONNECTOR_PROVIDER_IDS,
    "github",
    "notion",
    "trello",
    "generic_http",
}
SUPPORTED_CONNECTOR_AUTH_TYPES = {"oauth2", "bearer", "api_key", "basic", "header"}
SUPPORTED_CONNECTOR_STATUSES = {"draft", "pending_oauth", "connected", "needs_attention", "expired", "revoked"}
CONNECTOR_AUTH_POLICY_SETTINGS_KEY = "connector_auth_policy"
CONNECTOR_SECRET_FIELD_INPUTS = {
    "client_secret": "client_secret_input",
    "access_token": "access_token_input",
    "refresh_token": "refresh_token_input",
    "api_key": "api_key_input",
    "password": "password_input",
    "header_value": "header_value_input",
}
DEFAULT_CONNECTOR_CATALOG: list[dict[str, Any]] = [
    {
        "id": "google",
        "name": "Google",
        "description": "Use one Google connector and choose the exact OAuth scopes needed for this workflow.",
        "category": "suite",
        "auth_types": ["oauth2"],
        "default_scopes": [],
        "docs_url": "https://developers.google.com/identity/protocols/oauth2/scopes",
        "base_url": "https://www.googleapis.com",
    },
    {
        "id": "github",
        "name": "GitHub",
        "description": "Use repository, issue, and workflow APIs.",
        "category": "developer",
        "auth_types": ["oauth2", "bearer"],
        "default_scopes": ["repo", "read:user"],
        "docs_url": "https://docs.github.com/en/rest/about-the-rest-api/about-the-rest-api",
        "base_url": "https://api.github.com",
    },
    {
        "id": "notion",
        "name": "Notion",
        "description": "Access internal workspace pages and databases.",
        "category": "documents",
        "auth_types": ["oauth2", "bearer"],
        "default_scopes": [],
        "docs_url": "https://developers.notion.com/guides/get-started/authorization",
        "base_url": "https://api.notion.com/v1",
    },
    {
        "id": "trello",
        "name": "Trello",
        "description": "Create and update boards, lists, and cards.",
        "category": "project_management",
        "auth_types": ["api_key", "header"],
        "default_scopes": [],
        "docs_url": "https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/",
        "base_url": "https://api.trello.com/1",
    },
]


def get_connector_protection_secret(*, root_dir: Path | None = None, db_path: str | None = None) -> str:
    configured = os.environ.get("MALCOM_CONNECTOR_SECRET")
    if configured:
        return configured

    seed_parts = [
        str(root_dir or ""),
        str(db_path or ""),
        "malcom-connectors",
    ]
    return "|".join(seed_parts)


def derive_connector_protection_key(protection_secret: str) -> bytes:
    return hashlib.sha256(protection_secret.encode("utf-8")).digest()


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(left_byte ^ right_byte for left_byte, right_byte in zip(left, right))


def build_connector_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0

    while len(output) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        output.extend(block)
        counter += 1

    return bytes(output[:length])


def _encode_protected_connector_value(nonce: bytes, signature: bytes, ciphertext: bytes) -> str:
    token = base64.urlsafe_b64encode(nonce + signature + ciphertext).decode("ascii")
    return f"{CONNECTOR_PROTECTION_VERSION}:{token}"


def _decode_protected_connector_value(value: str | None) -> tuple[bytes, bytes, bytes] | None:
    if not value or not value.startswith(f"{CONNECTOR_PROTECTION_VERSION}:"):
        return None

    encoded = value.split(":", 1)[1]
    try:
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except (ValueError, binascii.Error):
        return None

    minimum_size = CONNECTOR_NONCE_BYTES + CONNECTOR_SIGNATURE_BYTES
    if len(raw) < minimum_size:
        return None

    nonce = raw[:CONNECTOR_NONCE_BYTES]
    signature_end = CONNECTOR_NONCE_BYTES + CONNECTOR_SIGNATURE_BYTES
    signature = raw[CONNECTOR_NONCE_BYTES:signature_end]
    ciphertext = raw[signature_end:]
    return nonce, signature, ciphertext


def protect_connector_secret_value(value: str, protection_secret: str) -> str:
    key = derive_connector_protection_key(protection_secret)
    nonce = secrets.token_bytes(CONNECTOR_NONCE_BYTES)
    payload = value.encode("utf-8")
    keystream = build_connector_keystream(key, nonce, len(payload))
    ciphertext = _xor_bytes(payload, keystream)
    signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return _encode_protected_connector_value(nonce, signature, ciphertext)


def unprotect_connector_secret_value(value: str | None, protection_secret: str) -> str | None:
    decoded = _decode_protected_connector_value(value)
    if decoded is None:
        return None

    nonce, signature, ciphertext = decoded
    key = derive_connector_protection_key(protection_secret)
    expected_signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()

    if not hmac.compare_digest(signature, expected_signature):
        return None

    keystream = build_connector_keystream(key, nonce, len(ciphertext))
    try:
        plaintext = _xor_bytes(ciphertext, keystream)
        return plaintext.decode("utf-8")
    except UnicodeDecodeError:
        return None


def mask_connector_secret(value: str | None) -> str | None:
    if not value:
        return None

    if len(value) <= 8:
        return "••••"

    return f"{value[:4]}••••{value[-4:]}"


def get_default_connector_settings() -> dict[str, Any]:
    return {
        "catalog": json.loads(json.dumps(DEFAULT_CONNECTOR_CATALOG)),
        "records": [],
        "auth_policy": {
            "rotation_interval_days": 90,
            "reconnect_requires_approval": True,
            "credential_visibility": "masked",
        },
    }


def normalize_connector_auth_policy(value: dict[str, Any] | None) -> dict[str, Any]:
    defaults = get_default_connector_settings()["auth_policy"]
    payload = defaults | (value or {})
    if payload.get("rotation_interval_days") not in {30, 60, 90}:
        payload["rotation_interval_days"] = defaults["rotation_interval_days"]
    if payload.get("credential_visibility") not in {"masked", "admin_only"}:
        payload["credential_visibility"] = defaults["credential_visibility"]
    payload["reconnect_requires_approval"] = bool(payload.get("reconnect_requires_approval", defaults["reconnect_requires_approval"]))
    return payload


def _clone_connector_catalog_defaults() -> list[dict[str, Any]]:
    return json.loads(json.dumps(DEFAULT_CONNECTOR_CATALOG))


def canonicalize_connector_provider(provider: str | None) -> str | None:
    if not provider:
        return provider
    return CONNECTOR_PROVIDER_CANONICAL_MAP.get(provider, provider)


def _get_default_connector_preset(provider: str) -> dict[str, Any] | None:
    canonical_provider = canonicalize_connector_provider(provider)
    return next((item for item in DEFAULT_CONNECTOR_CATALOG if item["id"] == canonical_provider), None)


def _row_to_connector_preset(row: DatabaseRow) -> dict[str, Any]:
    canonical_id = canonicalize_connector_provider(row.get("id"))
    if canonical_id == "google":
        google_preset = _get_default_connector_preset("google")
        if google_preset is not None:
            return dict(google_preset)

    try:
        auth_types = json.loads(row.get("auth_types_json") or "[]")
    except json.JSONDecodeError:
        auth_types = []

    try:
        default_scopes = json.loads(row.get("default_scopes_json") or "[]")
    except json.JSONDecodeError:
        default_scopes = []

    return {
        "id": canonical_id or row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "auth_types": [item for item in auth_types if isinstance(item, str)],
        "default_scopes": [item for item in default_scopes if isinstance(item, str)],
        "docs_url": row.get("docs_url") or "",
        "base_url": row.get("base_url") or "",
    }


def build_connector_catalog(connection: DatabaseConnection | None = None) -> list[dict[str, Any]]:
    if connection is None:
        return _clone_connector_catalog_defaults()

    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, category, auth_types_json, default_scopes_json, docs_url, base_url
        FROM integration_presets
        WHERE integration_type = 'connector_provider'
        ORDER BY name ASC
        """,
    )
    if not rows:
        return _clone_connector_catalog_defaults()

    deduped_catalog: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in rows:
        preset = _row_to_connector_preset(row)
        preset_id = preset["id"]
        if preset_id in seen_ids:
            continue
        seen_ids.add(preset_id)
        deduped_catalog.append(preset)
    return deduped_catalog


def get_connector_preset(provider: str, *, connection: DatabaseConnection | None = None) -> dict[str, Any] | None:
    canonical_provider = canonicalize_connector_provider(provider)
    if connection is None:
        return _get_default_connector_preset(canonical_provider or provider)

    row = fetch_one(
        connection,
        """
        SELECT id, name, description, category, auth_types_json, default_scopes_json, docs_url, base_url
        FROM integration_presets
        WHERE integration_type = 'connector_provider' AND id = ?
        """,
        (canonical_provider,),
    )
    if row is None:
        return _get_default_connector_preset(canonical_provider or provider)
    return _row_to_connector_preset(row)


def extract_connector_secret_map(auth_config: dict[str, Any], protection_secret: str) -> dict[str, str]:
    protected_values = auth_config.get("protected_secrets") or {}
    secret_map: dict[str, str] = {}

    for field_name in CONNECTOR_SECRET_FIELD_INPUTS:
        decrypted = unprotect_connector_secret_value(protected_values.get(field_name), protection_secret)
        if decrypted:
            secret_map[field_name] = decrypted

    return secret_map


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
    protected_secrets: dict[str, str] = {}

    clear_credentials = bool(incoming_auth_config.get("clear_credentials"))

    for field_name, input_key in CONNECTOR_SECRET_FIELD_INPUTS.items():
        next_value = None if clear_credentials else incoming_auth_config.get(input_key)
        if next_value:
            protected_secrets[field_name] = protect_connector_secret_value(next_value, protection_secret)
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
    return {
        **record,
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

    scopes = [item for item in (record.get("scopes") or []) if isinstance(item, str)]
    auth_config = record.get("auth_config") if isinstance(record.get("auth_config"), dict) else {}

    return {
        "id": connector_id,
        "provider": provider,
        "name": str(record.get("name") or connector_id),
        "status": status_value,
        "auth_type": auth_type,
        "scopes_json": json.dumps(scopes),
        "base_url": record.get("base_url"),
        "owner": record.get("owner"),
        "docs_url": record.get("docs_url"),
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


def _read_connector_auth_policy_setting(connection: DatabaseConnection) -> dict[str, Any] | None:
    row_value = read_stored_settings_section(connection, CONNECTOR_AUTH_POLICY_SETTINGS_KEY)
    if isinstance(row_value, dict):
        return row_value

    legacy_value = read_stored_settings_section(connection, "connectors")
    if isinstance(legacy_value, dict) and isinstance(legacy_value.get("auth_policy"), dict):
        return {"auth_policy": legacy_value.get("auth_policy")}
    return None


def _migrate_legacy_connectors_from_settings(connection: DatabaseConnection) -> None:
    legacy_value = read_stored_settings_section(connection, "connectors")
    if not isinstance(legacy_value, dict):
        return

    legacy_records = [item for item in legacy_value.get("records", []) if isinstance(item, dict)]
    if legacy_records and not list_stored_connector_records(connection):
        replace_stored_connector_records(connection, legacy_records)

    auth_policy_value = legacy_value.get("auth_policy")
    if isinstance(auth_policy_value, dict):
        write_settings_section(
            connection,
            CONNECTOR_AUTH_POLICY_SETTINGS_KEY,
            {"auth_policy": normalize_connector_auth_policy(auth_policy_value)},
        )

    connection.execute("DELETE FROM settings WHERE key = ?", ("connectors",))
    connection.commit()


def persist_connector_settings(connection: DatabaseConnection, settings_value: dict[str, Any]) -> None:
    records = [item for item in settings_value.get("records", []) if isinstance(item, dict)]
    replace_stored_connector_records(connection, records)

    auth_policy = normalize_connector_auth_policy(settings_value.get("auth_policy"))
    write_settings_section(
        connection,
        CONNECTOR_AUTH_POLICY_SETTINGS_KEY,
        {"auth_policy": auth_policy},
    )

    connection.execute("DELETE FROM settings WHERE key = ?", ("connectors",))
    connection.commit()


def get_stored_connector_settings(connection: DatabaseConnection) -> dict[str, Any]:
    _migrate_legacy_connectors_from_settings(connection)
    policy_payload = _read_connector_auth_policy_setting(connection)
    records = list_stored_connector_records(connection)

    return {
        "catalog": build_connector_catalog(connection),
        "records": records,
        "auth_policy": normalize_connector_auth_policy((policy_payload or {}).get("auth_policy")),
    }


def find_stored_connector_record(connection: DatabaseConnection, connector_id: str) -> dict[str, Any] | None:
    settings = get_stored_connector_settings(connection)
    return next((item for item in settings["records"] if item.get("id") == connector_id), None)


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
    connector_request_auth_type = "bearer" if connector_auth_type == "oauth2" else ("header" if connector_auth_type == "api_key" else connector_auth_type)
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


__all__ = [
    "CONNECTOR_OAUTH_STATE_TTL_SECONDS",
    "CONNECTOR_PROTECTION_VERSION",
    "CONNECTOR_SECRET_FIELD_INPUTS",
    "DEFAULT_CONNECTOR_CATALOG",
    "SUPPORTED_CONNECTOR_AUTH_TYPES",
    "SUPPORTED_CONNECTOR_PROVIDERS",
    "SUPPORTED_CONNECTOR_STATUSES",
    "build_connector_catalog",
    "build_connector_keystream",
    "build_connector_oauth_authorization_url",
    "build_outgoing_auth_config_from_connector",
    "build_pkce_code_challenge",
    "canonicalize_connector_provider",
    "derive_connector_protection_key",
    "extract_connector_secret_map",
    "find_stored_connector_record",
    "get_connector_preset",
    "get_connector_protection_secret",
    "get_default_connector_settings",
    "get_stored_connector_settings",
    "hydrate_outgoing_configuration_from_connector",
    "mask_connector_secret",
    "merge_outgoing_auth_config",
    "normalize_connector_auth_config_for_storage",
    "normalize_connector_auth_policy",
    "normalize_connector_record_for_storage",
    "normalize_connector_settings_for_storage",
    "protect_connector_secret_value",
    "persist_connector_settings",
    "replace_stored_connector_records",
    "list_stored_connector_records",
    "sanitize_connector_auth_config_response",
    "sanitize_connector_record_for_response",
    "sanitize_connector_settings_for_response",
    "unprotect_connector_secret_value",
]
