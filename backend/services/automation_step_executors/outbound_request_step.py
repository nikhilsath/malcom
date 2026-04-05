"""Executor for automation outbound_request steps."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from backend.database import get_database_url
from backend.runtime import RuntimeExecutionResult
from backend.schemas import AutomationStepDefinition, OutgoingApiTestRequest, OutgoingApiTestResponse
from backend.services.automation_execution import (
    _materialize_http_preset_config,
    extract_response_fields,
    record_outgoing_delivery_history,
    render_template_string,
    try_parse_json_response_body,
    utc_now_iso,
    write_application_log,
)
from backend.services.automation_runs import finalize_automation_run_step
from backend.services.connectors import (
    get_connector_protection_secret,
    hydrate_outgoing_configuration_from_connector,
)
from backend.services.network import execute_outgoing_test_delivery
from backend.database import connect


def parse_template_json(template: str | None, context: dict[str, Any]) -> str:
    rendered = render_template_string(template or "{}", context)
    parsed = json.loads(rendered)
    return json.dumps(parsed)


def _execute_outbound_request_delivery(
    connection: Any,
    *,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    history_resource_id: str | None = None,
    delivery_executor: Callable[[OutgoingApiTestRequest], OutgoingApiTestResponse] | None = None,
) -> tuple[OutgoingApiTestResponse, Any | None, dict[str, Any]]:
    protection_secret = get_connector_protection_secret(root_dir=root_dir)
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        connection,
        connector_id=step.config.connector_id,
        destination_url=render_template_string(step.config.destination_url, context),
        auth_type=step.config.auth_type or "none",
        auth_config=step.config.auth_config,
        protection_secret=protection_secret,
    )
    executor = delivery_executor or execute_outgoing_test_delivery
    started_at = utc_now_iso()
    delivery = executor(
        OutgoingApiTestRequest(
            type="outgoing_scheduled",
            destination_url=destination_url,
            http_method=step.config.http_method or "POST",
            auth_type=auth_type,
            auth_config=auth_config,
            webhook_signing=step.config.webhook_signing,
            payload_template=parse_template_json(step.config.payload_template, context),
            connector_id=step.config.connector_id,
        )
    )
    finished_at = utc_now_iso()
    if history_resource_id:
        record_outgoing_delivery_history(
            connection,
            delivery_id=f"delivery_{uuid4().hex}",
            resource_type="automation_http_step",
            resource_id=history_resource_id,
            status_value="completed" if delivery.ok else "failed",
            http_status_code=delivery.status_code,
            request_summary=f"{step.config.http_method or 'POST'} {destination_url}",
            response_summary=(delivery.response_body or "")[:500] or f"{delivery.status_code} {delivery.destination_url}",
            error_summary=None if delivery.ok else (delivery.response_body or "")[:500],
            started_at=started_at,
            finished_at=finished_at,
        )
        connection.commit()
    response_body_json = try_parse_json_response_body(delivery.response_body)
    extracted_fields = extract_response_fields(response_body_json, step.config.response_mappings)
    return delivery, response_body_json, extracted_fields


def finalize_non_blocking_http_step(
    *,
    database_url: str,
    logger_name: str,
    run_step_id: str,
    automation_id: str,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    delivery_executor: Callable[[OutgoingApiTestRequest], OutgoingApiTestResponse] | None = None,
) -> None:
    connection = connect(database_url=database_url)
    logger = logging.getLogger(logger_name)
    try:
        delivery, response_body_json, extracted_fields = _execute_outbound_request_delivery(
            connection,
            step=step,
            context=context,
            root_dir=root_dir,
            history_resource_id=run_step_id,
            delivery_executor=delivery_executor,
        )
        detail = delivery.model_dump()
        detail["response_mode"] = "background"
        detail["response_mappings"] = step.config.response_mappings or []
        finalize_automation_run_step(
            connection,
            step_id=run_step_id,
            status_value="completed" if delivery.ok else "failed",
            response_summary=f"{delivery.status_code} {delivery.destination_url}",
            detail=detail,
            response_body_json=response_body_json,
            extracted_fields_json=extracted_fields,
            finished_at=utc_now_iso(),
        )
        write_application_log(
            logger,
            logging.INFO if delivery.ok else logging.WARNING,
            "automation_http_step_background_completed",
            automation_id=automation_id,
            step_name=step.name,
            run_step_id=run_step_id,
            status_code=delivery.status_code,
        )
    except Exception as error:
        finalize_automation_run_step(
            connection,
            step_id=run_step_id,
            status_value="failed",
            response_summary=str(error),
            detail={"error": str(error), "response_mode": "background"},
            finished_at=utc_now_iso(),
        )
        write_application_log(
            logger,
            logging.WARNING,
            "automation_http_step_background_failed",
            automation_id=automation_id,
            step_name=step.name,
            run_step_id=run_step_id,
            error=str(error),
        )
    finally:
        connection.close()


def execute_outbound_request_step(
    connection: Any,
    logger: logging.Logger,  # noqa: ARG001
    *,
    automation_id: str,
    run_step_id: str | None = None,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    database_url: str | None = None,
    background_executor: Any = None,
) -> RuntimeExecutionResult:
    """Execute an outbound_request automation step."""
    if step.config.http_preset_id:
        try:
            step = _materialize_http_preset_config(connection, step=step, context=context)
        except RuntimeError as error:
            return RuntimeExecutionResult(status="failed", response_summary=str(error), detail={"error": str(error)}, output={})

    if not step.config.wait_for_response:
        if not run_step_id:
            raise RuntimeError("Non-blocking HTTP steps require a runtime step identifier.")
        if background_executor is None:
            from concurrent.futures import ThreadPoolExecutor
            background_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="malcom-bg-delivery")
        background_executor.submit(
            finalize_non_blocking_http_step,
            database_url=database_url or get_database_url(),
            logger_name=logger.name,
            run_step_id=run_step_id,
            automation_id=automation_id,
            step=step.model_copy(deep=True),
            context=json.loads(json.dumps(context)),
            root_dir=root_dir,
            delivery_executor=execute_outgoing_test_delivery,
        )
        return RuntimeExecutionResult(
            status="completed",
            response_summary="Request sent in background mode.",
            detail={"response_mode": "background", "response_mappings": step.config.response_mappings or []},
            output={},
        )

    delivery, response_body_json, extracted_fields = _execute_outbound_request_delivery(
        connection,
        step=step,
        context=context,
        root_dir=root_dir,
        history_resource_id=run_step_id,
    )
    output_payload = delivery.model_dump()
    output_payload.update(extracted_fields)
    output_payload["extracted_fields"] = extracted_fields
    output_payload["response_body_json"] = response_body_json
    detail = dict(output_payload)
    detail["response_mode"] = "blocking"
    return RuntimeExecutionResult(
        status="completed" if delivery.ok else "failed",
        response_summary=f"{delivery.status_code} {delivery.destination_url}",
        detail=detail,
        output=output_payload,
    )
