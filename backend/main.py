from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.database import DEFAULT_DB_PATH, connect, fetch_all, fetch_one, initialize
from backend.runtime import RuntimeTrigger, runtime_event_bus
from backend.tool_registry import get_project_root, update_tool_metadata, write_tools_manifest


INBOUND_SECRET_PREFIX = "malcom_sk_v1_"
INBOUND_SECRET_BYTES = 32


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_ui_dir(root_dir: Path) -> Path:
    return root_dir / "ui"


def get_ui_dist_dir(root_dir: Path) -> Path:
    return get_ui_dir(root_dir) / "dist"


def ensure_built_ui(root_dir: Path) -> None:
    dist_dir = get_ui_dist_dir(root_dir)
    required_paths = [
        dist_dir / "index.html",
        dist_dir / "dashboard" / "overview.html",
        dist_dir / "assets",
    ]
    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_display = ", ".join(str(path.relative_to(root_dir)) for path in missing_paths)
        raise RuntimeError(
            "Built UI assets are missing. Run './malcom' or 'npm run build' in 'ui/' before starting the backend. "
            f"Missing: {missing_display}"
        )


def get_built_ui_file(root_dir: Path, relative_path: str) -> Path:
    return get_ui_dist_dir(root_dir) / relative_path


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_secret() -> str:
    encoded_secret = base64.urlsafe_b64encode(secrets.token_bytes(INBOUND_SECRET_BYTES)).decode("ascii").rstrip("=")
    return f"{INBOUND_SECRET_PREFIX}{encoded_secret}"


def developer_mode_enabled(request: Request) -> bool:
    return request.headers.get("x-developer-mode", "").lower() == "true"


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


def seed_developer_mock_data(connection: sqlite3.Connection) -> None:
    existing_row = fetch_one(
        connection,
        "SELECT id FROM inbound_apis WHERE is_mock = 1 LIMIT 1",
    )

    if existing_row is not None:
        return

    now = utc_now_iso()
    # Developer mode keeps a fixed token so local UI verification remains deterministic.
    # Production inbound APIs always use generate_secret().
    secret = "malcom_dev_demo_token"
    connection.execute(
        """
        INSERT INTO inbound_apis (
            id,
            name,
            description,
            path_slug,
            auth_type,
            secret_hash,
            is_mock,
            enabled,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "demo_webhook",
            "Demo Webhook",
            "Seeded developer-mode endpoint for local UI verification.",
            "demo-webhook",
            "bearer",
            hash_secret(secret),
            1,
            1,
            now,
            now,
        ),
    )
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
            error_message,
            is_mock
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "evt_demo001",
            "demo_webhook",
            now,
            "accepted",
            json.dumps(
                {
                    "content-type": "application/json",
                    "user-agent": "developer-mode",
                }
            ),
            json.dumps(
                {
                    "source": "developer-mode",
                    "ok": True,
                }
            ),
            "127.0.0.1",
            None,
            1,
        ),
    )
    connection.execute(
        """
        INSERT INTO outgoing_scheduled_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            schedule_expression,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "scheduled_demo_push",
            "Scheduled Demo Push",
            "Runs every hour in developer mode.",
            "scheduled-demo-push",
            1,
            1,
            "0 * * * *",
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO outgoing_continuous_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            stream_mode,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "continuous_demo_stream",
            "Continuous Demo Stream",
            "Always-on outbound developer-mode stream.",
            "continuous-demo-stream",
            1,
            1,
            "continuous",
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO webhook_apis (
            id,
            name,
            description,
            path_slug,
            is_mock,
            enabled,
            delivery_mode,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "webhook_demo_registry",
            "Demo Webhook Registry",
            "Developer-mode webhook definition.",
            "webhook-demo-registry",
            1,
            1,
            "webhook",
            now,
            now,
        ),
    )
    connection.commit()


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




def row_to_run(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "automation_id": row["automation_id"],
        "trigger_type": row["trigger_type"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
        "error_summary": row["error_summary"],
    }


def row_to_run_step(row: sqlite3.Row) -> dict[str, Any]:
    detail_json = row["detail_json"]
    return {
        "step_id": row["step_id"],
        "run_id": row["run_id"],
        "step_name": row["step_name"],
        "status": row["status"],
        "request_summary": row["request_summary"],
        "response_summary": row["response_summary"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
        "detail_json": json.loads(detail_json) if detail_json else None,
    }
def row_to_simple_api_resource(
    row: sqlite3.Row,
    *,
    api_type: str,
    endpoint_path: str | None = None,
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": api_type,
        "name": row["name"],
        "description": row["description"],
        "path_slug": row["path_slug"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "endpoint_path": endpoint_path,
    }


DEFAULT_APP_SETTINGS: dict[str, Any] = {
    "general": {
        "environment": "staging",
        "timezone": "local",
        "preview_mode": True,
    },
    "logging": {
        "max_stored_entries": 250,
        "max_visible_entries": 50,
        "max_detail_characters": 4000,
    },
    "notifications": {
        "channel": "slack",
        "digest": "hourly",
        "escalate_oncall": True,
    },
    "security": {
        "session_timeout_minutes": 30,
        "dual_approval_required": True,
        "token_rotation_days": 90,
    },
    "data": {
        "payload_redaction": True,
        "export_window_utc": "02:00",
        "audit_retention_days": 365,
    },
}


def get_default_settings() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_APP_SETTINGS))


def seed_default_settings(connection: sqlite3.Connection) -> None:
    now = utc_now_iso()

    for key, value in get_default_settings().items():
        connection.execute(
            """
            INSERT INTO settings (key, value_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            (key, json.dumps(value), now, now),
        )

    connection.commit()


def get_settings_payload(connection: sqlite3.Connection) -> dict[str, Any]:
    settings = get_default_settings()
    rows = fetch_all(
        connection,
        """
        SELECT key, value_json
        FROM settings
        """,
    )

    for row in rows:
        if row["key"] not in settings:
            continue
        settings[row["key"]] = json.loads(row["value_json"])

    return settings


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


class ApiResourceCreate(BaseModel):
    type: str = Field(pattern=r"^(incoming|outgoing_scheduled|outgoing_continuous|webhook)$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    path_slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool = True


class ApiResourceResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    path_slug: str
    enabled: bool
    created_at: str
    updated_at: str
    endpoint_path: str | None = None
    endpoint_url: str | None = None
    secret: str | None = None


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




class AutomationRunStepResponse(BaseModel):
    step_id: str
    run_id: str
    step_name: str
    status: str
    request_summary: str | None
    response_summary: str | None
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    detail_json: dict[str, Any] | None


class AutomationRunResponse(BaseModel):
    run_id: str
    automation_id: str
    trigger_type: str
    status: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    error_summary: str | None


class AutomationRunDetailResponse(AutomationRunResponse):
    steps: list[AutomationRunStepResponse]
class ToolMetadataResponse(BaseModel):
    id: str
    name: str
    description: str


class ToolMetadataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class GeneralSettings(BaseModel):
    environment: str = Field(pattern=r"^(staging|production|lab)$")
    timezone: str = Field(pattern=r"^(utc|local|ops)$")
    preview_mode: bool


class LoggingSettings(BaseModel):
    max_stored_entries: int = Field(ge=50, le=5000)
    max_visible_entries: int = Field(ge=10, le=500)
    max_detail_characters: int = Field(ge=500, le=20000)


class NotificationSettings(BaseModel):
    channel: str = Field(pattern=r"^(email|slack|pager)$")
    digest: str = Field(pattern=r"^(realtime|hourly|daily)$")
    escalate_oncall: bool


class SecuritySettings(BaseModel):
    session_timeout_minutes: int = Field(ge=15, le=60)
    dual_approval_required: bool
    token_rotation_days: Literal[30, 60, 90]


class DataSettings(BaseModel):
    payload_redaction: bool
    export_window_utc: str = Field(pattern=r"^(00:00|02:00|04:00)$")
    audit_retention_days: Literal[30, 90, 365]


class AppSettingsResponse(BaseModel):
    general: GeneralSettings
    logging: LoggingSettings
    notifications: NotificationSettings
    security: SecuritySettings
    data: DataSettings


class AppSettingsUpdate(BaseModel):
    general: GeneralSettings | None = None
    logging: LoggingSettings | None = None
    notifications: NotificationSettings | None = None
    security: SecuritySettings | None = None
    data: DataSettings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = connect(Path(app.state.db_path))
    initialize(connection)
    seed_developer_mock_data(connection)
    seed_default_settings(connection)
    write_tools_manifest(Path(app.state.root_dir), connection)
    ensure_built_ui(Path(app.state.root_dir))
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
app.mount("/assets", StaticFiles(directory=str(get_ui_dist_dir(get_project_root()) / "assets"), check_dir=False), name="ui-assets")
app.mount("/scripts", StaticFiles(directory=str(get_ui_dir(get_project_root()) / "scripts"), check_dir=False), name="ui-scripts")
app.mount("/modals", StaticFiles(directory=str(get_ui_dir(get_project_root()) / "modals"), check_dir=False), name="ui-modals")


UI_HTML_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/settings.html": "settings.html",
    "/settings/general.html": "settings/general.html",
    "/settings/logging.html": "settings/logging.html",
    "/settings/notifications.html": "settings/notifications.html",
    "/settings/security.html": "settings/security.html",
    "/settings/data.html": "settings/data.html",
    "/apis.html": "apis.html",
    "/tools.html": "tools.html",
    "/apis/overview.html": "apis/overview.html",
    "/apis/incoming.html": "apis/incoming.html",
    "/apis/outgoing.html": "apis/outgoing.html",
    "/apis/webhooks.html": "apis/webhooks.html",
    "/tools/overview.html": "tools/overview.html",
    "/tools/sftp.html": "tools/sftp.html",
    "/tools/storage.html": "tools/storage.html",
    "/dashboard/overview.html": "dashboard/overview.html",
}


def get_ui_html_response(relative_path: str, request: Request) -> FileResponse:
    root_dir = get_root_dir(request)
    ensure_built_ui(root_dir)
    html_path = get_built_ui_file(root_dir, relative_path)

    if not html_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UI page not found.")

    return FileResponse(html_path)


def build_ui_route(relative_path: str):
    def serve_ui_route(request: Request) -> FileResponse:
        return get_ui_html_response(relative_path, request)

    return serve_ui_route


@app.get("/dashboard")
@app.get("/dashboard/")
def redirect_dashboard_root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/overview.html")


@app.get("/settings")
@app.get("/settings/")
def redirect_settings_root() -> RedirectResponse:
    return RedirectResponse(url="/settings/general.html")


@app.get("/dashboard/devices.html")
def redirect_dashboard_devices() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/overview.html#/devices")


@app.get("/dashboard/logs.html")
def redirect_dashboard_logs() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/overview.html#/logs")


@app.get("/apis")
@app.get("/apis/")
def redirect_apis_root() -> RedirectResponse:
    return RedirectResponse(url="/apis/overview.html")


@app.get("/tools")
@app.get("/tools/")
def redirect_tools_root() -> RedirectResponse:
    return RedirectResponse(url="/tools/overview.html")


for route_path, relative_path in UI_HTML_ROUTES.items():
    app.add_api_route(
        route_path,
        build_ui_route(relative_path),
        methods=["GET"],
        include_in_schema=False,
    )


def get_connection(request: Request) -> sqlite3.Connection:
    return request.app.state.connection


def get_root_dir(request: Request) -> Path:
    return Path(request.app.state.root_dir)


def get_api_or_404(connection: sqlite3.Connection, api_id: str, *, include_mock: bool = True) -> sqlite3.Row:
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
        AND (? = 1 OR inbound_apis.is_mock = 0)
        """,
        (api_id, int(include_mock)),
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound API not found.")

    return row


def serialize_api_detail(connection: sqlite3.Connection, api_id: str, request: Request) -> InboundApiDetail:
    api_row = get_api_or_404(connection, api_id, include_mock=developer_mode_enabled(request))
    event_rows = fetch_all(
        connection,
        """
        SELECT event_id, api_id, received_at, status, request_headers_subset, payload_json, source_ip, error_message
        FROM inbound_api_events
        WHERE api_id = ?
        AND (? = 1 OR is_mock = 0)
        ORDER BY received_at DESC
        LIMIT 20
        """,
        (api_id, int(developer_mode_enabled(request))),
    )
    detail = row_to_api_summary(api_row)
    detail["endpoint_url"] = str(request.base_url).rstrip("/") + detail["endpoint_path"]
    detail["events"] = [row_to_event(row) for row in event_rows]
    return InboundApiDetail(**detail)


def get_resource_config(resource_type: str) -> dict[str, str]:
    configs = {
        "incoming": {
            "table": "inbound_apis",
            "id_prefix": "inbound",
            "path_prefix": "/api/v1/inbound",
        },
        "outgoing_scheduled": {
            "table": "outgoing_scheduled_apis",
            "id_prefix": "outgoing_scheduled",
            "path_prefix": "/api/v1/outgoing/scheduled",
        },
        "outgoing_continuous": {
            "table": "outgoing_continuous_apis",
            "id_prefix": "outgoing_continuous",
            "path_prefix": "/api/v1/outgoing/continuous",
        },
        "webhook": {
            "table": "webhook_apis",
            "id_prefix": "webhook",
            "path_prefix": "/api/v1/webhooks",
        },
    }
    return configs[resource_type]


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
    is_mock: bool = False,
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
            error_message,
            is_mock
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            int(is_mock),
        ),
    )
    connection.commit()




def calculate_duration_ms(started_at: str, finished_at: str) -> int:
    started = datetime.fromisoformat(started_at)
    finished = datetime.fromisoformat(finished_at)
    return max(int((finished - started).total_seconds() * 1000), 0)


def create_automation_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    automation_id: str,
    trigger_type: str,
    status_value: str,
    started_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO automation_runs (
            run_id,
            automation_id,
            trigger_type,
            status,
            started_at,
            finished_at,
            duration_ms,
            error_summary
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
        """,
        (run_id, automation_id, trigger_type, status_value, started_at),
    )
    connection.commit()


def create_automation_run_step(
    connection: sqlite3.Connection,
    *,
    step_id: str,
    run_id: str,
    step_name: str,
    status_value: str,
    request_summary: str | None,
    started_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO automation_run_steps (
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
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)
        """,
        (step_id, run_id, step_name, status_value, request_summary, started_at),
    )
    connection.commit()


def finalize_automation_run_step(
    connection: sqlite3.Connection,
    *,
    step_id: str,
    status_value: str,
    response_summary: str | None,
    detail: dict[str, Any] | None,
    finished_at: str,
) -> None:
    step_row = fetch_one(connection, "SELECT started_at FROM automation_run_steps WHERE step_id = ?", (step_id,))

    if step_row is None:
        return

    duration_ms = calculate_duration_ms(step_row["started_at"], finished_at)
    connection.execute(
        """
        UPDATE automation_run_steps
        SET status = ?,
            response_summary = ?,
            finished_at = ?,
            duration_ms = ?,
            detail_json = ?
        WHERE step_id = ?
        """,
        (
            status_value,
            response_summary,
            finished_at,
            duration_ms,
            json.dumps(detail) if detail is not None else None,
            step_id,
        ),
    )
    connection.commit()


def finalize_automation_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    status_value: str,
    error_summary: str | None,
    finished_at: str,
) -> None:
    run_row = fetch_one(connection, "SELECT started_at FROM automation_runs WHERE run_id = ?", (run_id,))

    if run_row is None:
        return

    duration_ms = calculate_duration_ms(run_row["started_at"], finished_at)
    connection.execute(
        """
        UPDATE automation_runs
        SET status = ?,
            finished_at = ?,
            duration_ms = ?,
            error_summary = ?
        WHERE run_id = ?
        """,
        (status_value, finished_at, duration_ms, error_summary, run_id),
    )
    connection.commit()
@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/settings", response_model=AppSettingsResponse)
def get_app_settings(request: Request) -> AppSettingsResponse:
    payload = get_settings_payload(get_connection(request))
    return AppSettingsResponse(**payload)


@app.patch("/api/v1/settings", response_model=AppSettingsResponse)
def patch_app_settings(payload: AppSettingsUpdate, request: Request) -> AppSettingsResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        return AppSettingsResponse(**get_settings_payload(connection))

    now = utc_now_iso()

    for key, value in changes.items():
        connection.execute(
            """
            INSERT INTO settings (key, value_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """
            ,
            (key, json.dumps(value), now, now),
        )

    connection.commit()
    return AppSettingsResponse(**get_settings_payload(connection))


@app.get("/api/v1/inbound", response_model=list[InboundApiResponse])
def list_inbound_apis(request: Request) -> list[InboundApiResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT
            inbound_apis.*,
            COUNT(CASE WHEN ? = 1 OR inbound_api_events.is_mock = 0 THEN inbound_api_events.event_id END) AS events_count,
            MAX(CASE WHEN ? = 1 OR inbound_api_events.is_mock = 0 THEN inbound_api_events.received_at END) AS last_received_at,
            (
                SELECT status
                FROM inbound_api_events AS latest_events
                WHERE latest_events.api_id = inbound_apis.id
                AND (? = 1 OR latest_events.is_mock = 0)
                ORDER BY latest_events.received_at DESC
                LIMIT 1
            ) AS last_delivery_status
        FROM inbound_apis
        LEFT JOIN inbound_api_events ON inbound_api_events.api_id = inbound_apis.id
        WHERE (? = 1 OR inbound_apis.is_mock = 0)
        GROUP BY inbound_apis.id
        ORDER BY inbound_apis.created_at DESC
        """
        ,
        (int(include_mock), int(include_mock), int(include_mock), int(include_mock)),
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
                is_mock,
                enabled,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                api_id,
                payload.name,
                payload.description,
                payload.path_slug,
                "bearer",
                hash_secret(secret),
                0,
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


@app.get("/api/v1/outgoing/scheduled", response_model=list[ApiResourceResponse])
def list_outgoing_scheduled_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, created_at, updated_at
        FROM outgoing_scheduled_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_scheduled", endpoint_path="/api/v1/outgoing/scheduled"))
        for row in rows
    ]


@app.get("/api/v1/outgoing/continuous", response_model=list[ApiResourceResponse])
def list_outgoing_continuous_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, created_at, updated_at
        FROM outgoing_continuous_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="outgoing_continuous", endpoint_path="/api/v1/outgoing/continuous"))
        for row in rows
    ]


@app.get("/api/v1/webhooks", response_model=list[ApiResourceResponse])
def list_webhook_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, created_at, updated_at
        FROM webhook_apis
        WHERE (? = 1 OR is_mock = 0)
        ORDER BY created_at DESC
        """,
        (int(include_mock),),
    )
    return [
        ApiResourceResponse(**row_to_simple_api_resource(row, api_type="webhook", endpoint_path="/api/v1/webhooks"))
        for row in rows
    ]


@app.post("/api/v1/apis", response_model=ApiResourceResponse, status_code=status.HTTP_201_CREATED)
def create_api_resource(payload: ApiResourceCreate, request: Request) -> ApiResourceResponse:
    connection = get_connection(request)
    now = utc_now_iso()
    config = get_resource_config(payload.type)
    api_id = payload.path_slug.replace("-", "_") + "_" + uuid4().hex[:6]

    try:
        if payload.type == "incoming":
            secret = generate_secret()
            connection.execute(
                """
                INSERT INTO inbound_apis (
                    id,
                    name,
                    description,
                    path_slug,
                    auth_type,
                    secret_hash,
                    is_mock,
                    enabled,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    "bearer",
                    hash_secret(secret),
                    0,
                    int(payload.enabled),
                    now,
                    now,
                ),
            )
        elif payload.type == "outgoing_scheduled":
            connection.execute(
                """
                INSERT INTO outgoing_scheduled_apis (
                    id,
                    name,
                    description,
                    path_slug,
                    is_mock,
                    enabled,
                    schedule_expression,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    "0 * * * *",
                    now,
                    now,
                ),
            )
        elif payload.type == "outgoing_continuous":
            connection.execute(
                """
                INSERT INTO outgoing_continuous_apis (
                    id,
                    name,
                    description,
                    path_slug,
                    is_mock,
                    enabled,
                    stream_mode,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    "continuous",
                    now,
                    now,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO webhook_apis (
                    id,
                    name,
                    description,
                    path_slug,
                    is_mock,
                    enabled,
                    delivery_mode,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    "webhook",
                    now,
                    now,
                ),
            )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

    row = fetch_one(
        connection,
        f"""
        SELECT id, name, description, path_slug, enabled, created_at, updated_at
        FROM {config['table']}
        WHERE id = ?
        """,
        (api_id,),
    )
    assert row is not None
    endpoint_path = config["path_prefix"] if payload.type != "incoming" else f"/api/v1/inbound/{api_id}"
    resource = row_to_simple_api_resource(row, api_type=payload.type, endpoint_path=endpoint_path)
    resource["endpoint_url"] = str(request.base_url).rstrip("/") + endpoint_path

    if payload.type == "incoming":
        resource["secret"] = secret

    return ApiResourceResponse(**resource)


@app.get("/api/v1/inbound/{api_id}", response_model=InboundApiDetail)
def get_inbound_api(api_id: str, request: Request) -> InboundApiDetail:
    connection = get_connection(request)
    return serialize_api_detail(connection, api_id, request)


@app.patch("/api/v1/inbound/{api_id}", response_model=InboundApiResponse)
def update_inbound_api(api_id: str, payload: InboundApiUpdate, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    current = get_api_or_404(connection, api_id, include_mock=True)
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
    api_row = get_api_or_404(connection, api_id, include_mock=True)
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
    get_api_or_404(connection, api_id, include_mock=True)
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
    api_row = get_api_or_404(connection, api_id, include_mock=True)

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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
            is_mock=bool(api_row["is_mock"]),
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
        is_mock=bool(api_row["is_mock"]),
    )

    trigger = RuntimeTrigger(
        type="inbound_api",
        api_id=api_id,
        event_id=event_id,
        payload=payload,
        received_at=received_at,
    )

    run_id = f"run_{uuid4().hex}"
    step_id = f"step_{uuid4().hex}"
    create_automation_run(
        connection,
        run_id=run_id,
        automation_id=api_id,
        trigger_type=trigger.type,
        status_value="running",
        started_at=received_at,
    )
    create_automation_run_step(
        connection,
        step_id=step_id,
        run_id=run_id,
        step_name="emit_runtime_trigger",
        status_value="running",
        request_summary=f"event_id={event_id}",
        started_at=received_at,
    )

    finished_at = utc_now_iso()
    runtime_event_bus.emit(trigger)
    finalize_automation_run_step(
        connection,
        step_id=step_id,
        status_value="completed",
        response_summary="Trigger emitted to runtime event bus.",
        detail={"event_id": event_id, "api_id": api_id},
        finished_at=finished_at,
    )
    finalize_automation_run(
        connection,
        run_id=run_id,
        status_value="completed",
        error_summary=None,
        finished_at=finished_at,
    )

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




@app.get("/api/v1/runs", response_model=list[AutomationRunResponse])
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


@app.get("/api/v1/runs/{run_id}", response_model=AutomationRunDetailResponse)
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
            detail_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )

    detail = row_to_run(run_row)
    detail["steps"] = [row_to_run_step(step_row) for step_row in step_rows]
    return AutomationRunDetailResponse(**detail)
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
