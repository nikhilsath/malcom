from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConnectorActivityDefinition:
    provider_id: str
    activity_id: str
    service: str
    operation_type: str
    label: str
    description: str
    required_scopes: tuple[str, ...]
    input_schema: tuple[dict[str, Any], ...]
    output_schema: tuple[dict[str, Any], ...]
    execution: dict[str, Any]


def _field(key: str, label: str, type_: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "type": type_, **extra}


def _output(key: str, label: str, type_: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "type": type_, **extra}


UPLOAD_SOURCE_OPTIONS = ["previous_step_output", "local_storage_reference", "cloud_storage_reference", "raw_text"]
VALUE_SOURCE_HINT = "Supports raw values and mapped automation variables like {{steps.previous.output}}."
JSON_SOURCE_HINT = "Provide structured JSON, or template JSON with mapped automation variables."

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
