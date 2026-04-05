from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Tuple
from uuid import uuid4

from backend.services.connectors import get_connector_protection_secret, hydrate_outgoing_configuration_from_connector
from backend.services.network import execute_outgoing_test_delivery
from backend.services.automation_execution import (
    utc_now_iso,
    record_outgoing_delivery_history,
    get_database_url,
    render_template_string,
)
from backend.schemas import OutgoingApiTestRequest


def _execute_outbound_request_delivery(
    connection: Any,
    *,
    step: Any,
    context: dict[str, Any],
    root_dir: Path,
    history_resource_id: str | None = None,
) -> tuple[Any, Any, dict[str, Any]]:
    protection_secret = get_connector_protection_secret(root_dir=root_dir)
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        connection,
        connector_id=step.config.connector_id,
        destination_url=render_template_string(step.config.destination_url, context),
        auth_type=step.config.auth_type or "none",
        auth_config=step.config.auth_config,
        protection_secret=protection_secret,
    )
    delivery = execute_outgoing_test_delivery(
        OutgoingApiTestRequest(
            type="outgoing_scheduled",
            destination_url=destination_url,
            http_method=step.config.http_method or "POST",
            auth_type=auth_type,
            auth_config=auth_config,
            webhook_signing=step.config.webhook_signing,
            payload_template=json.dumps({}) if step.config.payload_template is None else step.config.payload_template,
            connector_id=step.config.connector_id,
        )
    )
    response_body_json = None
    try:
        response_body_json = json.loads(delivery.response_body) if delivery.response_body else None
    except Exception:
        response_body_json = None
    extracted_fields = {}
    # Caller may map extracted fields; preserve empty dict here
    if history_resource_id:
        record_outgoing_delivery_history(
            connection,
            delivery_id=f"delivery_{uuid4().hex}",
            resource_type="automation_http_step",
            resource_id=history_resource_id,
            status_value="completed" if delivery.ok else "failed",
            http_status_code=delivery.status_code,
            request_summary=f"{step.config.http_method or 'POST'} {destination_url}",
            response_summary=(delivery.response_body or "")[:500] or f"{delivery.status_code} {destination_url}",
            error_summary=None if delivery.ok else (delivery.response_body or "")[:500],
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
        )
        connection.commit()
    return delivery, response_body_json, extracted_fields


def finalize_non_blocking_http_step(
    *,
    database_url: str,
    logger_name: str,
    run_step_id: str,
    automation_id: str,
    step: Any,
    context: dict[str, Any],
    root_dir: Path,
    delivery_executor=None,
) -> None:
    connection = None
    try:
        from backend.database import connect

        connection = connect(database_url=database_url)
        delivery, response_body_json, extracted_fields = _execute_outbound_request_delivery(
            connection,
            step=step,
            context=context,
            root_dir=root_dir,
            history_resource_id=run_step_id,
        )
        detail = delivery.model_dump()
        detail["response_mode"] = "background"
        detail["response_mappings"] = step.config.response_mappings or []
        record_outgoing_delivery_history(
            connection,
            delivery_id=f"delivery_{uuid4().hex}",
            resource_type="automation_http_step",
            resource_id=run_step_id,
            status_value="completed" if delivery.ok else "failed",
            http_status_code=delivery.status_code,
            request_summary=f"{step.config.http_method or 'POST'} {step.config.destination_url}",
            response_summary=(delivery.response_body or "")[:500] or f"{delivery.status_code} {step.config.destination_url}",
            error_summary=None if delivery.ok else (delivery.response_body or "")[:500],
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
        )
        connection.commit()
    finally:
        if connection:
            connection.close()


def execute_outbound_request_step(
    connection: Any,
    logger: logging.Logger,
    *,
    automation_id: str,
    run_step_id: str | None = None,
    step: Any,
    context: dict[str, Any],
    root_dir: Path,
    database_url: str | None = None,
) -> dict:
    # Materialize http preset if provided
    from backend.services.automation_execution import _materialize_http_preset_config

    if step.config.http_preset_id:
        try:
            step = _materialize_http_preset_config(connection, step=step, context=context)
        except RuntimeError as error:
            return {"error": str(error)}

    if not step.config.wait_for_response:
        if not run_step_id:
            return {"error": "Non-blocking HTTP steps require a runtime step identifier."}
        # Caller (automation_executor) is responsible for submitting background tasks; return the payload needed.
        payload = {
            "database_url": database_url or get_database_url(),
            "logger_name": logger.name,
            "run_step_id": run_step_id,
            "automation_id": automation_id,
            "step": step.model_copy(deep=True),
            "context": json.loads(json.dumps(context)),
            "root_dir": str(root_dir),
        }
        return {"background": payload}

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
    return {"result": {"ok": delivery.ok, "status_code": delivery.status_code, "destination_url": getattr(delivery, "destination_url", None), "detail": detail}}
