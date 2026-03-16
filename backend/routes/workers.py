from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

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
            detail_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (completed_job.run_id,),
    )
    detail = row_to_run(run_row)
    detail["steps"] = [row_to_run_step(step_row) for step_row in step_rows]
    return AutomationRunDetailResponse(**detail)
