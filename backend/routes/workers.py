from __future__ import annotations

import smtplib

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *
from backend.services.tool_runtime import assert_worker_rpc_authorized

router = APIRouter()


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


@router.post("/api/v1/internal/workers/tools/smtp/sync", response_model=SmtpToolResponse)
def sync_worker_smtp_tool(payload: WorkerRpcSmtpSyncRequest, request: Request) -> SmtpToolResponse:
    assert_worker_rpc_authorized(request)
    connection = get_connection(request)
    next_config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    next_config["bind_host"] = payload.bind_host
    next_config["port"] = payload.port
    next_config["recipient_email"] = payload.recipient_email
    next_config["target_worker_id"] = get_local_worker_id()
    save_smtp_tool_config(connection, next_config)
    sync_managed_tool_enabled_state(request, "smtp", payload.enabled)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@router.get("/api/v1/internal/workers/tools/smtp/status", response_model=SmtpToolResponse)
def get_worker_smtp_tool_status(request: Request) -> SmtpToolResponse:
    assert_worker_rpc_authorized(request)
    return build_smtp_tool_response(request.app, get_connection(request))


@router.post("/api/v1/internal/workers/tools/smtp/send-test", response_model=SmtpSendTestResponse)
def send_worker_smtp_test_message(payload: SmtpSendTestRequest, request: Request) -> SmtpSendTestResponse:
    assert_worker_rpc_authorized(request)
    runtime = get_local_smtp_runtime_or_400(request.app)
    connection = get_connection(request)
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
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
        message="Test email sent through the SMTP listener.",
        message_id=(latest_message or {}).get("id") if isinstance(latest_message, dict) else None,
    )


@router.post("/api/v1/internal/workers/tools/image-magic/execute", response_model=ImageMagicExecuteResponse)
def execute_worker_image_magic(payload: ImageMagicExecuteRequest, request: Request) -> ImageMagicExecuteResponse:
    assert_worker_rpc_authorized(request)
    connection = get_connection(request)
    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
    if not config["enabled"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Image Magic tool is disabled.")

    try:
        result = execute_image_magic_conversion_request(
            payload,
            root_dir=get_root_dir(request),
            command=config["command"],
        )
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ImageMagicExecuteResponse(
        ok=True,
        output_file_path=result["output_file_path"],
        worker_id=get_local_worker_id(),
        worker_name=get_local_worker_name(),
    )


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
        (completed_job.run_id,),
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
        (completed_job.run_id,),
    )
    detail = row_to_run(run_row)
    detail["steps"] = [row_to_run_step(step_row) for step_row in step_rows]
    return AutomationRunDetailResponse(**detail)
