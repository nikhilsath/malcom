from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


@router.get("/api/v1/inbound", response_model=list[InboundApiResponse])
def list_inbound_apis(request: Request) -> list[InboundApiResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        WITH filtered_events AS (
            SELECT api_id, event_id, received_at, status
            FROM inbound_api_events
            WHERE is_mock = 0
        ),
        event_aggregates AS (
            SELECT
                api_id,
                COUNT(event_id) AS events_count,
                MAX(received_at) AS last_received_at
            FROM filtered_events
            GROUP BY api_id
        ),
        ranked_events AS (
            SELECT
                api_id,
                status,
                ROW_NUMBER() OVER (PARTITION BY api_id ORDER BY received_at DESC) AS row_number
            FROM filtered_events
        )
        SELECT
            inbound_apis.*,
            COALESCE(event_aggregates.events_count, 0) AS events_count,
            event_aggregates.last_received_at,
            ranked_events.status AS last_delivery_status
        FROM inbound_apis
        LEFT JOIN event_aggregates ON event_aggregates.api_id = inbound_apis.id
        LEFT JOIN ranked_events ON ranked_events.api_id = inbound_apis.id AND ranked_events.row_number = 1
        WHERE inbound_apis.is_mock = 0
        ORDER BY inbound_apis.created_at DESC
        """,
    )
    return [InboundApiResponse(**row_to_api_summary(row)) for row in rows]


@router.post("/api/v1/inbound", response_model=InboundApiCreated, status_code=status.HTTP_201_CREATED)
def create_inbound_api(payload: InboundApiCreate, request: Request) -> InboundApiCreated:
    connection = get_connection(request)
    logger = get_application_logger(request)
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
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

    created = row_to_api_summary(get_api_or_404(connection, api_id))
    created["secret"] = secret
    created["endpoint_url"] = str(request.base_url).rstrip("/") + created["endpoint_path"]
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_created",
        api_id=api_id,
        path_slug=payload.path_slug,
        enabled=payload.enabled,
    )
    return InboundApiCreated(**created)


@router.get("/api/v1/outgoing/scheduled", response_model=list[ApiResourceResponse])
def list_outgoing_scheduled_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, destination_url, http_method, auth_type,
               payload_template, scheduled_time, schedule_expression, status, created_at, updated_at
        FROM outgoing_scheduled_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_scheduled", endpoint_path="/api/v1/outgoing/scheduled"))
        for row in rows
    ]


@router.get("/api/v1/outgoing/continuous", response_model=list[ApiResourceResponse])
def list_outgoing_continuous_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, repeat_interval_minutes, destination_url, http_method, auth_type,
               payload_template, stream_mode, created_at, updated_at
        FROM outgoing_continuous_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_continuous", endpoint_path="/api/v1/outgoing/continuous"))
        for row in rows
    ]


@router.get("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def get_outgoing_api_detail(
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
    request: Request,
) -> OutgoingApiDetailResponse:
    connection = get_connection(request)
    row = get_outgoing_api_or_404(connection, api_id, api_type)
    endpoint_path = "/api/v1/outgoing/scheduled" if api_type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    return row_to_outgoing_detail_response(row, api_type=api_type, endpoint_path=endpoint_path)


@router.get("/api/v1/webhooks", response_model=list[ApiResourceResponse])
def list_webhook_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, callback_path, signature_header, event_filter, verification_token, signing_secret, created_at, updated_at
        FROM webhook_apis
        WHERE is_mock = 0
        ORDER BY created_at DESC
        """,
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="webhook", endpoint_path="/api/v1/webhooks"))
        for row in rows
    ]


@router.post("/api/v1/apis", response_model=ApiResourceResponse, status_code=status.HTTP_201_CREATED)
def create_api_resource(payload: ApiResourceCreate, request: Request) -> ApiResourceResponse:
    connection = get_connection(request)
    now = utc_now_iso()
    config = get_resource_config(payload.type)
    api_id = payload.path_slug.replace("-", "_") + "_" + uuid4().hex[:6]
    validate_outgoing_resource_payload(payload)
    validate_webhook_resource_payload(payload)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)

    try:
        if payload.type == "incoming":
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
        elif payload.type == "outgoing_scheduled":
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
                    build_schedule_expression(payload.scheduled_time or "09:00"),
                    now,
                    now,
                ),
            )
            refresh_outgoing_schedule(connection, api_id)
        elif payload.type == "outgoing_continuous":
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
        else:
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
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

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
    resource["endpoint_url"] = str(request.base_url).rstrip("/") + endpoint_path

    if payload.type == "incoming":
        resource["secret"] = secret
    if payload.type in {"outgoing_scheduled", "outgoing_continuous"}:
        resource["connector_id"] = payload.connector_id

    return ApiResourceResponse(**resource)


@router.post("/api/v1/apis/test-delivery", response_model=OutgoingApiTestResponse)
def test_outgoing_api_delivery(payload: OutgoingApiTestRequest, request: Request) -> OutgoingApiTestResponse:
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        get_connection(request),
        connector_id=payload.connector_id,
        destination_url=payload.destination_url,
        auth_type=payload.auth_type,
        auth_config=payload.auth_config,
        protection_secret=get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path),
    )
    return execute_outgoing_test_delivery(
        OutgoingApiTestRequest(
            **payload.model_dump(exclude={"destination_url", "auth_type", "auth_config"}),
            destination_url=destination_url,
            auth_type=auth_type,
            auth_config=auth_config,
        )
    )


@router.get("/api/v1/inbound/{api_id}", response_model=InboundApiDetail)
def get_inbound_api(api_id: str, request: Request) -> InboundApiDetail:
    connection = get_connection(request)
    return serialize_api_detail(connection, api_id, request)


@router.patch("/api/v1/inbound/{api_id}", response_model=InboundApiResponse)
def update_inbound_api(api_id: str, payload: InboundApiUpdate, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    current = get_api_or_404(connection, api_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        return InboundApiResponse(**row_to_api_summary(current))

    assignments = []
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
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

    updated = row_to_api_summary(get_api_or_404(connection, api_id))
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_updated",
        api_id=api_id,
        changed_fields=sorted(changes.keys()),
    )
    return InboundApiResponse(**updated)


@router.patch("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def update_outgoing_api(api_id: str, payload: OutgoingApiUpdate, request: Request) -> OutgoingApiDetailResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    current = get_outgoing_api_or_404(connection, api_id, payload.type)
    validate_outgoing_update_payload(payload)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        endpoint_path = "/api/v1/outgoing/scheduled" if payload.type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
        return row_to_outgoing_detail_response(current, api_type=payload.type, endpoint_path=endpoint_path)

    assignments = []
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
    table_name = "outgoing_scheduled_apis" if payload.type == "outgoing_scheduled" else "outgoing_continuous_apis"

    try:
        connection.execute(
            f"UPDATE {table_name} SET {', '.join(assignments)} WHERE id = ?",
            tuple(values),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

    updated = get_outgoing_api_or_404(connection, api_id, payload.type)
    endpoint_path = "/api/v1/outgoing/scheduled" if payload.type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    write_application_log(
        logger,
        logging.INFO,
        "outgoing_api_updated",
        api_id=api_id,
        api_type=payload.type,
        changed_fields=sorted(key for key in changes.keys() if key != "type"),
    )
    return row_to_outgoing_detail_response(updated, api_type=payload.type, endpoint_path=endpoint_path)


@router.post("/api/v1/inbound/{api_id}/rotate-secret", response_model=InboundSecretResponse)
def rotate_inbound_api_secret(api_id: str, request: Request) -> InboundSecretResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    api_row = get_api_or_404(connection, api_id)
    secret = generate_secret()
    connection.execute(
        "UPDATE inbound_apis SET secret_hash = ?, updated_at = ? WHERE id = ?",
        (hash_secret(secret), utc_now_iso(), api_row["id"]),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_secret_rotated",
        api_id=api_id,
    )
    return InboundSecretResponse(
        id=api_id,
        secret=secret,
        endpoint_url=str(request.base_url).rstrip("/") + f"/api/v1/inbound/{api_id}",
    )


@router.post("/api/v1/inbound/{api_id}/disable", response_model=InboundApiResponse)
def disable_inbound_api(api_id: str, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    get_api_or_404(connection, api_id)
    connection.execute(
        "UPDATE inbound_apis SET enabled = 0, updated_at = ? WHERE id = ?",
        (utc_now_iso(), api_id),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_disabled",
        api_id=api_id,
    )
    return InboundApiResponse(**row_to_api_summary(get_api_or_404(connection, api_id)))


@router.post("/api/v1/inbound/{api_id}", response_model=InboundReceiveAccepted, status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound_event(api_id: str, request: Request, response: Response) -> InboundReceiveAccepted:
    connection = get_connection(request)
    logger = get_application_logger(request)
    event_id = f"evt_{uuid4().hex[:10]}"
    received_at = utc_now_iso()
    headers = header_subset(request.headers)
    source_ip = request.client.host if request.client else None
    api_row = get_api_or_404(connection, api_id)

    if not api_row["enabled"]:
        log_event(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="disabled",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Inbound API is disabled.",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inbound API is disabled.")

    auth_header = request.headers.get("authorization", "")
    expected_secret_hash = api_row["secret_hash"]

    if not auth_header.startswith("Bearer "):
        log_event(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unauthorized",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Missing bearer token.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    provided_secret = auth_header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(hash_secret(provided_secret), expected_secret_hash):
        log_event(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unauthorized",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Invalid bearer token.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")

    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        log_event(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unsupported_media_type",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Only application/json is supported.",
        )
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only application/json is supported.")

    try:
        payload = await request.json()
    except json.JSONDecodeError as error:
        log_event(
            connection,
            logger,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="invalid_json",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message=str(error),
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid JSON payload.") from error

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
    matching_automations = fetch_all(
        connection,
        """
        SELECT id
        FROM automations
        WHERE enabled = 1
          AND trigger_type = 'inbound_api'
          AND json_extract(trigger_config_json, '$.inbound_api_id') = ?
        ORDER BY created_at ASC
        """,
        (api_id,),
    )
    for automation_row in matching_automations:
        execute_automation_definition(
            connection,
            logger,
            automation_id=automation_row["id"],
            trigger_type="inbound_api",
            payload=payload if isinstance(payload, dict) else {"payload": payload},
            root_dir=get_root_dir(request),
        )

    response.headers["X-Malcom-Event-Id"] = event_id
    return InboundReceiveAccepted(
        status="accepted",
        event_id=event_id,
        trigger={
            "type": trigger.type,
            "api_id": trigger.api_id,
            "event_id": trigger.event_id,
            "payload": trigger.payload,
            "received_at": trigger.received_at,
        },
    )
