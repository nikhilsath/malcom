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


@router.get("/api/v1/dashboard/devices", response_model=DashboardDevicesApiResponse)
def get_dashboard_devices() -> DashboardDevicesApiResponse:
    return get_runtime_devices_response()


@router.get("/api/v1/dashboard/queue", response_model=DashboardQueueApiResponse)
def get_dashboard_queue() -> DashboardQueueApiResponse:
    return get_runtime_queue_response()


@router.post("/api/v1/dashboard/queue/pause", response_model=DashboardQueueApiResponse)
def pause_dashboard_queue() -> DashboardQueueApiResponse:
    return set_runtime_queue_pause_state(True)


@router.post("/api/v1/dashboard/queue/unpause", response_model=DashboardQueueApiResponse)
def unpause_dashboard_queue() -> DashboardQueueApiResponse:
    return set_runtime_queue_pause_state(False)


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
