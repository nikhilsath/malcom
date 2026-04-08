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


__all__ = [
    "ConnectorActivityDefinition",
    "JSON_SOURCE_HINT",
    "UPLOAD_SOURCE_OPTIONS",
    "VALUE_SOURCE_HINT",
    "_field",
    "_output",
]
