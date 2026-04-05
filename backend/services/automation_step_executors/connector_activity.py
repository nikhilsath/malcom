from __future__ import annotations

from typing import Any

from backend.runtime import RuntimeExecutionResult
from backend.services.connector_activities import execute_connector_activity


def execute_connector_activity_step(connection: Any, logger: Any, *, step: Any, context: dict[str, Any], root_dir: Any) -> dict:
    activity_output = execute_connector_activity(
        connection,
        connector_id=step.config.connector_id or "",
        activity_id=step.config.activity_id or "",
        inputs=step.config.activity_inputs,
        root_dir=root_dir,
        context=context,
    )
    detail = {
        "connector_id": step.config.connector_id,
        "activity_id": step.config.activity_id,
        "activity_output": activity_output,
    }
    result = RuntimeExecutionResult(status="completed", response_summary=f"Connector activity {step.config.activity_id} completed.", detail=detail, output=activity_output)
    return {"runtime_result": result}
