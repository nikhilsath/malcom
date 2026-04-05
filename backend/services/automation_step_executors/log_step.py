"""Executor for automation log steps."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.runtime import RuntimeExecutionResult
from backend.schemas import AutomationStepDefinition
from backend.services.automation_execution import (
    _execute_log_db_write,
    get_settings_payload,
    render_template_string,
    write_application_log,
)
from backend.services.storage_locations import (
    check_location_quota,
    resolve_storage_location,
)
from backend.services.workflow_storage import execute_workflow_write

_DEFAULT_WORKFLOW_STORAGE_PATH = "backend/data/workflows"
_DEFAULT_STORAGE_TYPE = "json"
_DEFAULT_STORAGE_TARGET = "output"


def execute_log_step(
    connection: Any,
    logger: logging.Logger,
    *,
    automation_id: str,
    run_step_id: str | None = None,  # noqa: ARG001
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    database_url: str | None = None,  # noqa: ARG001
) -> RuntimeExecutionResult:
    """Execute a log automation step."""
    if step.config.log_table_id:
        return _execute_log_db_write(connection, logger, automation_id=automation_id, step=step, context=context)

    # File-backed write support: use storage fields when provided on the step
    if getattr(step.config, "storage_type", None) or getattr(step.config, "storage_target", None):
        storage_type = getattr(step.config, "storage_type", None) or _DEFAULT_STORAGE_TYPE
        storage_target = getattr(step.config, "storage_target", None) or _DEFAULT_STORAGE_TARGET
        new_file = getattr(step.config, "storage_new_file", True)
        raw_payload = render_template_string(step.config.message or "{}", context)
        try:
            payload: Any = json.loads(raw_payload)
        except (ValueError, TypeError):
            payload = raw_payload

        location_id = getattr(step.config, "storage_location_id", None)
        if location_id:
            # Resolve the named storage location
            try:
                resolved = resolve_storage_location(connection, location_id, root_dir=root_dir)
            except ValueError as exc:
                return RuntimeExecutionResult(status="failed", response_summary=str(exc), detail={"error": str(exc)}, output={})
            location_type = resolved["location_type"]

            # Apply folder/file name templates when provided
            folder_tmpl = getattr(step.config, "folder_template", None) or resolved.get("folder_template")
            file_tmpl = getattr(step.config, "file_name_template", None) or resolved.get("file_name_template")
            if folder_tmpl:
                rendered_folder = render_template_string(folder_tmpl, context)
                if rendered_folder:
                    if resolved["path"]:
                        resolved["path"] = str(Path(resolved["path"]) / rendered_folder)
                    else:
                        resolved["path"] = rendered_folder
            if file_tmpl:
                storage_target = render_template_string(file_tmpl, context) or storage_target

            if location_type == "google_drive":
                # Delegate to Drive connector activity
                connector_id = resolved.get("connector_id")
                if not connector_id:
                    return RuntimeExecutionResult(
                        status="failed",
                        response_summary="Google Drive location has no connector_id",
                        detail={"error": "connector_id missing on storage location"},
                        output={},
                    )
                import json as _json
                content = _json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
                from backend.services.connector_activities import execute_connector_activity
                try:
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
                except Exception as exc:
                    return RuntimeExecutionResult(
                        status="failed",
                        response_summary=f"Google Drive write failed: {exc}",
                        detail={"error": str(exc)},
                        output={},
                    )
                result = {"file": f"drive://{resolved['path']}/{storage_target}.json", "storage_type": "google_drive", "target": storage_target, "drive_result": drive_result}
                return RuntimeExecutionResult(status="completed", response_summary=f"Wrote to Google Drive: {storage_target}", detail=result, output=result)

            # Local or repo location — enforce quota then write
            try:
                import json as _json_size
                estimated_bytes = len(_json_size.dumps(payload, ensure_ascii=False).encode())
                check_location_quota(connection, location_id, estimated_bytes, root_dir=root_dir)
            except RuntimeError as exc:
                return RuntimeExecutionResult(status="failed", response_summary=str(exc), detail={"error": str(exc)}, output={})

            configured_path = resolved["path"] or _DEFAULT_WORKFLOW_STORAGE_PATH

        else:
            # Fall back to global workflow_storage_path setting
            try:
                settings_payload = get_settings_payload(connection)
                configured_path = (settings_payload.get("data") or {}).get("workflow_storage_path") or _DEFAULT_WORKFLOW_STORAGE_PATH
            except Exception:
                configured_path = _DEFAULT_WORKFLOW_STORAGE_PATH

        result = execute_workflow_write(
            root_dir,
            configured_path,
            storage_type,
            storage_target,
            payload,
            new_file=new_file,
        )
        summary = f"Wrote {storage_type} to {result.get('file', storage_target)}"
        return RuntimeExecutionResult(status="completed", response_summary=summary, detail=result, output=result)

    message = render_template_string(step.config.message, context)
    # Check for a default-logs storage location and route there if present
    try:
        default_log_row = connection.execute(
            "SELECT * FROM storage_locations WHERE is_default_logs = 1 LIMIT 1"
        ).fetchone()
    except Exception:
        default_log_row = None

    if default_log_row is not None:
        default_log_row = dict(default_log_row)
        log_location_id = default_log_row["id"]
        log_path = default_log_row.get("path") or _DEFAULT_WORKFLOW_STORAGE_PATH
        log_payload = {"message": message, "automation_id": automation_id, "step_name": step.name}
        try:
            estimated = len(json.dumps(log_payload, ensure_ascii=False).encode())
            check_location_quota(connection, log_location_id, estimated, root_dir=root_dir)
            log_result = execute_workflow_write(root_dir, log_path, "json", "automation_logs", log_payload, new_file=True)
            log_detail = {"message": message, "log_file": log_result.get("file")}
        except Exception:
            log_detail = {"message": message}
    else:
        log_detail = {"message": message}

    write_application_log(
        logger,
        logging.INFO,
        "automation_log_step",
        automation_id=automation_id,
        step_name=step.name,
        message=message,
    )
    return RuntimeExecutionResult(status="completed", response_summary=message, detail=log_detail, output=message)
