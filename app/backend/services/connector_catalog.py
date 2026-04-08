from __future__ import annotations
import json
from typing import Any

from backend.database import fetch_all, fetch_one

CONNECTOR_PROVIDER_CANONICAL_MAP = {
    "google_calendar": "google",
    "google_gmail": "google",
    "google_sheets": "google",
}

SUPPORTED_CONNECTOR_AUTH_TYPES = {"oauth2", "bearer", "api_key", "basic", "header"}
SUPPORTED_CONNECTOR_STATUSES = {"draft", "pending_oauth", "connected", "needs_attention", "expired", "revoked"}

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


def _clone_connector_catalog_defaults() -> list[dict[str, Any]]:
    return json.loads(json.dumps(DEFAULT_CONNECTOR_CATALOG))


def canonicalize_connector_provider(provider: str | None) -> str | None:
    if not provider:
        return provider
    return CONNECTOR_PROVIDER_CANONICAL_MAP.get(provider, provider)


def _get_default_connector_preset(provider: str) -> dict[str, Any] | None:
    canonical_provider = canonicalize_connector_provider(provider)
    return next((item for item in DEFAULT_CONNECTOR_CATALOG if item["id"] == canonical_provider), None)


def _row_to_connector_preset(row: dict[str, Any]) -> dict[str, Any]:
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


def build_connector_catalog(connection: object | None = None) -> list[dict[str, Any]]:
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


def get_connector_preset(provider: str, *, connection: object | None = None) -> dict[str, Any] | None:
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
