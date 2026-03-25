"""Worker domain schemas for worker registration, claims, machine inventory, and host telemetry."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DashboardDeviceResponse(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    location: str
    detail: str
    last_seen_at: str


class HostMachineSummary(BaseModel):
    id: str
    name: str
    status: str
    location: str
    detail: str
    last_seen_at: str
    hostname: str
    operating_system: str
    architecture: str
    memory_total_bytes: int
    memory_used_bytes: int
    memory_available_bytes: int
    memory_usage_percent: float
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    storage_usage_percent: float
    sampled_at: str


class DashboardDevicesApiResponse(BaseModel):
    host: HostMachineSummary | None
    devices: list[DashboardDeviceResponse]


class DashboardQueueJobResponse(BaseModel):
    job_id: str
    run_id: str
    step_id: str
    status: Literal["pending", "claimed"]
    worker_id: str | None
    worker_name: str | None
    claimed_at: str | None
    completed_at: str | None
    trigger_type: str
    api_id: str
    event_id: str
    received_at: str


class DashboardQueueApiResponse(BaseModel):
    status: Literal["running", "paused"]
    is_paused: bool
    status_updated_at: str
    total_jobs: int
    pending_jobs: int
    claimed_jobs: int
    jobs: list[DashboardQueueJobResponse]


class DashboardSummaryRunCountsResponse(BaseModel):
    success: int
    warning: int
    error: int
    idle: int


class DashboardSummaryRecentRunResponse(BaseModel):
    id: str
    automation_name: str
    trigger_type: Literal["schedule", "manual", "api"]
    status: Literal["success", "warning", "error", "idle"]
    started_at: str
    finished_at: str | None
    duration_ms: int | None


class DashboardSummaryAlertResponse(BaseModel):
    id: str
    severity: Literal["info", "warning", "error"]
    title: str
    message: str
    source: str
    created_at: str


class DashboardSummaryQuickLinkResponse(BaseModel):
    id: str
    label: str
    href: str
    count: int


class DashboardSummaryHealthResponse(BaseModel):
    id: str
    status: Literal["healthy", "degraded", "offline"]
    label: str
    summary: str
    updated_at: str


class DashboardSummaryServiceResponse(BaseModel):
    id: str
    name: str
    status: Literal["healthy", "degraded", "offline"]
    detail: str
    last_check_at: str


class DashboardSummaryRuntimeOverviewResponse(BaseModel):
    scheduler_active: bool
    queue_status: Literal["running", "paused"]
    queue_pending_jobs: int
    queue_claimed_jobs: int
    queue_updated_at: str
    scheduler_last_tick_started_at: str | None
    scheduler_last_tick_finished_at: str | None


class DashboardSummaryWorkerHealthResponse(BaseModel):
    total: int
    healthy: int
    offline: int


class DashboardSummaryApiPerformanceResponse(BaseModel):
    inbound_total_24h: int
    inbound_errors_24h: int
    error_rate_percent_24h: float
    outgoing_scheduled_enabled: int
    outgoing_continuous_enabled: int


class DashboardSummaryConnectorHealthResponse(BaseModel):
    total: int
    connected: int
    needs_attention: int
    expired: int
    revoked: int
    draft: int
    pending_oauth: int


class DashboardSummaryApiResponse(BaseModel):
    health: DashboardSummaryHealthResponse
    services: list[DashboardSummaryServiceResponse]
    run_counts: DashboardSummaryRunCountsResponse
    recent_runs: list[DashboardSummaryRecentRunResponse]
    alerts: list[DashboardSummaryAlertResponse]
    quick_links: list[DashboardSummaryQuickLinkResponse]
    runtime_overview: DashboardSummaryRuntimeOverviewResponse
    worker_health: DashboardSummaryWorkerHealthResponse
    api_performance: DashboardSummaryApiPerformanceResponse
    connector_health: DashboardSummaryConnectorHealthResponse


class WorkerRegistrationRequest(BaseModel):
    worker_id: str | None = Field(default=None, min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=255)
    capabilities: list[str] = Field(default_factory=list)


class WorkerResponse(BaseModel):
    worker_id: str
    name: str
    hostname: str
    address: str
    capabilities: list[str]
    status: str
    created_at: str
    updated_at: str
    last_seen_at: str


class WorkerClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)


class WorkerClaimedJobResponse(BaseModel):
    job_id: str
    run_id: str
    step_id: str
    worker_id: str
    worker_name: str
    trigger: dict[str, Any]
    claimed_at: str


class WorkerClaimResponse(BaseModel):
    job: WorkerClaimedJobResponse | None


class WorkerCompletionRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    job_id: str = Field(min_length=1, max_length=120)
    status: Literal["completed", "failed"]
    response_summary: str | None = Field(default=None, max_length=500)
    error_summary: str | None = Field(default=None, max_length=500)
    detail: dict[str, Any] | None = None


class RuntimeMachineResponse(BaseModel):
    id: str
    name: str
    hostname: str
    address: str
    status: str
    is_local: bool
    capabilities: list[str]


class WorkerRpcStatusResponse(BaseModel):
    worker_id: str
    worker_name: str
    ok: bool
    error: str | None = None


__all__ = [
    "DashboardDeviceResponse",
    "DashboardDevicesApiResponse",
    "DashboardSummaryAlertResponse",
    "DashboardSummaryApiPerformanceResponse",
    "DashboardSummaryApiResponse",
    "DashboardSummaryConnectorHealthResponse",
    "DashboardSummaryHealthResponse",
    "DashboardSummaryQuickLinkResponse",
    "DashboardSummaryRecentRunResponse",
    "DashboardSummaryRunCountsResponse",
    "DashboardSummaryRuntimeOverviewResponse",
    "DashboardSummaryServiceResponse",
    "DashboardSummaryWorkerHealthResponse",
    "DashboardQueueApiResponse",
    "DashboardQueueJobResponse",
    "HostMachineSummary",
    "RuntimeMachineResponse",
    "WorkerClaimedJobResponse",
    "WorkerClaimRequest",
    "WorkerClaimResponse",
    "WorkerCompletionRequest",
    "WorkerRegistrationRequest",
    "WorkerRpcStatusResponse",
    "WorkerResponse",
]
