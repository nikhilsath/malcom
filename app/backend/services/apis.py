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
    OutgoingWebhookSigningConfig,
    ScheduledApiResourceCreate,
    WebhookApiResourceCreate,
)
from backend.services.support import *
from backend.services.github_webhook import dispatch_normalized_event, extract_delivery_id, normalize_github_event


JsonLoader = Callable[[], Awaitable[Any]]


@dataclass(frozen=True)
class OutgoingApiUpdateResult:
    detail: OutgoingApiDetailResponse
    changed_fields: list[str]


@dataclass(frozen=True)
class InboundReceiveResult:
    accepted: InboundReceiveAccepted
    event_id: str


@dataclass(frozen=True)
class WebhookReceiveResult:
    accepted: InboundReceiveAccepted
    event_id: str


def _payload_redaction_enabled(connection: Any) -> bool:
    data_settings = read_stored_settings_section(connection, "data") or {}
    configured = data_settings.get("payload_redaction")
    return True if not isinstance(configured, bool) else configured


def _redact_stored_event_samples(
    connection: Any,
    *,
    headers: dict[str, str] | None,
    payload: Any,
    raw_body: str | None = None,
) -> tuple[dict[str, str] | None, Any, str | None]:
    enabled = _payload_redaction_enabled(connection)
    redacted_headers = redact_sensitive_payload_sample(headers, enabled=enabled) if headers is not None else None
    redacted_payload = redact_sensitive_payload_sample(payload, enabled=enabled)
    redacted_raw_body = raw_body
    if enabled and raw_body is not None and isinstance(payload, (dict, list)):
        try:
            redacted_raw_body = json.dumps(redacted_payload)
        except (TypeError, ValueError):
            redacted_raw_body = raw_body
    return redacted_headers, redacted_payload, redacted_raw_body


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

    if payload.type == "incoming":
        endpoint_path = f"/api/v1/inbound/{api_id}"
    elif payload.type == "webhook":
        endpoint_path = row["callback_path"]
    else:
        endpoint_path = config["path_prefix"]
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
            detail=row_to_outgoing_detail_response(current, api_type=payload.type, endpoint_path=endpoint_path, connection=connection),
            changed_fields=[],
        )

    assignments, values = _build_outgoing_update_statement(payload, api_id, changes)
    table_name = "outgoing_scheduled_apis" if payload.type == "outgoing_scheduled" else "outgoing_continuous_apis"

    connection.execute(
        f"UPDATE {table_name} SET {', '.join(assignments)} WHERE id = ?",
        tuple(values),
    )
    connection.commit()
    if payload.type == "outgoing_scheduled":
        refresh_outgoing_schedule(connection, api_id)
    else:
        refresh_continuous_outgoing_schedule(connection, api_id)

    updated = get_outgoing_api_or_404(connection, api_id, payload.type)
    return OutgoingApiUpdateResult(
        detail=row_to_outgoing_detail_response(updated, api_type=payload.type, endpoint_path=endpoint_path, connection=connection),
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
    refresh_continuous_outgoing_schedule(connection, api_id)
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

    redacted_headers, redacted_payload, _ = _redact_stored_event_samples(
        connection,
        headers=headers,
        payload=payload,
    )
    log_event(
        connection,
        logger,
        event_id=event_id,
        api_id=api_id,
        received_at=received_at,
        status_value="accepted",
        headers=redacted_headers or {},
        payload=redacted_payload,
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


def get_webhook_api_or_404(connection: Any, api_id: str) -> dict[str, Any]:
    row = fetch_one(connection, "SELECT * FROM webhook_apis WHERE id = ?", (api_id,))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook API not found.")
    return dict(row)


def _infer_webhook_event_name(headers: dict[str, str], payload: Any) -> str | None:
    for header_name in ("x-event-name", "x-github-event", "x-event-type"):
        if headers.get(header_name):
            return str(headers[header_name])
    if isinstance(payload, dict):
        for key in ("event", "type", "event_name"):
            if payload.get(key):
                return str(payload[key])
    return None


def _normalize_signature_value(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith("sha256="):
        return normalized.split("=", 1)[1]
    return normalized


def log_webhook_event(
    connection: Any,
    *,
    event_id: str,
    api_id: str,
    received_at: str,
    status_value: str,
    event_name: str | None,
    delivery_id: str | None = None,
    verification_ok: bool,
    signature_ok: bool,
    headers: dict[str, str],
    payload: Any,
    raw_body: str,
    source_ip: str | None,
    error_message: str | None,
    triggered_automation_count: int = 0,
) -> None:
    redacted_headers, redacted_payload, redacted_raw_body = _redact_stored_event_samples(
        connection,
        headers=headers,
        payload=payload,
        raw_body=raw_body,
    )
    connection.execute(
        """
        INSERT INTO webhook_api_events (
            event_id,
            api_id,
            received_at,
            status,
            event_name,
            delivery_id,
            verification_ok,
            signature_ok,
            request_headers_subset,
            payload_json,
            raw_body,
            source_ip,
            error_message,
            triggered_automation_count,
            is_mock
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            api_id,
            received_at,
            status_value,
            event_name,
            delivery_id,
            int(verification_ok),
            int(signature_ok),
            json.dumps(redacted_headers),
            json.dumps(redacted_payload) if redacted_payload is not None else None,
            redacted_raw_body,
            source_ip,
            error_message,
            triggered_automation_count,
            0,
        ),
    )
    connection.commit()


def _execute_matching_webhook_automations(
    connection: Any,
    logger: Any,
    *,
    api_id: str,
    payload: dict[str, Any],
    root_dir: Path,
    database_url: str,
) -> int:
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
            payload=payload,
            root_dir=root_dir,
            database_url=database_url,
        )
    return len(matching_automations)


async def receive_webhook_event(
    connection: Any,
    *,
    api_row: dict[str, Any],
    request: Request,
    logger: Any,
    root_dir: Path,
    database_url: str,
) -> WebhookReceiveResult:
    event_id = f"webhook_event_{uuid4().hex}"
    received_at = utc_now_iso()
    headers = {str(key).lower(): str(value) for key, value in request.headers.items()}
    source_ip = request.client.host if request.client else None
    raw_body_bytes = await request.body()
    raw_body = raw_body_bytes.decode("utf-8", errors="replace")
    payload: Any = None
    error_message: str | None = None

    content_type = str(request.headers.get("content-type") or "")
    if content_type.split(";")[0].strip() == "application/json":
        try:
            payload = json.loads(raw_body) if raw_body else None
        except json.JSONDecodeError as error:
            error_message = f"Invalid JSON payload: {error}"

    verification_token = str(api_row.get("verification_token") or "")
    received_verification_token = (
        str(request.headers.get("x-malcom-verification-token") or "").strip()
        or str(request.query_params.get("verification_token") or "").strip()
    )
    verification_ok = bool(verification_token) and hmac.compare_digest(received_verification_token, verification_token)

    signature_header_name = str(api_row.get("signature_header") or "").strip()
    received_signature = str(request.headers.get(signature_header_name) or "").strip() if signature_header_name else ""
    expected_signature = hmac.new(
        str(api_row.get("signing_secret") or "").encode("utf-8"),
        raw_body_bytes,
        "sha256",
    ).hexdigest()
    signature_ok = bool(received_signature) and hmac.compare_digest(
        _normalize_signature_value(received_signature),
        expected_signature,
    )
    event_name = _infer_webhook_event_name(headers, payload)

    # Extract GitHub delivery id for dedupe/audit when present
    delivery_id: str | None = None
    try:
        delivery_id = extract_delivery_id(headers)
    except Exception:
        delivery_id = None

    if not verification_ok:
        log_webhook_event(
            connection,
            event_id=event_id,
            api_id=api_row["id"],
            received_at=received_at,
            status_value="invalid_verification",
            event_name=event_name,
            delivery_id=delivery_id,
            verification_ok=False,
            signature_ok=signature_ok,
            headers=header_subset(request.headers),
            payload=payload,
            raw_body=raw_body,
            source_ip=source_ip,
            error_message="Webhook verification token did not match.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook verification token did not match.")

    if not signature_ok:
        log_webhook_event(
            connection,
            event_id=event_id,
            api_id=api_row["id"],
            received_at=received_at,
            status_value="invalid_signature",
            event_name=event_name,
            delivery_id=delivery_id,
            verification_ok=True,
            signature_ok=False,
            headers=header_subset(request.headers),
            payload=payload,
            raw_body=raw_body,
            source_ip=source_ip,
            error_message="Webhook signature did not match.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook signature did not match.")

    event_filter = str(api_row.get("event_filter") or "").strip()
    if event_filter and event_name != event_filter:
        log_webhook_event(
            connection,
            event_id=event_id,
            api_id=api_row["id"],
            received_at=received_at,
            status_value="ignored",
            event_name=event_name,
            delivery_id=delivery_id,
            verification_ok=True,
            signature_ok=True,
            headers=header_subset(request.headers),
            payload=payload,
            raw_body=raw_body,
            source_ip=source_ip,
            error_message=f"Event '{event_name or ''}' did not match filter '{event_filter}'.",
        )
        return WebhookReceiveResult(
            event_id=event_id,
            accepted=InboundReceiveAccepted(
                status="ignored",
                event_id=event_id,
                trigger={"type": "webhook", "api_id": api_row["id"], "event_id": event_id, "payload": None, "received_at": received_at},
            ),
        )

    webhook_payload = {
        "headers": header_subset(request.headers),
        "raw_body": raw_body,
        "parsed_json": payload if isinstance(payload, (dict, list)) else None,
        "event_name": event_name,
        "verification_ok": verification_ok,
        "signature_ok": signature_ok,
        "callback_path": api_row.get("callback_path") or "",
        "delivery_id": delivery_id,
    }
    normalized_metadata: dict[str, Any] | None = None
    # Attach normalized GitHub event if this looks like a GitHub delivery
    try:
        if event_name and (str(event_name).lower() in ("push", "pull_request") or headers.get("x-github-event")):
            normalized, metadata = normalize_github_event(payload if isinstance(payload, dict) else {}, str(event_name or ""))
            webhook_payload["normalized"] = normalized
            webhook_payload["normalized_metadata"] = metadata
            normalized_metadata = metadata
    except Exception:
        # Normalization must not break webhook processing; log and continue.
        try:
            write_application_log(logger, logging.WARNING, "github_normalize_failed", api_id=api_row.get("id"), event_name=event_name)
        except Exception:
            pass

    # Deduplicate by delivery id when possible. If the schema hasn't been migrated yet,
    # the SELECT may fail — swallow errors and continue to avoid blocking webhook processing.
    if delivery_id:
        try:
            existing = fetch_one(connection, "SELECT event_id FROM webhook_api_events WHERE delivery_id = ? LIMIT 1", (delivery_id,))
        except Exception:
            existing = None
        if existing:
            log_webhook_event(
                connection,
                event_id=event_id,
                api_id=api_row["id"],
                received_at=received_at,
                status_value="duplicate",
                event_name=event_name,
                delivery_id=delivery_id,
                verification_ok=verification_ok,
                signature_ok=signature_ok,
                headers=header_subset(request.headers),
                payload=payload,
                raw_body=raw_body,
                source_ip=source_ip,
                error_message="Duplicate delivery id",
            )
            return WebhookReceiveResult(
                event_id=event_id,
                accepted=InboundReceiveAccepted(
                    status="duplicate",
                    event_id=event_id,
                    trigger={"type": "webhook", "api_id": api_row["id"], "event_id": event_id, "payload": None, "received_at": received_at},
                ),
            )
    inbound_trigger_count = _execute_matching_webhook_automations(
        connection,
        logger,
        api_id=api_row["id"],
        payload=webhook_payload,
        root_dir=root_dir,
        database_url=database_url,
    )
    github_trigger_count = 0
    if isinstance(webhook_payload.get("normalized"), dict) and isinstance(normalized_metadata, dict):
        github_trigger_count = dispatch_normalized_event(
            connection,
            logger,
            webhook_payload["normalized"],
            normalized_metadata,
            root_dir=root_dir,
            database_url=database_url,
        )
    triggered_automation_count = inbound_trigger_count + github_trigger_count
    log_webhook_event(
        connection,
        event_id=event_id,
        api_id=api_row["id"],
        received_at=received_at,
        status_value="accepted",
        event_name=event_name,
        delivery_id=delivery_id,
        verification_ok=True,
        signature_ok=True,
        headers=header_subset(request.headers),
        payload=payload,
        raw_body=raw_body,
        source_ip=source_ip,
        error_message=error_message,
        triggered_automation_count=triggered_automation_count,
    )
    return WebhookReceiveResult(
        event_id=event_id,
        accepted=InboundReceiveAccepted(
            status="accepted",
            event_id=event_id,
            trigger={
                "type": "webhook",
                "api_id": api_row["id"],
                "event_id": event_id,
                "payload": webhook_payload,
                "received_at": received_at,
            },
        ),
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
    refresh_continuous_outgoing_schedule(connection, api_id)
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
            webhook_signing_json,
            payload_template,
            scheduled_time,
            schedule_expression,
            last_run_at,
            next_run_at,
            last_error,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps((payload.webhook_signing or OutgoingWebhookSigningConfig()).model_dump()),
            payload.payload_template,
            payload.scheduled_time,
            build_schedule_expression(payload.scheduled_time),
            None,
            None,
            None,
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
            webhook_signing_json,
            payload_template,
            stream_mode,
            last_run_at,
            next_run_at,
            last_error,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps((payload.webhook_signing or OutgoingWebhookSigningConfig()).model_dump()),
            payload.payload_template,
            "continuous",
            None,
            None,
            None,
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

        if key == "webhook_signing":
            assignments.append("webhook_signing_json = ?")
            if isinstance(value, dict):
                values.append(json.dumps(value))
            else:
                values.append(json.dumps((value or OutgoingWebhookSigningConfig()).model_dump()))
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
    redacted_headers, _, _ = _redact_stored_event_samples(
        connection,
        headers=headers,
        payload=None,
    )
    log_event(
        connection,
        logger,
        event_id=event_id,
        api_id=api_id,
        received_at=received_at,
        status_value=status_value,
        headers=redacted_headers or {},
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
    "WebhookReceiveResult",
    "create_api_resource_record",
    "create_api_resource_response",
    "create_inbound_api_record",
    "get_webhook_api_or_404",
    "log_webhook_event",
    "receive_inbound_api_event",
    "receive_inbound_event_result",
    "receive_webhook_event",
    "update_inbound_api_record",
    "update_outgoing_api_record",
    "update_outgoing_api_response",
]
