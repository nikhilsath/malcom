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
from datetime import UTC, datetime, timedelta
from pathlib import Path
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

DatabaseConnection = Any
DatabaseRow = dict[str, Any]

CONNECTOR_PROTECTION_VERSION = "enc_v1"
CONNECTOR_NONCE_BYTES = 16
CONNECTOR_SIGNATURE_BYTES = 32
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
GOOGLE_RECOMMENDED_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
GITHUB_AVAILABLE_SCOPES = [
    "repo",
    "repo:status",
    "repo_deployment",
    "public_repo",
    "repo:invite",
    "security_events",
    "admin:repo_hook",
    "write:repo_hook",
    "read:repo_hook",
    "admin:org",
    "write:org",
    "read:org",
    "admin:public_key",
    "write:public_key",
    "read:public_key",
    "admin:org_hook",
    "gist",
    "notifications",
    "user",
    "read:user",
    "user:email",
    "user:follow",
    "delete_repo",
    "write:discussion",
    "read:discussion",
    "write:packages",
    "read:packages",
    "delete:packages",
    "workflow",
    "admin:gpg_key",
    "write:gpg_key",
    "read:gpg_key",
    "admin:ssh_signing_key",
    "write:ssh_signing_key",
    "read:ssh_signing_key",
]
CONNECTOR_REQUEST_AUTH_TYPE_MAP = {
    "oauth2": "bearer",
    "bearer": "bearer",
    "api_key": "header",
    "basic": "basic",
    "header": "header",
}
CONNECTOR_AUTH_POLICY_ROW_ID = "workspace"
CONNECTOR_STATUS_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "draft", "label": "Draft", "description": "Saved locally but not ready for runtime use."},
    {"value": "pending_oauth", "label": "Pending OAuth", "description": "Waiting for OAuth authorization to complete."},
    {"value": "connected", "label": "Connected", "description": "Ready for runtime requests and workflow actions."},
    {"value": "needs_attention", "label": "Needs attention", "description": "Saved, but missing or failing credential material."},
    {"value": "expired", "label": "Expired", "description": "Stored credential material is no longer valid."},
    {"value": "revoked", "label": "Revoked", "description": "Access has been explicitly revoked and must be reconnected."},
)
CONNECTOR_ROTATION_INTERVAL_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "30", "label": "30 days"},
    {"value": "60", "label": "60 days"},
    {"value": "90", "label": "90 days"},
)
CONNECTOR_CREDENTIAL_VISIBILITY_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "masked", "label": "Masked"},
    {"value": "admin_only", "label": "Admin only"},
)
ACTIVE_STORAGE_CONNECTOR_STATUSES = {"connected", "pending_oauth", "needs_attention"}
DEFAULT_CONNECTOR_CATALOG: list[dict[str, Any]] = [
    {
        "id": "google",
        "name": "Google",
        "description": "Use one Google connector and choose the exact OAuth scopes needed for this workflow.",
        "category": "suite",
        "auth_types": ["oauth2"],
        "default_scopes": list(GOOGLE_RECOMMENDED_SCOPES),
        "recommended_scopes": list(GOOGLE_RECOMMENDED_SCOPES),
        "docs_url": "https://developers.google.com/identity/protocols/oauth2/scopes",
        "base_url": "https://www.googleapis.com",
    },
    {
        "id": "github",
        "name": "GitHub",
        "description": "Use repository, issue, and workflow APIs with a GitHub personal access token.",
        "category": "developer",
        "auth_types": ["bearer"],
        "default_scopes": [],
        "recommended_scopes": list(GITHUB_AVAILABLE_SCOPES),
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
        "recommended_scopes": [],
        "docs_url": "https://developers.notion.com/guides/get-started/authorization",
        "base_url": "https://api.notion.com/v1",
    },
    {
        "id": "trello",
        "name": "Trello",
        "description": "Create and update boards, lists, and cards.",
        "category": "project_management",
        "auth_types": ["oauth2", "header"],
        "default_scopes": ["read", "write"],
        "recommended_scopes": ["read", "write"],
        "docs_url": "https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/",
        "base_url": "https://api.trello.com/1",
    },
]
DEFAULT_CONNECTOR_PROVIDER_METADATA: tuple[dict[str, Any], ...] = (
    {
        "id": "google",
        "name": "Google",
        "onboarding_mode": "oauth",
        "oauth_supported": True,
        "callback_supported": True,
        "refresh_supported": True,
        "revoke_supported": True,
        "redirect_uri_required": True,
        "redirect_uri_readonly": True,
        "scopes_locked": True,
        "default_redirect_path": "/api/v1/connectors/google/oauth/callback",
        "required_fields": ["name", "client_id", "client_secret", "redirect_uri"],
        "setup_fields": [
            {"key": "name", "label": "Integration name", "input_type": "text", "required": True},
            {"key": "client_id", "label": "Client ID", "input_type": "text", "required": True},
            {"key": "client_secret", "label": "Client secret", "input_type": "password", "required": True, "secret": True},
            {"key": "scopes", "label": "Scopes", "input_type": "text", "readonly": True},
            {"key": "redirect_uri", "label": "Redirect URI", "input_type": "url", "required": True, "readonly": True},
        ],
        "ui_copy": {
            "eyebrow": "Google",
            "title": "Google OAuth setup",
            "description": "Add your Google OAuth client details, then continue with Google to authorize this workspace.",
            "last_checked_empty": "Google connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Check connection",
            "connect": "Continue with Google",
            "reconnect": "Reconnect Google",
            "refresh": "Refresh Google token",
            "revoke": "Revoke Google connector",
        },
        "status_messages": {
            "draft": "Add your Google OAuth client details to begin, then continue with Google.",
            "pending_oauth": "Complete the Google sign-in flow in the browser to finish setup.",
            "connected": "Google OAuth is complete. Use Check connection to verify the saved token before using this integration in workflows or API resources.",
            "needs_attention": "Google needs attention. Check the connection or reconnect to repair the saved credentials.",
            "expired": "The saved Google token has expired. Refresh it or reconnect Google to continue.",
            "revoked": "Google access has been revoked. Reconnect Google to restore this integration.",
        },
    },
    {
        "id": "github",
        "name": "GitHub",
        "onboarding_mode": "credentials",
        "oauth_supported": False,
        "callback_supported": False,
        "refresh_supported": False,
        "revoke_supported": True,
        "redirect_uri_required": False,
        "redirect_uri_readonly": False,
        "scopes_locked": True,
        "default_redirect_path": None,
        "required_fields": ["name", "access_token_input"],
        "setup_fields": [
            {"key": "name", "label": "Integration name", "input_type": "text", "required": True},
            {
                "key": "access_token_input",
                "label": "Personal access token",
                "input_type": "password",
                "required": True,
                "secret": True,
            },
            {"key": "scopes", "label": "Detected scopes", "input_type": "multiselect", "readonly": True},
        ],
        "ui_copy": {
            "eyebrow": "GitHub",
            "title": "GitHub PAT setup",
            "description": "Add a GitHub personal access token to authorize this workspace.",
            "last_checked_empty": "GitHub connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Check connection",
            "connect": "Save token",
            "reconnect": "Replace token",
            "refresh": "Rotate token",
            "revoke": "Revoke GitHub connector",
        },
        "status_messages": {
            "draft": "Add a GitHub personal access token to begin.",
            "pending_oauth": "GitHub does not use browser OAuth setup in this workspace.",
            "connected": "GitHub token is saved. Use Check connection to verify access before using this connector in workflow actions or API resources.",
            "needs_attention": "GitHub needs attention. Check the connection or replace the saved token.",
            "expired": "The saved GitHub token has expired. Replace it to continue.",
            "revoked": "GitHub credentials were cleared. Save a new token to restore this integration.",
        },
    },
    {
        "id": "notion",
        "name": "Notion",
        "onboarding_mode": "oauth",
        "oauth_supported": True,
        "callback_supported": True,
        "refresh_supported": True,
        "revoke_supported": True,
        "redirect_uri_required": True,
        "redirect_uri_readonly": True,
        "scopes_locked": False,
        "default_redirect_path": "/api/v1/connectors/notion/oauth/callback",
        "required_fields": ["name", "client_id", "client_secret", "redirect_uri"],
        "setup_fields": [
            {"key": "name", "label": "Integration name", "input_type": "text", "required": True},
            {"key": "client_id", "label": "Client ID", "input_type": "text", "required": True},
            {"key": "client_secret", "label": "Client secret", "input_type": "password", "required": True, "secret": True},
            {"key": "redirect_uri", "label": "Redirect URI", "input_type": "url", "required": True, "readonly": True},
        ],
        "ui_copy": {
            "eyebrow": "Notion",
            "title": "Notion OAuth setup",
            "description": "Add your Notion public integration details, then continue with Notion to authorize this workspace.",
            "last_checked_empty": "Notion connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Check connection",
            "connect": "Continue with Notion",
            "reconnect": "Reconnect Notion",
            "refresh": "Refresh Notion token",
            "revoke": "Revoke Notion connector",
        },
        "status_messages": {
            "draft": "Add your Notion integration details to begin, then continue with Notion.",
            "pending_oauth": "Complete the Notion authorization flow in the browser to finish setup.",
            "connected": "Notion OAuth is complete. Use Check connection to verify the saved token before using this integration in workflows or API resources.",
            "needs_attention": "Notion needs attention. Check the connection or reconnect to repair the saved credentials.",
            "expired": "The saved Notion token has expired. Refresh it or reconnect Notion to continue.",
            "revoked": "Notion access has been revoked. Reconnect Notion to restore this integration.",
        },
    },
    {
        "id": "trello",
        "name": "Trello",
        "onboarding_mode": "oauth",
        "oauth_supported": True,
        "callback_supported": True,
        "refresh_supported": False,
        "revoke_supported": True,
        "redirect_uri_required": True,
        "redirect_uri_readonly": True,
        "scopes_locked": True,
        "default_redirect_path": "/api/v1/connectors/trello/oauth/callback",
        "required_fields": ["name", "client_id", "redirect_uri"],
        "setup_fields": [
            {"key": "name", "label": "Integration name", "input_type": "text", "required": True},
            {"key": "client_id", "label": "Client ID", "input_type": "text", "required": True},
            {"key": "client_secret", "label": "Client secret", "input_type": "password", "secret": True},
            {"key": "redirect_uri", "label": "Redirect URI", "input_type": "url", "required": True, "readonly": True},
        ],
        "ui_copy": {
            "eyebrow": "Trello",
            "title": "Trello OAuth setup",
            "description": "Add your Trello app client details, then continue with Trello to authorize this workspace.",
            "last_checked_empty": "Trello connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Check connection",
            "connect": "Continue with Trello",
            "reconnect": "Reconnect Trello",
            "refresh": "Refresh Trello token",
            "revoke": "Revoke Trello connector",
        },
        "status_messages": {
            "draft": "Add your Trello app details to begin, then continue with Trello.",
            "pending_oauth": "Complete the Trello authorization flow in the browser to finish setup.",
            "connected": "Trello OAuth is complete. Use Check connection to verify the saved token before using this integration.",
            "needs_attention": "Trello needs attention. Check the connection or reconnect to repair the saved credentials.",
            "expired": "The saved Trello token is no longer valid. Reconnect Trello and try again.",
            "revoked": "Trello access has been revoked. Reconnect Trello to restore this integration.",
        },
    },
)


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


def get_default_connector_settings(connection: DatabaseConnection | None = None) -> dict[str, Any]:
    return {
        "catalog": build_connector_catalog(connection),
        "records": [],
        "auth_policy": {
            "rotation_interval_days": 90,
            "reconnect_requires_approval": True,
            "credential_visibility": "masked",
        },
        "metadata": build_connector_response_metadata(),
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
        "recommended_scopes": [item for item in default_scopes if isinstance(item, str)],
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


def get_connector_provider_metadata(provider: str | None) -> dict[str, Any] | None:
    canonical_provider = canonicalize_connector_provider(provider)
    if not canonical_provider:
        return None
    return next((json.loads(json.dumps(item)) for item in DEFAULT_CONNECTOR_PROVIDER_METADATA if item["id"] == canonical_provider), None)


def _provider_display_name(provider: str | None) -> str:
    metadata = get_connector_provider_metadata(provider)
    if metadata:
        return str(metadata.get("name") or provider or "Connector")
    return str(provider or "Connector").replace("_", " ").title()


def _provider_metadata(provider: str | None) -> dict[str, Any]:
    metadata = get_connector_provider_metadata(provider)
    if metadata is not None:
        return metadata
    display_name = _provider_display_name(provider)
    return {
        "id": canonicalize_connector_provider(provider) or "generic_http",
        "name": display_name,
        "onboarding_mode": "credentials",
        "oauth_supported": False,
        "callback_supported": False,
        "refresh_supported": False,
        "revoke_supported": True,
        "redirect_uri_required": False,
        "redirect_uri_readonly": False,
        "scopes_locked": False,
        "default_redirect_path": None,
        "required_fields": [],
        "setup_fields": [],
        "ui_copy": {
            "eyebrow": display_name,
            "title": f"{display_name} setup",
            "description": f"Enter the saved credentials needed for {display_name}.",
            "last_checked_empty": f"{display_name} connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Test connector",
            "connect": f"Save {display_name} credentials",
            "reconnect": f"Reconnect {display_name}",
            "refresh": "Refresh token",
            "revoke": "Revoke connector",
        },
        "status_messages": {},
    }


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


def normalize_connector_request_auth_type(auth_type: str | None) -> str:
    normalized_auth_type = str(auth_type or "none").strip().lower()
    return CONNECTOR_REQUEST_AUTH_TYPE_MAP.get(normalized_auth_type, "none")


def build_connector_response_metadata() -> dict[str, Any]:
    return {
        "statuses": [dict(item) for item in CONNECTOR_STATUS_OPTIONS],
        "active_storage_statuses": sorted(ACTIVE_STORAGE_CONNECTOR_STATUSES),
        "auth_policy": {
            "rotation_intervals": [dict(item) for item in CONNECTOR_ROTATION_INTERVAL_OPTIONS],
            "credential_visibility_options": [dict(item) for item in CONNECTOR_CREDENTIAL_VISIBILITY_OPTIONS],
        },
        "providers": [json.loads(json.dumps(item)) for item in DEFAULT_CONNECTOR_PROVIDER_METADATA],
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


def _read_connector_auth_policy_row(connection: DatabaseConnection) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT auth_policy_json
        FROM connector_auth_policies
        WHERE policy_id = ?
        """,
        (CONNECTOR_AUTH_POLICY_ROW_ID,),
    )
    if row is None:
        return None

    try:
        parsed_value = json.loads(row["auth_policy_json"])
    except json.JSONDecodeError:
        return {"auth_policy": normalize_connector_auth_policy(None)}
    if not isinstance(parsed_value, dict):
        return {"auth_policy": normalize_connector_auth_policy(None)}
    return {"auth_policy": normalize_connector_auth_policy(parsed_value)}


def _migrate_legacy_connector_auth_policy_setting(
    connection: DatabaseConnection,
    settings_value: dict[str, Any],
    *,
    delete_connectors_row: bool = False,
) -> dict[str, Any]:
    auth_policy = normalize_connector_auth_policy(settings_value.get("auth_policy"))
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO connector_auth_policies (policy_id, auth_policy_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(policy_id) DO UPDATE SET
            auth_policy_json = excluded.auth_policy_json,
            updated_at = excluded.updated_at
        """,
        (CONNECTOR_AUTH_POLICY_ROW_ID, json.dumps(auth_policy), now, now),
    )
    connection.execute("DELETE FROM settings WHERE key = ?", (CONNECTOR_AUTH_POLICY_SETTINGS_KEY,))
    if delete_connectors_row:
        connection.execute("DELETE FROM settings WHERE key = ?", ("connectors",))
    connection.commit()
    return {"auth_policy": auth_policy}


def _read_connector_auth_policy_setting(connection: DatabaseConnection) -> dict[str, Any] | None:
    row_value = _read_connector_auth_policy_row(connection)
    if isinstance(row_value, dict):
        return row_value

    row_value = read_stored_settings_section(connection, CONNECTOR_AUTH_POLICY_SETTINGS_KEY)
    if isinstance(row_value, dict):
        return _migrate_legacy_connector_auth_policy_setting(connection, row_value)

    legacy_value = read_stored_settings_section(connection, "connectors")
    if isinstance(legacy_value, dict) and isinstance(legacy_value.get("auth_policy"), dict):
        return _migrate_legacy_connector_auth_policy_setting(connection, legacy_value, delete_connectors_row=False)
    return None


def _migrate_legacy_connectors_from_settings(connection: DatabaseConnection) -> None:
    if list_stored_connector_records(connection):
        return

    legacy_value = read_stored_settings_section(connection, "connectors")
    if not isinstance(legacy_value, dict):
        return

    legacy_records = [item for item in legacy_value.get("records", []) if isinstance(item, dict)]
    if legacy_records:
        replace_stored_connector_records(connection, legacy_records)

    auth_policy_value = legacy_value.get("auth_policy")
    if isinstance(auth_policy_value, dict):
        write_connector_auth_policy(connection, auth_policy_value)

    delete_stored_settings_section(connection, "connectors")


def ensure_legacy_connector_storage_migrated(connection: DatabaseConnection) -> None:
    _migrate_legacy_connectors_from_settings(connection)


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
