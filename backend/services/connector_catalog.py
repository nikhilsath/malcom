"""Connector provider catalog constants and normalization helpers.

Provides catalog data, provider metadata, and normalization functions.
Primary identifiers: ``DEFAULT_CONNECTOR_CATALOG``, ``build_connector_catalog``,
``normalize_connector_auth_policy``, ``get_default_connector_settings``.
"""

from __future__ import annotations

import json
from typing import Any

from backend.database import fetch_all, fetch_one

DatabaseConnection = Any
DatabaseRow = dict[str, Any]

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
    defaults = {
        "rotation_interval_days": 90,
        "reconnect_requires_approval": True,
        "credential_visibility": "masked",
    }
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


__all__ = [
    "ACTIVE_STORAGE_CONNECTOR_STATUSES",
    "CONNECTOR_AUTH_POLICY_ROW_ID",
    "CONNECTOR_AUTH_POLICY_SETTINGS_KEY",
    "CONNECTOR_CREDENTIAL_VISIBILITY_OPTIONS",
    "CONNECTOR_PROVIDER_CANONICAL_MAP",
    "CONNECTOR_REQUEST_AUTH_TYPE_MAP",
    "CONNECTOR_ROTATION_INTERVAL_OPTIONS",
    "CONNECTOR_STATUS_OPTIONS",
    "DEFAULT_CONNECTOR_CATALOG",
    "DEFAULT_CONNECTOR_PROVIDER_METADATA",
    "GITHUB_AVAILABLE_SCOPES",
    "GOOGLE_RECOMMENDED_SCOPES",
    "LEGACY_GOOGLE_CONNECTOR_PROVIDER_IDS",
    "SUPPORTED_CONNECTOR_AUTH_TYPES",
    "SUPPORTED_CONNECTOR_PROVIDERS",
    "SUPPORTED_CONNECTOR_STATUSES",
    "_clone_connector_catalog_defaults",
    "_get_default_connector_preset",
    "_provider_display_name",
    "_provider_metadata",
    "_row_to_connector_preset",
    "build_connector_catalog",
    "build_connector_response_metadata",
    "canonicalize_connector_provider",
    "get_connector_preset",
    "get_connector_provider_metadata",
    "get_default_connector_settings",
    "normalize_connector_auth_policy",
    "normalize_connector_request_auth_type",
]
