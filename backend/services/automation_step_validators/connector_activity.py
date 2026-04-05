from __future__ import annotations

import json
from typing import Any

from backend.services.connector_activities import get_connector_activity_definition, get_missing_connector_activity_scopes
from backend.services.connectors import find_stored_connector_record


def validate_connector_activity_step(step: Any, index: int, connection: object | None) -> list[str]:
    issues: list[str] = []
    if not step.config.connector_id:
        issues.append(f"Step {index} requires config.connector_id for connector activity steps.")
    if not step.config.activity_id:
        issues.append(f"Step {index} requires config.activity_id for connector activity steps.")
    elif step.config.connector_id and connection is not None:
        connector_record = find_stored_connector_record(connection, step.config.connector_id)
        if connector_record is None:
            issues.append(f"Step {index} references an unknown connector.")
        else:
            activity_definition = get_connector_activity_definition(connector_record.get("provider") or "", step.config.activity_id)
            if activity_definition is None:
                issues.append(f"Step {index}: connector provider does not support activity '{step.config.activity_id}'.")
            else:
                missing_scopes = get_missing_connector_activity_scopes(connector_record, activity_definition)
                if missing_scopes:
                    issues.append(f"Step {index}: connector is missing required scopes: {', '.join(missing_scopes)}.")
                try:
                    from backend.services.connector_activities import _resolve_inputs

                    _resolve_inputs(activity_definition.get("input_schema", []), step.config.activity_inputs or {})
                except json.JSONDecodeError as error:
                    issues.append(f"Step {index}: connector activity input contains invalid JSON: {error.msg}.")
                except RuntimeError as error:
                    issues.append(f"Step {index}: {error}.")

    return issues
