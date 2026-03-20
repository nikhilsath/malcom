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


__all__ = [
    "DashboardDeviceResponse",
    "DashboardDevicesApiResponse",
    "DashboardQueueApiResponse",
    "DashboardQueueJobResponse",
    "HostMachineSummary",
    "RuntimeMachineResponse",
    "WorkerClaimedJobResponse",
    "WorkerClaimRequest",
    "WorkerClaimResponse",
    "WorkerCompletionRequest",
    "WorkerRegistrationRequest",
    "WorkerResponse",
]