from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.runtime import RuntimeExecutionResult
from backend.services.connector_activities import execute_connector_activity
from backend.services.storage_locations import check_location_quota, resolve_storage_location
from backend.services.tool_execution import render_template_string
from backend.services.workflow_storage import execute_workflow_write

_DEFAULT_WORKFLOW_STORAGE_PATH = "data/workflows"


def _resolve_payload(context: dict[str, Any]) -> Any:
    payload = context.get("payload")
    if payload is None:
        return context
    return payload


def _resolve_storage_path(resolved_location: dict[str, Any] | None = None) -> str:
    if resolved_location and resolved_location.get("path"):
        return str(resolved_location["path"])
    return _DEFAULT_WORKFLOW_STORAGE_PATH


def execute_storage_step(
    connection: Any,
    logger: logging.Logger,
    *,
    step: Any,
    context: dict[str, Any],
    root_dir: Path,
) -> dict:
    """Execute a standalone `storage` automation step.

    The step writes the current payload to the workflow storage area using the
    same file helpers used by Log-step storage output, but without requiring a
    Log step wrapper.
    """

    storage_type = getattr(step.config, "storage_type", None) or "json"
    storage_target = getattr(step.config, "storage_target", None) or "output"
    new_file = bool(getattr(step.config, "storage_new_file", True))
    payload = _resolve_payload(context)

    location_id = getattr(step.config, "storage_location_id", None)
    if location_id:
        if connection is None:
            return {"error": "storage_location_id requires a database connection."}

        try:
            resolved = resolve_storage_location(connection, location_id, root_dir=root_dir)
        except ValueError as exc:
            return {"error": str(exc)}

        folder_tmpl = getattr(step.config, "folder_template", None) or resolved.get("folder_template")
        file_tmpl = getattr(step.config, "file_name_template", None) or resolved.get("file_name_template")
        if folder_tmpl:
            rendered_folder = render_template_string(folder_tmpl, context)
            if rendered_folder:
                if resolved.get("path"):
                    resolved["path"] = str(Path(resolved["path"]) / rendered_folder)
                else:
                    resolved["path"] = rendered_folder
        if file_tmpl:
            rendered_target = render_template_string(file_tmpl, context)
            if rendered_target:
                storage_target = rendered_target

        if resolved["location_type"] == "google_drive":
            connector_id = resolved.get("connector_id")
            if not connector_id:
                return {"error": "Google Drive location has no connector_id"}

            content = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
            drive_result = execute_connector_activity(
                connection,
                connector_id=connector_id,
                activity_id="drive_create_file",
                inputs={
                    "parent_folder_id": resolved["path"] or "root",
                    "name": f"{storage_target}.json",
                    "content": content,
                    "mime_type": "application/json",
                },
                root_dir=root_dir,
                context=context,
            )
            result = {
                "file": f"drive://{resolved['path']}/{storage_target}.json",
                "storage_type": "google_drive",
                "target": storage_target,
                "drive_result": drive_result,
            }
            summary = f"Wrote {storage_target} to Google Drive."
            return {
                "result": RuntimeExecutionResult(
                    status="completed",
                    response_summary=summary,
                    detail={"storage_type": "google_drive", "target": storage_target, "file": result["file"]},
                    output=result,
                )
            }

        try:
            estimated_bytes = len(json.dumps(payload, ensure_ascii=False).encode())
            check_location_quota(connection, location_id, estimated_bytes, root_dir=root_dir)
        except RuntimeError as exc:
            return {"error": str(exc)}

        storage_path = _resolve_storage_path(resolved)
    else:
        storage_path = _DEFAULT_WORKFLOW_STORAGE_PATH

    result = execute_workflow_write(
        root_dir,
        storage_path,
        storage_type,
        storage_target,
        payload,
        new_file=new_file,
    )
    summary = f"Wrote {storage_type} to {result.get('file', storage_target)}"
    logger.info("storage step completed", extra={"step_name": getattr(step, "name", ""), "storage_type": storage_type, "target": storage_target})
    return {
        "result": RuntimeExecutionResult(
            status="completed",
            response_summary=summary,
            detail={"storage_type": storage_type, "target": storage_target, "file": result["file"]},
            output=result,
        )
    }
