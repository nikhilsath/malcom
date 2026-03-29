from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.metrics import get_metrics_collector
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


@router.get("/api/v1/dashboard/summary", response_model=DashboardSummaryApiResponse)
def get_dashboard_summary(request: Request) -> DashboardSummaryApiResponse:
    return get_runtime_dashboard_summary_response(get_connection(request))


@router.get("/api/v1/dashboard/queue", response_model=DashboardQueueApiResponse)
def get_dashboard_queue() -> DashboardQueueApiResponse:
    return get_runtime_queue_response()


@router.get("/api/v1/dashboard/logs", response_model=DashboardLogsApiResponse)
def get_dashboard_logs(request: Request) -> DashboardLogsApiResponse:
    return get_runtime_dashboard_logs_response(get_connection(request), get_root_dir(request))


@router.get("/api/v1/dashboard/resource-history", response_model=DashboardResourceHistoryApiResponse)
def get_dashboard_resource_history(request: Request) -> DashboardResourceHistoryApiResponse:
    connection = get_connection(request)
    persist_runtime_resource_history_snapshot(connection)
    return get_runtime_resource_history_response(connection)


@router.get("/api/v1/dashboard/resource-dashboard", response_model=DashboardResourceDashboardApiResponse)
def get_dashboard_resource_dashboard(request: Request) -> DashboardResourceDashboardApiResponse:
    connection = get_connection(request)
    persist_runtime_resource_history_snapshot(connection)
    return get_runtime_resource_dashboard_response(connection)


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


@router.get("/api/v1/debug/resource-profile", response_model=dict[str, Any])
def get_resource_profile(request: Request) -> dict[str, Any]:
    persist_runtime_resource_history_snapshot(get_connection(request))
    return get_metrics_collector().summary()


@router.get("/api/v1/debug/resource-profile/{component}", response_model=dict[str, Any])
def get_resource_profile_component(component: str, request: Request) -> dict[str, Any]:
    persist_runtime_resource_history_snapshot(get_connection(request))
    return get_metrics_collector().by_component(component)


@router.post("/api/v1/debug/resource-profile/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_resource_profile() -> Response:
    get_metrics_collector().clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
