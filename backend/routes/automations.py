from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


def _ensure_inbound_trigger_reference_exists(connection: DatabaseConnection, payload: AutomationCreate) -> None:
    if payload.trigger_type != "inbound_api":
        return
    inbound_api_id = payload.trigger_config.inbound_api_id
    if not inbound_api_id:
        return
    inbound_row = fetch_one(connection, "SELECT id FROM inbound_apis WHERE id = ?", (inbound_api_id,))
    webhook_row = fetch_one(connection, "SELECT id FROM webhook_apis WHERE id = ?", (inbound_api_id,))
    if inbound_row is None and webhook_row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Inbound API automations require an existing trigger_config.inbound_api_id.",
        )


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


@router.get("/api/v1/automations/workflow-connectors", response_model=list[WorkflowBuilderConnectorOptionResponse])
def list_workflow_builder_connectors_endpoint(request: Request) -> list[WorkflowBuilderConnectorOptionResponse]:
    options = list_workflow_builder_connectors(get_connection(request))
    return [WorkflowBuilderConnectorOptionResponse(**item) for item in options]


@router.post("/api/v1/automations", response_model=AutomationDetailResponse, status_code=status.HTTP_201_CREATED)
def create_automation(payload: AutomationCreate, request: Request) -> AutomationDetailResponse:
    connection = get_connection(request)
    issues = validate_automation_definition(payload, require_steps=True, connection=connection)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))
    _ensure_inbound_trigger_reference_exists(connection, payload)
    now = utc_now_iso()
    automation_id = f"automation_{uuid4().hex[:10]}"
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
            payload.trigger_config.model_dump_json(),
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
    issues = validate_automation_definition(next_payload, require_steps=True, connection=connection)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))
    _ensure_inbound_trigger_reference_exists(connection, next_payload)

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
            next_payload.trigger_config.model_dump_json(),
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
    connection = get_connection(request)
    automation = serialize_automation_detail(connection, automation_id)
    _ensure_inbound_trigger_reference_exists(connection, AutomationCreate(**automation.model_dump()))
    issues = validate_automation_definition(automation, require_steps=True, connection=connection)
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
        database_url=request.app.state.database_url,
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
            detail_json,
            response_body_json,
            extracted_fields_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )

    detail = row_to_run(run_row)
    detail["steps"] = [row_to_run_step(step_row) for step_row in step_rows]
    return AutomationRunDetailResponse(**detail)
