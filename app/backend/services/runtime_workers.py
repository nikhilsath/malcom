"""Runtime worker identity, registration, and polling loops.

Primary identifiers: worker identity helpers, ``register_runtime_worker``,
``process_runtime_job``, ``fail_runtime_job``, and local/remote worker loops.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Any

import httpx
from fastapi import FastAPI

from backend.runtime import RegisteredWorker, RuntimeTrigger, RuntimeTriggerJob, runtime_event_bus
from backend.services.automation_runs import (
    assign_automation_run_worker,
    finalize_automation_run,
    finalize_automation_run_step,
)
from backend.services.logging_service import write_application_log
from backend.services.utils import utc_now_iso

LOCAL_WORKER_POLL_INTERVAL_SECONDS = 0.25
REMOTE_WORKER_POLL_INTERVAL_SECONDS = 1.0
DatabaseConnection = Any


def slugify_identifier(value: str) -> str:
    import re

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "runtime"


def get_runtime_hostname() -> str:
    return platform.node() or "unknown-host"


def get_local_worker_id() -> str:
    return f"worker-local-{slugify_identifier(get_runtime_hostname())}"


def get_local_worker_name() -> str:
    return f"{get_runtime_hostname()} local worker"


def get_local_worker_address() -> str:
    return get_runtime_hostname()


def register_runtime_worker(*, worker_id: str, name: str, hostname: str, address: str, capabilities: list[str] | None = None) -> RegisteredWorker:
    return runtime_event_bus.register_worker(
        worker_id=worker_id,
        name=name,
        hostname=hostname,
        address=address,
        capabilities=capabilities or ["runtime-trigger-execution"],
        seen_at=utc_now_iso(),
    )


def process_runtime_job(connection: DatabaseConnection, logger: logging.Logger, *, job: RuntimeTriggerJob, worker_id: str, worker_name: str) -> None:
    finished_at = utc_now_iso()
    runtime_event_bus.complete_job(job_id=job.job_id, worker_id=worker_id, status_value="completed", completed_at=finished_at)
    assign_automation_run_worker(connection, run_id=job.run_id, worker_id=worker_id, worker_name=worker_name)
    write_application_log(
        logger,
        logging.INFO,
        "runtime_trigger_emitted",
        api_id=job.trigger.api_id,
        event_id=job.trigger.event_id,
        trigger_type=job.trigger.type,
        worker_id=worker_id,
        worker_name=worker_name,
    )
    runtime_event_bus.record_history(job.trigger)
    finalize_automation_run_step(
        connection,
        step_id=job.step_id,
        status_value="completed",
        response_summary="Trigger emitted to runtime event bus.",
        detail={
            "event_id": job.trigger.event_id,
            "api_id": job.trigger.api_id,
            "worker_id": worker_id,
            "worker_name": worker_name,
        },
        finished_at=finished_at,
    )
    finalize_automation_run(connection, run_id=job.run_id, status_value="completed", error_summary=None, finished_at=finished_at)


def fail_runtime_job(connection: DatabaseConnection, logger: logging.Logger, *, job: RuntimeTriggerJob, worker_id: str, worker_name: str, error_summary: str) -> None:
    finished_at = utc_now_iso()
    completed_job = runtime_event_bus.complete_job(job_id=job.job_id, worker_id=worker_id, status_value="failed", completed_at=finished_at)
    if completed_job is None:
        write_application_log(
            logger,
            logging.WARNING,
            "runtime_trigger_failure_untracked",
            api_id=job.trigger.api_id,
            event_id=job.trigger.event_id,
            trigger_type=job.trigger.type,
            worker_id=worker_id,
            worker_name=worker_name,
            error=error_summary,
        )
        return
    assign_automation_run_worker(connection, run_id=job.run_id, worker_id=worker_id, worker_name=worker_name)
    write_application_log(
        logger,
        logging.WARNING,
        "runtime_trigger_failed",
        api_id=job.trigger.api_id,
        event_id=job.trigger.event_id,
        trigger_type=job.trigger.type,
        worker_id=worker_id,
        worker_name=worker_name,
        error=error_summary,
    )
    finalize_automation_run_step(
        connection,
        step_id=job.step_id,
        status_value="failed",
        response_summary=error_summary,
        detail={
            "event_id": job.trigger.event_id,
            "api_id": job.trigger.api_id,
            "worker_id": worker_id,
            "worker_name": worker_name,
            "error": error_summary,
        },
        finished_at=finished_at,
    )
    finalize_automation_run(connection, run_id=job.run_id, status_value="failed", error_summary=error_summary, finished_at=finished_at)


def run_local_worker_loop(app: FastAPI, stop_event: threading.Event) -> None:
    logger = app.state.logger
    connection = app.state.connection
    worker_id = get_local_worker_id()
    worker_name = get_local_worker_name()
    register_runtime_worker(worker_id=worker_id, name=worker_name, hostname=get_runtime_hostname(), address=get_local_worker_address())
    while not stop_event.is_set():
        register_runtime_worker(worker_id=worker_id, name=worker_name, hostname=get_runtime_hostname(), address=get_local_worker_address())
        job = runtime_event_bus.claim_next(worker_id=worker_id, worker_name=worker_name, claimed_at=utc_now_iso())
        if job is None:
            stop_event.wait(LOCAL_WORKER_POLL_INTERVAL_SECONDS)
            continue
        try:
            process_runtime_job(connection, logger, job=job, worker_id=worker_id, worker_name=worker_name)
        except Exception as error:
            fail_runtime_job(connection, logger, job=job, worker_id=worker_id, worker_name=worker_name, error_summary=str(error))


def run_remote_worker_loop(app: FastAPI, stop_event: threading.Event, coordinator_url: str) -> None:
    logger = app.state.logger
    worker_id = get_local_worker_id()
    worker_name = get_local_worker_name()
    payload = {
        "worker_id": worker_id,
        "name": worker_name,
        "hostname": get_runtime_hostname(),
        "address": get_local_worker_address(),
        "capabilities": ["runtime-trigger-execution"],
    }
    while not stop_event.is_set():
        try:
            with httpx.Client(base_url=coordinator_url, timeout=5.0) as client:
                client.post("/api/v1/workers/register", json=payload).raise_for_status()
                claim_response = client.post("/api/v1/workers/claim-trigger", json={"worker_id": worker_id})
                claim_response.raise_for_status()
                job = claim_response.json().get("job")
                if job:
                    trigger = job["trigger"]
                    runtime_event_bus.record_history(
                        RuntimeTrigger(
                            type=trigger["type"],
                            api_id=trigger["api_id"],
                            event_id=trigger["event_id"],
                            payload=trigger["payload"],
                            received_at=trigger["received_at"],
                        )
                    )
                    client.post(
                        "/api/v1/workers/complete-trigger",
                        json={
                            "worker_id": worker_id,
                            "job_id": job["job_id"],
                            "status": "completed",
                            "response_summary": "Trigger emitted to remote runtime event bus.",
                            "detail": {"worker_id": worker_id, "worker_name": worker_name, "execution_mode": "remote"},
                        },
                    ).raise_for_status()
        except Exception as error:
            if not stop_event.is_set():
                write_application_log(
                    logger,
                    logging.WARNING,
                    "remote_worker_poll_failed",
                    coordinator_url=coordinator_url,
                    worker_id=worker_id,
                    worker_name=worker_name,
                    error=str(error),
                )
        stop_event.wait(REMOTE_WORKER_POLL_INTERVAL_SECONDS)


__all__ = [
    "LOCAL_WORKER_POLL_INTERVAL_SECONDS",
    "REMOTE_WORKER_POLL_INTERVAL_SECONDS",
    "fail_runtime_job",
    "get_local_worker_address",
    "get_local_worker_id",
    "get_local_worker_name",
    "get_runtime_hostname",
    "process_runtime_job",
    "register_runtime_worker",
    "run_local_worker_loop",
    "run_remote_worker_loop",
    "slugify_identifier",
]
