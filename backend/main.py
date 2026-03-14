from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from backend.database import DEFAULT_DB_PATH, connect, fetch_all, fetch_one, initialize
from backend.runtime import RuntimeTrigger, runtime_event_bus
from backend.tool_registry import get_project_root, update_tool_metadata, write_tools_manifest


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_secret() -> str:
    return f"malcom_{secrets.token_urlsafe(24)}"


def header_subset(headers: Any) -> dict[str, str]:
    allowed_headers = {"content-type", "user-agent", "x-request-id"}
    return {
        key.lower(): value
        for key, value in headers.items()
        if key.lower() in allowed_headers
    }


def row_to_api_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "path_slug": row["path_slug"],
        "auth_type": row["auth_type"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "endpoint_path": f"/api/v1/inbound/{row['id']}",
        "last_received_at": row["last_received_at"],
        "last_delivery_status": row["last_delivery_status"],
        "events_count": row["events_count"],
    }


def row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    payload_json = row["payload_json"]
    return {
        "event_id": row["event_id"],
        "api_id": row["api_id"],
        "received_at": row["received_at"],
        "status": row["status"],
        "request_headers_subset": json.loads(row["request_headers_subset"]),
        "payload_json": json.loads(payload_json) if payload_json else None,
        "source_ip": row["source_ip"],
        "error_message": row["error_message"],
    }


class InboundApiCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    path_slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool = True


class InboundApiUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None


class InboundReceiveAccepted(BaseModel):
    status: str
    event_id: str
    trigger: dict[str, Any]


class InboundSecretResponse(BaseModel):
    id: str
    secret: str
    endpoint_url: str


class InboundApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    path_slug: str
    auth_type: str
    enabled: bool
    created_at: str
    updated_at: str
    endpoint_path: str
    last_received_at: str | None
    last_delivery_status: str | None
    events_count: int


class InboundApiCreated(InboundApiResponse):
    secret: str
    endpoint_url: str


class InboundApiDetail(InboundApiResponse):
    endpoint_url: str
    events: list[dict[str, Any]]


class ToolMetadataResponse(BaseModel):
    id: str
    name: str
    description: str


class ToolMetadataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = connect(Path(app.state.db_path))
    initialize(connection)
    write_tools_manifest(Path(app.state.root_dir), connection)
    app.state.connection = connection
    try:
        yield
    finally:
        connection.close()


app = FastAPI(title="Malcom API", version="0.1.0", lifespan=lifespan)
app.state.db_path = str(DEFAULT_DB_PATH)
app.state.root_dir = get_project_root()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection(request: Request) -> sqlite3.Connection:
    return request.app.state.connection


def get_root_dir(request: Request) -> Path:
    return Path(request.app.state.root_dir)


def get_api_or_404(connection: sqlite3.Connection, api_id: str) -> sqlite3.Row:
    row = fetch_one(
        connection,
        """
        SELECT
            inbound_apis.*,
            (
                SELECT COUNT(*)
                FROM inbound_api_events
                WHERE inbound_api_events.api_id = inbound_apis.id
            ) AS events_count,
            (
                SELECT received_at
                FROM inbound_api_events
                WHERE inbound_api_events.api_id = inbound_apis.id
                ORDER BY received_at DESC
                LIMIT 1
            ) AS last_received_at,
            (
                SELECT status
                FROM inbound_api_events
                WHERE inbound_api_events.api_id = inbound_apis.id
                ORDER BY received_at DESC
                LIMIT 1
            ) AS last_delivery_status
        FROM inbound_apis
        WHERE id = ?
        """,
        (api_id,),
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound API not found.")

    return row


def serialize_api_detail(connection: sqlite3.Connection, api_id: str, request: Request) -> InboundApiDetail:
    api_row = get_api_or_404(connection, api_id)
    event_rows = fetch_all(
        connection,
        """
        SELECT event_id, api_id, received_at, status, request_headers_subset, payload_json, source_ip, error_message
        FROM inbound_api_events
        WHERE api_id = ?
        ORDER BY received_at DESC
        LIMIT 20
        """,
        (api_id,),
    )
    detail = row_to_api_summary(api_row)
    detail["endpoint_url"] = str(request.base_url).rstrip("/") + detail["endpoint_path"]
    detail["events"] = [row_to_event(row) for row in event_rows]
    return InboundApiDetail(**detail)


def log_event(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    api_id: str,
    received_at: str,
    status_value: str,
    headers: dict[str, str],
    payload: Any,
    source_ip: str | None,
    error_message: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO inbound_api_events (
            event_id,
            api_id,
            received_at,
            status,
            request_headers_subset,
            payload_json,
            source_ip,
            error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            api_id,
            received_at,
            status_value,
            json.dumps(headers),
            json.dumps(payload) if payload is not None else None,
            source_ip,
            error_message,
        ),
    )
    connection.commit()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/inbound", response_model=list[InboundApiResponse])
def list_inbound_apis(request: Request) -> list[InboundApiResponse]:
    connection = get_connection(request)
    rows = fetch_all(
        connection,
        """
        SELECT
            inbound_apis.*,
            COUNT(inbound_api_events.event_id) AS events_count,
            MAX(inbound_api_events.received_at) AS last_received_at,
            (
                SELECT status
                FROM inbound_api_events AS latest_events
                WHERE latest_events.api_id = inbound_apis.id
                ORDER BY latest_events.received_at DESC
                LIMIT 1
            ) AS last_delivery_status
        FROM inbound_apis
        LEFT JOIN inbound_api_events ON inbound_api_events.api_id = inbound_apis.id
        GROUP BY inbound_apis.id
        ORDER BY inbound_apis.created_at DESC
        """
    )
    return [InboundApiResponse(**row_to_api_summary(row)) for row in rows]


@app.post("/api/v1/inbound", response_model=InboundApiCreated, status_code=status.HTTP_201_CREATED)
def create_inbound_api(payload: InboundApiCreate, request: Request) -> InboundApiCreated:
    connection = get_connection(request)
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
                enabled,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                api_id,
                payload.name,
                payload.description,
                payload.path_slug,
                "bearer",
                hash_secret(secret),
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
    return InboundApiCreated(**created)


@app.get("/api/v1/inbound/{api_id}", response_model=InboundApiDetail)
def get_inbound_api(api_id: str, request: Request) -> InboundApiDetail:
    connection = get_connection(request)
    return serialize_api_detail(connection, api_id, request)


@app.patch("/api/v1/inbound/{api_id}", response_model=InboundApiResponse)
def update_inbound_api(api_id: str, payload: InboundApiUpdate, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    current = get_api_or_404(connection, api_id)
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
    return InboundApiResponse(**updated)


@app.post("/api/v1/inbound/{api_id}/rotate-secret", response_model=InboundSecretResponse)
def rotate_inbound_api_secret(api_id: str, request: Request) -> InboundSecretResponse:
    connection = get_connection(request)
    api_row = get_api_or_404(connection, api_id)
    secret = generate_secret()
    connection.execute(
        "UPDATE inbound_apis SET secret_hash = ?, updated_at = ? WHERE id = ?",
        (hash_secret(secret), utc_now_iso(), api_row["id"]),
    )
    connection.commit()
    return InboundSecretResponse(
        id=api_id,
        secret=secret,
        endpoint_url=str(request.base_url).rstrip("/") + f"/api/v1/inbound/{api_id}",
    )


@app.post("/api/v1/inbound/{api_id}/disable", response_model=InboundApiResponse)
def disable_inbound_api(api_id: str, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    get_api_or_404(connection, api_id)
    connection.execute(
        "UPDATE inbound_apis SET enabled = 0, updated_at = ? WHERE id = ?",
        (utc_now_iso(), api_id),
    )
    connection.commit()
    return InboundApiResponse(**row_to_api_summary(get_api_or_404(connection, api_id)))


@app.patch("/api/v1/tools/{tool_id}", response_model=ToolMetadataResponse)
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    return ToolMetadataResponse(**updated)


@app.post("/api/v1/inbound/{api_id}", response_model=InboundReceiveAccepted, status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound_event(api_id: str, request: Request, response: Response) -> InboundReceiveAccepted:
    connection = get_connection(request)
    event_id = f"evt_{uuid4().hex[:10]}"
    received_at = utc_now_iso()
    headers = header_subset(request.headers)
    source_ip = request.client.host if request.client else None
    api_row = get_api_or_404(connection, api_id)

    if not api_row["enabled"]:
        log_event(
            connection,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="disabled",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Inbound API is disabled.",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inbound API is disabled.")

    auth_header = request.headers.get("authorization", "")
    expected_secret_hash = api_row["secret_hash"]

    if not auth_header.startswith("Bearer "):
        log_event(
            connection,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unauthorized",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Missing bearer token.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    provided_secret = auth_header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(hash_secret(provided_secret), expected_secret_hash):
        log_event(
            connection,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unauthorized",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Invalid bearer token.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")

    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        log_event(
            connection,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="unsupported_media_type",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message="Only application/json is supported.",
        )
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only application/json is supported.")

    try:
        payload = await request.json()
    except json.JSONDecodeError as error:
        log_event(
            connection,
            event_id=event_id,
            api_id=api_id,
            received_at=received_at,
            status_value="invalid_json",
            headers=headers,
            payload=None,
            source_ip=source_ip,
            error_message=str(error),
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid JSON payload.") from error

    log_event(
        connection,
        event_id=event_id,
        api_id=api_id,
        received_at=received_at,
        status_value="accepted",
        headers=headers,
        payload=payload,
        source_ip=source_ip,
        error_message=None,
    )

    trigger = RuntimeTrigger(
        type="inbound_api",
        api_id=api_id,
        event_id=event_id,
        payload=payload,
        received_at=received_at,
    )
    runtime_event_bus.emit(trigger)
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


@app.get("/api/v1/runtime/triggers")
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
