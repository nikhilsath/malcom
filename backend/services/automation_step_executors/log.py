from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.services.workflow_storage import execute_workflow_write
from backend.services.storage_locations import check_location_quota, resolve_storage_location
from backend.services.automation_execution import render_template_string, write_application_log
from backend.services.metrics import snapshot_process_memory_mb
from backend.services.support import utc_now_iso


def execute_log_step(connection: Any, logger: logging.Logger, *, automation_id: str, step: Any, context: dict[str, Any], root_dir: Path) -> dict:
    # This function encapsulates the logic for `log` steps extracted from automation_executor._execute_automation_step_impl
    _DEFAULT_WORKFLOW_STORAGE_PATH = "backend/data/workflows"
    _DEFAULT_STORAGE_TYPE = "json"
    _DEFAULT_STORAGE_TARGET = "output"

    if step.config.log_table_id:
        # Delegate to existing DB write handler in automation_execution
        from backend.services.automation_execution import _execute_log_db_write

        result = _execute_log_db_write(connection, logger, automation_id=automation_id, step=step, context=context)
        return {"result": result}

    # File-backed write support
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
            try:
                resolved = resolve_storage_location(connection, location_id, root_dir=root_dir)
            except ValueError as exc:
                return {"error": str(exc)}

            # Apply folder/file name templates when provided
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
                storage_target = render_template_string(file_tmpl, context) or storage_target

            if resolved["location_type"] == "google_drive":
                # Delegate to connector activity for drive writes
                connector_id = resolved.get("connector_id")
                if not connector_id:
                    return {"error": "Google Drive location has no connector_id"}
                import json as _json
                content = _json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
                from backend.services.connector_activities import execute_connector_activity

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
                result = {"file": f"drive://{resolved['path']}/{storage_target}.json", "storage_type": "google_drive", "target": storage_target, "drive_result": drive_result}
                return {"result": result}

            # Local or repo location — enforce quota then write
            try:
                import json as _json_size

                estimated_bytes = len(_json_size.dumps(payload, ensure_ascii=False).encode())
                check_location_quota(connection, location_id, estimated_bytes, root_dir=root_dir)
            except RuntimeError as exc:
                return {"error": str(exc)}

            configured_path = resolved.get("path") or _DEFAULT_WORKFLOW_STORAGE_PATH
        else:
            try:
                from backend.services.settings import get_settings_payload

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
        write_application_log(logger, logging.INFO, "automation_log_step", automation_id=automation_id, step_name=step.name, message=summary)
        return {"result": {"status": "completed", "summary": summary, "detail": result}}

    # Default simple log path
    message = render_template_string(step.config.message, context)
    write_application_log(logger, logging.INFO, "automation_log_step", automation_id=automation_id, step_name=step.name, message=message)
    return {"result": {"status": "completed", "summary": message}}
