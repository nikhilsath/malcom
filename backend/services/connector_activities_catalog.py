from __future__ import annotations

from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, JSON_SOURCE_HINT, UPLOAD_SOURCE_OPTIONS, VALUE_SOURCE_HINT, _field, _output

from .connector_activities_github import GITHUB_CONNECTOR_ACTIVITY_DEFINITIONS
from .connector_activities_google import GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS


CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    *GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS,
    *GITHUB_CONNECTOR_ACTIVITY_DEFINITIONS,
)

_ACTIVITY_INDEX = {(item.provider_id, item.activity_id): item for item in CONNECTOR_ACTIVITY_DEFINITIONS}


def build_connector_activity_catalog() -> list[dict[str, Any]]:
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


def get_connector_activity_definition(provider_id: str, activity_id: str) -> dict[str, Any] | None:
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


def get_provider_activities(provider_id: str) -> list[dict[str, Any]]:
    return [item for item in build_connector_activity_catalog() if item["provider_id"] == provider_id]
