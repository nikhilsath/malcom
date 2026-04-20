from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from backend.database import connect, fetch_all, fetch_one, get_database_url
from backend.runtime import RuntimeExecutionResult, next_daily_run_at, parse_iso_datetime, runtime_scheduler
from backend.schemas import (
    AutomationRunDetailResponse,
    AutomationRunStepResponse,
    AutomationStepDefinition,
    OutgoingApiTestRequest,
    OutgoingApiTestResponse,
    OutgoingAuthConfig,
    OutgoingWebhookSigningConfig,
)
from backend.services.automation_execution import (
    _build_script_runtime_context,
    _execute_log_db_write,
    _materialize_http_preset_config,
    execute_script_step,
    extract_response_fields,
    parse_template_json,
    record_outgoing_delivery_history,
    refresh_automation_schedule,
    refresh_outgoing_schedule,
    render_template_string,
    replace_automation_steps,
    row_to_run,
    row_to_run_step,
    serialize_automation_detail,
    try_parse_json_response_body,
    utc_now_iso,
    write_application_log,
    log_event,
)
from backend.services.workflow_storage import execute_workflow_write
from backend.services.storage_locations import (
    check_location_quota,
    resolve_storage_location,
)
from backend.services.repo_checkout_service import (
    clone_or_pull_repo,
    get_checkout_path,
    record_checkout_size,
)
from backend.services.automation_runs import (
    assign_automation_run_worker,
    calculate_duration_ms,
    create_automation_run,
    create_automation_run_step,
    finalize_automation_run,
    finalize_automation_run_step,
)
from backend.services.connector_activities import execute_connector_activity
from backend.services.connectors import (
    get_connector_protection_secret,
    hydrate_outgoing_configuration_from_connector,
)
from backend.services.metrics import get_metrics_collector, snapshot_process_memory_mb
from backend.services.network import execute_outgoing_test_delivery
from backend.services.tool_execution import (
    execute_coqui_tts_tool_step,
    execute_image_magic_tool_step,
    execute_llm_deepl_tool_step,
    execute_local_llm_chat_request,
    execute_smtp_tool_step,
)
from backend.services.validation import validate_automation_definition
from backend.services.runtime_workers import (
    LOCAL_WORKER_POLL_INTERVAL_SECONDS,
    REMOTE_WORKER_POLL_INTERVAL_SECONDS,
    process_runtime_job,
    register_runtime_worker,
    run_local_worker_loop,
    run_remote_worker_loop,
)
from backend.services.automation_step_executors.outbound_request import (
    finalize_non_blocking_http_step,
)


BACKGROUND_DELIVERY_EXECUTOR = ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="malcom-http-bg",
)


def _execute_automation_step_impl(
    connection: Any,
    logger: logging.Logger,
    *,
    automation_id: str,
    run_step_id: str | None = None,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    database_url: str | None = None,
) -> RuntimeExecutionResult:
    if step.type == "log":
        from backend.services.automation_step_executors.log import execute_log_step

        result = execute_log_step(connection, logger, automation_id=automation_id, step=step, context=context, root_dir=root_dir)
        # Translate executor result into RuntimeExecutionResult minimal wrapper
        if isinstance(result, dict) and result.get("error"):
            return RuntimeExecutionResult(status="failed", response_summary=result.get("error"), detail={"error": result.get("error")}, output={})
        if isinstance(result, dict) and result.get("result"):
            detail = result.get("result")
            summary = detail.get("summary") if isinstance(detail, dict) else str(detail)
            return RuntimeExecutionResult(status="completed", response_summary=summary or "completed", detail=detail, output=detail)
        return RuntimeExecutionResult(status="completed", response_summary=str(result), detail={"result": result}, output=result)

    if step.type == "outbound_request":
        from backend.services.automation_step_executors.outbound_request import execute_outbound_request_step

        exec_result = execute_outbound_request_step(
            connection, logger, automation_id=automation_id, run_step_id=run_step_id, step=step, context=context, root_dir=root_dir, database_url=database_url
        )
        if exec_result.get("error"):
            return RuntimeExecutionResult(status="failed", response_summary=exec_result.get("error"), detail={"error": exec_result.get("error")}, output={})
        if exec_result.get("background"):
            # Submit background finalizer similar to previous behavior
            payload = exec_result["background"]
            from concurrent.futures import ThreadPoolExecutor
            from backend.services.automation_step_executors.outbound_request import finalize_non_blocking_http_step

            # Use a short-lived executor to submit background task; the global BACKGROUND_DELIVERY_EXECUTOR remains available for production.
            BACKGROUND_DELIVERY_EXECUTOR.submit(
                finalize_non_blocking_http_step,
                database_url=payload.get("database_url"),
                logger_name=payload.get("logger_name"),
                run_step_id=payload.get("run_step_id"),
                automation_id=payload.get("automation_id"),
                step=payload.get("step"),
                context=payload.get("context"),
                root_dir=Path(payload.get("root_dir")),
            )
            return RuntimeExecutionResult(
                status="completed",
                response_summary="Request sent in background mode.",
                detail={"response_mode": "background", "response_mappings": step.config.response_mappings or []},
                output={},
            )
        if exec_result.get("result"):
            r = exec_result["result"]
            detail = r.get("detail") if isinstance(r, dict) else r
            ok = r.get("ok") if isinstance(r, dict) else True
            status_code = r.get("status_code") if isinstance(r, dict) else None
            dest = r.get("destination_url") if isinstance(r, dict) else None
            return RuntimeExecutionResult(
                status="completed" if ok else "failed",
                response_summary=f"{status_code} {dest}",
                detail=detail,
                output=detail,
            )

    if step.type == "connector_activity":
        from backend.services.automation_step_executors.connector_activity import execute_connector_activity_step

        exec_result = execute_connector_activity_step(connection, logger, step=step, context=context, root_dir=root_dir)
        if exec_result.get("runtime_result"):
            return exec_result.get("runtime_result")
        return RuntimeExecutionResult(status="failed", response_summary=exec_result.get("error") or "Connector activity executor error", detail={"error": exec_result.get("error")}, output={})

    if step.type == "script":
        script_row = fetch_one(connection, "SELECT * FROM scripts WHERE id = ?", (step.config.script_id,))
        if script_row is None:
            raise RuntimeError(f"Script '{step.config.script_id}' was not found.")

        # Determine working directory: repo checkout root + optional subdirectory
        effective_root_dir = root_dir
        repo_checkout_id = getattr(step.config, "repo_checkout_id", None)
        if repo_checkout_id:
            try:
                clone_or_pull_repo(connection, repo_checkout_id)
            except (ValueError, RuntimeError) as exc:
                write_application_log(
                    logger,
                    logging.WARNING,
                    "repo_checkout_sync_failed",
                    automation_id=automation_id,
                    step_name=step.name,
                    checkout_id=repo_checkout_id,
                    error=str(exc),
                )
            try:
                checkout_path = get_checkout_path(connection, repo_checkout_id)
                working_dir = getattr(step.config, "working_directory", None)
                if working_dir:
                    effective_root_dir = checkout_path / working_dir.lstrip("/")
                else:
                    effective_root_dir = checkout_path
            except ValueError:
                pass  # Checkout path not found – use default root_dir

        result = execute_script_step(
            script_row,
            context,
            root_dir=effective_root_dir,
            script_input_template=step.config.script_input_template,
        )

        # Update size after execution if a checkout was used
        if repo_checkout_id:
            try:
                record_checkout_size(connection, repo_checkout_id)
            except (ValueError, RuntimeError):
                pass

        return result

    if step.type == "llm_chat":
        messages: list[dict[str, str]] = []
        if step.config.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": render_template_string(step.config.system_prompt, context),
                }
            )
        messages.append(
            {
                "role": "user",
                "content": render_template_string(step.config.user_prompt, context),
            }
        )
        llm_response = execute_local_llm_chat_request(
            connection,
            messages=messages,
            model_identifier_override=render_template_string(step.config.model_identifier, context) if step.config.model_identifier else None,
        )
        detail = llm_response.model_dump()
        detail["request_messages"] = messages
        return RuntimeExecutionResult(
            status="completed",
            response_summary=llm_response.response_text[:500],
            detail=detail,
            output=detail,
        )

    if step.type == "tool":
        from backend.services.automation_step_executors.tool import execute_tool_step

        exec_result = execute_tool_step(connection, logger, step=step, context=context, root_dir=root_dir)
        if exec_result.get("error"):
            return RuntimeExecutionResult(status="failed", response_summary=exec_result.get("error"), detail={"error": exec_result.get("error")}, output={})
        result = exec_result.get("result")
        if isinstance(result, dict) and result.get("status"):
            return RuntimeExecutionResult(status=result.get("status"), response_summary=result.get("response_summary") or "", detail=result.get("detail"), output=result.get("detail"))
        return RuntimeExecutionResult(status="completed", response_summary="Tool executed.", detail=result, output=result)

    if step.type == "storage":
        from backend.services.automation_step_executors.storage import execute_storage_step

        exec_result = execute_storage_step(
            connection,
            logger,
            step=step,
            context=context,
            root_dir=root_dir,
        )
        if exec_result.get("error"):
            return RuntimeExecutionResult(
                status="failed",
                response_summary=exec_result.get("error"),
                detail={"error": exec_result.get("error")},
                output={},
            )
        runtime_result = exec_result.get("result")
        if isinstance(runtime_result, RuntimeExecutionResult):
            return runtime_result
        return RuntimeExecutionResult(
            status="completed",
            response_summary="Storage step executed.",
            detail=runtime_result,
            output=runtime_result,
        )

    from backend.services.automation_step_executors.condition import execute_condition_step

    return execute_condition_step(connection, logger, step=step, context=context)


def execute_automation_step(
    connection: Any,
    logger: logging.Logger,
    *,
    automation_id: str,
    run_step_id: str | None = None,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    database_url: str | None = None,
) -> RuntimeExecutionResult:
    started_at = time.perf_counter()
    start_memory_mb = snapshot_process_memory_mb()
    collector = get_metrics_collector()
    operation = f"step_{(step.type or 'unknown').strip() or 'unknown'}"

    try:
        result = _execute_automation_step_impl(
            connection,
            logger,
            automation_id=automation_id,
            run_step_id=run_step_id,
            step=step,
            context=context,
            root_dir=root_dir,
            database_url=database_url,
        )
    except Exception:
        collector.record_execution(
            component="automation_executor",
            operation=operation,
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            memory_mb=max(0.0, snapshot_process_memory_mb() - start_memory_mb),
            error=True,
        )
        raise

    collector.record_execution(
        component="automation_executor",
        operation=operation,
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        memory_mb=max(0.0, snapshot_process_memory_mb() - start_memory_mb),
        error=result.status == "failed",
    )
    return result


def fetch_run_detail(connection: Any, run_id: str) -> AutomationRunDetailResponse:
    run_row = fetch_one(
        connection,
        "SELECT run_id, automation_id, trigger_type, status, started_at, finished_at, duration_ms, error_summary FROM automation_runs WHERE run_id = ?",
        (run_id,),
    )
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation run not found.")
    step_rows = fetch_all(
        connection,
        """
        SELECT
            step_id,
            run_id,
            step_name,
            status,
            request_summary,
            response_summary,
            started_at,
            finished_at,
            duration_ms,
            detail_json,
            response_body_json,
            extracted_fields_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )
    return AutomationRunDetailResponse(
        **row_to_run(run_row),
        steps=[AutomationRunStepResponse(**row_to_run_step(row)) for row in step_rows],
    )


def execute_automation_definition(
    connection: Any,
    logger: logging.Logger,
    *,
    automation_id: str,
    trigger_type: str,
    payload: dict[str, Any] | None,
    root_dir: Path,
    database_url: str | None = None,
) -> AutomationRunDetailResponse:
    automation = serialize_automation_detail(connection, automation_id)
    run_id = f"run_{uuid4().hex}"
    started_at = utc_now_iso()
    create_automation_run(
        connection,
        run_id=run_id,
        automation_id=automation_id,
        trigger_type=trigger_type,
        status_value="running",
        started_at=started_at,
    )
    context: dict[str, Any] = {
        "automation": automation.model_dump(exclude={"steps"}),
        "payload": payload or {},
        "steps": {},
        "timestamp": started_at,
    }
    run_status = "completed"
    error_summary: str | None = None

    step_index_by_id = {step.id: index for index, step in enumerate(automation.steps) if step.id}
    executed_step_ids: set[str] = set()
    current_index = 0
    execution_order = 0

    while current_index < len(automation.steps):
        step = automation.steps[current_index]
        step_id_key = step.id or step.name
        if step_id_key in executed_step_ids:
            break
        executed_step_ids.add(step_id_key)
        execution_order += 1

        runtime_step_id = f"step_{uuid4().hex}"
        if step.type == "tool":
            step_inputs = step.config.tool_inputs
        elif step.type == "script":
            runtime_context, rendered_script_input = _build_script_runtime_context(
                context,
                script_input_template=step.config.script_input_template,
            )
            step_inputs = {
                "script_id": step.config.script_id or "",
                "script_input_raw": rendered_script_input,
                "script_input": runtime_context.get("script_input"),
            }
        else:
            step_inputs = None

        create_automation_run_step(
            connection,
            step_id=runtime_step_id,
            run_id=run_id,
            step_name=step.name,
            status_value="running",
            request_summary=f"{step.type} step #{execution_order}",
            started_at=utc_now_iso(),
            inputs_json=step_inputs,
        )
        try:
            result = execute_automation_step(
                connection,
                logger,
                automation_id=automation_id,
                run_step_id=runtime_step_id,
                step=step,
                context=context,
                root_dir=root_dir,
                database_url=database_url,
            )
            context["steps"][step.name] = result.output
            if step.id:
                context["steps"][step.id] = result.output
            finalize_automation_run_step(
                connection,
                step_id=runtime_step_id,
                status_value=result.status,
                response_summary=result.response_summary,
                detail=result.detail,
                response_body_json=result.detail.get("response_body_json") if result.detail else None,
                extracted_fields_json=result.detail.get("extracted_fields") if result.detail else None,
                finished_at=utc_now_iso(),
            )

            next_index: int | None = None
            if step.type == "condition":
                if result.output is True and step.on_true_step_id:
                    next_index = step_index_by_id.get(step.on_true_step_id)
                elif result.output is False:
                    if step.on_false_step_id:
                        next_index = step_index_by_id.get(step.on_false_step_id)
                    elif step.config.stop_on_false:
                        break
            if result.status != "completed":
                run_status = "failed"
                error_summary = result.response_summary or f"Step '{step.name}' failed."
                break
            current_index = next_index if next_index is not None else current_index + 1
        except Exception as error:
            run_status = "failed"
            error_summary = str(error)
            finalize_automation_run_step(
                connection,
                step_id=runtime_step_id,
                status_value="failed",
                response_summary=str(error),
                detail={"error": str(error)},
                finished_at=utc_now_iso(),
            )
            break

    finished_at = utc_now_iso()
    finalize_automation_run(connection, run_id=run_id, status_value=run_status, error_summary=error_summary, finished_at=finished_at)
    connection.execute(
        "UPDATE automations SET last_run_at = ?, updated_at = ? WHERE id = ?",
        (finished_at, finished_at, automation_id),
    )
    if automation.trigger_type == "schedule" and automation.trigger_config.schedule_time:
        connection.execute(
            "UPDATE automations SET next_run_at = ? WHERE id = ?",
            (next_daily_run_at(automation.trigger_config.schedule_time), automation_id),
        )
    connection.commit()
    return fetch_run_detail(connection, run_id)


def _execute_outgoing_api_delivery(
    connection: Any,
    logger: logging.Logger,
    *,
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
) -> None:
    table_name = "outgoing_scheduled_apis" if api_type == "outgoing_scheduled" else "outgoing_continuous_apis"
    row = fetch_one(connection, f"SELECT * FROM {table_name} WHERE id = ?", (api_id,))
    if row is None:
        return

    run_id = f"run_{uuid4().hex}"
    started_at = utc_now_iso()
    create_automation_run(connection, run_id=run_id, automation_id=api_id, trigger_type="schedule", status_value="running", started_at=started_at)
    runtime_step_id = f"step_{uuid4().hex}"
    create_automation_run_step(
        connection,
        step_id=runtime_step_id,
        run_id=run_id,
        step_name=f"{api_type}_delivery",
        status_value="running",
        request_summary=row["destination_url"],
        started_at=started_at,
    )
    try:
        webhook_signing_payload = json.loads(row.get("webhook_signing_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        webhook_signing_payload = {}
    result = execute_outgoing_test_delivery(
        OutgoingApiTestRequest(
            type=api_type,
            destination_url=row["destination_url"],
            http_method=row["http_method"],
            auth_type=row["auth_type"],
            auth_config=OutgoingAuthConfig(**json.loads(row["auth_config_json"])),
            webhook_signing=OutgoingWebhookSigningConfig(**webhook_signing_payload),
            payload_template=row["payload_template"],
        )
    )
    finished_at = utc_now_iso()
    next_run_at: str | None = None
    last_error = None if result.ok else (result.response_body or "")[:500]
    if api_type == "outgoing_scheduled":
        next_run_at = next_daily_run_at(row["scheduled_time"])
    elif bool(row.get("enabled")) and bool(row.get("repeat_enabled")) and row.get("repeat_interval_minutes"):
        next_run = parse_iso_datetime(finished_at) or datetime.now(UTC)
        next_run_at = (next_run + timedelta(minutes=int(row["repeat_interval_minutes"]))).isoformat()

    finalize_automation_run_step(
        connection,
        step_id=runtime_step_id,
        status_value="completed" if result.ok else "failed",
        response_summary=f"{result.status_code} {result.destination_url}",
        detail=result.model_dump(),
        finished_at=finished_at,
    )
    finalize_automation_run(
        connection,
        run_id=run_id,
        status_value="completed" if result.ok else "failed",
        error_summary=last_error,
        finished_at=finished_at,
    )
    connection.execute(
        f"UPDATE {table_name} SET last_run_at = ?, next_run_at = ?, last_error = ?, updated_at = ? WHERE id = ?",
        (finished_at, next_run_at, last_error, finished_at, api_id),
    )
    record_outgoing_delivery_history(
        connection,
        delivery_id=f"delivery_{uuid4().hex}",
        resource_type=api_type,
        resource_id=api_id,
        status_value="completed" if result.ok else "failed",
        http_status_code=result.status_code,
        request_summary=f"{row['http_method']} {row['destination_url']}",
        response_summary=(result.response_body or "")[:500] or f"{result.status_code} {result.destination_url}",
        error_summary=last_error,
        started_at=started_at,
        finished_at=finished_at,
    )
    connection.commit()
    write_application_log(
        logger,
        logging.INFO if result.ok else logging.WARNING,
        "scheduled_outgoing_api_executed" if api_type == "outgoing_scheduled" else "continuous_outgoing_api_executed",
        api_id=api_id,
        status_code=result.status_code,
    )


def execute_scheduled_api(connection: Any, logger: logging.Logger, *, api_id: str) -> None:
    _execute_outgoing_api_delivery(connection, logger, api_id=api_id, api_type="outgoing_scheduled")


def execute_continuous_api(connection: Any, logger: logging.Logger, *, api_id: str) -> None:
    _execute_outgoing_api_delivery(connection, logger, api_id=api_id, api_type="outgoing_continuous")


def refresh_scheduler_jobs(connection: Any) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for row in fetch_all(
        connection,
        "SELECT id, name, trigger_config_json, next_run_at FROM automations WHERE enabled = 1 AND trigger_type = 'schedule' ORDER BY created_at ASC",
    ):
        trigger_config = json.loads(row["trigger_config_json"])
        jobs.append(
            {
                "id": row["id"],
                "kind": "automation",
                "name": row["name"],
                "schedule_time": trigger_config.get("schedule_time"),
                "next_run_at": row["next_run_at"] or next_daily_run_at(trigger_config["schedule_time"]),
            }
        )

    for row in fetch_all(connection, "SELECT id, name, scheduled_time, next_run_at FROM outgoing_scheduled_apis WHERE enabled = 1 ORDER BY created_at ASC"):
        jobs.append(
            {
                "id": row["id"],
                "kind": "outgoing_scheduled",
                "name": row["name"],
                "schedule_time": row["scheduled_time"],
                "next_run_at": row["next_run_at"] or next_daily_run_at(row["scheduled_time"]),
            }
        )

    for row in fetch_all(
        connection,
        """
        SELECT id, name, repeat_interval_minutes, next_run_at
        FROM outgoing_continuous_apis
        WHERE enabled = 1 AND repeat_enabled = 1 AND repeat_interval_minutes IS NOT NULL
        ORDER BY created_at ASC
        """,
    ):
        jobs.append(
            {
                "id": row["id"],
                "kind": "outgoing_continuous",
                "name": row["name"],
                "schedule_time": f"every {row['repeat_interval_minutes']}m",
                "next_run_at": row["next_run_at"] or utc_now_iso(),
            }
        )
    runtime_scheduler.update_jobs(jobs)
    return jobs


def run_scheduler_tick(app: FastAPI) -> None:
    connection = app.state.connection
    logger = app.state.logger
    now = datetime.now(UTC)
    refresh_scheduler_jobs(connection)

    for row in fetch_all(
        connection,
        "SELECT id, next_run_at FROM automations WHERE enabled = 1 AND trigger_type = 'schedule' AND next_run_at IS NOT NULL",
    ):
        scheduled_at = parse_iso_datetime(row["next_run_at"])
        if scheduled_at is not None and scheduled_at <= now:
            execute_automation_definition(
                connection,
                logger,
                automation_id=row["id"],
                trigger_type="schedule",
                payload=None,
                root_dir=Path(app.state.root_dir),
                database_url=app.state.database_url,
            )

    for row in fetch_all(connection, "SELECT id, next_run_at FROM outgoing_scheduled_apis WHERE enabled = 1 AND next_run_at IS NOT NULL"):
        scheduled_at = parse_iso_datetime(row["next_run_at"])
        if scheduled_at is not None and scheduled_at <= now:
            execute_scheduled_api(connection, logger, api_id=row["id"])

    for row in fetch_all(
        connection,
        """
        SELECT id, next_run_at
        FROM outgoing_continuous_apis
        WHERE enabled = 1 AND repeat_enabled = 1 AND next_run_at IS NOT NULL
        """,
    ):
        scheduled_at = parse_iso_datetime(row["next_run_at"])
        if scheduled_at is not None and scheduled_at <= now:
            execute_continuous_api(connection, logger, api_id=row["id"])


__all__ = [
    "LOCAL_WORKER_POLL_INTERVAL_SECONDS",
    "REMOTE_WORKER_POLL_INTERVAL_SECONDS",
    "assign_automation_run_worker",
    "calculate_duration_ms",
    "create_automation_run",
    "create_automation_run_step",
    "execute_automation_definition",
    "execute_automation_step",
    "execute_continuous_api",
    "execute_scheduled_api",
    "execute_script_step",
    "fetch_run_detail",
    "finalize_automation_run",
    "finalize_automation_run_step",
    "finalize_non_blocking_http_step",
    "log_event",
    "parse_template_json",
    "process_runtime_job",
    "refresh_automation_schedule",
    "refresh_outgoing_schedule",
    "refresh_scheduler_jobs",
    "register_runtime_worker",
    "render_template_string",
    "replace_automation_steps",
    "run_local_worker_loop",
    "run_remote_worker_loop",
    "run_scheduler_tick",
    "validate_automation_definition",
]
