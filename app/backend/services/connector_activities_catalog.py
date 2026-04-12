from __future__ import annotations

from typing import Any

from backend.database import fetch_all, fetch_one

from .connector_activities_defs import ConnectorActivityDefinition, JSON_SOURCE_HINT, UPLOAD_SOURCE_OPTIONS, VALUE_SOURCE_HINT, _field, _output

from .connector_activities_github import GITHUB_CONNECTOR_ACTIVITY_DEFINITIONS
from .connector_activities_google import GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS
from .connector_activities_notion import NOTION_CONNECTOR_ACTIVITY_DEFINITIONS
from .connector_activities_trello import TRELLO_CONNECTOR_ACTIVITY_DEFINITIONS


CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    *GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS,
    *GITHUB_CONNECTOR_ACTIVITY_DEFINITIONS,
    *NOTION_CONNECTOR_ACTIVITY_DEFINITIONS,
    *TRELLO_CONNECTOR_ACTIVITY_DEFINITIONS,
)

_ACTIVITY_INDEX = {(item.provider_id, item.activity_id): item for item in CONNECTOR_ACTIVITY_DEFINITIONS}


def _build_default_activity_catalog() -> list[dict[str, Any]]:
    return [
        {
            "provider_id": item.provider_id,
            "activity_id": item.activity_id,
            "service": item.service,
            "operation_type": item.operation_type,
            "label": item.label,
            "description": item.description,
            "required_scopes": list(item.required_scopes),
            "input_schema": list(item.input_schema),
            "output_schema": list(item.output_schema),
            "execution": dict(item.execution),
        }
        for item in CONNECTOR_ACTIVITY_DEFINITIONS
    ]


def _decode_json_field(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            import json

            return json.loads(value)
        except Exception:
            return fallback
    return fallback


def _serialize_activity_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = _decode_json_field(row.get("metadata_json"), {})
    return {
        "provider_id": row["provider_id"],
        "activity_id": metadata.get("activity_id") or str(row.get("endpoint_id") or "").rsplit(":", 1)[-1],
        "service": row["service"],
        "operation_type": row["operation_type"],
        "label": row["label"],
        "description": row.get("description") or "",
        "required_scopes": _decode_json_field(row.get("required_scopes_json"), []),
        "input_schema": _decode_json_field(row.get("input_schema_json"), []),
        "output_schema": _decode_json_field(row.get("output_schema_json"), []),
        "execution": _decode_json_field(row.get("execution_json"), {}),
    }


def build_connector_activity_catalog(connection: Any | None = None) -> list[dict[str, Any]]:
    if connection is None:
        return _build_default_activity_catalog()

    rows = fetch_all(
        connection,
        """
        SELECT endpoint_id, provider_id, service, operation_type, label, description,
               required_scopes_json, input_schema_json, output_schema_json, execution_json, metadata_json
        FROM connector_endpoint_definitions
        WHERE endpoint_kind = 'activity'
        ORDER BY provider_id ASC, service ASC, operation_type ASC, label ASC
        """,
    )
    if not rows:
        return _build_default_activity_catalog()
    return [_serialize_activity_row(dict(row)) for row in rows]


def get_connector_activity_definition(provider_id: str, activity_id: str, connection: Any | None = None) -> dict[str, Any] | None:
    if connection is not None:
        row = fetch_one(
            connection,
            """
            SELECT endpoint_id, provider_id, service, operation_type, label, description,
                   required_scopes_json, input_schema_json, output_schema_json, execution_json, metadata_json
            FROM connector_endpoint_definitions
            WHERE endpoint_kind = 'activity' AND provider_id = ? AND endpoint_id = ?
            LIMIT 1
            """,
            (provider_id, f"activity:{provider_id}:{activity_id}"),
        )
        if row is not None:
            return _serialize_activity_row(dict(row))

    item = _ACTIVITY_INDEX.get((provider_id, activity_id))
    if item is None:
        return None
    return {
        "provider_id": item.provider_id,
        "activity_id": item.activity_id,
        "service": item.service,
        "operation_type": item.operation_type,
        "label": item.label,
        "description": item.description,
        "required_scopes": list(item.required_scopes),
        "input_schema": list(item.input_schema),
        "output_schema": list(item.output_schema),
        "execution": dict(item.execution),
    }


def get_provider_activities(provider_id: str, connection: Any | None = None) -> list[dict[str, Any]]:
    return [item for item in build_connector_activity_catalog(connection) if item["provider_id"] == provider_id]
