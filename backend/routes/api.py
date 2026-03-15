from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()

@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/api/v1/runtime/status", response_model=RuntimeStatusResponse)
def get_runtime_status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse(**runtime_scheduler.status())

@router.get("/api/v1/scheduler/jobs")
def get_scheduler_jobs(request: Request) -> list[dict[str, Any]]:
    refresh_scheduler_jobs(get_connection(request))
    return runtime_scheduler.jobs()

@router.get("/api/v1/automations", response_model=list[AutomationSummaryResponse])
def list_automations(request: Request) -> list[AutomationSummaryResponse]:
    rows = fetch_all(
        get_connection(request),
        """
        SELECT
            automations.*,
            COUNT(automation_steps.step_id) AS step_count
        FROM automations
        LEFT JOIN automation_steps ON automation_steps.automation_id = automations.id
        GROUP BY automations.id
        ORDER BY automations.created_at DESC
        """,
    )
    return [AutomationSummaryResponse(**row_to_automation_summary(row)) for row in rows]

@router.post("/api/v1/automations", response_model=AutomationDetailResponse, status_code=status.HTTP_201_CREATED)
def create_automation(payload: AutomationCreate, request: Request) -> AutomationDetailResponse:
    issues = validate_automation_definition(payload, require_steps=True)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))

    connection = get_connection(request)
    now = utc_now_iso()
    automation_id = f"automation_{uuid4().hex[:10]}"
    trigger_config = payload.trigger_config.model_dump()
    next_run_at = None
    if payload.enabled and payload.trigger_type == "schedule" and payload.trigger_config.schedule_time:
        next_run_at = next_daily_run_at(payload.trigger_config.schedule_time)

    connection.execute(
        """
        INSERT INTO automations (
            id,
            name,
            description,
            enabled,
            trigger_type,
            trigger_config_json,
            created_at,
            updated_at,
            last_run_at,
            next_run_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (
            automation_id,
            payload.name,
            payload.description,
            int(payload.enabled),
            payload.trigger_type,
            json.dumps(trigger_config),
            now,
            now,
            next_run_at,
        ),
    )
    replace_automation_steps(connection, automation_id, payload.steps, timestamp=now)
    connection.commit()
    refresh_scheduler_jobs(connection)
    return serialize_automation_detail(connection, automation_id)

@router.get("/api/v1/automations/{automation_id}", response_model=AutomationDetailResponse)
def get_automation(automation_id: str, request: Request) -> AutomationDetailResponse:
    return serialize_automation_detail(get_connection(request), automation_id)

@router.patch("/api/v1/automations/{automation_id}", response_model=AutomationDetailResponse)
def update_automation(automation_id: str, payload: AutomationUpdate, request: Request) -> AutomationDetailResponse:
    connection = get_connection(request)
    current = serialize_automation_detail(connection, automation_id)
    next_payload = AutomationCreate(
        name=payload.name if payload.name is not None else current.name,
        description=payload.description if payload.description is not None else current.description,
        enabled=payload.enabled if payload.enabled is not None else current.enabled,
        trigger_type=payload.trigger_type if payload.trigger_type is not None else current.trigger_type,
        trigger_config=payload.trigger_config if payload.trigger_config is not None else current.trigger_config,
        steps=payload.steps if payload.steps is not None else current.steps,
    )
    issues = validate_automation_definition(next_payload, require_steps=True)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))

    now = utc_now_iso()
    next_run_at = None
    if next_payload.enabled and next_payload.trigger_type == "schedule" and next_payload.trigger_config.schedule_time:
        next_run_at = next_daily_run_at(next_payload.trigger_config.schedule_time)
    connection.execute(
        """
        UPDATE automations
        SET name = ?, description = ?, enabled = ?, trigger_type = ?, trigger_config_json = ?, updated_at = ?, next_run_at = ?
        WHERE id = ?
        """,
        (
            next_payload.name,
            next_payload.description,
            int(next_payload.enabled),
            next_payload.trigger_type,
            json.dumps(next_payload.trigger_config.model_dump()),
            now,
            next_run_at,
            automation_id,
        ),
    )
    replace_automation_steps(connection, automation_id, next_payload.steps, timestamp=now)
    connection.commit()
    refresh_scheduler_jobs(connection)
    return serialize_automation_detail(connection, automation_id)

@router.delete("/api/v1/automations/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation(automation_id: str, request: Request) -> Response:
    connection = get_connection(request)
    get_automation_or_404(connection, automation_id)
    connection.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
    connection.commit()
    refresh_scheduler_jobs(connection)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/api/v1/automations/{automation_id}/validate", response_model=AutomationValidationResponse)
def validate_automation_endpoint(automation_id: str, request: Request) -> AutomationValidationResponse:
    automation = serialize_automation_detail(get_connection(request), automation_id)
    issues = validate_automation_definition(automation, require_steps=True)
    return AutomationValidationResponse(valid=not issues, issues=issues)

@router.post("/api/v1/automations/{automation_id}/execute", response_model=AutomationRunDetailResponse)
def execute_automation(automation_id: str, request: Request) -> AutomationRunDetailResponse:
    connection = get_connection(request)
    automation = serialize_automation_detail(connection, automation_id)
    if not automation.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Automation is disabled.")
    return execute_automation_definition(
        connection,
        get_application_logger(request),
        automation_id=automation_id,
        trigger_type="manual",
        payload=None,
        root_dir=get_root_dir(request),
    )

@router.get("/api/v1/automations/{automation_id}/runs", response_model=list[AutomationRunResponse])
def list_automation_runs_for_automation(automation_id: str, request: Request) -> list[AutomationRunResponse]:
    get_automation_or_404(get_connection(request), automation_id)
    rows = fetch_all(
        get_connection(request),
        """
        SELECT run_id, automation_id, trigger_type, status, started_at, finished_at, duration_ms, error_summary
        FROM automation_runs
        WHERE automation_id = ?
        ORDER BY started_at DESC
        """,
        (automation_id,),
    )
    return [AutomationRunResponse(**row_to_run(row)) for row in rows]

@router.get("/api/v1/settings", response_model=AppSettingsResponse)
def get_app_settings(request: Request) -> AppSettingsResponse:
    payload = get_settings_payload(
        get_connection(request),
        protection_secret=get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path),
    )
    return AppSettingsResponse(**payload)

@router.post("/api/v1/scripts/validate", response_model=ScriptValidationResult)
def validate_script(request_payload: ScriptValidationRequest, request: Request) -> ScriptValidationResult:
    return validate_script_payload(
        request_payload.language,
        request_payload.code,
        root_dir=get_root_dir(request),
    )

@router.get("/api/v1/scripts", response_model=list[ScriptSummaryResponse])
def list_scripts(request: Request) -> list[ScriptSummaryResponse]:
    rows = fetch_all(
        get_connection(request),
        """
        SELECT id, name, description, language, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        ORDER BY updated_at DESC, name COLLATE NOCASE ASC
        """,
    )
    return [row_to_script_summary(row) for row in rows]

@router.get("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def get_script(script_id: str, request: Request) -> ScriptResponse:
    row = fetch_one(
        get_connection(request),
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    return row_to_script_response(row)

@router.post("/api/v1/scripts", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(payload: ScriptCreate, request: Request) -> ScriptResponse:
    validation_result = validate_script_payload(payload.language, payload.code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    now = utc_now_iso()
    script_id = f"script_{uuid4().hex[:12]}"
    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    connection = get_connection(request)
    connection.execute(
        """
        INSERT INTO scripts (
            id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            script_id,
            payload.name.strip(),
            payload.description.strip(),
            payload.language,
            payload.code,
            validation_status,
            validation_message,
            last_validated_at,
            now,
            now,
        ),
    )
    connection.commit()
    row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(row)

@router.patch("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def update_script(script_id: str, payload: ScriptUpdate, request: Request) -> ScriptResponse:
    connection = get_connection(request)
    existing_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if existing_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row_to_script_response(existing_row)

    next_name = (changes.get("name") if "name" in changes else existing_row["name"]).strip()
    next_description = (changes.get("description") if "description" in changes else existing_row["description"]).strip()
    next_language = changes.get("language", existing_row["language"])
    next_code = changes.get("code", existing_row["code"])

    validation_result = validate_script_payload(next_language, next_code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    updated_at = utc_now_iso()
    connection.execute(
        """
        UPDATE scripts
        SET name = ?, description = ?, language = ?, code = ?, validation_status = ?, validation_message = ?, last_validated_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            next_name,
            next_description,
            next_language,
            next_code,
            validation_status,
            validation_message,
            last_validated_at,
            updated_at,
            script_id,
        ),
    )
    connection.commit()
    saved_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(saved_row)

@router.get("/api/v1/dashboard/devices", response_model=DashboardDevicesApiResponse)
def get_dashboard_devices() -> DashboardDevicesApiResponse:
    return get_runtime_devices_response()

@router.get("/api/v1/workers", response_model=list[WorkerResponse])
def list_workers() -> list[WorkerResponse]:
    return [worker_to_response(worker) for worker in runtime_event_bus.list_workers()]

@router.post("/api/v1/workers/register", response_model=WorkerResponse)
def register_worker(payload: WorkerRegistrationRequest) -> WorkerResponse:
    worker_id = payload.worker_id or f"worker_{uuid4().hex}"
    worker = register_runtime_worker(
        worker_id=worker_id,
        name=payload.name,
        hostname=payload.hostname,
        address=payload.address,
        capabilities=payload.capabilities,
    )
    return worker_to_response(worker)

@router.post("/api/v1/workers/claim-trigger", response_model=WorkerClaimResponse)
def claim_worker_trigger(payload: WorkerClaimRequest) -> WorkerClaimResponse:
    worker = next((item for item in runtime_event_bus.list_workers() if item.worker_id == payload.worker_id), None)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not registered.")

    claimed_job = runtime_event_bus.claim_next(
        worker_id=worker.worker_id,
        worker_name=worker.name,
        claimed_at=utc_now_iso(),
    )
    if claimed_job is None:
        return WorkerClaimResponse(job=None)

    return claim_job_response(claimed_job)

@router.post("/api/v1/workers/complete-trigger", response_model=AutomationRunDetailResponse)
def complete_worker_trigger(payload: WorkerCompletionRequest, request: Request) -> AutomationRunDetailResponse:
    job = runtime_event_bus.get_job(payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker job not found.")

    if job.worker_id != payload.worker_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Worker does not own this job.")

    completed_job = runtime_event_bus.complete_job(
        job_id=payload.job_id,
        worker_id=payload.worker_id,
        status_value=payload.status,
        completed_at=utc_now_iso(),
    )
    if completed_job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Worker job could not be completed.")

    connection = get_connection(request)
    worker = next((item for item in runtime_event_bus.list_workers() if item.worker_id == payload.worker_id), None)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not registered.")

    finished_at = completed_job.completed_at or utc_now_iso()
    assign_automation_run_worker(
        connection,
        run_id=completed_job.run_id,
        worker_id=worker.worker_id,
        worker_name=worker.name,
    )
    finalize_automation_run_step(
        connection,
        step_id=completed_job.step_id,
        status_value="completed" if payload.status == "completed" else "failed",
        response_summary=payload.response_summary,
        detail={
            **(payload.detail or {}),
            "worker_id": worker.worker_id,
            "worker_name": worker.name,
        },
        finished_at=finished_at,
    )
    finalize_automation_run(
        connection,
        run_id=completed_job.run_id,
        status_value="completed" if payload.status == "completed" else "failed",
        error_summary=payload.error_summary,
        finished_at=finished_at,
    )
    return get_automation_run(completed_job.run_id, request)

@router.patch("/api/v1/settings", response_model=AppSettingsResponse)
def patch_app_settings(payload: AppSettingsUpdate, request: Request) -> AppSettingsResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    changes = payload.model_dump(exclude_unset=True)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)

    if not changes:
        return AppSettingsResponse(**get_settings_payload(connection, protection_secret=protection_secret))

    if "connectors" in changes:
        changes["connectors"] = normalize_connector_settings_for_storage(
            changes["connectors"],
            existing_settings=get_stored_connector_settings(connection),
            protection_secret=protection_secret,
        )

    now = utc_now_iso()

    for key, value in changes.items():
        connection.execute(
            """
            INSERT INTO settings (key, value_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """
            ,
            (key, json.dumps(value), now, now),
        )

    connection.commit()
    settings_payload = get_settings_payload(connection, protection_secret=protection_secret)
    if "logging" in changes:
        request.app.state.logger = configure_application_logger(
            request.app,
            root_dir=get_root_dir(request),
            max_file_size_mb=settings_payload["logging"]["max_file_size_mb"],
        )
        logger = request.app.state.logger
    write_application_log(
        logger,
        logging.INFO,
        "settings_updated",
        changed_sections=sorted(changes.keys()),
        logging=settings_payload.get("logging"),
    )
    return AppSettingsResponse(**settings_payload)

@router.post("/api/v1/connectors/{connector_id}/test", response_model=ConnectorActionResponse)
def test_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    if record.get("status") == "revoked":
        record["status"] = "revoked"
        message = "Connector is revoked."
        ok = False
    elif record.get("auth_config", {}).get("expires_at") and parse_iso_datetime(record["auth_config"]["expires_at"]) and parse_iso_datetime(record["auth_config"]["expires_at"]) <= datetime.now(UTC):
        record["status"] = "expired"
        message = "Connector token has expired."
        ok = False
    elif any(secret_map.values()) or record.get("auth_type") == "oauth2":
        record["status"] = "connected"
        message = "Connector credentials look complete."
        ok = True
    else:
        record["status"] = "needs_attention"
        message = "Connector is missing credential material."
        ok = False

    record["last_tested_at"] = utc_now_iso()
    record["updated_at"] = record["last_tested_at"]
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=ok, message=message, connector=ConnectorRecordResponse(**sanitized))

@router.post("/api/v1/connectors/{provider}/oauth/start", response_model=ConnectorOAuthStartResponse)
def start_connector_oauth(provider: str, payload: ConnectorOAuthStartRequest, request: Request) -> ConnectorOAuthStartResponse:
    if provider not in SUPPORTED_CONNECTOR_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector provider not found.")

    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    connection = get_connection(request)
    settings = get_stored_connector_settings(connection)
    existing_records = {item["id"]: item for item in settings["records"]}
    now = utc_now_iso()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = build_pkce_code_challenge(verifier)
    preset = get_connector_preset(provider) or {}
    scopes = payload.scopes or list(preset.get("default_scopes", []))
    next_record = normalize_connector_record_for_storage(
        {
            "id": payload.connector_id,
            "provider": provider,
            "name": payload.name,
            "status": "pending_oauth",
            "auth_type": "oauth2",
            "scopes": scopes,
            "owner": payload.owner or "Workspace",
            "base_url": preset.get("base_url"),
            "docs_url": preset.get("docs_url"),
            "auth_config": {
                "client_id": payload.client_id,
                "client_secret_input": payload.client_secret_input,
                "redirect_uri": payload.redirect_uri,
                "scope_preset": provider,
                "expires_at": None,
            },
        },
        existing_record=existing_records.get(payload.connector_id),
        protection_secret=protection_secret,
        timestamp=now,
    )
    settings["records"] = [item for item in settings["records"] if item.get("id") != payload.connector_id] + [next_record]
    write_settings_section(connection, "connectors", settings)
    request.app.state.connector_oauth_states[state] = {
        "provider": provider,
        "connector_id": payload.connector_id,
        "code_verifier": verifier,
        "expires_at": (datetime.now(UTC) + timedelta(seconds=CONNECTOR_OAUTH_STATE_TTL_SECONDS)).isoformat(),
    }
    sanitized = sanitize_connector_record_for_response(next_record, protection_secret)
    return ConnectorOAuthStartResponse(
        connector=ConnectorRecordResponse(**sanitized),
        authorization_url=build_connector_oauth_authorization_url(
            provider,
            client_id=payload.client_id or "missing-client-id",
            redirect_uri=payload.redirect_uri,
            scopes=scopes,
            state=state,
            code_challenge=challenge,
        ),
        state=state,
        expires_at=request.app.state.connector_oauth_states[state]["expires_at"],
        code_challenge_method="S256",
    )

@router.get("/api/v1/connectors/{provider}/oauth/callback", response_model=ConnectorOAuthCallbackResponse)
def complete_connector_oauth(
    provider: str,
    state: str,
    request: Request,
    code: str | None = None,
    error: str | None = None,
    scope: str | None = None,
) -> ConnectorOAuthCallbackResponse:
    oauth_states = getattr(request.app.state, "connector_oauth_states", {})
    state_payload = oauth_states.get(state)
    if not state_payload or state_payload.get("provider") != provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")

    expires_at = parse_iso_datetime(state_payload.get("expires_at"))
    if expires_at is None or expires_at <= datetime.now(UTC):
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired.")

    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    connector_id = state_payload["connector_id"]
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if error:
        record["status"] = "needs_attention"
        record["updated_at"] = utc_now_iso()
        write_settings_section(connection, "connectors", settings)
        oauth_states.pop(state, None)
        sanitized_error = sanitize_connector_record_for_response(record, protection_secret)
        return ConnectorOAuthCallbackResponse(
            ok=False,
            message=f"OAuth authorization failed: {error}.",
            connector=ConnectorRecordResponse(**sanitized_error),
        )

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    incoming_scopes = [item for item in re.split(r"[\s,]+", scope or "") if item]
    if incoming_scopes:
        record["scopes"] = incoming_scopes
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **(record.get("auth_config") or {}),
            "access_token_input": f"token_{(code or 'demo')[:24]}",
            "refresh_token_input": f"refresh_{uuid4().hex[:24]}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "has_refresh_token": True,
        },
        record.get("auth_config"),
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    oauth_states.pop(state, None)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorOAuthCallbackResponse(
        ok=True,
        message="Connector authorized successfully.",
        connector=ConnectorRecordResponse(**sanitized),
    )

@router.post("/api/v1/connectors/{connector_id}/refresh", response_model=ConnectorActionResponse)
def refresh_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if record.get("auth_type") != "oauth2":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only OAuth connectors support refresh.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    if not secret_map.get("refresh_token"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector does not have a refresh token.")

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **(record.get("auth_config") or {}),
            "access_token_input": f"token_{uuid4().hex[:24]}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "has_refresh_token": True,
        },
        record.get("auth_config"),
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message="Connector token refreshed.", connector=ConnectorRecordResponse(**sanitized))

@router.get("/api/v1/inbound", response_model=list[InboundApiResponse])
def list_inbound_apis(request: Request) -> list[InboundApiResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        WITH filtered_events AS (
            SELECT api_id, event_id, received_at, status
            FROM inbound_api_events
            WHERE (? = 1 OR is_mock = 0)
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
        WHERE (? = 1 OR inbound_apis.is_mock = 0)
        ORDER BY inbound_apis.created_at DESC
        """
        ,
        (int(include_mock), int(include_mock)),
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
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, destination_url, http_method, auth_type,
               payload_template, scheduled_time, schedule_expression, status, created_at, updated_at
        FROM outgoing_scheduled_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_scheduled", endpoint_path="/api/v1/outgoing/scheduled"))
        for row in rows
    ]

@router.get("/api/v1/outgoing/continuous", response_model=list[ApiResourceResponse])
def list_outgoing_continuous_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, repeat_interval_minutes, destination_url, http_method, auth_type,
               payload_template, stream_mode, created_at, updated_at
        FROM outgoing_continuous_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
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
    row = get_outgoing_api_or_404(connection, api_id, api_type, include_mock=developer_mode_enabled(request))
    endpoint_path = "/api/v1/outgoing/scheduled" if api_type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    return row_to_outgoing_detail_response(row, api_type=api_type, endpoint_path=endpoint_path)

@router.get("/api/v1/webhooks", response_model=list[ApiResourceResponse])
def list_webhook_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, callback_path, signature_header, event_filter, verification_token, signing_secret, created_at, updated_at
        FROM webhook_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
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
    current = get_api_or_404(connection, api_id, include_mock=True)
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
    current = get_outgoing_api_or_404(connection, api_id, payload.type, include_mock=True)
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

    updated = get_outgoing_api_or_404(connection, api_id, payload.type, include_mock=True)
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
    api_row = get_api_or_404(connection, api_id, include_mock=True)
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
    get_api_or_404(connection, api_id, include_mock=True)
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

@router.get("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def get_smtp_tool(request: Request) -> SmtpToolResponse:
    return build_smtp_tool_response(request.app, get_connection(request))

@router.get("/api/v1/tools/llm-deepl/local-llm", response_model=LocalLlmToolResponse)
def get_local_llm_tool(request: Request) -> LocalLlmToolResponse:
    return build_local_llm_tool_response(get_connection(request))

@router.get("/api/v1/tools/coqui-tts", response_model=CoquiTtsToolResponse)
def get_coqui_tts_tool(request: Request) -> CoquiTtsToolResponse:
    return build_coqui_tts_tool_response(get_connection(request), root_dir=get_root_dir(request))

@router.post("/api/v1/tools/llm-deepl/chat", response_model=LocalLlmChatResponse)
def create_local_llm_chat(payload: LocalLlmChatRequest, request: Request) -> LocalLlmChatResponse:
    messages = [message.model_dump() for message in payload.messages]
    return execute_local_llm_chat_request(
        get_connection(request),
        messages=messages,
        model_identifier_override=payload.model_identifier,
        previous_response_id=payload.previous_response_id,
    )

@router.post("/api/v1/tools/llm-deepl/chat/stream")
def stream_local_llm_chat(payload: LocalLlmChatRequest, request: Request) -> StreamingResponse:
    messages = [message.model_dump() for message in payload.messages]
    return StreamingResponse(
        build_local_llm_stream(
            get_connection(request),
            messages=messages,
            model_identifier_override=payload.model_identifier,
            previous_response_id=payload.previous_response_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.get("/api/v1/tools", response_model=list[ToolDirectoryEntryResponse])
def list_tools(request: Request) -> list[ToolDirectoryEntryResponse]:
    return build_tool_directory_response(request)

@router.patch("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def patch_smtp_tool(payload: SmtpToolUpdate, request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No SMTP tool changes provided.")

    next_config = get_smtp_tool_config(connection)
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "target_worker_id" in changes:
        next_config["target_worker_id"] = changes["target_worker_id"] or None
    if "bind_host" in changes:
        next_config["bind_host"] = str(changes["bind_host"]).strip()
    if "port" in changes:
        next_config["port"] = int(changes["port"])
    if "recipient_email" in changes:
        next_config["recipient_email"] = (str(changes["recipient_email"]).strip().lower() or None) if changes["recipient_email"] is not None else None

    save_smtp_tool_config(connection, next_config)
    sync_managed_tool_enabled_state(request, "smtp", next_config["enabled"])
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)

@router.patch("/api/v1/tools/llm-deepl/local-llm", response_model=LocalLlmToolResponse)
def patch_local_llm_tool(payload: LocalLlmToolUpdate, request: Request) -> LocalLlmToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No local LLM tool changes provided.")

    next_config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))

    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "provider" in changes:
        provider = str(changes["provider"]).strip()
        if provider not in LOCAL_LLM_ENDPOINT_PRESETS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported local LLM provider preset.")
        next_config["provider"] = provider
    if "server_base_url" in changes:
        next_config["server_base_url"] = str(changes["server_base_url"] or "").strip()
    if "model_identifier" in changes:
        next_config["model_identifier"] = str(changes["model_identifier"] or "").strip()
    if "endpoints" in changes and isinstance(changes["endpoints"], dict):
        for key, value in changes["endpoints"].items():
            if value is not None:
                next_config["endpoints"][key] = str(value).strip()

    normalized_config = normalize_local_llm_tool_config(next_config)
    save_local_llm_tool_config(connection, normalized_config)
    sync_managed_tool_enabled_state(request, "llm-deepl", normalized_config["enabled"])
    return build_local_llm_tool_response(connection)

@router.patch("/api/v1/tools/coqui-tts", response_model=CoquiTtsToolResponse)
def patch_coqui_tts_tool(payload: CoquiTtsToolUpdate, request: Request) -> CoquiTtsToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Coqui TTS tool changes provided.")

    next_config = normalize_coqui_tts_tool_config(
        get_coqui_tts_tool_config(connection),
        root_dir=get_root_dir(request),
    )
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "command" in changes:
        next_config["command"] = str(changes["command"] or "").strip()
    if "model_name" in changes:
        next_config["model_name"] = str(changes["model_name"] or "").strip()
    if "speaker" in changes:
        next_config["speaker"] = str(changes["speaker"] or "").strip()
    if "language" in changes:
        next_config["language"] = str(changes["language"] or "").strip()
    if "output_directory" in changes:
        next_config["output_directory"] = str(changes["output_directory"] or "").strip()

    normalized_config = normalize_coqui_tts_tool_config(next_config, root_dir=get_root_dir(request))
    save_coqui_tts_tool_config(connection, normalized_config)
    sync_managed_tool_enabled_state(request, "coqui-tts", normalized_config["enabled"])
    return build_coqui_tts_tool_response(connection, root_dir=get_root_dir(request))

@router.post("/api/v1/tools/smtp/start", response_model=SmtpToolResponse)
def start_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = True
    save_smtp_tool_config(connection, config)
    sync_managed_tool_enabled_state(request, "smtp", True)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)

@router.post("/api/v1/tools/smtp/stop", response_model=SmtpToolResponse)
def stop_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = False
    save_smtp_tool_config(connection, config)
    sync_managed_tool_enabled_state(request, "smtp", False)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)

@router.post("/api/v1/tools/smtp/send-test", response_model=SmtpSendTestResponse)
def send_smtp_test_message(payload: SmtpSendTestRequest, request: Request) -> SmtpSendTestResponse:
    runtime = get_local_smtp_runtime_or_400(request.app)
    config = normalize_smtp_tool_config(get_smtp_tool_config(get_connection(request)))
    recipients = validate_smtp_send_inputs(mail_from=payload.mail_from, recipients=payload.recipients)

    if config.get("recipient_email") and any(recipient != config["recipient_email"] for recipient in recipients):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Test recipients must match the configured receive email.")

    message = build_smtp_email_message(
        mail_from=payload.mail_from.strip(),
        recipients=recipients,
        subject=payload.subject.strip(),
        body=payload.body,
    )

    try:
        with smtplib.SMTP(str(runtime["listening_host"]), int(runtime["listening_port"]), timeout=10) as client:
            client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
    except smtplib.SMTPException as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP test send failed: {error}") from error
    except (OSError, TimeoutError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP test connection failed: {error}") from error

    snapshot = request.app.state.smtp_manager.snapshot()
    latest_message = (snapshot.get("recent_messages") or [None])[0]
    return SmtpSendTestResponse(
        ok=True,
        message="Test email sent through the local SMTP listener.",
        message_id=(latest_message or {}).get("id") if isinstance(latest_message, dict) else None,
    )

@router.post("/api/v1/tools/smtp/send-relay", response_model=SmtpRelaySendResponse)
def send_smtp_relay(payload: SmtpRelaySendRequest, request: Request) -> SmtpRelaySendResponse:
    _ = request
    try:
        send_smtp_relay_message(payload)
    except HTTPException as error:
        detail = str(error.detail)
        if "authentication failed" in detail.lower():
            status_value = "auth_failed"
        elif "tls negotiation failed" in detail.lower():
            status_value = "tls_failed"
        elif "connection failed" in detail.lower():
            status_value = "connection_failed"
        elif error.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT:
            status_value = "invalid_input"
        else:
            status_value = "send_failed"
        return SmtpRelaySendResponse(ok=False, status=status_value, message=detail)

    return SmtpRelaySendResponse(ok=True, status="sent", message="Email sent through the external SMTP relay.")

@router.patch("/api/v1/tools/{tool_id}/directory", response_model=ToolDirectoryEntryResponse)
def patch_tool_directory(tool_id: str, payload: ToolDirectoryUpdate, request: Request) -> ToolDirectoryEntryResponse:
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tool changes provided.")

    connection = get_connection(request)

    try:
        if "name" in changes or "description" in changes:
            update_tool_metadata(
                get_root_dir(request),
                connection,
                tool_id,
                name=changes.get("name"),
                description=changes.get("description"),
            )

        if "enabled" in changes:
            if tool_id == "smtp":
                config = get_smtp_tool_config(connection)
                config["enabled"] = bool(changes["enabled"])
                save_smtp_tool_config(connection, config)
                sync_smtp_tool_runtime(request.app, connection)
            if tool_id == "llm-deepl":
                config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
                config["enabled"] = bool(changes["enabled"])
                save_local_llm_tool_config(connection, config)
            if tool_id == "coqui-tts":
                config = normalize_coqui_tts_tool_config(
                    get_coqui_tts_tool_config(connection),
                    root_dir=get_root_dir(request),
                )
                config["enabled"] = bool(changes["enabled"])
                save_coqui_tts_tool_config(connection, config)
            set_tool_enabled(
                get_root_dir(request),
                connection,
                tool_id,
                enabled=bool(changes["enabled"]),
            )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    directory = build_tool_directory_response(request)
    entry = next((item for item in directory if item.id == tool_id), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    return entry

@router.patch("/api/v1/tools/{tool_id}", response_model=ToolMetadataResponse)
def patch_tool_metadata(tool_id: str, payload: ToolMetadataUpdate, request: Request) -> ToolMetadataResponse:
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tool changes provided.")

    try:
        updated = update_tool_metadata(
            get_root_dir(request),
            get_connection(request),
            tool_id,
            name=changes.get("name"),
            description=changes.get("description"),
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ToolMetadataResponse(**updated)

@router.post("/api/v1/inbound/{api_id}", response_model=InboundReceiveAccepted, status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound_event(api_id: str, request: Request, response: Response) -> InboundReceiveAccepted:
    connection = get_connection(request)
    logger = get_application_logger(request)
    event_id = f"evt_{uuid4().hex[:10]}"
    received_at = utc_now_iso()
    headers = header_subset(request.headers)
    source_ip = request.client.host if request.client else None
    api_row = get_api_or_404(connection, api_id, include_mock=True)

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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
        is_mock=bool(api_row["is_mock"]),
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

@router.get("/api/v1/runs", response_model=list[AutomationRunResponse])
def list_automation_runs(
    request: Request,
    status: str | None = None,
    automation_id: str | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
) -> list[AutomationRunResponse]:
    connection = get_connection(request)
    where_clauses: list[str] = []
    params: list[Any] = []

    if status is not None:
        where_clauses.append("status = ?")
        params.append(status)

    if automation_id is not None:
        where_clauses.append("automation_id = ?")
        params.append(automation_id)

    if started_after is not None:
        where_clauses.append("started_at >= ?")
        params.append(started_after)

    if started_before is not None:
        where_clauses.append("started_at <= ?")
        params.append(started_before)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = fetch_all(
        connection,
        f"""
        SELECT
            run_id,
            automation_id,
            trigger_type,
            status,
            worker_id,
            worker_name,
            started_at,
            finished_at,
            duration_ms,
            error_summary
        FROM automation_runs
        {where_sql}
        ORDER BY started_at DESC
        """,
        tuple(params),
    )
    return [AutomationRunResponse(**row_to_run(row)) for row in rows]

@router.get("/api/v1/runs/{run_id}", response_model=AutomationRunDetailResponse)
def get_automation_run(run_id: str, request: Request) -> AutomationRunDetailResponse:
    connection = get_connection(request)
    run_row = fetch_one(
        connection,
        """
        SELECT
            run_id,
            automation_id,
            trigger_type,
            status,
            worker_id,
            worker_name,
            started_at,
            finished_at,
            duration_ms,
            error_summary
        FROM automation_runs
        WHERE run_id = ?
        """,
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
            detail_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )

    detail = row_to_run(run_row)
    detail["steps"] = [row_to_run_step(step_row) for step_row in step_rows]
    return AutomationRunDetailResponse(**detail)

@router.get("/api/v1/runtime/triggers")
def list_runtime_triggers() -> list[dict[str, Any]]:
    return [
        {
            "type": trigger.type,
            "api_id": trigger.api_id,
            "event_id": trigger.event_id,
            "payload": trigger.payload,
            "received_at": trigger.received_at,
        }
        for trigger in runtime_event_bus.history()
    ]
