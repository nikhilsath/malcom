from __future__ import annotations

from dataclasses import dataclass
import hmac
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi import HTTPException, Request, status

from backend.database import is_unique_violation
from backend.runtime import RuntimeTrigger
from backend.schemas.apis import (
    ApiResourceCreate,
    ApiResourceResponse,
    ContinuousApiResourceCreate,
    InboundApiCreate,
    InboundApiCreated,
    InboundApiResponse,
    InboundApiUpdate,
    InboundReceiveAccepted,
    IncomingApiResourceCreate,
    OutgoingApiDetailResponse,
    OutgoingApiUpdate,
    OutgoingAuthConfig,
    ScheduledApiResourceCreate,
    WebhookApiResourceCreate,
)
from backend.services.support import *


JsonLoader = Callable[[], Awaitable[Any]]


@dataclass(frozen=True)
class OutgoingApiUpdateResult:
    detail: OutgoingApiDetailResponse
    changed_fields: list[str]


@dataclass(frozen=True)
class InboundReceiveResult:
    accepted: InboundReceiveAccepted
    event_id: str


def _raise_path_slug_conflict(error: Exception) -> None:
    if is_unique_violation(error):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error


def create_inbound_api_record(
    connection: Any,
    *,
    payload: InboundApiCreate,
    base_url: str,
    logger: Any,
) -> InboundApiCreated:
    now = utc_now_iso()
    api_id = payload.path_slug.replace("-", "_") + "_" + uuid4().hex[:6]
    secret = generate_secret()

    try:
        connection.execute(
            """
            INSERT INTO inbound_apis (
                id,
                name,
                description,
                path_slug,
                auth_type,
                secret_hash,
                is_mock,
                enabled,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                api_id,
                payload.name,
                payload.description,
                payload.path_slug,
                "bearer",
                hash_secret(secret),
                0,
                int(payload.enabled),
                now,
                now,
            ),
        )
        connection.commit()
    except Exception as error:
        _raise_path_slug_conflict(error)
        raise

    created = row_to_api_summary(get_api_or_404(connection, api_id))
    created["secret"] = secret
    created["endpoint_url"] = base_url + created["endpoint_path"]
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_created",
        api_id=api_id,
        path_slug=payload.path_slug,
        enabled=payload.enabled,
    )
    return InboundApiCreated(**created)


def create_api_resource_record(
    connection: Any,
    *,
    payload: ApiResourceCreate,
    base_url: str,
    root_dir: Path,
    db_path: str | None,
) -> ApiResourceResponse:
    try:
        return create_api_resource_response(
            connection,
            payload,
            request_base_url=base_url,
            now=utc_now_iso(),
            protection_secret=get_connector_protection_secret(root_dir=root_dir, db_path=db_path),
        )
    except Exception as error:
        _raise_path_slug_conflict(error)
        raise


def create_api_resource_response(
    connection: Any,
    payload: ApiResourceCreate,
    *,
    request_base_url: str,
    now: str,
    protection_secret: str,
) -> ApiResourceResponse:
    config = get_resource_config(payload.type)
    api_id = payload.path_slug.replace("-", "_") + "_" + uuid4().hex[:6]

    validate_outgoing_resource_payload(payload)
    validate_webhook_resource_payload(payload)

    secret: str | None = None
    connector_id: str | None = None

    if payload.type == "incoming":
        secret = _create_incoming_api_resource(connection, api_id, payload, now=now)
    elif payload.type == "outgoing_scheduled":
        connector_id = payload.connector_id
        _create_outgoing_scheduled_api_resource(
            connection,
            api_id,
            payload,
            now=now,
            protection_secret=protection_secret,
        )
    elif payload.type == "outgoing_continuous":
        connector_id = payload.connector_id
        _create_outgoing_continuous_api_resource(
            connection,
            api_id,
            payload,
            now=now,
            protection_secret=protection_secret,
        )
    else:
        _create_webhook_api_resource(connection, api_id, payload, now=now)

    connection.commit()

    row = fetch_one(
        connection,
        f"""
        SELECT *
        FROM {config['table']}
        WHERE id = ?
        """,
        (api_id,),
    )
    assert row is not None

    endpoint_path = config["path_prefix"] if payload.type != "incoming" else f"/api/v1/inbound/{api_id}"
    resource = row_to_simple_api_resource(row, api_type=payload.type, endpoint_path=endpoint_path)
    resource["endpoint_url"] = request_base_url.rstrip("/") + endpoint_path

    if secret is not None:
        resource["secret"] = secret
    if connector_id is not None:
        resource["connector_id"] = connector_id

    return ApiResourceResponse(**resource)


def update_outgoing_api_response(
    connection: Any,
    api_id: str,
    payload: OutgoingApiUpdate,
) -> OutgoingApiUpdateResult:
    current = get_outgoing_api_or_404(connection, api_id, payload.type)
    validate_outgoing_update_payload(payload)
    changes = payload.model_dump(exclude_unset=True)
    endpoint_path = "/api/v1/outgoing/scheduled" if payload.type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"

    if not changes:
        return OutgoingApiUpdateResult(
            detail=row_to_outgoing_detail_response(current, api_type=payload.type, endpoint_path=endpoint_path),
            changed_fields=[],
        )

    assignments, values = _build_outgoing_update_statement(payload, api_id, changes)
    table_name = "outgoing_scheduled_apis" if payload.type == "outgoing_scheduled" else "outgoing_continuous_apis"

    connection.execute(
        f"UPDATE {table_name} SET {', '.join(assignments)} WHERE id = ?",
        tuple(values),
    )
    connection.commit()

    updated = get_outgoing_api_or_404(connection, api_id, payload.type)
    return OutgoingApiUpdateResult(
        detail=row_to_outgoing_detail_response(updated, api_type=payload.type, endpoint_path=endpoint_path),
        changed_fields=sorted(key for key in changes.keys() if key != "type"),
    )


def update_inbound_api_record(
    connection: Any,
    *,
    api_id: str,
    payload: InboundApiUpdate,
    logger: Any,
) -> InboundApiResponse:
    current = get_api_or_404(connection, api_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        return InboundApiResponse(**row_to_api_summary(current))

    assignments: list[str] = []
    values: list[Any] = []
    for key, value in changes.items():
        assignments.append(f"{key} = ?")
        values.append(value)

    assignments.append("updated_at = ?")
    values.append(utc_now_iso())
    values.append(api_id)

    try:
        connection.execute(
            f"UPDATE inbound_apis SET {', '.join(assignments)} WHERE id = ?",
            tuple(values),
        )
        connection.commit()
    except Exception as error:
        _raise_path_slug_conflict(error)
        raise

    updated = row_to_api_summary(get_api_or_404(connection, api_id))
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_updated",
        api_id=api_id,
        changed_fields=sorted(changes.keys()),
    )
    return InboundApiResponse(**updated)


def update_outgoing_api_record(
    connection: Any,
    *,
    api_id: str,
    payload: OutgoingApiUpdate,
    logger: Any,
) -> OutgoingApiDetailResponse:
    try:
        result = update_outgoing_api_response(connection, api_id, payload)
    except Exception as error:
        _raise_path_slug_conflict(error)
        raise

    write_application_log(
        logger,
        logging.INFO,
        "outgoing_api_updated",
        api_id=api_id,
        api_type=payload.type,
        changed_fields=result.changed_fields,
    )
    return result.detail


async def receive_inbound_event_result(
    connection: Any,
    logger: Any,
    *,
    api_id: str,
    authorization_header: str,
    content_type: str,
    headers: dict[str, str],
    source_ip: str | None,
    load_json: JsonLoader,
    root_dir: Path,
    database_url: str,
) -> InboundReceiveResult:
    event_id = f"evt_{uuid4().hex[:10]}"
    received_at = utc_now_iso()
    api_row = get_api_or_404(connection, api_id)

    if not api_row["enabled"]:
        _log_and_raise_inbound_event_error(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_code=status.HTTP_409_CONFLICT,
            status_value="disabled",
            detail="Inbound API is disabled.",
            headers=headers,
            source_ip=source_ip,
            error_message="Inbound API is disabled.",
        )

    if not authorization_header.startswith("Bearer "):
        _log_and_raise_inbound_event_error(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_code=status.HTTP_401_UNAUTHORIZED,
            status_value="unauthorized",
            detail="Missing bearer token.",
            headers=headers,
            source_ip=source_ip,
            error_message="Missing bearer token.",
        )

    provided_secret = authorization_header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(hash_secret(provided_secret), api_row["secret_hash"]):
        _log_and_raise_inbound_event_error(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_code=status.HTTP_401_UNAUTHORIZED,
            status_value="unauthorized",
            detail="Invalid bearer token.",
            headers=headers,
            source_ip=source_ip,
            error_message="Invalid bearer token.",
        )

    if content_type.split(";")[0].strip() != "application/json":
        _log_and_raise_inbound_event_error(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status_value="unsupported_media_type",
            detail="Only application/json is supported.",
            headers=headers,
            source_ip=source_ip,
            error_message="Only application/json is supported.",
        )

    try:
        payload = await load_json()
    except json.JSONDecodeError as error:
        _log_and_raise_inbound_event_error(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            status_value="invalid_json",
            detail="Invalid JSON payload.",
            headers=headers,
            source_ip=source_ip,
            error_message=str(error),
        )

    log_event(
        connection,
        logger,
        event_id=event_id,
        api_id=api_id,
        received_at=received_at,
        status_value="accepted",
        headers=headers,
        payload=payload,
        source_ip=source_ip,
        error_message=None,
    )

    trigger = RuntimeTrigger(
        type="inbound_api",
        api_id=api_id,
        event_id=event_id,
        payload=payload,
        received_at=received_at,
    )

    _queue_runtime_trigger(connection, logger, api_id=api_id, event_id=event_id, received_at=received_at, trigger=trigger)
    _execute_matching_inbound_automations(
        connection,
        logger,
        api_id=api_id,
        payload=payload,
        root_dir=root_dir,
        database_url=database_url,
    )

    return InboundReceiveResult(
        event_id=event_id,
        accepted=InboundReceiveAccepted(
            status="accepted",
            event_id=event_id,
            trigger={
                "type": trigger.type,
                "api_id": trigger.api_id,
                "event_id": trigger.event_id,
                "payload": trigger.payload,
                "received_at": trigger.received_at,
            },
        ),
    )


async def receive_inbound_api_event(
    connection: Any,
    *,
    api_id: str,
    request: Request,
    logger: Any,
    root_dir: Path,
    database_url: str,
) -> InboundReceiveResult:
    return await receive_inbound_event_result(
        connection,
        logger,
        api_id=api_id,
        authorization_header=request.headers.get("authorization", ""),
        content_type=request.headers.get("content-type", ""),
        headers=header_subset(request.headers),
        source_ip=request.client.host if request.client else None,
        load_json=request.json,
        root_dir=root_dir,
        database_url=database_url,
    )


def _create_incoming_api_resource(
    connection: Any,
    api_id: str,
    payload: IncomingApiResourceCreate,
    *,
    now: str,
) -> str:
    secret = generate_secret()
    connection.execute(
        """
        INSERT INTO inbound_apis (
            id,
            name,
            description,
            path_slug,
            auth_type,
            secret_hash,
            is_mock,
            enabled,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            api_id,
            payload.name,
            payload.description,
            payload.path_slug,
            "bearer",
            hash_secret(secret),
            0,
            int(payload.enabled),
            now,
            now,
        ),
    )
    return secret


def _create_outgoing_scheduled_api_resource(
    connection: Any,
    api_id: str,
    payload: ScheduledApiResourceCreate,
    *,
    now: str,
    protection_secret: str,
) -> None:
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        connection,
        connector_id=payload.connector_id,
        destination_url=payload.destination_url,
        auth_type=payload.auth_type or "none",
        auth_config=payload.auth_config,
        protection_secret=protection_secret,
    )
    connection.execute(
        """
        INSERT INTO outgoing_scheduled_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            status,
            repeat_enabled,
            destination_url,
            http_method,
            auth_type,
            auth_config_json,
            payload_template,
            scheduled_time,
            schedule_expression,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            api_id,
            payload.name,
            payload.description,
            payload.path_slug,
            0,
            int(payload.enabled),
            "active" if payload.enabled else "paused",
            int(payload.repeat_enabled),
            destination_url,
            payload.http_method,
            auth_type,
            json.dumps((auth_config or OutgoingAuthConfig()).model_dump()),
            payload.payload_template,
            payload.scheduled_time,
            build_schedule_expression(payload.scheduled_time),
            now,
            now,
        ),
    )
    refresh_outgoing_schedule(connection, api_id)


def _create_outgoing_continuous_api_resource(
    connection: Any,
    api_id: str,
    payload: ContinuousApiResourceCreate,
    *,
    now: str,
    protection_secret: str,
) -> None:
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        connection,
        connector_id=payload.connector_id,
        destination_url=payload.destination_url,
        auth_type=payload.auth_type or "none",
        auth_config=payload.auth_config,
        protection_secret=protection_secret,
    )
    connection.execute(
        """
        INSERT INTO outgoing_continuous_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            repeat_enabled,
            repeat_interval_minutes,
            destination_url,
            http_method,
            auth_type,
            auth_config_json,
            payload_template,
            stream_mode,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            api_id,
            payload.name,
            payload.description,
            payload.path_slug,
            0,
            int(payload.enabled),
            int(payload.repeat_enabled),
            payload.repeat_interval_minutes,
            destination_url,
            payload.http_method,
            auth_type,
            json.dumps((auth_config or OutgoingAuthConfig()).model_dump()),
            payload.payload_template,
            "continuous",
            now,
            now,
        ),
    )


def _create_webhook_api_resource(
    connection: Any,
    api_id: str,
    payload: WebhookApiResourceCreate,
    *,
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO webhook_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            delivery_mode,
            callback_path,
            verification_token,
            signing_secret,
            signature_header,
            event_filter,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            api_id,
            payload.name,
            payload.description,
            payload.path_slug,
            0,
            int(payload.enabled),
            "webhook",
            payload.callback_path.strip() if payload.callback_path else "",
            payload.verification_token,
            payload.signing_secret,
            payload.signature_header.strip() if payload.signature_header else "",
            payload.event_filter.strip() if payload.event_filter else "",
            now,
            now,
        ),
    )


def _build_outgoing_update_statement(
    payload: OutgoingApiUpdate,
    api_id: str,
    changes: dict[str, Any],
) -> tuple[list[str], list[Any]]:
    assignments: list[str] = []
    values: list[Any] = []

    for key, value in changes.items():
        if key == "type":
            continue

        if key == "auth_config":
            assignments.append("auth_config_json = ?")
            if isinstance(value, dict):
                values.append(json.dumps(value))
            else:
                values.append(json.dumps((value or OutgoingAuthConfig()).model_dump()))
            continue

        if key == "repeat_enabled":
            assignments.append("repeat_enabled = ?")
            values.append(int(value))
            continue

        if key == "enabled":
            assignments.append("enabled = ?")
            values.append(int(value))
            if payload.type == "outgoing_scheduled":
                assignments.append("status = ?")
                values.append("active" if value else "paused")
            continue

        if key == "scheduled_time" and payload.type == "outgoing_scheduled" and value is not None:
            assignments.append("scheduled_time = ?")
            values.append(value)
            assignments.append("schedule_expression = ?")
            values.append(build_schedule_expression(value))
            continue

        assignments.append(f"{key} = ?")
        values.append(value)

    if payload.type == "outgoing_continuous" and changes.get("repeat_enabled") is False and "repeat_interval_minutes" not in changes:
        assignments.append("repeat_interval_minutes = ?")
        values.append(None)

    assignments.append("updated_at = ?")
    values.append(utc_now_iso())
    values.append(api_id)
    return assignments, values


def _log_and_raise_inbound_event_error(
    connection: Any,
    logger: Any,
    *,
    event_id: str,
    api_id: str,
    received_at: str,
    status_code: int,
    status_value: str,
    detail: str,
    headers: dict[str, str],
    source_ip: str | None,
    error_message: str,
) -> None:
    log_event(
        connection,
        logger,
        event_id=event_id,
        api_id=api_id,
        received_at=received_at,
        status_value=status_value,
        headers=headers,
        payload=None,
        source_ip=source_ip,
        error_message=error_message,
    )
    raise HTTPException(status_code=status_code, detail=detail)


def _queue_runtime_trigger(
    connection: Any,
    logger: Any,
    *,
    api_id: str,
    event_id: str,
    received_at: str,
    trigger: RuntimeTrigger,
) -> None:
    run_id = f"run_{uuid4().hex}"
    step_id = f"step_{uuid4().hex}"
    job_id = f"job_{uuid4().hex}"
    create_automation_run(
        connection,
        run_id=run_id,
        automation_id=api_id,
        trigger_type=trigger.type,
        status_value="queued",
        started_at=received_at,
    )
    create_automation_run_step(
        connection,
        step_id=step_id,
        run_id=run_id,
        step_name="emit_runtime_trigger",
        status_value="pending",
        request_summary=f"event_id={event_id}",
        started_at=received_at,
    )
    runtime_event_bus.emit(trigger, job_id=job_id, run_id=run_id, step_id=step_id)
    write_application_log(
        logger,
        logging.INFO,
        "runtime_trigger_queued",
        api_id=api_id,
        event_id=event_id,
        trigger_type=trigger.type,
        run_id=run_id,
        job_id=job_id,
    )


def _execute_matching_inbound_automations(
    connection: Any,
    logger: Any,
    *,
    api_id: str,
    payload: Any,
    root_dir: Path,
    database_url: str,
) -> None:
    matching_automations = []
    for automation_row in fetch_all(
        connection,
        """
        SELECT id, trigger_config_json
        FROM automations
        WHERE enabled = 1
          AND trigger_type = 'inbound_api'
        ORDER BY created_at ASC
        """,
    ):
        try:
            trigger_config = json.loads(automation_row["trigger_config_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if trigger_config.get("inbound_api_id") == api_id:
            matching_automations.append(automation_row)

    for automation_row in matching_automations:
        execute_automation_definition(
            connection,
            logger,
            automation_id=automation_row["id"],
            trigger_type="inbound_api",
            payload=payload if isinstance(payload, dict) else {"payload": payload},
            root_dir=root_dir,
            database_url=database_url,
        )


__all__ = [
    "InboundReceiveResult",
    "OutgoingApiUpdateResult",
    "create_api_resource_record",
    "create_api_resource_response",
    "create_inbound_api_record",
    "receive_inbound_api_event",
    "receive_inbound_event_result",
    "update_inbound_api_record",
    "update_outgoing_api_record",
    "update_outgoing_api_response",
]
