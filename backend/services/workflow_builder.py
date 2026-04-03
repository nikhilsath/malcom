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

AUTOMATION_TRIGGER_TYPE_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "manual", "label": "Manual", "description": "Run the automation only when an operator starts it."},
    {"value": "schedule", "label": "Schedule", "description": "Start automatically at a set time each day."},
    {"value": "inbound_api", "label": "Inbound API", "description": "Start when an inbound API endpoint receives an event."},
    {"value": "smtp_email", "label": "SMTP email", "description": "Start when incoming email matches your filters."},
)

AUTOMATION_STEP_TYPE_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "log", "label": "Write", "description": "Write a row to a managed database table."},
    {
        "value": "connector_activity",
        "label": "Connector action",
        "description": "Call a provider-aware action backed by a saved connector.",
    },
    {
        "value": "outbound_request",
        "label": "HTTP request",
        "description": "Send a custom or connector-backed HTTP request.",
    },
    {"value": "script", "label": "Script", "description": "Run a stored script from the script library."},
    {"value": "tool", "label": "Tool", "description": "Dispatch a configured tool from the tool catalog."},
    {
        "value": "condition",
        "label": "Condition",
        "description": "Evaluate a guard expression and optionally halt the automation.",
    },
    {"value": "llm_chat", "label": "LLM chat", "description": "Prompt a language model with workflow context."},
)

AUTOMATION_HTTP_METHOD_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "GET", "label": "GET"},
    {"value": "POST", "label": "POST"},
    {"value": "PUT", "label": "PUT"},
    {"value": "PATCH", "label": "PATCH"},
    {"value": "DELETE", "label": "DELETE"},
)

AUTOMATION_STORAGE_TYPE_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "table", "label": "Database table", "description": "Write rows into a managed log table."},
    {"value": "csv", "label": "CSV file", "description": "Append rows to a CSV file target."},
    {"value": "json", "label": "JSON file", "description": "Write structured JSON output to a file target."},
    {"value": "other", "label": "Other", "description": "Write to another file-backed target identifier."},
)

AUTOMATION_LOG_COLUMN_TYPE_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "text", "label": "Text"},
    {"value": "integer", "label": "Integer"},
    {"value": "real", "label": "Real"},
    {"value": "boolean", "label": "Boolean"},
    {"value": "timestamp", "label": "Timestamp"},
)


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


def get_automation_builder_metadata() -> dict[str, Any]:
    return {
        "trigger_types": [dict(item) for item in AUTOMATION_TRIGGER_TYPE_OPTIONS],
        "step_types": [dict(item) for item in AUTOMATION_STEP_TYPE_OPTIONS],
        "http_methods": [dict(item) for item in AUTOMATION_HTTP_METHOD_OPTIONS],
        "storage_types": [dict(item) for item in AUTOMATION_STORAGE_TYPE_OPTIONS],
        "log_column_types": [dict(item) for item in AUTOMATION_LOG_COLUMN_TYPE_OPTIONS],
    }


__all__ = ["get_automation_builder_metadata", "list_workflow_builder_connectors"]
