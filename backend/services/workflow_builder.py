"""Automation workflow builder support resolvers.

Source of truth for workflow-builder connector options:
1) persisted connector rows in connectors table
2) provider metadata from integration_presets via build_connector_catalog()
3) canonical provider mapping via canonicalize_connector_provider()
"""

from __future__ import annotations

from typing import Any

from backend.database import DatabaseConnection
from backend.services.connectors import (
    build_connector_catalog,
    canonicalize_connector_provider,
    get_stored_connector_settings,
)

INACTIVE_WORKFLOW_CONNECTOR_STATUSES = {"draft", "expired", "revoked"}


def list_workflow_builder_connectors(connection: DatabaseConnection) -> list[dict[str, Any]]:
    """Return deterministic connector options for automation step pickers.

    Data lineage: See README.md > Data Lineage Reference > Saved Connectors
    Source: connectors table rows in database.
    
    This resolver intentionally does not keep an independent allowlist or
    status-based override in UI code. The workflow builder consumes these
    normalized records directly.
    """

    settings = get_stored_connector_settings(connection)
    provider_catalog = {item.get("id"): item for item in build_connector_catalog(connection)}
    records = settings.get("records", [])

    options: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        connector_id = str(record.get("id") or "").strip()
        if not connector_id:
            continue

        status_value = str(record.get("status") or "").strip().lower()
        if status_value in INACTIVE_WORKFLOW_CONNECTOR_STATUSES:
            continue

        canonical_provider = canonicalize_connector_provider(record.get("provider")) or ""
        provider_preset = provider_catalog.get(canonical_provider, {})
        option = {
            "id": connector_id,
            "name": record.get("name") or connector_id,
            "provider": canonical_provider,
            "provider_name": provider_preset.get("name") or canonical_provider,
            "status": record.get("status") or "draft",
            "auth_type": record.get("auth_type") or "",
            "scopes": [item for item in (record.get("scopes") or []) if isinstance(item, str)],
            "owner": record.get("owner"),
            "base_url": record.get("base_url"),
            "docs_url": record.get("docs_url"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "last_tested_at": record.get("last_tested_at"),
            "source_path": "connectors",
        }
        options.append(option)

    options.sort(key=lambda item: (str(item.get("name") or "").lower(), str(item.get("id") or "").lower()))
    return options


__all__ = ["list_workflow_builder_connectors"]
