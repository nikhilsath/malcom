from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field

from backend.services.support import get_connection, get_root_dir
from backend.services.storage_locations import (
    check_location_quota,
    create_storage_location,
    delete_storage_location,
    get_current_location_usage,
    get_storage_location,
    list_storage_locations,
    update_storage_location,
)
from backend.services.repo_checkout_service import (
    clone_or_pull_repo,
    create_repo_checkout,
    delete_repo_checkout,
    get_repo_checkout,
    list_repo_checkouts,
)

try:
    from fastapi import Request
except ImportError:
    Request = Any  # type: ignore[misc,assignment]

router = APIRouter()


# ── Pydantic models ───────────────────────────────────────────────────────────


class StorageLocationCreate(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    location_type: str = Field(pattern=r"^(local|google_drive|repo)$")
    path: str | None = Field(default=None, max_length=1000)
    connector_id: str | None = Field(default=None, max_length=120)
    folder_template: str | None = Field(default=None, max_length=500)
    file_name_template: str | None = Field(default=None, max_length=500)
    max_size_mb: int | None = Field(default=None, ge=1)
    is_default_logs: bool = False


class StorageLocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_type: str | None = Field(default=None, pattern=r"^(local|google_drive|repo)$")
    path: str | None = Field(default=None, max_length=1000)
    connector_id: str | None = Field(default=None, max_length=120)
    folder_template: str | None = Field(default=None, max_length=500)
    file_name_template: str | None = Field(default=None, max_length=500)
    max_size_mb: int | None = Field(default=None, ge=1)
    is_default_logs: bool | None = None


class StorageLocationResponse(BaseModel):
    id: str
    name: str
    location_type: str
    path: str | None
    connector_id: str | None
    folder_template: str | None
    file_name_template: str | None
    max_size_mb: int | None
    is_default_logs: bool
    created_at: str
    updated_at: str


class StorageLocationUsageResponse(BaseModel):
    location_id: str
    size_bytes: int
    size_mb: float
    max_size_mb: int | None
    quota_used_pct: float | None


class RepoCheckoutCreate(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    storage_location_id: str = Field(min_length=1, max_length=120)
    repo_url: str = Field(min_length=1, max_length=2000)
    local_path: str = Field(min_length=1, max_length=1000)
    branch: str = Field(default="main", min_length=1, max_length=255)


class RepoCheckoutResponse(BaseModel):
    id: str
    storage_location_id: str
    repo_url: str
    local_path: str
    branch: str
    last_synced_at: str | None
    size_bytes: int | None
    created_at: str
    updated_at: str


class RepoSyncResponse(BaseModel):
    action: str
    local_path: str
    branch: str
    size_bytes: int


# ── Storage location routes ───────────────────────────────────────────────────


def _row_to_location_response(row: dict[str, Any]) -> StorageLocationResponse:
    return StorageLocationResponse(
        id=row["id"],
        name=row["name"],
        location_type=row["location_type"],
        path=row.get("path"),
        connector_id=row.get("connector_id"),
        folder_template=row.get("folder_template"),
        file_name_template=row.get("file_name_template"),
        max_size_mb=row.get("max_size_mb"),
        is_default_logs=bool(row.get("is_default_logs", 0)),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/api/v1/storage/locations", response_model=list[StorageLocationResponse])
def list_storage_locations_endpoint(request: Request) -> list[StorageLocationResponse]:
    rows = list_storage_locations(get_connection(request))
    return [_row_to_location_response(row) for row in rows]


@router.post(
    "/api/v1/storage/locations",
    response_model=StorageLocationResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_storage_location_endpoint(
    payload: StorageLocationCreate, request: Request
) -> StorageLocationResponse:
    try:
        row = create_storage_location(get_connection(request), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return _row_to_location_response(row)


@router.put("/api/v1/storage/locations/{location_id}", response_model=StorageLocationResponse)
def update_storage_location_endpoint(
    location_id: str, payload: StorageLocationUpdate, request: Request
) -> StorageLocationResponse:
    try:
        row = update_storage_location(
            get_connection(request),
            location_id,
            {k: v for k, v in payload.model_dump().items() if v is not None},
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Storage location not found.")
    return _row_to_location_response(row)


@router.delete("/api/v1/storage/locations/{location_id}")
def delete_storage_location_endpoint(location_id: str, request: Request) -> dict[str, Any]:
    if get_storage_location(get_connection(request), location_id) is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Storage location not found.")
    delete_storage_location(get_connection(request), location_id)
    return {"ok": True, "id": location_id}


@router.get(
    "/api/v1/storage/locations/{location_id}/usage",
    response_model=StorageLocationUsageResponse,
)
def get_storage_location_usage_endpoint(
    location_id: str, request: Request
) -> StorageLocationUsageResponse:
    if get_storage_location(get_connection(request), location_id) is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Storage location not found.")
    usage = get_current_location_usage(
        get_connection(request), location_id, root_dir=get_root_dir(request)
    )
    return StorageLocationUsageResponse(**usage)


# ── Repo checkout routes ──────────────────────────────────────────────────────


def _row_to_checkout_response(row: dict[str, Any]) -> RepoCheckoutResponse:
    return RepoCheckoutResponse(
        id=row["id"],
        storage_location_id=row["storage_location_id"],
        repo_url=row["repo_url"],
        local_path=row["local_path"],
        branch=row.get("branch") or "main",
        last_synced_at=row.get("last_synced_at"),
        size_bytes=row.get("size_bytes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/api/v1/storage/repos", response_model=list[RepoCheckoutResponse])
def list_repo_checkouts_endpoint(request: Request) -> list[RepoCheckoutResponse]:
    rows = list_repo_checkouts(get_connection(request))
    return [_row_to_checkout_response(row) for row in rows]


@router.post(
    "/api/v1/storage/repos",
    response_model=RepoCheckoutResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def create_repo_checkout_endpoint(
    payload: RepoCheckoutCreate, request: Request
) -> RepoCheckoutResponse:
    try:
        row = create_repo_checkout(get_connection(request), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return _row_to_checkout_response(row)


@router.delete("/api/v1/storage/repos/{checkout_id}")
def delete_repo_checkout_endpoint(checkout_id: str, request: Request) -> dict[str, Any]:
    if get_repo_checkout(get_connection(request), checkout_id) is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Repo checkout not found.")
    delete_repo_checkout(get_connection(request), checkout_id)
    return {"ok": True, "id": checkout_id}


@router.post("/api/v1/storage/repos/{checkout_id}/sync", response_model=RepoSyncResponse)
def sync_repo_checkout_endpoint(checkout_id: str, request: Request) -> RepoSyncResponse:
    if get_repo_checkout(get_connection(request), checkout_id) is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Repo checkout not found.")
    try:
        result = clone_or_pull_repo(get_connection(request), checkout_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return RepoSyncResponse(**result)
