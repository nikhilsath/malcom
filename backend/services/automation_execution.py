from __future__ import annotations
import ast
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import secrets
import shlex
import inspect
import shutil
import smtplib
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated, Any, Callable, Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from backend.schemas import *
from backend.database import connect, fetch_all, fetch_one, get_database_url, initialize, run_migrations
import httpx
from pydantic import Field, ValidationError
from backend.runtime import (
    RegisteredWorker,
    RuntimeExecutionResult,
    RuntimeTrigger,
    RuntimeTriggerJob,
    next_daily_run_at,
    parse_iso_datetime,
    runtime_event_bus,
    runtime_scheduler,
)
from backend.smtp_runtime import SmtpMachineAssignment, SmtpRuntimeManager
from backend.tool_registry import (
    get_project_root,
    load_tool_directory,
    set_tool_enabled,
    update_tool_metadata,
    write_tools_manifest,
)
from backend.services.scripts import (
    build_script_validation_fields,
    build_script_validation_issue,
    row_to_script_response,
    row_to_script_summary,
    seed_default_scripts,
    validate_javascript_script,
    validate_python_script,
    validate_script_payload,
)
from backend.services.settings import (
    merge_settings_section,
    read_stored_settings_section,
    write_settings_section,
)
from backend.services.network import (
    header_subset,
    build_outgoing_request_headers,
    redact_outgoing_request_headers,
    execute_outgoing_test_delivery,
)
from backend.services.connector_activities import execute_connector_activity
from backend.services.connector_activities_catalog import CONNECTOR_ACTIVITY_DEFINITIONS
from backend.services.http_presets import DEFAULT_HTTP_PRESET_CATALOG
from backend.services.logging_service import (
    configure_application_logger as configure_application_logger_core,
    get_log_file_path as get_log_file_path_core,
    write_application_exception_log as write_application_exception_log_core,
    write_application_log as write_application_log_core,
)
from backend.services.metrics import get_metrics_collector, snapshot_process_cpu_percent, snapshot_process_memory_mb
from backend.services.automation_runs import (
    assign_automation_run_worker as assign_automation_run_worker_core,
    calculate_duration_ms as calculate_duration_ms_core,
    create_automation_run as create_automation_run_core,
    create_automation_run_step as create_automation_run_step_core,
    finalize_automation_run as finalize_automation_run_core,
    finalize_automation_run_step as finalize_automation_run_step_core,
)
from backend.services.connectors import (
    DEFAULT_CONNECTOR_CATALOG,
    ensure_legacy_connector_storage_migrated,
    get_connector_protection_secret,
    get_stored_connector_settings,
    hydrate_outgoing_configuration_from_connector,
)

INBOUND_SECRET_PREFIX = "malcom_sk_v1_"
INBOUND_SECRET_BYTES = 32
LOGGER_NAME = "malcom"
DEFAULT_LOG_FILE_NAME = "malcom.log"
DEFAULT_LOG_BACKUP_COUNT = 5
LOCAL_WORKER_POLL_INTERVAL_SECONDS = 0.25
REMOTE_WORKER_POLL_INTERVAL_SECONDS = 1.0
SMTP_TOOL_SETTINGS_KEY = "smtp_tool"
LOCAL_LLM_TOOL_SETTINGS_KEY = "local_llm_tool"
COQUI_TTS_TOOL_SETTINGS_KEY = "coqui_tts_tool"
IMAGE_MAGIC_TOOL_SETTINGS_KEY = "image_magic_tool"
DatabaseConnection = Any
DatabaseRow = dict[str, Any]
DEFAULT_SMTP_TOOL_CONFIG = {
    "enabled": False,
    "target_worker_id": None,
    "bind_host": "127.0.0.1",
    "port": 2525,
    "recipient_email": None,
}
DEFAULT_LOCAL_LLM_TOOL_CONFIG = {
    "enabled": False,
    "provider": "custom",
    "server_base_url": "",
    "model_identifier": "",
    "endpoints": {
        "models": "",
        "chat": "",
        "model_load": "",
        "model_download": "",
        "model_download_status": "",
    },
}
DEFAULT_COQUI_TTS_TOOL_CONFIG = {
    "enabled": False,
    "command": "tts",
    "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
    "speaker": "",
    "language": "",
    "output_directory": "backend/data/generated/coqui-tts",
}
DEFAULT_IMAGE_MAGIC_TOOL_CONFIG = {
    "enabled": False,
    "target_worker_id": None,
    "command": "magick",
}
DEFAULT_TOOL_RETRY_SETTINGS = {
    "default_tool_retries": 2,
}
SETTINGS_NOTIFICATION_CHANNEL_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "email", "label": "Email digest", "description": "Send alerts through the default email digest route."},
    {"value": "pager", "label": "Pager duty queue", "description": "Route incident alerts into the pager queue."},
)
SETTINGS_NOTIFICATION_DIGEST_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "realtime", "label": "Real time"},
    {"value": "hourly", "label": "Hourly"},
    {"value": "daily", "label": "Daily"},
)
# Scheduled export window options removed — export scheduling not supported
DEFAULT_DASHBOARD_LOG_LEVEL_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "debug", "label": "Debug"},
    {"value": "info", "label": "Info"},
    {"value": "warning", "label": "Warning"},
    {"value": "error", "label": "Error"},
)
RESOURCE_SNAPSHOT_INTERVAL_SECONDS = 10.0
RESOURCE_SNAPSHOT_DEFAULT_LIMIT = 30
_RESOURCE_SNAPSHOT_LOCK = threading.Lock()
_RESOURCE_SNAPSHOT_LAST_PERSISTED_AT_MONOTONIC = 0.0

LOCAL_LLM_ENDPOINT_PRESETS: dict[str, dict[str, Any]] = {
    "custom": {
        "label": "Custom",
        "server_base_url": "",
        "endpoints": {
            "models": "",
            "chat": "",
            "model_load": "",
            "model_download": "",
            "model_download_status": "",
        },
    },
    "lm_studio_api_v1": {
        "label": "LM Studio API v1",
        "server_base_url": "http://127.0.0.1:1234",
        "endpoints": {
            "models": "/api/v1/models",
            "chat": "/api/v1/chat",
            "model_load": "/api/v1/models/load",
            "model_download": "/api/v1/models/download",
            "model_download_status": "/api/v1/models/download/status/:job_id",
        },
    },
}
def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
def slugify_identifier(value: str) -> str:
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
def get_ui_dir(root_dir: Path) -> Path:
    return root_dir / "ui"
def get_ui_dist_dir(root_dir: Path) -> Path:
    return get_ui_dir(root_dir) / "dist"
def ensure_built_ui(root_dir: Path) -> None:
    dist_dir = get_ui_dist_dir(root_dir)
    required_paths = [
        dist_dir / "dashboard" / "home.html",
        dist_dir / "assets",
    ]
    missing_paths = [path for path in required_paths if not path.exists()]

    if missing_paths:
        missing_display = ", ".join(str(path.relative_to(root_dir)) for path in missing_paths)
        raise RuntimeError(
            "Built UI assets are missing. Run './malcom' or 'npm run build' in 'ui/' before starting the backend. "
            f"Missing: {missing_display}"
        )
def configure_application_logger(app: FastAPI, *, root_dir: Path, max_file_size_mb: int) -> logging.Logger:
    return configure_application_logger_core(app, root_dir=root_dir, max_file_size_mb=max_file_size_mb)
def get_application_logger(request: Request) -> logging.Logger:
    logger = getattr(request.app.state, "logger", None)
    if logger is None:
        logger = configure_application_logger(
            request.app,
            root_dir=get_root_dir(request),
            max_file_size_mb=DEFAULT_APP_SETTINGS["logging"]["max_file_size_mb"],
        )
        request.app.state.logger = logger
    return logger
def write_application_log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    write_application_log_core(logger, level, event, **fields)
def write_application_exception_log(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    error: Exception,
    **fields: Any,
) -> None:
    write_application_exception_log_core(logger, level, event, error=error, **fields)
def get_built_ui_file(root_dir: Path, relative_path: str) -> Path:
    return get_ui_dist_dir(root_dir) / relative_path
def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
def generate_secret() -> str:
    encoded_secret = base64.urlsafe_b64encode(secrets.token_bytes(INBOUND_SECRET_BYTES)).decode("ascii").rstrip("=")
    return f"{INBOUND_SECRET_PREFIX}{encoded_secret}"


def get_cluster_shared_secret() -> str:
    configured = os.environ.get("MALCOM_CLUSTER_SECRET", "").strip()
    return configured or "malcom-lan-shared-secret"


def build_worker_rpc_headers() -> dict[str, str]:
    return {"X-Malcom-Cluster-Secret": get_cluster_shared_secret()}


def assert_worker_rpc_authorized(request: Request) -> None:
    provided_secret = str(request.headers.get("x-malcom-cluster-secret") or "").strip()
    if not provided_secret or not hmac.compare_digest(provided_secret, get_cluster_shared_secret()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cluster secret.")


def row_to_api_summary(row: DatabaseRow) -> dict[str, Any]:
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
def row_to_event(row: DatabaseRow) -> dict[str, Any]:
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
def row_to_run(row: DatabaseRow) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "automation_id": row["automation_id"],
        "trigger_type": row["trigger_type"],
        "status": row["status"],
        "worker_id": row["worker_id"] if "worker_id" in row.keys() else None,
        "worker_name": row["worker_name"] if "worker_name" in row.keys() else None,
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
        "error_summary": row["error_summary"],
    }
def row_to_run_step(row: DatabaseRow) -> dict[str, Any]:
    detail_json = row["detail_json"]
    response_body_json = row["response_body_json"] if "response_body_json" in row.keys() else None
    extracted_fields_json = row["extracted_fields_json"] if "extracted_fields_json" in row.keys() else None
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
        "response_body_json": json.loads(response_body_json) if response_body_json else None,
        "extracted_fields_json": json.loads(extracted_fields_json) if extracted_fields_json else None,
    }
def row_to_automation_summary(row: DatabaseRow) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "enabled": bool(row["enabled"]),
        "trigger_type": row["trigger_type"],
        "trigger_config": json.loads(row["trigger_config_json"]),
        "step_count": row["step_count"] if "step_count" in row.keys() else 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_run_at": row["last_run_at"] if "last_run_at" in row.keys() else None,
        "next_run_at": row["next_run_at"] if "next_run_at" in row.keys() else None,
    }
def row_to_automation_step(row: DatabaseRow) -> AutomationStepDefinition:
    row_keys = row.keys()
    return AutomationStepDefinition(
        id=row["step_id"],
        type=row["step_type"],
        name=row["name"],
        config=AutomationStepConfig(**json.loads(row["config_json"])),
        on_true_step_id=row["on_true_step_id"] if "on_true_step_id" in row_keys else None,
        on_false_step_id=row["on_false_step_id"] if "on_false_step_id" in row_keys else None,
        is_merge_target=bool(row["is_merge_target"]) if "is_merge_target" in row_keys else False,
    )
def worker_to_response(worker: RegisteredWorker) -> WorkerResponse:
    return WorkerResponse(
        worker_id=worker.worker_id,
        name=worker.name,
        hostname=worker.hostname,
        address=worker.address,
        capabilities=list(worker.capabilities),
        status=worker.status,
        created_at=worker.created_at,
        updated_at=worker.updated_at,
        last_seen_at=worker.last_seen_at,
    )
def claim_job_response(job: RuntimeTriggerJob) -> WorkerClaimResponse:
    return WorkerClaimResponse(
        job=WorkerClaimedJobResponse(
            job_id=job.job_id,
            run_id=job.run_id,
            step_id=job.step_id,
            worker_id=job.worker_id or "",
            worker_name=job.worker_name or "",
            trigger={
                "type": job.trigger.type,
                "api_id": job.trigger.api_id,
                "event_id": job.trigger.event_id,
                "payload": job.trigger.payload,
                "received_at": job.trigger.received_at,
            },
            claimed_at=job.claimed_at or "",
        )
    )
def row_to_simple_api_resource(
    row: DatabaseRow,
    *,
    api_type: str,
    endpoint_path: str | None = None,
) -> dict[str, Any]:
    webhook_signing_payload: dict[str, Any] = {}
    if "webhook_signing_json" in row.keys():
        try:
            webhook_signing_payload = json.loads(row["webhook_signing_json"] or "{}")
        except json.JSONDecodeError:
            webhook_signing_payload = {}

    return {
        "id": row["id"],
        "type": api_type,
        "name": row["name"],
        "description": row["description"],
        "path_slug": row["path_slug"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"] if "status" in row.keys() else None,
        "endpoint_path": endpoint_path,
        "destination_url": row["destination_url"] if "destination_url" in row.keys() else None,
        "http_method": row["http_method"] if "http_method" in row.keys() else None,
        "auth_type": row["auth_type"] if "auth_type" in row.keys() else None,
        "repeat_enabled": bool(row["repeat_enabled"]) if "repeat_enabled" in row.keys() else None,
        "repeat_interval_minutes": row["repeat_interval_minutes"] if "repeat_interval_minutes" in row.keys() else None,
        "payload_template": row["payload_template"] if "payload_template" in row.keys() else None,
        "webhook_signing": OutgoingWebhookSigningConfig(**webhook_signing_payload) if webhook_signing_payload else None,
        "scheduled_time": row["scheduled_time"] if "scheduled_time" in row.keys() else None,
        "schedule_expression": row["schedule_expression"] if "schedule_expression" in row.keys() else None,
        "stream_mode": row["stream_mode"] if "stream_mode" in row.keys() else None,
        "last_run_at": row["last_run_at"] if "last_run_at" in row.keys() else None,
        "next_run_at": row["next_run_at"] if "next_run_at" in row.keys() else None,
        "last_error": row["last_error"] if "last_error" in row.keys() else None,
        "callback_path": row["callback_path"] if "callback_path" in row.keys() else None,
        "signature_header": row["signature_header"] if "signature_header" in row.keys() else None,
        "event_filter": row["event_filter"] if "event_filter" in row.keys() else None,
        "has_verification_token": bool(row["verification_token"]) if "verification_token" in row.keys() else None,
        "has_signing_secret": bool(row["signing_secret"]) if "signing_secret" in row.keys() else None,
        "last_received_at": row["last_received_at"] if "last_received_at" in row.keys() else None,
        "last_delivery_status": row["last_delivery_status"] if "last_delivery_status" in row.keys() else None,
        "events_count": int(row["events_count"]) if "events_count" in row.keys() and row["events_count"] is not None else None,
    }
def row_to_outgoing_detail_response(
    row: DatabaseRow,
    *,
    api_type: str,
    endpoint_path: str,
    connection: DatabaseConnection | None = None,
) -> OutgoingApiDetailResponse:
    resource = row_to_simple_api_resource(row, api_type=api_type, endpoint_path=endpoint_path)
    auth_config_json = row["auth_config_json"] if "auth_config_json" in row.keys() else "{}"

    try:
      auth_config_payload = json.loads(auth_config_json or "{}")
    except json.JSONDecodeError:
      auth_config_payload = {}

    resource["auth_config"] = OutgoingAuthConfig(**auth_config_payload)
    resource["recent_deliveries"] = (
        list_outgoing_delivery_history(connection, resource_id=row["id"], resource_type=api_type)
        if connection is not None
        else []
    )
    return OutgoingApiDetailResponse(**resource)


def list_outgoing_delivery_history(
    connection: DatabaseConnection | None,
    *,
    resource_id: str,
    resource_type: str,
    limit: int = 10,
) -> list[OutgoingDeliveryHistoryEntry]:
    if connection is None:
        return []

    rows = fetch_all(
        connection,
        """
        SELECT delivery_id, resource_type, resource_id, status, http_status_code, request_summary,
               response_summary, error_summary, started_at, finished_at
        FROM outgoing_delivery_history
        WHERE resource_id = ? AND resource_type = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (resource_id, resource_type, limit),
    )
    return [OutgoingDeliveryHistoryEntry(**dict(row)) for row in rows]


def record_outgoing_delivery_history(
    connection: DatabaseConnection,
    *,
    delivery_id: str,
    resource_type: str,
    resource_id: str,
    status_value: str,
    http_status_code: int | None,
    request_summary: str | None,
    response_summary: str | None,
    error_summary: str | None,
    started_at: str,
    finished_at: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO outgoing_delivery_history (
            delivery_id,
            resource_type,
            resource_id,
            status,
            http_status_code,
            request_summary,
            response_summary,
            error_summary,
            started_at,
            finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            delivery_id,
            resource_type,
            resource_id,
            status_value,
            http_status_code,
            request_summary,
            response_summary,
            error_summary,
            started_at,
            finished_at,
        ),
    )
DEFAULT_APP_SETTINGS: dict[str, Any] = {
    "general": {
        "environment": "live",
        "timezone": "local",
    },
    "logging": {
        "max_stored_entries": 250,
        "max_visible_entries": 50,
        "max_detail_characters": 4000,
        "max_file_size_mb": 5,
    },
    "notifications": {
        "channel": "email",
        "digest": "hourly",
    },
    "security": {
        "session_timeout_minutes": 60,
        "dual_approval_required": False,
        "token_rotation_days": 30,
    },
    "data": {
        "payload_redaction": True,
        "workflow_storage_path": "backend/data/workflows",
    },
    "automation": DEFAULT_TOOL_RETRY_SETTINGS,
}
def get_default_settings() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_APP_SETTINGS))
def seed_default_settings(connection: DatabaseConnection) -> None:
    now = utc_now_iso()

    seed_integration_presets(connection, timestamp=now)
    seed_connector_endpoint_definitions(connection, timestamp=now)
    seed_default_scripts(connection, timestamp=now)

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
def seed_connector_endpoint_definitions(connection: DatabaseConnection, *, timestamp: str | None = None) -> None:
    now = timestamp or utc_now_iso()
    endpoint_ids: list[str] = []

    for activity in CONNECTOR_ACTIVITY_DEFINITIONS:
        endpoint_id = f"activity:{activity.provider_id}:{activity.activity_id}"
        endpoint_ids.append(endpoint_id)
        connection.execute(
            """
            INSERT INTO connector_endpoint_definitions (
                endpoint_id,
                provider_id,
                endpoint_kind,
                service,
                operation_type,
                label,
                description,
                http_method,
                endpoint_path_template,
                query_params_json,
                required_scopes_json,
                input_schema_json,
                output_schema_json,
                payload_template,
                execution_json,
                metadata_json,
                created_at,
                updated_at
            ) VALUES (?, ?, 'activity', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(endpoint_id) DO UPDATE SET
                provider_id = excluded.provider_id,
                endpoint_kind = excluded.endpoint_kind,
                service = excluded.service,
                operation_type = excluded.operation_type,
                label = excluded.label,
                description = excluded.description,
                http_method = excluded.http_method,
                endpoint_path_template = excluded.endpoint_path_template,
                query_params_json = excluded.query_params_json,
                required_scopes_json = excluded.required_scopes_json,
                input_schema_json = excluded.input_schema_json,
                output_schema_json = excluded.output_schema_json,
                payload_template = excluded.payload_template,
                execution_json = excluded.execution_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                endpoint_id,
                activity.provider_id,
                activity.service,
                activity.operation_type,
                activity.label,
                activity.description,
                str(activity.execution.get("http_method") or "POST"),
                str(activity.execution.get("endpoint_path_template") or ""),
                json.dumps(activity.execution.get("query_params") or {}),
                json.dumps(list(activity.required_scopes)),
                json.dumps(list(activity.input_schema)),
                json.dumps(list(activity.output_schema)),
                str(activity.execution.get("payload_template") or ""),
                json.dumps(dict(activity.execution)),
                json.dumps({"activity_id": activity.activity_id}),
                now,
                now,
            ),
        )

    for preset in DEFAULT_HTTP_PRESET_CATALOG:
        endpoint_id = f"http_preset:{preset.provider_id}:{preset.preset_id}"
        endpoint_ids.append(endpoint_id)
        connection.execute(
            """
            INSERT INTO connector_endpoint_definitions (
                endpoint_id,
                provider_id,
                endpoint_kind,
                service,
                operation_type,
                label,
                description,
                http_method,
                endpoint_path_template,
                query_params_json,
                required_scopes_json,
                input_schema_json,
                output_schema_json,
                payload_template,
                execution_json,
                metadata_json,
                created_at,
                updated_at
            ) VALUES (?, ?, 'http_preset', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(endpoint_id) DO UPDATE SET
                provider_id = excluded.provider_id,
                endpoint_kind = excluded.endpoint_kind,
                service = excluded.service,
                operation_type = excluded.operation_type,
                label = excluded.label,
                description = excluded.description,
                http_method = excluded.http_method,
                endpoint_path_template = excluded.endpoint_path_template,
                query_params_json = excluded.query_params_json,
                required_scopes_json = excluded.required_scopes_json,
                input_schema_json = excluded.input_schema_json,
                output_schema_json = excluded.output_schema_json,
                payload_template = excluded.payload_template,
                execution_json = excluded.execution_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                endpoint_id,
                preset.provider_id,
                preset.service,
                preset.operation,
                preset.label,
                preset.description,
                preset.http_method,
                preset.endpoint_path_template,
                json.dumps(preset.query_params),
                json.dumps(list(preset.required_scopes)),
                json.dumps(list(preset.input_schema)),
                json.dumps([]),
                preset.payload_template,
                json.dumps({}),
                json.dumps({"preset_id": preset.preset_id}),
                now,
                now,
            ),
        )

    if endpoint_ids:
        placeholders = ", ".join("?" for _ in endpoint_ids)
        connection.execute(
            f"DELETE FROM connector_endpoint_definitions WHERE endpoint_kind IN ('activity', 'http_preset') AND endpoint_id NOT IN ({placeholders})",
            tuple(endpoint_ids),
        )
    else:
        connection.execute("DELETE FROM connector_endpoint_definitions WHERE endpoint_kind IN ('activity', 'http_preset')")

def seed_integration_presets(connection: DatabaseConnection, *, timestamp: str | None = None) -> None:
    now = timestamp or utc_now_iso()

    for preset in DEFAULT_CONNECTOR_CATALOG:
        connection.execute(
            """
            INSERT INTO integration_presets (
                id,
                integration_type,
                name,
                description,
                category,
                auth_types_json,
                default_scopes_json,
                docs_url,
                base_url,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                integration_type = excluded.integration_type,
                name = excluded.name,
                description = excluded.description,
                category = excluded.category,
                auth_types_json = excluded.auth_types_json,
                default_scopes_json = excluded.default_scopes_json,
                docs_url = excluded.docs_url,
                base_url = excluded.base_url,
                updated_at = excluded.updated_at
            """,
            (
                preset["id"],
                "connector_provider",
                preset["name"],
                preset["description"],
                preset["category"],
                json.dumps(preset.get("auth_types", [])),
                json.dumps(preset.get("default_scopes", [])),
                preset.get("docs_url") or "",
                preset.get("base_url") or "",
                now,
                now,
            ),
        )
def normalize_settings_response_section(
    section_key: str,
    value: Any,
    *,
    connection: DatabaseConnection | None = None,
) -> Any:
    schema_map = {
        "general": GeneralSettings,
        "logging": LoggingSettings,
        "notifications": NotificationSettings,
        "security": SecuritySettings,
        "data": DataSettings,
        "automation": AutomationSettings,
        "options": AppSettingsOptionsResponse,
    }
    schema = schema_map[section_key]
    try:
        return schema.model_validate(value).model_dump()
    except ValidationError:
        fallback_value = (
            {
                "notification_channels": [dict(item) for item in SETTINGS_NOTIFICATION_CHANNEL_OPTIONS],
                "notification_digests": [dict(item) for item in SETTINGS_NOTIFICATION_DIGEST_OPTIONS],
            }
            if section_key == "options"
            else get_default_settings()[section_key]
        )
        return schema.model_validate(fallback_value).model_dump()
def get_settings_payload(connection: DatabaseConnection) -> dict[str, Any]:
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
        try:
            stored_value = json.loads(row["value_json"])
        except json.JSONDecodeError:
            continue
        settings[row["key"]] = merge_settings_section(
            settings[row["key"]],
            stored_value,
        )

    settings["options"] = {
        "notification_channels": [dict(item) for item in SETTINGS_NOTIFICATION_CHANNEL_OPTIONS],
        "notification_digests": [dict(item) for item in SETTINGS_NOTIFICATION_DIGEST_OPTIONS],
    }

    for section_key in tuple(settings.keys()):
        settings[section_key] = normalize_settings_response_section(
            section_key,
            settings[section_key],
            connection=connection,
        )

    return settings
def get_default_smtp_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SMTP_TOOL_CONFIG))


def _get_managed_tool_enabled_state(
    connection: DatabaseConnection,
    tool_id: str,
    *,
    default: bool = False,
) -> bool:
    row = fetch_one(
        connection,
        """
        SELECT enabled
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )
    if row is None:
        return default
    return bool(row["enabled"])


def _save_managed_tool_enabled_state(
    connection: DatabaseConnection,
    tool_id: str,
    enabled: bool,
    *,
    commit: bool = True,
) -> None:
    connection.execute(
        """
        UPDATE tools
        SET enabled = ?, updated_at = ?
        WHERE id = ?
        """,
        (int(enabled), utc_now_iso(), tool_id),
    )
    if commit:
        connection.commit()


def _read_managed_tool_config_row(connection: DatabaseConnection, tool_id: str) -> dict[str, Any] | None:
    row = fetch_one(
        connection,
        """
        SELECT config_json
        FROM tool_configs
        WHERE tool_id = ?
        """,
        (tool_id,),
    )
    if row is None:
        return None

    try:
        parsed = json.loads(row["config_json"])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _save_managed_tool_config_row(
    connection: DatabaseConnection,
    tool_id: str,
    config: dict[str, Any],
    *,
    legacy_settings_key: str | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO tool_configs (tool_id, config_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tool_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (tool_id, json.dumps(config), now, now),
    )
    if legacy_settings_key:
        connection.execute("DELETE FROM settings WHERE key = ?", (legacy_settings_key,))
    connection.commit()
    return config


def _load_managed_tool_config_payload(
    connection: DatabaseConnection,
    *,
    tool_id: str,
    legacy_settings_key: str,
) -> dict[str, Any]:
    stored_config = _read_managed_tool_config_row(connection, tool_id)
    if stored_config is not None:
        return stored_config

    legacy_value = read_stored_settings_section(connection, legacy_settings_key)
    if not isinstance(legacy_value, dict):
        return {}

    migrated_config = dict(legacy_value)
    legacy_enabled = migrated_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        tool_id,
        migrated_config,
        legacy_settings_key=legacy_settings_key,
    )
    if legacy_enabled is not None:
        _save_managed_tool_enabled_state(connection, tool_id, bool(legacy_enabled))
    return migrated_config


def get_smtp_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_smtp_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="smtp",
            legacy_settings_key=SMTP_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "smtp",
        default=bool(config.get("enabled")),
    )
    return config


def save_smtp_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "smtp",
        next_config,
        legacy_settings_key=SMTP_TOOL_SETTINGS_KEY,
    )
    return get_smtp_tool_config(connection)


def normalize_smtp_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_smtp_tool_config()
    normalized.update(config)
    normalized["target_worker_id"] = normalized.get("target_worker_id") or None
    normalized["bind_host"] = str(normalized.get("bind_host") or DEFAULT_SMTP_TOOL_CONFIG["bind_host"])
    raw_port = normalized.get("port")
    normalized["port"] = int(DEFAULT_SMTP_TOOL_CONFIG["port"] if raw_port is None else raw_port)
    normalized["enabled"] = bool(normalized.get("enabled"))
    recipient_email = str(normalized.get("recipient_email") or "").strip().lower()
    normalized["recipient_email"] = recipient_email or None
    return normalized
def get_default_local_llm_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_LOCAL_LLM_TOOL_CONFIG))


def get_local_llm_endpoint_presets() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(LOCAL_LLM_ENDPOINT_PRESETS))


def get_local_llm_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_local_llm_tool_config()
    stored_value = _load_managed_tool_config_payload(
        connection,
        tool_id="llm-deepl",
        legacy_settings_key=LOCAL_LLM_TOOL_SETTINGS_KEY,
    )
    if isinstance(stored_value, dict):
        config.update(stored_value)
        if isinstance(stored_value.get("endpoints"), dict):
            config["endpoints"].update(stored_value["endpoints"])
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "llm-deepl",
        default=bool(config.get("enabled")),
    )
    return config


def save_local_llm_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "llm-deepl",
        next_config,
        legacy_settings_key=LOCAL_LLM_TOOL_SETTINGS_KEY,
    )
    return get_local_llm_tool_config(connection)


def normalize_local_llm_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_local_llm_tool_config()
    normalized.update(config or {})
    stored_endpoints = config.get("endpoints") if isinstance(config, dict) else None
    if isinstance(stored_endpoints, dict):
        normalized["endpoints"].update(stored_endpoints)

    provider = str(normalized.get("provider") or DEFAULT_LOCAL_LLM_TOOL_CONFIG["provider"]).strip()
    if provider not in LOCAL_LLM_ENDPOINT_PRESETS:
        provider = DEFAULT_LOCAL_LLM_TOOL_CONFIG["provider"]
    normalized["provider"] = provider
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["server_base_url"] = str(normalized.get("server_base_url") or "").strip()
    normalized["model_identifier"] = str(normalized.get("model_identifier") or "").strip()
    normalized["endpoints"] = {
        "models": str(normalized["endpoints"].get("models") or "").strip(),
        "chat": str(normalized["endpoints"].get("chat") or "").strip(),
        "model_load": str(normalized["endpoints"].get("model_load") or "").strip(),
        "model_download": str(normalized["endpoints"].get("model_download") or "").strip(),
        "model_download_status": str(normalized["endpoints"].get("model_download_status") or "").strip(),
    }
    return normalized
def get_default_coqui_tts_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_COQUI_TTS_TOOL_CONFIG))


def get_coqui_tts_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_coqui_tts_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="coqui-tts",
            legacy_settings_key=COQUI_TTS_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "coqui-tts",
        default=bool(config.get("enabled")),
    )
    return config


def save_coqui_tts_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "coqui-tts",
        next_config,
        legacy_settings_key=COQUI_TTS_TOOL_SETTINGS_KEY,
    )
    return get_coqui_tts_tool_config(connection)


def normalize_coqui_tts_tool_config(config: dict[str, Any], *, root_dir: Path | None = None) -> dict[str, Any]:
    normalized = get_default_coqui_tts_tool_config()
    normalized.update(config or {})
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["command"] = str(normalized.get("command") or DEFAULT_COQUI_TTS_TOOL_CONFIG["command"]).strip()
    normalized["model_name"] = str(normalized.get("model_name") or DEFAULT_COQUI_TTS_TOOL_CONFIG["model_name"]).strip()
    normalized["speaker"] = str(normalized.get("speaker") or "").strip()
    normalized["language"] = str(normalized.get("language") or "").strip()
    output_directory = str(normalized.get("output_directory") or DEFAULT_COQUI_TTS_TOOL_CONFIG["output_directory"]).strip()
    if root_dir is not None and not Path(output_directory).is_absolute():
        output_directory = str((root_dir / output_directory).resolve())
    normalized["output_directory"] = output_directory
    return normalized


def get_default_image_magic_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_IMAGE_MAGIC_TOOL_CONFIG))


def get_image_magic_tool_config(connection: DatabaseConnection) -> dict[str, Any]:
    config = get_default_image_magic_tool_config()
    config.update(
        _load_managed_tool_config_payload(
            connection,
            tool_id="image-magic",
            legacy_settings_key=IMAGE_MAGIC_TOOL_SETTINGS_KEY,
        )
    )
    config["enabled"] = _get_managed_tool_enabled_state(
        connection,
        "image-magic",
        default=bool(config.get("enabled")),
    )
    return config


def save_image_magic_tool_config(connection: DatabaseConnection, config: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(config)
    next_config.pop("enabled", None)
    _save_managed_tool_config_row(
        connection,
        "image-magic",
        next_config,
        legacy_settings_key=IMAGE_MAGIC_TOOL_SETTINGS_KEY,
    )
    return get_image_magic_tool_config(connection)


def normalize_image_magic_tool_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = get_default_image_magic_tool_config()
    normalized.update(config or {})
    normalized["enabled"] = bool(normalized.get("enabled"))
    normalized["target_worker_id"] = str(normalized.get("target_worker_id") or "").strip() or None
    normalized["command"] = str(normalized.get("command") or DEFAULT_IMAGE_MAGIC_TOOL_CONFIG["command"]).strip()
    return normalized


def get_default_tool_retries(connection: DatabaseConnection) -> int:
    settings = get_settings_payload(connection)
    automation_settings = settings.get("automation") or {}
    try:
        retries = int(automation_settings.get("default_tool_retries", DEFAULT_TOOL_RETRY_SETTINGS["default_tool_retries"]))
    except (TypeError, ValueError):
        retries = DEFAULT_TOOL_RETRY_SETTINGS["default_tool_retries"]
    return max(0, min(10, retries))


def sanitize_generated_audio_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return filename or f"coqui-output-{uuid4().hex[:8]}"
def _get_tool_input(step: AutomationStepDefinition, key: str, context: dict[str, Any], *, legacy_attr: str | None = None) -> str:
    inputs = step.config.tool_inputs or {}
    raw = inputs.get(key)
    if raw is None and legacy_attr:
        raw = getattr(step.config, legacy_attr, None)
    return render_template_string(raw, context).strip() if raw else ""

def verify_local_command_ready(command: str, *, working_dir: Path | None = None, tool_name: str = "Command") -> list[str]:
    command_parts = shlex.split(str(command or "").strip())
    if not command_parts:
        raise RuntimeError(f"{tool_name} command is invalid.")

    executable = command_parts[0]
    executable_path = Path(executable).expanduser()
    has_explicit_path = executable_path.is_absolute() or any(separator in executable for separator in ("/", "\\"))

    if has_explicit_path:
        if not executable_path.is_absolute() and working_dir is not None:
            executable_path = (working_dir / executable_path).resolve()
        if not executable_path.exists() or not os.access(executable_path, os.X_OK):
            raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")
        return command_parts

    if shutil.which(executable) is None:
        raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")

    return command_parts


def execute_coqui_tts_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    *,
    root_dir: Path,
) -> RuntimeExecutionResult:
    config = normalize_coqui_tts_tool_config(get_coqui_tts_tool_config(connection), root_dir=root_dir)
    if not config["enabled"]:
        raise RuntimeError("Tool 'coqui-tts' is disabled.")
    if not config["command"]:
        raise RuntimeError("Coqui TTS command is not configured.")
    if not config["model_name"]:
        raise RuntimeError("Coqui TTS model name is not configured.")

    rendered_text = _get_tool_input(step, "text", context, legacy_attr="tool_text")
    if not rendered_text:
        raise RuntimeError("Coqui TTS steps require a 'text' input.")

    output_directory = Path(config["output_directory"])
    output_directory.mkdir(parents=True, exist_ok=True)
    requested_filename = _get_tool_input(step, "output_filename", context, legacy_attr="tool_output_filename")
    safe_filename = sanitize_generated_audio_filename(requested_filename) if requested_filename else f"coqui-output-{uuid4().hex[:8]}"
    if "." not in safe_filename:
        safe_filename = f"{safe_filename}.wav"
    output_path = output_directory / safe_filename

    command_parts = shlex.split(config["command"])
    if not command_parts:
        raise RuntimeError("Coqui TTS command is invalid.")
    command = [
        *command_parts,
        "--text",
        rendered_text,
        "--model_name",
        config["model_name"],
        "--out_path",
        str(output_path),
    ]
    speaker = _get_tool_input(step, "speaker", context, legacy_attr="tool_speaker") or config["speaker"]
    language = _get_tool_input(step, "language", context, legacy_attr="tool_language") or config["language"]
    if speaker:
        command.extend(["--speaker_idx", speaker])
    if language:
        command.extend(["--language_idx", language])

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root_dir),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Coqui TTS command was not found: {config['command']}") from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "Unknown Coqui TTS failure."
        raise RuntimeError(f"Coqui TTS generation failed: {detail}") from error

    outputs = {
        "audio_file_path": str(output_path),
    }
    detail = {
        "tool_id": "coqui-tts",
        "model_name": config["model_name"],
        "speaker": speaker or None,
        "language": language or None,
        "stdout": (completed.stdout or "").strip() or None,
        **outputs,
    }
    return RuntimeExecutionResult(
        status="completed",
        response_summary=f"Generated speech audio at {output_path.name}.",
        detail=detail,
        output=outputs,
    )


def execute_llm_deepl_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> RuntimeExecutionResult:
    messages: list[dict[str, str]] = []
    system_prompt = _get_tool_input(step, "system_prompt", context)
    user_prompt = _get_tool_input(step, "user_prompt", context)
    model_identifier = _get_tool_input(step, "model_identifier", context) or None

    if not user_prompt:
        raise RuntimeError("llm-deepl tool steps require a 'user_prompt' input.")

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    llm_response = execute_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier,
    )
    outputs = {
        "response_text": llm_response.response_text,
        "model_used": llm_response.model_identifier or "",
    }
    detail = llm_response.model_dump()
    detail["tool_id"] = "llm-deepl"
    detail.update(outputs)
    return RuntimeExecutionResult(
        status="completed",
        response_summary=llm_response.response_text[:500],
        detail=detail,
        output=outputs,
    )


def execute_smtp_tool_step(
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> RuntimeExecutionResult:
    relay_host = _get_tool_input(step, "relay_host", context)
    relay_port_raw = _get_tool_input(step, "relay_port", context)
    relay_security = _get_tool_input(step, "relay_security", context) or "none"
    relay_username = _get_tool_input(step, "relay_username", context) or None
    relay_password = _get_tool_input(step, "relay_password", context) or None
    from_address = _get_tool_input(step, "from_address", context)
    to_address = _get_tool_input(step, "to", context)
    subject = _get_tool_input(step, "subject", context)
    body = _get_tool_input(step, "body", context)

    if not relay_host:
        raise RuntimeError("SMTP tool steps require a 'relay_host' input.")
    if not relay_port_raw:
        raise RuntimeError("SMTP tool steps require a 'relay_port' input.")
    if not from_address:
        raise RuntimeError("SMTP tool steps require a 'from_address' input.")
    if not to_address:
        raise RuntimeError("SMTP tool steps require a 'to' input.")
    if not subject:
        raise RuntimeError("SMTP tool steps require a 'subject' input.")
    if not body:
        raise RuntimeError("SMTP tool steps require a 'body' input.")

    try:
        relay_port = int(relay_port_raw)
    except (ValueError, TypeError) as error:
        raise RuntimeError(f"SMTP relay_port must be a valid integer, got: {relay_port_raw!r}") from error

    if relay_security not in ("none", "starttls", "tls"):
        relay_security = "none"

    send_smtp_relay_message(
        SmtpRelaySendRequest(
            host=relay_host,
            port=relay_port,
            security=relay_security,
            auth_mode="password" if relay_username else "none",
            username=relay_username,
            password=relay_password,
            mail_from=from_address,
            recipients=[r.strip() for r in to_address.split(",") if r.strip()],
            subject=subject,
            body=body,
        )
    )
    outputs = {
        "status": "sent",
        "message": f"Email sent to {to_address} via {relay_host}:{relay_port}.",
    }
    return RuntimeExecutionResult(
        status="completed",
        response_summary=outputs["message"],
        detail={"tool_id": "smtp", **outputs},
        output=outputs,
    )
def _resolve_worker_base_url(address: str) -> str:
    value = str(address or "").strip()
    if not value:
        raise RuntimeError("Target worker address is missing.")
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/")
    if ":" in value:
        return f"http://{value}".rstrip("/")
    return f"http://{value}:8000"


def call_worker_rpc(
    worker: RegisteredWorker,
    *,
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    base_url = _resolve_worker_base_url(worker.address)
    response = httpx.request(
        method,
        f"{base_url}{path}",
        json=json_body,
        headers=build_worker_rpc_headers(),
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def get_runtime_worker_or_error(worker_id: str) -> RegisteredWorker:
    worker = next((item for item in runtime_event_bus.list_workers() if item.worker_id == worker_id), None)
    if worker is None:
        raise RuntimeError(f"Target worker '{worker_id}' is not connected.")
    return worker


def _build_image_magic_output_path(
    *,
    input_file: str,
    output_format: str,
    output_filename: str | None,
    root_dir: Path,
) -> tuple[Path, Path]:
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = root_dir / input_file

    output_directory = input_path.parent
    requested_filename = output_filename.strip() if output_filename else ""
    safe_filename = sanitize_generated_audio_filename(requested_filename) if requested_filename else f"{input_path.stem}-converted"
    if "." not in safe_filename:
        safe_filename = f"{safe_filename}.{output_format}"

    return input_path, output_directory / safe_filename


def execute_image_magic_conversion_request(
    payload: ImageMagicExecuteRequest,
    *,
    root_dir: Path,
    command: str,
) -> dict[str, str]:
    output_format = str(payload.output_format or "").strip().lower()
    valid_formats = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif"}
    if output_format not in valid_formats:
        raise RuntimeError(f"Image Magic output_format must be one of: {', '.join(sorted(valid_formats))}.")

    input_path, output_path = _build_image_magic_output_path(
        input_file=payload.input_file,
        output_format=output_format,
        output_filename=payload.output_filename,
        root_dir=root_dir,
    )
    if not input_path.exists():
        raise RuntimeError(f"Image Magic input file was not found: {input_path}")

    command_parts = verify_local_command_ready(command, working_dir=root_dir, tool_name="Image Magic")
    image_command = [*command_parts, str(input_path)]
    resize_value = str(payload.resize or "").strip()
    if resize_value:
        image_command.extend(["-resize", resize_value])
    image_command.append(str(output_path))

    try:
        completed = subprocess.run(
            image_command,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root_dir),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Image Magic command was not found: {command}") from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "Unknown Image Magic failure."
        raise RuntimeError(f"Image conversion failed: {detail}") from error

    return {
        "output_file_path": str(output_path),
        "stdout": (completed.stdout or "").strip() or "",
    }


def _parse_tool_retry_count(raw_value: str, *, default_retries: int) -> int:
    if not raw_value:
        return default_retries
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default_retries
    return max(0, min(10, parsed))


def execute_image_magic_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    *,
    root_dir: Path,
) -> RuntimeExecutionResult:
    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
    if not config["enabled"]:
        raise RuntimeError("Tool 'image-magic' is disabled.")

    input_file = _get_tool_input(step, "input_file", context)
    output_format = _get_tool_input(step, "output_format", context)
    resize = _get_tool_input(step, "resize", context) or None
    output_filename = _get_tool_input(step, "output_filename", context) or None
    retries_override = _get_tool_input(step, "max_retries", context)

    if not input_file:
        raise RuntimeError("Image Magic steps require an 'input_file' input.")
    if not output_format:
        raise RuntimeError("Image Magic steps require an 'output_format' input.")

    default_retries = get_default_tool_retries(connection)
    max_retries = _parse_tool_retry_count(retries_override, default_retries=default_retries)
    attempts_total = max_retries + 1
    last_error: RuntimeError | None = None

    for attempt in range(1, attempts_total + 1):
        try:
            target_worker_id = config.get("target_worker_id")
            worker_id = get_local_worker_id()
            worker_name = get_local_worker_name()

            if target_worker_id and target_worker_id != worker_id:
                worker = get_runtime_worker_or_error(target_worker_id)
                response = call_worker_rpc(
                    worker,
                    method="POST",
                    path="/api/v1/internal/workers/tools/image-magic/execute",
                    json_body={
                        "input_file": input_file,
                        "output_format": output_format,
                        "output_filename": output_filename,
                        "resize": resize,
                    },
                    timeout=120.0,
                )
                payload = response.json()
                outputs = {
                    "output_file_path": str(payload.get("output_file_path") or ""),
                }
                detail = {
                    "tool_id": "image-magic",
                    "execution_mode": "remote",
                    "target_worker_id": worker.worker_id,
                    "target_worker_name": worker.name,
                    "resize": resize,
                    "attempt": attempt,
                    "attempts_total": attempts_total,
                    **outputs,
                }
                return RuntimeExecutionResult(
                    status="completed",
                    response_summary=f"Converted image on {worker.name}.",
                    detail=detail,
                    output=outputs,
                )

            execution = execute_image_magic_conversion_request(
                ImageMagicExecuteRequest(
                    input_file=input_file,
                    output_format=output_format,
                    output_filename=output_filename,
                    resize=resize,
                ),
                root_dir=root_dir,
                command=config["command"],
            )
            outputs = {
                "output_file_path": execution["output_file_path"],
            }
            detail = {
                "tool_id": "image-magic",
                "execution_mode": "local",
                "worker_id": worker_id,
                "worker_name": worker_name,
                "resize": resize,
                "attempt": attempt,
                "attempts_total": attempts_total,
                "stdout": execution.get("stdout") or None,
                **outputs,
            }
            return RuntimeExecutionResult(
                status="completed",
                response_summary=f"Converted image to {Path(outputs['output_file_path']).name}.",
                detail=detail,
                output=outputs,
            )
        except (RuntimeError, httpx.HTTPError, ValueError) as error:
            last_error = RuntimeError(str(error))
            if attempt >= attempts_total:
                break
            time.sleep(min(1.0, 0.25 * attempt))

    raise RuntimeError(f"Image Magic failed after {attempts_total} attempts: {last_error}")


def build_local_llm_endpoint_url(config: dict[str, Any], endpoint_key: str) -> str:
    base_url = str(config.get("server_base_url") or "").strip().rstrip("/")
    endpoint_path = str((config.get("endpoints") or {}).get(endpoint_key) or "").strip()

    if not base_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM server base URL is not configured.")
    if not endpoint_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Local LLM endpoint '{endpoint_key}' is not configured.")
    if endpoint_path.startswith("http://") or endpoint_path.startswith("https://"):
        return endpoint_path
    return f"{base_url}{endpoint_path if endpoint_path.startswith('/') else f'/{endpoint_path}'}"
def local_llm_uses_native_chat_api(config: dict[str, Any]) -> bool:
    chat_path = str((config.get("endpoints") or {}).get("chat") or "").strip().lower()
    return chat_path.endswith("/api/v1/chat")
def build_local_llm_openai_chat_url(config: dict[str, Any]) -> str:
    base_url = str(config.get("server_base_url") or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM server base URL is not configured.")
    return f"{base_url}/v1/chat/completions"
def should_retry_local_llm_with_openai_chat(config: dict[str, Any], error: httpx.HTTPError) -> bool:
    if not local_llm_uses_native_chat_api(config):
        return False
    if not isinstance(error, httpx.HTTPStatusError):
        return False
    return error.response.status_code == status.HTTP_404_NOT_FOUND
def extract_text_from_content_parts(parts: Any) -> str:
    if isinstance(parts, str):
        return parts
    if not isinstance(parts, list):
        return ""

    output: list[str] = []
    for item in parts:
        if isinstance(item, dict):
            if isinstance(item.get("text"), str):
                output.append(item["text"])
            elif isinstance(item.get("content"), str):
                output.append(item["content"])
    return "".join(output)
def extract_local_llm_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]

    if isinstance(payload.get("choices"), list) and payload["choices"]:
        choice = payload["choices"][0]
        if isinstance(choice, dict):
            message = choice.get("message") or {}
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            delta = choice.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]

    if isinstance(payload.get("output"), list):
        fragments: list[str] = []
        for item in payload["output"]:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            extracted = extract_text_from_content_parts(content)
            if extracted:
                fragments.append(extracted)
        if fragments:
            return "".join(fragments)

    if isinstance(payload.get("message"), dict) and isinstance(payload["message"].get("content"), str):
        return payload["message"]["content"]

    if isinstance(payload.get("content"), str):
        return payload["content"]

    return ""
def extract_local_llm_response_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "response_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
def build_local_llm_native_chat_body(
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    previous_response_id: str | None = None,
    stream: bool,
) -> dict[str, Any]:
    latest_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    system_message = next((message["content"] for message in messages if message["role"] == "system"), None)

    if previous_response_id:
        native_input = latest_user_message
    else:
        transcript_lines: list[str] = []
        if system_message:
            transcript_lines.append(f"System instructions:\n{system_message}")
        conversation_messages = [message for message in messages if message["role"] != "system"]
        if conversation_messages:
            transcript_lines.append("Conversation:")
            transcript_lines.extend(
                f"{message['role'].capitalize()}: {message['content']}" for message in conversation_messages
            )
        native_input = "\n\n".join(line for line in transcript_lines if line.strip()) or latest_user_message

    body: dict[str, Any] = {
        "model": model_identifier,
        "input": native_input,
        "stream": stream,
        "store": False,
    }
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
    return body
def build_local_llm_openai_chat_body(
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    stream: bool,
) -> dict[str, Any]:
    return {
        "model": model_identifier,
        "messages": messages,
        "stream": stream,
    }


def prepare_local_llm_chat_request(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
    stream: bool,
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
    if not config["enabled"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM tool is disabled.")

    model_identifier = (model_identifier_override or config.get("model_identifier") or "").strip()
    if not model_identifier:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM model identifier is not configured.")

    chat_url = build_local_llm_endpoint_url(config, "chat")
    if local_llm_uses_native_chat_api(config):
        request_body = build_local_llm_native_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            previous_response_id=previous_response_id,
            stream=stream,
        )
    else:
        request_body = build_local_llm_openai_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            stream=stream,
        )
    return config, model_identifier, chat_url, request_body


def build_local_llm_fallback_chat_request(
    config: dict[str, Any],
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    stream: bool,
) -> tuple[str, dict[str, Any]]:
    return (
        build_local_llm_openai_chat_url(config),
        build_local_llm_openai_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            stream=stream,
        ),
    )


def execute_local_llm_chat_request(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
) -> LocalLlmChatResponse:
    config, model_identifier, chat_url, request_body = prepare_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier_override,
        previous_response_id=previous_response_id,
        stream=False,
    )
    try:
        response = httpx.post(chat_url, json=request_body, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        if not should_retry_local_llm_with_openai_chat(config, error):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Local LLM request failed: {error}") from error
        try:
            fallback_chat_url, fallback_body = build_local_llm_fallback_chat_request(
                config,
                model_identifier=model_identifier,
                messages=messages,
                stream=False,
            )
            response = httpx.post(fallback_chat_url, json=fallback_body, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPError as fallback_error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Local LLM request failed: {fallback_error}") from fallback_error

    payload = response.json()
    response_text = extract_local_llm_response_text(payload)
    return LocalLlmChatResponse(
        ok=True,
        model_identifier=model_identifier,
        response_text=response_text,
        response_id=extract_local_llm_response_id(payload),
    )


def encode_sse_event(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


def iter_local_llm_stream_events(response: httpx.Response, *, collected_fragments: list[str]):
    response_id: str | None = None
    event_name = "message"
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8", errors="replace")
        if line == "":
            if not data_lines:
                event_name = "message"
                continue
            data_payload = "\n".join(data_lines)
            if data_payload == "[DONE]":
                break
            try:
                parsed = json.loads(data_payload)
            except json.JSONDecodeError:
                parsed = {"raw": data_payload}

            fragment = ""
            if event_name == "message.delta":
                fragment = extract_text_from_content_parts(parsed.get("delta"))
            elif isinstance(parsed, dict):
                if isinstance(parsed.get("choices"), list) and parsed["choices"]:
                    choice = parsed["choices"][0]
                    if isinstance(choice, dict):
                        delta = choice.get("delta") or {}
                        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                            fragment = delta["content"]
                if not fragment:
                    fragment = extract_local_llm_response_text(parsed)
                if response_id is None:
                    response_id = extract_local_llm_response_id(parsed)

            if fragment:
                collected_fragments.append(fragment)
                yield encode_sse_event("delta", {"content": fragment})

            if event_name in {"chat.end", "response.completed"} and response_id is None and isinstance(parsed, dict):
                response_id = extract_local_llm_response_id(parsed)

            event_name = "message"
            data_lines = []
            continue

        if line.startswith("event:"):
            event_name = line[6:].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    return response_id


def build_local_llm_stream(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
):
    config, model_identifier, chat_url, request_body = prepare_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier_override,
        previous_response_id=previous_response_id,
        stream=True,
    )

    def event_stream():
        response_id: str | None = None
        collected_fragments: list[str] = []
        try:
            try:
                with httpx.stream("POST", chat_url, json=request_body, timeout=60.0) as response:
                    response.raise_for_status()
                    response_id = yield from iter_local_llm_stream_events(response, collected_fragments=collected_fragments)
            except httpx.HTTPError as error:
                if not should_retry_local_llm_with_openai_chat(config, error):
                    raise
                fallback_chat_url, fallback_body = build_local_llm_fallback_chat_request(
                    config,
                    model_identifier=model_identifier,
                    messages=messages,
                    stream=True,
                )
                with httpx.stream("POST", fallback_chat_url, json=fallback_body, timeout=60.0) as response:
                    response.raise_for_status()
                    response_id = yield from iter_local_llm_stream_events(response, collected_fragments=collected_fragments)

            yield encode_sse_event(
                "done",
                {
                    "response_text": "".join(collected_fragments),
                    "response_id": response_id,
                    "model_identifier": model_identifier,
                },
            )
        except httpx.HTTPError as error:
            yield encode_sse_event("error", {"message": f"Local LLM streaming request failed: {error}"})

    return event_stream()
class IncomingApiResourceCreate(ApiResourceBase):
    type: Literal["incoming"]
class OutgoingApiResourceBase(ApiResourceBase):
    repeat_enabled: bool = False
    repeat_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    destination_url: str = Field(min_length=1, max_length=2000)
    http_method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    webhook_signing: OutgoingWebhookSigningConfig | None = None
    payload_template: str = Field(default="{}", max_length=10000)
    connector_id: str | None = Field(default=None, max_length=120)
class ScheduledApiResourceCreate(OutgoingApiResourceBase):
    type: Literal["outgoing_scheduled"]
    scheduled_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    repeat_interval_minutes: None = None
class ContinuousApiResourceCreate(OutgoingApiResourceBase):
    type: Literal["outgoing_continuous"]
class WebhookApiResourceCreate(ApiResourceBase):
    type: Literal["webhook"]
    callback_path: str = Field(min_length=1, max_length=120)
    verification_token: str = Field(min_length=1, max_length=500)
    signing_secret: str = Field(min_length=1, max_length=500)
    signature_header: str = Field(min_length=1, max_length=120)
    event_filter: str = Field(default="", max_length=200)
class OutgoingApiDetailResponse(ApiResourceResponse):
    auth_config: OutgoingAuthConfig = Field(default_factory=OutgoingAuthConfig)
    recent_deliveries: list[OutgoingDeliveryHistoryEntry] = Field(default_factory=list)
class InboundApiCreated(InboundApiResponse):
    secret: str
    endpoint_url: str
class InboundApiDetail(InboundApiResponse):
    endpoint_url: str
    events: list[dict[str, Any]]
class AutomationRunDetailResponse(AutomationRunResponse):
    steps: list[AutomationRunStepResponse]
class AutomationDetailResponse(AutomationSummaryResponse):
    steps: list[AutomationStepDefinition]
class ScriptResponse(ScriptSummaryResponse):
    code: str
async def lifespan(app: FastAPI):
    run_migrations(database_url=app.state.database_url)
    connection = connect(database_url=app.state.database_url)
    seed_default_settings(connection)
    ensure_legacy_connector_storage_migrated(connection)
    write_tools_manifest(Path(app.state.root_dir), connection)
    if not getattr(app.state, "skip_ui_build_check", False):
        ensure_built_ui(Path(app.state.root_dir))
    app.state.connection = connection
    app.state.smtp_manager = SmtpRuntimeManager()
    configured_settings = get_settings_payload(connection)
    app.state.connector_oauth_states = {}
    app.state.logger = configure_application_logger(
        app,
        root_dir=Path(app.state.root_dir),
        max_file_size_mb=configured_settings["logging"]["max_file_size_mb"],
    )
    app.state.smtp_manager = SmtpRuntimeManager(app.state.logger)
    app.state.smtp_manager.set_message_callback(lambda message: handle_smtp_message_automation_triggers(app, message))
    write_application_log(
        app.state.logger,
        logging.INFO,
        "app_started",
        db_path=app.state.db_path,
        log_file_path=app.state.log_file_path,
        log_file_max_bytes=app.state.log_file_max_bytes,
    )
    runtime_event_bus.clear()
    refresh_scheduler_jobs(connection)
    runtime_scheduler.start(lambda: run_scheduler_tick(app), interval_seconds=30)
    stop_event = threading.Event()
    worker_thread: threading.Thread | None = None
    coordinator_url = os.getenv("MALCOM_COORDINATOR_URL", "").strip()
    if coordinator_url:
        worker_thread = threading.Thread(
            target=run_remote_worker_loop,
            args=(app, stop_event, coordinator_url.rstrip("/")),
            name="malcom-remote-worker",
            daemon=True,
        )
        worker_thread.start()
    else:
        worker_thread = threading.Thread(
            target=run_local_worker_loop,
            args=(app, stop_event),
            name="malcom-local-worker",
            daemon=True,
        )
        worker_thread.start()
    app.state.worker_stop_event = stop_event
    app.state.worker_thread = worker_thread
    sync_smtp_tool_runtime(app, connection)
    try:
        yield
    finally:
        runtime_scheduler.stop()
        stop_event.set()
        if worker_thread is not None:
            worker_thread.join(timeout=2.0)
        app.state.smtp_manager.shutdown()
        write_application_log(app.state.logger, logging.INFO, "app_stopped")
        log_handler: RotatingFileHandler | None = getattr(app.state, "log_handler", None)
        if log_handler is not None:
            log_handler.flush()
        connection.close()
def get_connection(request: Request) -> DatabaseConnection:
    return request.app.state.connection
def get_root_dir(request: Request) -> Path:
    return Path(request.app.state.root_dir)
def list_runtime_machine_assignments() -> list[SmtpMachineAssignment]:
    local_worker_id = get_local_worker_id()
    local_machine = SmtpMachineAssignment(
        worker_id=local_worker_id,
        name=get_local_worker_name(),
        hostname=get_runtime_hostname(),
        address=get_local_worker_address(),
        status="healthy",
        is_local=True,
        capabilities=("runtime-trigger-execution", "smtp-server", "image-magic-execution"),
    )
    machines: dict[str, SmtpMachineAssignment] = {local_worker_id: local_machine}

    for worker in runtime_event_bus.list_workers():
        capabilities = tuple(dict.fromkeys(worker.capabilities))
        if worker.worker_id == local_worker_id:
            machines[worker.worker_id] = SmtpMachineAssignment(
                worker_id=worker.worker_id,
                name=worker.name,
                hostname=worker.hostname,
                address=worker.address,
                status=worker.status,
                is_local=True,
                capabilities=tuple(dict.fromkeys((*capabilities, "smtp-server", "image-magic-execution"))),
            )
            continue

        machines[worker.worker_id] = SmtpMachineAssignment(
            worker_id=worker.worker_id,
            name=worker.name,
            hostname=worker.hostname,
            address=worker.address,
            status=worker.status,
            is_local=False,
            capabilities=capabilities,
        )

    return sorted(machines.values(), key=lambda item: (not item.is_local, item.name.lower()))
def machine_assignment_to_response(machine: SmtpMachineAssignment) -> RuntimeMachineResponse:
    return RuntimeMachineResponse(
        id=machine.worker_id,
        name=machine.name,
        hostname=machine.hostname,
        address=machine.address,
        status=machine.status,
        is_local=machine.is_local,
        capabilities=list(machine.capabilities),
    )
def get_selected_smtp_machine(config: dict[str, Any], machines: list[SmtpMachineAssignment]) -> SmtpMachineAssignment | None:
    target_worker_id = config.get("target_worker_id") or get_local_worker_id()
    return next((machine for machine in machines if machine.worker_id == target_worker_id), None)
def normalize_smtp_recipient_list(recipients: list[str]) -> list[str]:
    normalized: list[str] = []
    for recipient in recipients:
        value = str(recipient or "").strip().lower()
        if value:
            normalized.append(value)
    return normalized
def build_smtp_inbound_identity(config: dict[str, Any], runtime: dict[str, Any]) -> SmtpInboundIdentityResponse:
    configured_recipient_email = config.get("recipient_email")
    listening_host = runtime.get("listening_host")
    listening_port = runtime.get("listening_port")
    accepts_any_recipient = configured_recipient_email is None
    display_address = configured_recipient_email or "Catch-all recipient"
    endpoint = f"{listening_host}:{listening_port}" if listening_host and listening_port is not None else "listener offline"
    connection_hint = (
        f"Send SMTP mail to {display_address} via {endpoint}."
        if configured_recipient_email
        else f"Send SMTP mail to any recipient via {endpoint}."
    )
    return SmtpInboundIdentityResponse(
        display_address=display_address,
        configured_recipient_email=configured_recipient_email,
        accepts_any_recipient=accepts_any_recipient,
        listening_host=listening_host,
        listening_port=listening_port,
        connection_hint=connection_hint,
    )
def build_smtp_email_message(*, mail_from: str, recipients: list[str], subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body or "")
    return message
def get_local_smtp_runtime_or_400(app: FastAPI) -> dict[str, Any]:
    runtime = app.state.smtp_manager.snapshot()
    if runtime.get("status") != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SMTP listener is not running.")
    if runtime.get("listening_host") is None or runtime.get("listening_port") is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SMTP listener endpoint is unavailable.")
    return runtime
def validate_smtp_send_inputs(*, mail_from: str, recipients: list[str]) -> list[str]:
    normalized_sender = str(mail_from or "").strip().lower()
    normalized_recipients = normalize_smtp_recipient_list(recipients)
    if not normalized_sender or "@" not in normalized_sender:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A valid sender email is required.")
    if not normalized_recipients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="At least one recipient email is required.")
    if any("@" not in recipient for recipient in normalized_recipients):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Recipient email addresses must be valid.")
    return normalized_recipients
def send_smtp_relay_message(payload: SmtpRelaySendRequest) -> None:
    recipients = validate_smtp_send_inputs(mail_from=payload.mail_from, recipients=payload.recipients)
    message = build_smtp_email_message(
        mail_from=payload.mail_from.strip(),
        recipients=recipients,
        subject=payload.subject.strip(),
        body=payload.body,
    )
    timeout_seconds = 10

    if payload.auth_mode == "password":
        if not payload.username or not payload.password:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Username and password are required for SMTP authentication.")

    try:
        if payload.security == "tls":
            with smtplib.SMTP_SSL(payload.host, payload.port, timeout=timeout_seconds) as client:
                if payload.auth_mode == "password":
                    client.login(payload.username or "", payload.password or "")
                client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
            return

        with smtplib.SMTP(payload.host, payload.port, timeout=timeout_seconds) as client:
            if payload.security == "starttls":
                client.starttls(context=ssl.create_default_context())
            if payload.auth_mode == "password":
                client.login(payload.username or "", payload.password or "")
            client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
    except smtplib.SMTPAuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP authentication failed: {error.smtp_error.decode(errors='ignore') if isinstance(error.smtp_error, bytes) else error.smtp_error or 'authentication failed'}") from error
    except (ssl.SSLError, smtplib.SMTPNotSupportedError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP TLS negotiation failed: {error}") from error
    except (socket.gaierror, TimeoutError, OSError, smtplib.SMTPConnectError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP connection failed: {error}") from error
    except smtplib.SMTPRecipientsRefused as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP recipients refused: {', '.join(error.recipients.keys())}") from error
    except smtplib.SMTPException as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP send failed: {error}") from error
def sync_smtp_tool_runtime(app: FastAPI, connection: DatabaseConnection) -> None:
    smtp_manager: SmtpRuntimeManager = app.state.smtp_manager
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    machine = get_selected_smtp_machine(config, machines)
    if machine is None:
        smtp_manager.sync(
            enabled=False,
            bind_host=config["bind_host"],
            port=config["port"],
            recipient_email=config.get("recipient_email"),
            machine=None,
        )
        return

    if not machine.is_local:
        smtp_manager.stop()
        try:
            worker = get_runtime_worker_or_error(machine.worker_id)
            call_worker_rpc(
                worker,
                method="POST",
                path="/api/v1/internal/workers/tools/smtp/sync",
                json_body={
                    "enabled": config["enabled"],
                    "bind_host": config["bind_host"],
                    "port": config["port"],
                    "recipient_email": config.get("recipient_email"),
                },
                timeout=2.0,
            )
        except Exception:
            return
        return

    smtp_manager.sync(
        enabled=config["enabled"],
        bind_host=config["bind_host"],
        port=config["port"],
        recipient_email=config.get("recipient_email"),
        machine=machine,
    )


def fetch_remote_smtp_tool_state(connection: DatabaseConnection, worker_id: str) -> dict[str, Any]:
    worker = get_runtime_worker_or_error(worker_id)
    response = call_worker_rpc(
        worker,
        method="GET",
        path="/api/v1/internal/workers/tools/smtp/status",
        timeout=2.0,
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Remote SMTP status response was invalid.")
    return payload


def build_smtp_tool_response(app: FastAPI, connection: DatabaseConnection) -> SmtpToolResponse:
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    runtime = app.state.smtp_manager.snapshot()
    inbound_identity = build_smtp_inbound_identity(config, runtime)

    selected_machine = get_selected_smtp_machine(config, machines)
    if selected_machine is not None and not selected_machine.is_local:
        try:
            remote_state = fetch_remote_smtp_tool_state(connection, selected_machine.worker_id)
            runtime = remote_state.get("runtime") or runtime
            inbound_identity_payload = remote_state.get("inbound_identity") or {}
            inbound_identity = SmtpInboundIdentityResponse(**{
                "display_address": inbound_identity_payload.get("display_address") or inbound_identity.display_address,
                "configured_recipient_email": inbound_identity_payload.get("configured_recipient_email"),
                "accepts_any_recipient": bool(inbound_identity_payload.get("accepts_any_recipient")),
                "listening_host": inbound_identity_payload.get("listening_host"),
                "listening_port": inbound_identity_payload.get("listening_port"),
                "connection_hint": inbound_identity_payload.get("connection_hint") or inbound_identity.connection_hint,
            })
        except Exception as error:
            runtime = {
                **runtime,
                "status": "assigned",
                "message": f"Remote SMTP worker sync failed: {error}",
                "selected_machine_id": selected_machine.worker_id,
                "selected_machine_name": selected_machine.name,
                "last_error": str(error),
            }

    return SmtpToolResponse(
        tool_id="smtp",
        config=SmtpToolConfigResponse(
            enabled=config["enabled"],
            target_worker_id=config.get("target_worker_id"),
            bind_host=config["bind_host"],
            port=config["port"],
            recipient_email=config.get("recipient_email"),
        ),
        runtime=SmtpToolRuntimeResponse(**runtime),
        inbound_identity=inbound_identity,
        machines=[machine_assignment_to_response(machine) for machine in machines],
    )
def build_local_llm_tool_response(connection: DatabaseConnection) -> LocalLlmToolResponse:
    config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
    presets = [
        LocalLlmPresetResponse(
            id=preset_id,
            label=str(preset["label"]),
            server_base_url=str(preset["server_base_url"]),
            endpoints=LocalLlmEndpointsResponse(**preset["endpoints"]),
        )
        for preset_id, preset in get_local_llm_endpoint_presets().items()
    ]
    return LocalLlmToolResponse(
        tool_id="llm-deepl",
        config=LocalLlmToolConfigResponse(
            enabled=config["enabled"],
            provider=config["provider"],
            server_base_url=config["server_base_url"],
            model_identifier=config["model_identifier"],
            endpoints=LocalLlmEndpointsResponse(**config["endpoints"]),
        ),
        presets=presets,
    )
def build_coqui_tts_tool_response(connection: DatabaseConnection, *, root_dir: Path) -> CoquiTtsToolResponse:
    config = normalize_coqui_tts_tool_config(get_coqui_tts_tool_config(connection), root_dir=root_dir)
    return CoquiTtsToolResponse(
        tool_id="coqui-tts",
        config=CoquiTtsToolConfigResponse(
            enabled=config["enabled"],
            command=config["command"],
            model_name=config["model_name"],
            speaker=config["speaker"],
            language=config["language"],
            output_directory=config["output_directory"],
        ),
    )


def build_image_magic_tool_response(connection: DatabaseConnection) -> ImageMagicToolResponse:
    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
    machines = list_runtime_machine_assignments()
    return ImageMagicToolResponse(
        tool_id="image-magic",
        config=ImageMagicToolConfigResponse(
            enabled=config["enabled"],
            target_worker_id=config.get("target_worker_id"),
            command=config["command"],
            default_retries=get_default_tool_retries(connection),
        ),
        machines=[machine_assignment_to_response(machine) for machine in machines],
    )
def handle_smtp_message_automation_triggers(app: FastAPI, message: dict[str, Any]) -> None:
    connection = connect(database_url=app.state.database_url)
    try:
        initialize(connection)
        matching_automations = fetch_all(
            connection,
            """
            SELECT id, trigger_config_json
            FROM automations
            WHERE enabled = 1
              AND trigger_type = 'smtp_email'
            ORDER BY created_at ASC
            """,
        )
        message_subject = str(message.get("subject") or "").strip().lower()
        message_recipients = [str(item or "").strip().lower() for item in message.get("recipients", []) if str(item or "").strip()]

        for automation_row in matching_automations:
            trigger_config = AutomationTriggerConfig(**json.loads(automation_row["trigger_config_json"]))
            expected_subject = str(trigger_config.smtp_subject or "").strip().lower()
            expected_recipient = str(trigger_config.smtp_recipient_email or "").strip().lower()

            if expected_subject and message_subject != expected_subject:
                continue
            if expected_recipient and expected_recipient not in message_recipients:
                continue

            execute_automation_definition(
                connection,
                app.state.logger,
                automation_id=automation_row["id"],
                trigger_type="smtp_email",
                payload={
                    "smtp": message,
                    "subject": message.get("subject"),
                    "body": message.get("body"),
                    "mail_from": message.get("mail_from"),
                    "recipients": message.get("recipients"),
                    "received_at": message.get("received_at"),
                },
                root_dir=Path(app.state.root_dir),
                database_url=app.state.database_url,
            )
    finally:
        connection.close()
def sync_managed_tool_enabled_state(request: Request, tool_id: str, enabled: bool) -> ToolDirectoryEntryResponse:
    entry = set_tool_enabled(
        get_root_dir(request),
        get_connection(request),
        tool_id,
        enabled=enabled,
    )
    return ToolDirectoryEntryResponse(**entry)
def build_tool_directory_response(request: Request) -> list[ToolDirectoryEntryResponse]:
    """Build tool manifest for automation builder from the tools table.

    Data lineage: See README.md > Data Lineage Reference > Tools Manifest
    Source: tools table in database. Default tools synced at startup via sync_tools_to_database().
    """
    connection = get_connection(request)
    entries = load_tool_directory(get_root_dir(request), connection)
    return [ToolDirectoryEntryResponse(**entry) for entry in entries]


def _normalize_dashboard_log_level(level_value: str | None) -> Literal["debug", "info", "warning", "error"]:
    normalized = str(level_value or "").strip().lower()
    if normalized in {"critical", "fatal", "error"}:
        return "error"
    if normalized in {"warn", "warning"}:
        return "warning"
    if normalized == "debug":
        return "debug"
    return "info"


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _get_dashboard_log_settings(connection: DatabaseConnection) -> DashboardLogSettingsResponse:
    defaults = dict(DEFAULT_APP_SETTINGS.get("logging") or {})
    stored_settings = read_stored_settings_section(connection, "logging")
    merged_settings = defaults | (stored_settings if isinstance(stored_settings, dict) else {})

    return DashboardLogSettingsResponse(
        max_stored_entries=_coerce_int(merged_settings.get("max_stored_entries"), 250, 50, 5000),
        max_visible_entries=_coerce_int(merged_settings.get("max_visible_entries"), 50, 10, 500),
        max_detail_characters=_coerce_int(merged_settings.get("max_detail_characters"), 4000, 500, 20000),
    )


def _parse_log_timestamp(date_part: str | None, time_part: str | None) -> str:
    if not date_part or not time_part:
        return utc_now_iso()
    try:
        parsed = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S,%f")
        return parsed.replace(tzinfo=UTC).isoformat()
    except ValueError:
        return utc_now_iso()


def _normalize_dashboard_log_entry(
    *,
    line: str,
    line_number: int,
    date_part: str | None,
    time_part: str | None,
    level_part: str | None,
    message_part: str,
) -> DashboardLogEntryResponse:
    timestamp = _parse_log_timestamp(date_part, time_part)
    level = _normalize_dashboard_log_level(level_part)

    parsed_payload: Any
    try:
        parsed_payload = json.loads(message_part)
    except json.JSONDecodeError:
        parsed_payload = None

    event = "runtime_log"
    source = "backend.runtime"
    category = "runtime"
    action = "log_line"
    message = message_part.strip() or "Runtime log line recorded."
    details: dict[str, Any] = {}
    context: dict[str, Any] = {}

    if isinstance(parsed_payload, dict):
        payload = parsed_payload
        event_value = payload.get("event")
        if isinstance(event_value, str) and event_value.strip():
            event = event_value.strip()
            action = event

        context_value = payload.get("context")
        if isinstance(context_value, dict):
            context = context_value

        source_value = context.get("source") if isinstance(context.get("source"), str) else None
        if source_value:
            source = source_value

        component_value = context.get("component") if isinstance(context.get("component"), str) else None
        if component_value and not source_value:
            source = component_value

        category_value = context.get("category") if isinstance(context.get("category"), str) else None
        if category_value:
            category = category_value
        elif "." in source:
            category = source.split(".", 1)[0]

        message_value = context.get("message") if isinstance(context.get("message"), str) else None
        if message_value and message_value.strip():
            message = message_value.strip()
        elif isinstance(event_value, str) and event_value.strip():
            message = event_value.strip().replace("_", " ")

        details = {
            key: value
            for key, value in payload.items()
            if key not in {"event", "context"}
        }
    else:
        details = {
            "raw_line": line,
        }

    digest = hashlib.sha1(f"{line_number}:{line}".encode("utf-8", errors="ignore")).hexdigest()[:12]

    return DashboardLogEntryResponse(
        id=f"log-{digest}",
        timestamp=timestamp,
        level=level,
        source=source,
        category=category,
        action=action,
        message=message,
        details=details,
        context=context,
    )


def get_runtime_dashboard_logs_response(connection: DatabaseConnection, root_dir: Path) -> DashboardLogsApiResponse:
    settings = _get_dashboard_log_settings(connection)
    log_file_path = get_log_file_path_core(root_dir)
    metadata = DashboardLogsMetadataResponse(
        allowed_levels=[DashboardLogLevelOptionResponse(**item) for item in DEFAULT_DASHBOARD_LOG_LEVEL_OPTIONS]
    )

    if not log_file_path.exists() or not log_file_path.is_file():
        return DashboardLogsApiResponse(settings=settings, metadata=metadata, entries=[])

    try:
        raw_lines = log_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return DashboardLogsApiResponse(settings=settings, metadata=metadata, entries=[])

    pattern = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s+(?P<level>[A-Z]+)\s*(?P<message>.*)$"
    )

    entries: list[DashboardLogEntryResponse] = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue

        match = pattern.match(line)
        if match is None:
            entry = _normalize_dashboard_log_entry(
                line=line,
                line_number=line_number,
                date_part=None,
                time_part=None,
                level_part=None,
                message_part=line,
            )
        else:
            entry = _normalize_dashboard_log_entry(
                line=line,
                line_number=line_number,
                date_part=match.group("date"),
                time_part=match.group("time"),
                level_part=match.group("level"),
                message_part=match.group("message") or "",
            )

        entries.append(entry)

    if len(entries) > settings.max_stored_entries:
        entries = entries[-settings.max_stored_entries:]

    entries.reverse()
    return DashboardLogsApiResponse(settings=settings, metadata=metadata, entries=entries)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _snapshot_storage_usage() -> dict[str, float | int]:
    try:
        import psutil  # type: ignore

        local_usage = psutil.disk_usage("/")
        seen_devices: set[str] = set()
        total_used_bytes = 0
        total_capacity_bytes = 0

        for partition in psutil.disk_partitions(all=False):
            device_key = partition.device or partition.mountpoint
            if not device_key or device_key in seen_devices:
                continue
            seen_devices.add(device_key)
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except Exception:
                continue
            total_used_bytes += int(max(0, usage.used))
            total_capacity_bytes += int(max(0, usage.total))

        if total_capacity_bytes <= 0:
            total_used_bytes = int(max(0, local_usage.used))
            total_capacity_bytes = int(max(0, local_usage.total))

        total_usage_percent = 0.0
        if total_capacity_bytes > 0:
            total_usage_percent = (total_used_bytes / total_capacity_bytes) * 100.0

        return {
            "total_used_bytes": total_used_bytes,
            "total_capacity_bytes": total_capacity_bytes,
            "total_usage_percent": round(total_usage_percent, 2),
            "local_used_bytes": int(max(0, local_usage.used)),
            "local_capacity_bytes": int(max(0, local_usage.total)),
            "local_usage_percent": round(float(getattr(local_usage, "percent", 0.0)), 2),
        }
    except Exception:
        return {
            "total_used_bytes": 0,
            "total_capacity_bytes": 0,
            "total_usage_percent": 0.0,
            "local_used_bytes": 0,
            "local_capacity_bytes": 0,
            "local_usage_percent": 0.0,
        }


def _snapshot_io_counters() -> dict[str, int]:
    try:
        import psutil  # type: ignore

        disk_counters = psutil.disk_io_counters() or None
        network_counters = psutil.net_io_counters() or None
        return {
            "disk_read_bytes": int(max(0, getattr(disk_counters, "read_bytes", 0))),
            "disk_write_bytes": int(max(0, getattr(disk_counters, "write_bytes", 0))),
            "network_sent_bytes": int(max(0, getattr(network_counters, "bytes_sent", 0))),
            "network_received_bytes": int(max(0, getattr(network_counters, "bytes_recv", 0))),
        }
    except Exception:
        return {
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "network_sent_bytes": 0,
            "network_received_bytes": 0,
        }


def _snapshot_top_processes(*, limit: int = 5) -> list[dict[str, Any]]:
    try:
        import psutil  # type: ignore

        processes: list[dict[str, Any]] = []
        for process in psutil.process_iter(["pid", "name", "memory_info", "memory_percent"]):
            try:
                info = process.info
                memory_info = info.get("memory_info")
                rss_bytes = int(max(0, getattr(memory_info, "rss", 0)))
                processes.append(
                    {
                        "pid": _as_int(info.get("pid")),
                        "name": str(info.get("name") or f"pid-{_as_int(info.get('pid'))}"),
                        "memory_mb": round(rss_bytes / (1024.0 * 1024.0), 2),
                        "memory_percent": round(_as_float(info.get("memory_percent")), 2),
                    }
                )
            except Exception:
                continue

        processes.sort(key=lambda item: item["memory_mb"], reverse=True)
        return processes[: max(1, limit)]
    except Exception:
        return []


def _parse_top_processes(raw_value: Any) -> list[DashboardResourceDashboardTopProcessResponse]:
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(parsed, list):
        return []

    top_processes: list[DashboardResourceDashboardTopProcessResponse] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        pid = _as_int(item.get("pid"), default=-1)
        if pid < 0:
            continue
        top_processes.append(
            DashboardResourceDashboardTopProcessResponse(
                pid=pid,
                name=str(item.get("name") or f"pid-{pid}"),
                memory_mb=round(_as_float(item.get("memory_mb")), 2),
                memory_percent=round(_as_float(item.get("memory_percent")), 2),
            )
        )
    return top_processes


def _build_resource_trend_points(
    rows: list[dict[str, Any]],
    *,
    primary_key: str,
    secondary_key: str | None = None,
    use_delta: bool = False,
) -> list[DashboardResourceDashboardTrendPointResponse]:
    points: list[DashboardResourceDashboardTrendPointResponse] = []
    previous_primary = None
    previous_secondary = None

    for row in rows:
        primary_value = _as_float(row.get(primary_key))
        secondary_value = _as_float(row.get(secondary_key)) if secondary_key else None

        if use_delta:
            if previous_primary is None:
                primary_delta = 0.0
            else:
                primary_delta = max(0.0, primary_value - previous_primary)

            secondary_delta = None
            if secondary_key:
                if previous_secondary is None or secondary_value is None:
                    secondary_delta = 0.0
                else:
                    secondary_delta = max(0.0, secondary_value - previous_secondary)

            points.append(
                DashboardResourceDashboardTrendPointResponse(
                    captured_at=str(row.get("captured_at") or ""),
                    primary_value=round(primary_delta, 2),
                    secondary_value=round(secondary_delta, 2) if secondary_delta is not None else None,
                )
            )
        else:
            points.append(
                DashboardResourceDashboardTrendPointResponse(
                    captured_at=str(row.get("captured_at") or ""),
                    primary_value=round(primary_value, 2),
                    secondary_value=round(secondary_value, 2) if secondary_value is not None else None,
                )
            )

        previous_primary = primary_value
        previous_secondary = secondary_value

    return points


def persist_runtime_resource_history_snapshot(connection: DatabaseConnection, *, force: bool = False) -> None:
    global _RESOURCE_SNAPSHOT_LAST_PERSISTED_AT_MONOTONIC

    now_monotonic = time.monotonic()
    if not force and now_monotonic - _RESOURCE_SNAPSHOT_LAST_PERSISTED_AT_MONOTONIC < RESOURCE_SNAPSHOT_INTERVAL_SECONDS:
        return

    with _RESOURCE_SNAPSHOT_LOCK:
        now_monotonic = time.monotonic()
        if not force and now_monotonic - _RESOURCE_SNAPSHOT_LAST_PERSISTED_AT_MONOTONIC < RESOURCE_SNAPSHOT_INTERVAL_SECONDS:
            return

        summary = get_metrics_collector().summary()
        metrics = summary.get("metrics") if isinstance(summary, dict) else []
        metrics = metrics if isinstance(metrics, list) else []

        pending_jobs = 0
        claimed_jobs = 0
        for job in runtime_event_bus.pending_jobs():
            if job.status == "claimed":
                claimed_jobs += 1
            else:
                pending_jobs += 1

        hottest_metric = metrics[0] if metrics else None
        total_error_count = sum(_as_int(metric.get("error_count")) for metric in metrics if isinstance(metric, dict))
        max_memory_peak_mb = max(
            (_as_float(metric.get("memory_peak_mb")) for metric in metrics if isinstance(metric, dict)),
            default=0.0,
        )
        storage_usage = _snapshot_storage_usage()
        io_counters = _snapshot_io_counters()
        top_processes = _snapshot_top_processes()

        snapshot_id = f"resource-snapshot-{uuid4().hex}"
        captured_at = utc_now_iso()

        connection.execute(
            """
            INSERT INTO runtime_resource_snapshots (
                snapshot_id,
                captured_at,
                process_memory_mb,
                process_cpu_percent,
                queue_pending_jobs,
                queue_claimed_jobs,
                tracked_operations,
                total_error_count,
                hottest_operation,
                hottest_total_duration_ms,
                max_memory_peak_mb,
                total_storage_used_bytes,
                total_storage_capacity_bytes,
                total_storage_usage_percent,
                local_storage_used_bytes,
                local_storage_capacity_bytes,
                local_storage_usage_percent,
                disk_read_bytes,
                disk_write_bytes,
                network_sent_bytes,
                network_received_bytes,
                top_processes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                captured_at,
                round(max(0.0, snapshot_process_memory_mb()), 2),
                round(max(0.0, snapshot_process_cpu_percent()), 2),
                pending_jobs,
                claimed_jobs,
                _as_int(summary.get("total_metrics")) if isinstance(summary, dict) else 0,
                total_error_count,
                str(hottest_metric.get("operation")) if isinstance(hottest_metric, dict) and hottest_metric.get("operation") else None,
                round(_as_float(hottest_metric.get("total_duration_ms")) if isinstance(hottest_metric, dict) else 0.0, 2),
                round(max_memory_peak_mb, 2),
                _as_int(storage_usage.get("total_used_bytes")),
                _as_int(storage_usage.get("total_capacity_bytes")),
                round(_as_float(storage_usage.get("total_usage_percent")), 2),
                _as_int(storage_usage.get("local_used_bytes")),
                _as_int(storage_usage.get("local_capacity_bytes")),
                round(_as_float(storage_usage.get("local_usage_percent")), 2),
                _as_int(io_counters.get("disk_read_bytes")),
                _as_int(io_counters.get("disk_write_bytes")),
                _as_int(io_counters.get("network_sent_bytes")),
                _as_int(io_counters.get("network_received_bytes")),
                json.dumps(top_processes),
            ),
        )
        connection.commit()
        _RESOURCE_SNAPSHOT_LAST_PERSISTED_AT_MONOTONIC = now_monotonic


def get_runtime_resource_history_response(
    connection: DatabaseConnection,
    *,
    limit: int = RESOURCE_SNAPSHOT_DEFAULT_LIMIT,
) -> DashboardResourceHistoryApiResponse:
    safe_limit = max(1, min(limit, 200))

    count_row = fetch_one(connection, "SELECT COUNT(*) AS total FROM runtime_resource_snapshots")
    total_snapshots = _as_int((count_row or {}).get("total"))

    rows = fetch_all(
        connection,
        """
        SELECT
            snapshot_id,
            captured_at,
            process_memory_mb,
            process_cpu_percent,
            queue_pending_jobs,
            queue_claimed_jobs,
            tracked_operations,
            total_error_count,
            hottest_operation,
            hottest_total_duration_ms,
            max_memory_peak_mb,
            total_storage_used_bytes,
            total_storage_capacity_bytes,
            total_storage_usage_percent,
            local_storage_used_bytes,
            local_storage_capacity_bytes,
            local_storage_usage_percent,
            disk_read_bytes,
            disk_write_bytes,
            network_sent_bytes,
            network_received_bytes,
            top_processes_json
        FROM runtime_resource_snapshots
        ORDER BY captured_at DESC
        LIMIT ?
        """,
        (safe_limit,),
    )

    entries = [DashboardResourceHistoryEntryResponse(**dict(row)) for row in rows]
    return DashboardResourceHistoryApiResponse(
        collected_at=utc_now_iso(),
        total_snapshots=total_snapshots,
        entries=entries,
    )


def get_runtime_resource_dashboard_response(
    connection: DatabaseConnection,
    *,
    limit: int = 24,
) -> DashboardResourceDashboardApiResponse:
    safe_limit = max(1, min(limit, 72))

    count_row = fetch_one(connection, "SELECT COUNT(*) AS total FROM runtime_resource_snapshots")
    total_snapshots = _as_int((count_row or {}).get("total"))

    rows_desc = [
        dict(row)
        for row in fetch_all(
            connection,
            """
            SELECT
                snapshot_id,
                captured_at,
                process_memory_mb,
                process_cpu_percent,
                queue_pending_jobs,
                queue_claimed_jobs,
                tracked_operations,
                total_error_count,
                hottest_operation,
                hottest_total_duration_ms,
                max_memory_peak_mb,
                total_storage_used_bytes,
                total_storage_capacity_bytes,
                total_storage_usage_percent,
                local_storage_used_bytes,
                local_storage_capacity_bytes,
                local_storage_usage_percent,
                disk_read_bytes,
                disk_write_bytes,
                network_sent_bytes,
                network_received_bytes,
                top_processes_json
            FROM runtime_resource_snapshots
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        )
    ]

    latest_row = rows_desc[0] if rows_desc else None
    rows_asc = list(reversed(rows_desc))

    latest_snapshot = None
    if latest_row is not None:
        latest_snapshot = DashboardResourceDashboardLatestSnapshotResponse(
            captured_at=str(latest_row.get("captured_at") or ""),
            process_memory_mb=round(_as_float(latest_row.get("process_memory_mb")), 2),
            process_cpu_percent=round(_as_float(latest_row.get("process_cpu_percent")), 2),
            queue_pending_jobs=_as_int(latest_row.get("queue_pending_jobs")),
            queue_claimed_jobs=_as_int(latest_row.get("queue_claimed_jobs")),
            tracked_operations=_as_int(latest_row.get("tracked_operations")),
            total_error_count=_as_int(latest_row.get("total_error_count")),
            hottest_operation=str(latest_row.get("hottest_operation")) if latest_row.get("hottest_operation") else None,
            hottest_total_duration_ms=round(_as_float(latest_row.get("hottest_total_duration_ms")), 2),
            max_memory_peak_mb=round(_as_float(latest_row.get("max_memory_peak_mb")), 2),
        )

    storage = DashboardResourceDashboardStorageResponse(
        total_used_bytes=_as_int((latest_row or {}).get("total_storage_used_bytes")),
        total_capacity_bytes=_as_int((latest_row or {}).get("total_storage_capacity_bytes")),
        total_usage_percent=round(_as_float((latest_row or {}).get("total_storage_usage_percent")), 2),
        local_used_bytes=_as_int((latest_row or {}).get("local_storage_used_bytes")),
        local_capacity_bytes=_as_int((latest_row or {}).get("local_storage_capacity_bytes")),
        local_usage_percent=round(_as_float((latest_row or {}).get("local_storage_usage_percent")), 2),
    )

    cpu_points = _build_resource_trend_points(rows_asc, primary_key="process_cpu_percent")
    disk_points = _build_resource_trend_points(
        rows_asc,
        primary_key="disk_read_bytes",
        secondary_key="disk_write_bytes",
        use_delta=True,
    )
    network_points = _build_resource_trend_points(
        rows_asc,
        primary_key="network_sent_bytes",
        secondary_key="network_received_bytes",
        use_delta=True,
    )

    widgets = [
        DashboardResourceDashboardWidgetResponse(
            id="cpu",
            label="CPU",
            primary_label="Process CPU",
            primary_unit="percent",
            primary_latest=round(_as_float((latest_row or {}).get("process_cpu_percent")), 2),
            points=cpu_points,
        ),
        DashboardResourceDashboardWidgetResponse(
            id="disk-io",
            label="Disk I/O",
            primary_label="Read",
            primary_unit="bytes",
            primary_latest=round(disk_points[-1].primary_value, 2) if disk_points else 0.0,
            secondary_label="Write",
            secondary_unit="bytes",
            secondary_latest=round(disk_points[-1].secondary_value or 0.0, 2) if disk_points else 0.0,
            points=disk_points,
        ),
        DashboardResourceDashboardWidgetResponse(
            id="network-io",
            label="Network I/O",
            primary_label="Sent",
            primary_unit="bytes",
            primary_latest=round(network_points[-1].primary_value, 2) if network_points else 0.0,
            secondary_label="Received",
            secondary_unit="bytes",
            secondary_latest=round(network_points[-1].secondary_value or 0.0, 2) if network_points else 0.0,
            points=network_points,
        ),
    ]

    return DashboardResourceDashboardApiResponse(
        collected_at=utc_now_iso(),
        total_snapshots=total_snapshots,
        last_captured_at=str((latest_row or {}).get("captured_at")) if latest_row else None,
        latest_snapshot=latest_snapshot,
        storage=storage,
        highest_memory_processes=_parse_top_processes((latest_row or {}).get("top_processes_json")),
        widgets=widgets,
    )


def get_runtime_devices_response() -> DashboardDevicesApiResponse:
    sampled_at = utc_now_iso()
    hostname = platform.node() or "Unknown host"
    operating_system = f"{platform.system()} {platform.release()}".strip()
    architecture = platform.machine() or "Unknown architecture"

    try:
        import psutil

        memory = psutil.virtual_memory()
        storage = psutil.disk_usage("/")
    except Exception:
        host = HostMachineSummary(
            id="host-malcom-runtime",
            name="Malcom host",
            status="offline",
            location=hostname,
            detail="Host telemetry is temporarily unavailable from the local runtime.",
            last_seen_at=sampled_at,
            hostname=hostname,
            operating_system=operating_system,
            architecture=architecture,
            memory_total_bytes=0,
            memory_used_bytes=0,
            memory_available_bytes=0,
            memory_usage_percent=0,
            storage_total_bytes=0,
            storage_used_bytes=0,
            storage_free_bytes=0,
            storage_usage_percent=0,
            sampled_at=sampled_at,
        )
    else:
        host = HostMachineSummary(
            id="host-malcom-runtime",
            name="Malcom host",
            status="healthy",
            location=hostname,
            detail="Local runtime host serving the API, dashboard, and scheduler process set.",
            last_seen_at=sampled_at,
            hostname=hostname,
            operating_system=operating_system,
            architecture=architecture,
            memory_total_bytes=int(memory.total),
            memory_used_bytes=int(memory.used),
            memory_available_bytes=int(memory.available),
            memory_usage_percent=float(memory.percent),
            storage_total_bytes=int(storage.total),
            storage_used_bytes=int(storage.used),
            storage_free_bytes=int(storage.free),
            storage_usage_percent=float(getattr(storage, "percent", 0.0)),
            sampled_at=sampled_at,
        )

    devices = [
        DashboardDeviceResponse(
            id="service-runtime-endpoint",
            name="Runtime command endpoint",
            kind="service",
            status="healthy",
            location="127.0.0.1",
            detail="Command executor is available for automation step dispatch.",
            last_seen_at=sampled_at,
        ),
        DashboardDeviceResponse(
            id="service-api-endpoint",
            name="FastAPI server",
            kind="service",
            status="healthy",
            location="localhost:8000",
            detail="Serving local endpoints for the dashboard, settings, runs, and automations.",
            last_seen_at=sampled_at,
        ),
    ]

    for worker in runtime_event_bus.list_workers():
        if worker.worker_id == get_local_worker_id():
            continue

        devices.append(
            DashboardDeviceResponse(
                id=f"worker-{worker.worker_id}",
                name=worker.name,
                kind="service",
                status="healthy" if worker.status == "healthy" else "offline",
                location=worker.address,
                detail=f"Registered LAN worker on {worker.hostname} ready to claim queued automation runs.",
                last_seen_at=worker.last_seen_at,
            )
        )

    return DashboardDevicesApiResponse(host=host, devices=devices)


def get_runtime_queue_response() -> DashboardQueueApiResponse:
    jobs = runtime_event_bus.pending_jobs()
    queue_status = runtime_event_bus.queue_status()
    queue_jobs = [
        DashboardQueueJobResponse(
            job_id=job.job_id,
            run_id=job.run_id,
            step_id=job.step_id,
            status="claimed" if job.status == "claimed" else "pending",
            worker_id=job.worker_id,
            worker_name=job.worker_name,
            claimed_at=job.claimed_at,
            completed_at=job.completed_at,
            trigger_type=job.trigger.type,
            api_id=job.trigger.api_id,
            event_id=job.trigger.event_id,
            received_at=job.trigger.received_at,
        )
        for job in jobs
    ]
    pending_jobs = sum(1 for job in queue_jobs if job.status == "pending")
    claimed_jobs = sum(1 for job in queue_jobs if job.status == "claimed")

    return DashboardQueueApiResponse(
        status=queue_status["status"],
        is_paused=bool(queue_status["is_paused"]),
        status_updated_at=str(queue_status["updated_at"]),
        total_jobs=len(queue_jobs),
        pending_jobs=pending_jobs,
        claimed_jobs=claimed_jobs,
        jobs=queue_jobs,
    )


def set_runtime_queue_pause_state(paused: bool) -> DashboardQueueApiResponse:
    runtime_event_bus.set_queue_paused(paused)
    return get_runtime_queue_response()


def _normalize_dashboard_run_status(status_value: str, error_summary: str | None) -> Literal["success", "warning", "error", "idle"]:
    normalized_status = (status_value or "").strip().lower()
    has_error_summary = bool((error_summary or "").strip())

    if normalized_status == "failed" or has_error_summary:
        return "error"
    if normalized_status == "completed":
        return "success"
    if normalized_status in {"running", "queued", "pending", "claimed"}:
        return "warning"
    return "idle"


def _normalize_dashboard_trigger_type(trigger_type: str) -> Literal["schedule", "manual", "inbound_api", "smtp_email"]:
    normalized_trigger = (trigger_type or "").strip().lower()
    if normalized_trigger == "schedule":
        return "schedule"
    if normalized_trigger == "manual":
        return "manual"
    if normalized_trigger == "smtp_email":
        return "smtp_email"
    return "inbound_api"


def get_runtime_dashboard_summary_response(connection: DatabaseConnection) -> DashboardSummaryApiResponse:
    now_iso = utc_now_iso()
    runtime_status = runtime_scheduler.status()
    queue_response = get_runtime_queue_response()
    workers = runtime_event_bus.list_workers()

    runs_row = fetch_one(
        connection,
        """
        SELECT
            COUNT(*) AS total_runs,
            SUM(CASE WHEN status = 'completed' AND COALESCE(TRIM(error_summary), '') = '' THEN 1 ELSE 0 END) AS success_runs,
            SUM(CASE WHEN status IN ('running', 'pending', 'queued') THEN 1 ELSE 0 END) AS warning_runs,
            SUM(CASE WHEN status = 'failed' OR COALESCE(TRIM(error_summary), '') <> '' THEN 1 ELSE 0 END) AS error_runs
        FROM automation_runs
        WHERE started_at >= ?
        """,
        ((datetime.now(UTC) - timedelta(hours=24)).isoformat(),),
    )

    recent_run_rows = fetch_all(
        connection,
        """
        SELECT
            automation_runs.run_id,
            automation_runs.automation_id,
            automation_runs.trigger_type,
            automation_runs.status,
            automation_runs.started_at,
            automation_runs.finished_at,
            automation_runs.duration_ms,
            automation_runs.error_summary,
            automations.name AS automation_name
        FROM automation_runs
        LEFT JOIN automations ON automations.id = automation_runs.automation_id
        ORDER BY automation_runs.started_at DESC
        LIMIT 10
        """,
    )

    inbound_row = fetch_one(
        connection,
        """
        SELECT
            COUNT(*) AS inbound_total,
            SUM(CASE WHEN status NOT IN ('accepted', 'completed', 'success') THEN 1 ELSE 0 END) AS inbound_errors
        FROM inbound_api_events
        WHERE received_at >= ?
        """,
        ((datetime.now(UTC) - timedelta(hours=24)).isoformat(),),
    )

    outgoing_scheduled_row = fetch_one(
        connection,
        "SELECT COUNT(*) AS total FROM outgoing_scheduled_apis WHERE enabled = 1 AND is_mock = 0",
    )
    outgoing_continuous_row = fetch_one(
        connection,
        "SELECT COUNT(*) AS total FROM outgoing_continuous_apis WHERE enabled = 1 AND is_mock = 0",
    )

    connectors_settings = get_stored_connector_settings(connection)
    connector_records = connectors_settings.get("records") if isinstance(connectors_settings, dict) else []
    connector_records = connector_records if isinstance(connector_records, list) else []

    connector_status_counts = {
        "connected": 0,
        "needs_attention": 0,
        "expired": 0,
        "revoked": 0,
        "draft": 0,
        "pending_oauth": 0,
    }
    for record in connector_records:
        if not isinstance(record, dict):
            continue
        status_value = str(record.get("status") or "draft")
        if status_value in connector_status_counts:
            connector_status_counts[status_value] += 1
        else:
            connector_status_counts["draft"] += 1

    total_runs = int((runs_row or {}).get("total_runs") or 0)
    success_runs = int((runs_row or {}).get("success_runs") or 0)
    warning_runs = int((runs_row or {}).get("warning_runs") or 0)
    error_runs = int((runs_row or {}).get("error_runs") or 0)
    idle_runs = max(0, total_runs - success_runs - warning_runs - error_runs)

    inbound_total = int((inbound_row or {}).get("inbound_total") or 0)
    inbound_errors = int((inbound_row or {}).get("inbound_errors") or 0)
    inbound_error_rate = round((inbound_errors / inbound_total) * 100, 1) if inbound_total else 0.0

    worker_total = len(workers)
    worker_healthy = sum(1 for worker in workers if worker.status == "healthy")
    worker_offline = max(0, worker_total - worker_healthy)

    needs_attention_total = (
        connector_status_counts["needs_attention"]
        + connector_status_counts["expired"]
        + connector_status_counts["revoked"]
    )

    health_status: Literal["healthy", "degraded", "offline"] = "healthy"
    if not runtime_status.get("active"):
        health_status = "offline"
    elif queue_response.is_paused or error_runs > 0 or needs_attention_total > 0 or inbound_errors > 0:
        health_status = "degraded"

    alerts: list[DashboardSummaryAlertResponse] = []
    if not runtime_status.get("active"):
        alerts.append(
            DashboardSummaryAlertResponse(
                id="runtime-scheduler-offline",
                severity="error",
                title="Scheduler inactive",
                message="Runtime scheduler is not active. Scheduled automations may not execute.",
                source="runtime",
                created_at=now_iso,
            )
        )
    if queue_response.is_paused:
        alerts.append(
            DashboardSummaryAlertResponse(
                id="runtime-queue-paused",
                severity="warning",
                title="Queue paused",
                message="Trigger queue is paused. Pending jobs will not be claimed.",
                source="queue",
                created_at=now_iso,
            )
        )
    if error_runs > 0:
        alerts.append(
            DashboardSummaryAlertResponse(
                id="automation-run-errors",
                severity="error",
                title="Automation run failures detected",
                message=f"{error_runs} automation runs failed in the last 24 hours.",
                source="automations",
                created_at=now_iso,
            )
        )
    if needs_attention_total > 0:
        alerts.append(
            DashboardSummaryAlertResponse(
                id="connector-needs-attention",
                severity="warning",
                title="Connector attention required",
                message=f"{needs_attention_total} connectors need attention.",
                source="connectors",
                created_at=now_iso,
            )
        )
    if inbound_errors > 0:
        alerts.append(
            DashboardSummaryAlertResponse(
                id="inbound-api-errors",
                severity="warning",
                title="Inbound API delivery issues",
                message=f"{inbound_errors} inbound events reported non-success status in the last 24 hours.",
                source="apis",
                created_at=now_iso,
            )
        )

    if not alerts:
        alerts.append(
            DashboardSummaryAlertResponse(
                id="system-healthy",
                severity="info",
                title="No active incidents",
                message="All monitored services are operating within expected limits.",
                source="dashboard",
                created_at=now_iso,
            )
        )

    services: list[DashboardSummaryServiceResponse] = [
        DashboardSummaryServiceResponse(
            id="service-runtime-scheduler",
            name="Runtime scheduler",
            status="healthy" if runtime_status.get("active") else "offline",
            detail="Schedules and dispatches automation work.",
            last_check_at=str(runtime_status.get("last_tick_finished_at") or now_iso),
        ),
        DashboardSummaryServiceResponse(
            id="service-runtime-queue",
            name="Runtime queue",
            status="degraded" if queue_response.is_paused else "healthy",
            detail=f"{queue_response.pending_jobs} pending and {queue_response.claimed_jobs} claimed jobs.",
            last_check_at=queue_response.status_updated_at,
        ),
        DashboardSummaryServiceResponse(
            id="service-runtime-workers",
            name="Worker fleet",
            status="degraded" if worker_offline > 0 else "healthy",
            detail=f"{worker_healthy} healthy of {worker_total} registered workers.",
            last_check_at=now_iso,
        ),
        DashboardSummaryServiceResponse(
            id="service-runtime-apis",
            name="API deliveries",
            status="degraded" if inbound_errors > 0 else "healthy",
            detail=f"{inbound_total} inbound events in 24h, {inbound_errors} flagged as errors.",
            last_check_at=now_iso,
        ),
        DashboardSummaryServiceResponse(
            id="service-runtime-connectors",
            name="Connector health",
            status="degraded" if needs_attention_total > 0 else "healthy",
            detail=f"{connector_status_counts['connected']} connected, {needs_attention_total} require action.",
            last_check_at=now_iso,
        ),
    ]

    quick_links = [
        DashboardSummaryQuickLinkResponse(
            id="queue",
            label="Queue jobs",
            href="queue.html",
            count=queue_response.pending_jobs,
        ),
        DashboardSummaryQuickLinkResponse(
            id="logs",
            label="Recent incidents",
            href="logs.html",
            count=error_runs + inbound_errors,
        ),
        DashboardSummaryQuickLinkResponse(
            id="automations",
            label="Automations",
            href="../automations/overview.html",
            count=total_runs,
        ),
        DashboardSummaryQuickLinkResponse(
            id="apis",
            label="Inbound APIs",
            href="../apis/incoming.html",
            count=inbound_total,
        ),
        DashboardSummaryQuickLinkResponse(
            id="connectors",
            label="Connectors",
            href="../settings/connectors.html",
            count=len(connector_records),
        ),
    ]

    recent_runs = [
        DashboardSummaryRecentRunResponse(
            id=str(row["run_id"]),
            automation_name=str(row.get("automation_name") or row["automation_id"]),
            trigger_type=_normalize_dashboard_trigger_type(str(row.get("trigger_type") or "")),
            status=_normalize_dashboard_run_status(str(row.get("status") or ""), row.get("error_summary")),
            started_at=str(row.get("started_at") or now_iso),
            finished_at=row.get("finished_at"),
            duration_ms=row.get("duration_ms"),
        )
        for row in recent_run_rows
    ]

    health_label = {
        "healthy": "All systems healthy",
        "degraded": "Performance attention needed",
        "offline": "Runtime offline",
    }[health_status]
    health_summary = {
        "healthy": "Scheduler, queue, workers, and connectors report healthy behavior.",
        "degraded": "One or more runtime domains require attention. Review incidents and service cards.",
        "offline": "Runtime scheduler is inactive and automation orchestration is unavailable.",
    }[health_status]

    return DashboardSummaryApiResponse(
        health=DashboardSummaryHealthResponse(
            id="system-health",
            status=health_status,
            label=health_label,
            summary=health_summary,
            updated_at=now_iso,
        ),
        services=services,
        run_counts=DashboardSummaryRunCountsResponse(
            success=success_runs,
            warning=warning_runs,
            error=error_runs,
            idle=idle_runs,
        ),
        recent_runs=recent_runs,
        alerts=alerts,
        quick_links=quick_links,
        runtime_overview=DashboardSummaryRuntimeOverviewResponse(
            scheduler_active=bool(runtime_status.get("active")),
            queue_status=queue_response.status,
            queue_pending_jobs=queue_response.pending_jobs,
            queue_claimed_jobs=queue_response.claimed_jobs,
            queue_updated_at=queue_response.status_updated_at,
            scheduler_last_tick_started_at=runtime_status.get("last_tick_started_at"),
            scheduler_last_tick_finished_at=runtime_status.get("last_tick_finished_at"),
        ),
        worker_health=DashboardSummaryWorkerHealthResponse(
            total=worker_total,
            healthy=worker_healthy,
            offline=worker_offline,
        ),
        api_performance=DashboardSummaryApiPerformanceResponse(
            inbound_total_24h=inbound_total,
            inbound_errors_24h=inbound_errors,
            error_rate_percent_24h=inbound_error_rate,
            outgoing_scheduled_enabled=int((outgoing_scheduled_row or {}).get("total") or 0),
            outgoing_continuous_enabled=int((outgoing_continuous_row or {}).get("total") or 0),
        ),
        connector_health=DashboardSummaryConnectorHealthResponse(
            total=len(connector_records),
            connected=connector_status_counts["connected"],
            needs_attention=connector_status_counts["needs_attention"],
            expired=connector_status_counts["expired"],
            revoked=connector_status_counts["revoked"],
            draft=connector_status_counts["draft"],
            pending_oauth=connector_status_counts["pending_oauth"],
        ),
    )


def get_api_or_404(connection: DatabaseConnection, api_id: str) -> DatabaseRow:
    row = fetch_one(
        connection,
        """
        SELECT
            inbound_apis.*,
            COALESCE(ranked_events.events_count, 0) AS events_count,
            ranked_events.last_received_at,
            ranked_events.status AS last_delivery_status
        FROM inbound_apis
        LEFT JOIN (
            SELECT
                api_id,
                status,
                COUNT(*) OVER (PARTITION BY api_id) AS events_count,
                MAX(received_at) OVER (PARTITION BY api_id) AS last_received_at,
                ROW_NUMBER() OVER (PARTITION BY api_id ORDER BY received_at DESC) AS row_number
            FROM inbound_api_events
        ) AS ranked_events
            ON ranked_events.api_id = inbound_apis.id
            AND ranked_events.row_number = 1
        WHERE inbound_apis.id = ?
        AND inbound_apis.is_mock = 0
        """,
        (api_id,),
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound API not found.")

    return row
def serialize_api_detail(connection: DatabaseConnection, api_id: str, request: Request) -> InboundApiDetail:
    api_row = get_api_or_404(connection, api_id)
    event_rows = fetch_all(
        connection,
        """
        SELECT event_id, api_id, received_at, status, request_headers_subset, payload_json, source_ip, error_message
        FROM inbound_api_events
        WHERE api_id = ?
        AND is_mock = 0
        ORDER BY received_at DESC
        LIMIT 20
        """,
        (api_id,),
    )
    detail = row_to_api_summary(api_row)
    detail["endpoint_url"] = str(request.base_url).rstrip("/") + detail["endpoint_path"]
    detail["events"] = [row_to_event(row) for row in event_rows]
    return InboundApiDetail(**detail)
def get_outgoing_api_or_404(
    connection: DatabaseConnection,
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
) -> DatabaseRow:
    table_name = "outgoing_scheduled_apis" if api_type == "outgoing_scheduled" else "outgoing_continuous_apis"
    row = fetch_one(
        connection,
        f"SELECT * FROM {table_name} WHERE id = ? AND is_mock = 0",
        (api_id,),
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outgoing API not found.")

    return row
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
def build_schedule_expression(scheduled_time: str) -> str:
    hour, minute = scheduled_time.split(":")
    return f"{int(minute)} {int(hour)} * * *"
def log_event(
    connection: DatabaseConnection,
    logger: logging.Logger,
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
            0,
        ),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING if error_message else logging.INFO,
        "inbound_api_event_recorded",
        event_id=event_id,
        api_id=api_id,
        status=status_value,
        source_ip=source_ip,
        headers=headers,
        payload=payload,
        error_message=error_message,
    )
def calculate_duration_ms(started_at: str, finished_at: str) -> int:
    return calculate_duration_ms_core(started_at, finished_at)
def create_automation_run(
    connection: DatabaseConnection,
    *,
    run_id: str,
    automation_id: str,
    trigger_type: str,
    status_value: str,
    worker_id: str | None = None,
    worker_name: str | None = None,
    started_at: str,
) -> None:
    create_automation_run_core(
        connection,
        run_id=run_id,
        automation_id=automation_id,
        trigger_type=trigger_type,
        status_value=status_value,
        worker_id=worker_id,
        worker_name=worker_name,
        started_at=started_at,
    )
def create_automation_run_step(
    connection: DatabaseConnection,
    *,
    step_id: str,
    run_id: str,
    step_name: str,
    status_value: str,
    request_summary: str | None,
    started_at: str,
    inputs_json: dict[str, Any] | None = None,
) -> None:
    create_automation_run_step_core(
        connection,
        step_id=step_id,
        run_id=run_id,
        step_name=step_name,
        status_value=status_value,
        request_summary=request_summary,
        started_at=started_at,
        inputs_json=inputs_json,
    )


def finalize_automation_run_step(
    connection: DatabaseConnection,
    *,
    step_id: str,
    status_value: str,
    response_summary: str | None,
    detail: dict[str, Any] | None,
    finished_at: str,
    response_body_json: Any | None = None,
    extracted_fields_json: dict[str, Any] | None = None,
) -> None:
    finalize_automation_run_step_core(
        connection,
        step_id=step_id,
        status_value=status_value,
        response_summary=response_summary,
        detail=detail,
        finished_at=finished_at,
        response_body_json=response_body_json,
        extracted_fields_json=extracted_fields_json,
    )
def finalize_automation_run(
    connection: DatabaseConnection,
    *,
    run_id: str,
    status_value: str,
    error_summary: str | None,
    finished_at: str,
) -> None:
    finalize_automation_run_core(
        connection,
        run_id=run_id,
        status_value=status_value,
        error_summary=error_summary,
        finished_at=finished_at,
    )
def assign_automation_run_worker(
    connection: DatabaseConnection,
    *,
    run_id: str,
    worker_id: str,
    worker_name: str,
) -> None:
    assign_automation_run_worker_core(connection, run_id=run_id, worker_id=worker_id, worker_name=worker_name)
def register_runtime_worker(
    *,
    worker_id: str,
    name: str,
    hostname: str,
    address: str,
    capabilities: list[str] | None = None,
) -> RegisteredWorker:
    return runtime_event_bus.register_worker(
        worker_id=worker_id,
        name=name,
        hostname=hostname,
        address=address,
        capabilities=capabilities or ["runtime-trigger-execution"],
        seen_at=utc_now_iso(),
    )
def process_runtime_job(
    connection: DatabaseConnection,
    logger: logging.Logger,
    *,
    job: RuntimeTriggerJob,
    worker_id: str,
    worker_name: str,
) -> None:
    finished_at = utc_now_iso()
    runtime_event_bus.complete_job(
        job_id=job.job_id,
        worker_id=worker_id,
        status_value="completed",
        completed_at=finished_at,
    )
    assign_automation_run_worker(
        connection,
        run_id=job.run_id,
        worker_id=worker_id,
        worker_name=worker_name,
    )
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
    finalize_automation_run(
        connection,
        run_id=job.run_id,
        status_value="completed",
        error_summary=None,
        finished_at=finished_at,
    )


def fail_runtime_job(
    connection: DatabaseConnection,
    logger: logging.Logger,
    *,
    job: RuntimeTriggerJob,
    worker_id: str,
    worker_name: str,
    error_summary: str,
) -> None:
    finished_at = utc_now_iso()
    completed_job = runtime_event_bus.complete_job(
        job_id=job.job_id,
        worker_id=worker_id,
        status_value="failed",
        completed_at=finished_at,
    )
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

    assign_automation_run_worker(
        connection,
        run_id=job.run_id,
        worker_id=worker_id,
        worker_name=worker_name,
    )
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
    finalize_automation_run(
        connection,
        run_id=job.run_id,
        status_value="failed",
        error_summary=error_summary,
        finished_at=finished_at,
    )


def run_local_worker_loop(app: FastAPI, stop_event: threading.Event) -> None:
    logger = app.state.logger
    connection = app.state.connection
    worker_id = get_local_worker_id()
    worker_name = get_local_worker_name()
    register_runtime_worker(
        worker_id=worker_id,
        name=worker_name,
        hostname=get_runtime_hostname(),
        address=get_local_worker_address(),
    )

    while not stop_event.is_set():
        register_runtime_worker(
            worker_id=worker_id,
            name=worker_name,
            hostname=get_runtime_hostname(),
            address=get_local_worker_address(),
        )
        job = runtime_event_bus.claim_next(
            worker_id=worker_id,
            worker_name=worker_name,
            claimed_at=utc_now_iso(),
        )
        if job is None:
            stop_event.wait(LOCAL_WORKER_POLL_INTERVAL_SECONDS)
            continue

        try:
            process_runtime_job(
                connection,
                logger,
                job=job,
                worker_id=worker_id,
                worker_name=worker_name,
            )
        except Exception as error:
            fail_runtime_job(
                connection,
                logger,
                job=job,
                worker_id=worker_id,
                worker_name=worker_name,
                error_summary=str(error),
            )


def run_remote_worker_loop(app: FastAPI, stop_event: threading.Event, coordinator_url: str) -> None:
    logger = app.state.logger
    worker_id = get_local_worker_id()
    worker_name = get_local_worker_name()
    payload = {
        "worker_id": worker_id,
        "name": worker_name,
        "hostname": get_runtime_hostname(),
        "address": get_local_worker_address(),
        "capabilities": ["runtime-trigger-execution", "smtp-server", "image-magic-execution"],
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
                            "detail": {
                                "worker_id": worker_id,
                                "worker_name": worker_name,
                                "execution_mode": "remote",
                            },
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
def get_automation_or_404(connection: DatabaseConnection, automation_id: str) -> DatabaseRow:
    row = fetch_one(
        connection,
        """
        SELECT
            automations.*,
            COUNT(automation_steps.step_id) AS step_count
        FROM automations
        LEFT JOIN automation_steps ON automation_steps.automation_id = automations.id
        WHERE automations.id = ?
        GROUP BY automations.id
        """,
        (automation_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation not found.")
    return row
def list_automation_steps(connection: DatabaseConnection, automation_id: str) -> list[AutomationStepDefinition]:
    rows = fetch_all(
        connection,
        """
        SELECT step_id, automation_id, position, step_type, name, config_json,
               on_true_step_id, on_false_step_id, is_merge_target,
               created_at, updated_at
        FROM automation_steps
        WHERE automation_id = ?
        ORDER BY position ASC
        """,
        (automation_id,),
    )
    return [row_to_automation_step(row) for row in rows]
def serialize_automation_detail(connection: DatabaseConnection, automation_id: str) -> AutomationDetailResponse:
    row = get_automation_or_404(connection, automation_id)
    return AutomationDetailResponse(
        **row_to_automation_summary(row),
        steps=list_automation_steps(connection, automation_id),
    )
def replace_automation_steps(
    connection: DatabaseConnection,
    automation_id: str,
    steps: list[AutomationStepDefinition],
    *,
    timestamp: str,
) -> None:
    connection.execute("DELETE FROM automation_steps WHERE automation_id = ?", (automation_id,))
    for index, step in enumerate(steps):
        step_id = step.id or f"automation_step_{uuid4().hex[:10]}"
        connection.execute(
            """
            INSERT INTO automation_steps (
                step_id,
                automation_id,
                position,
                step_type,
                name,
                config_json,
                on_true_step_id,
                on_false_step_id,
                is_merge_target,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step_id,
                automation_id,
                index,
                step.type,
                step.name,
                json.dumps(step.config.model_dump()),
                step.on_true_step_id,
                step.on_false_step_id,
                1 if step.is_merge_target else 0,
                timestamp,
                timestamp,
            ),
        )
def refresh_automation_schedule(connection: DatabaseConnection, automation_id: str) -> None:
    row = get_automation_or_404(connection, automation_id)
    trigger_config = AutomationTriggerConfig(**json.loads(row["trigger_config_json"]))
    next_run_at: str | None = None
    if bool(row["enabled"]) and row["trigger_type"] == "schedule" and trigger_config.schedule_time:
        next_run_at = next_daily_run_at(trigger_config.schedule_time)
    connection.execute(
        "UPDATE automations SET next_run_at = ?, updated_at = ? WHERE id = ?",
        (next_run_at, utc_now_iso(), automation_id),
    )
    connection.commit()
def refresh_outgoing_schedule(connection: DatabaseConnection, api_id: str) -> None:
    row = fetch_one(connection, "SELECT enabled, scheduled_time FROM outgoing_scheduled_apis WHERE id = ?", (api_id,))
    if row is None:
        return
    next_run_at: str | None = None
    if bool(row["enabled"]) and row["scheduled_time"]:
        next_run_at = next_daily_run_at(row["scheduled_time"])
    connection.execute(
        "UPDATE outgoing_scheduled_apis SET next_run_at = ?, updated_at = ? WHERE id = ?",
        (next_run_at, utc_now_iso(), api_id),
    )
    connection.commit()


def refresh_continuous_outgoing_schedule(connection: DatabaseConnection, api_id: str) -> None:
    row = fetch_one(
        connection,
        """
        SELECT enabled, repeat_enabled, repeat_interval_minutes, next_run_at
        FROM outgoing_continuous_apis
        WHERE id = ?
        """,
        (api_id,),
    )
    if row is None:
        return

    next_run_at: str | None = None
    if bool(row["enabled"]) and bool(row["repeat_enabled"]) and row["repeat_interval_minutes"]:
        existing = parse_iso_datetime(row["next_run_at"])
        if existing is not None:
            next_run_at = existing.isoformat()
        else:
            next_run_at = utc_now_iso()
    connection.execute(
        "UPDATE outgoing_continuous_apis SET next_run_at = ?, updated_at = ? WHERE id = ?",
        (next_run_at, utc_now_iso(), api_id),
    )
    connection.commit()
def render_template_string(template: str | None, context: dict[str, Any]) -> str:
    raw = template or ""

    def replace(match: re.Match[str]) -> str:
        current: Any = context
        for segment in match.group(1).strip().split("."):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return ""
        return str(current if current is not None else "")

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace, raw)


_JSON_PATH_SEGMENT_RE = re.compile(r"([^[.\]]+)|\[(\d+)\]")


def normalize_response_mapping_key(path: str) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9_]+", "_", path.strip()).strip("_").lower()
    if not candidate:
        return "value"
    if candidate[0].isdigit():
        candidate = f"field_{candidate}"
    return candidate


def parse_json_path_segments(path: str) -> list[str | int]:
    segments: list[str | int] = []
    for match in _JSON_PATH_SEGMENT_RE.finditer(path.strip()):
        key_segment, index_segment = match.groups()
        if key_segment is not None:
            segments.append(key_segment)
        elif index_segment is not None:
            segments.append(int(index_segment))
    return segments


def resolve_json_path(payload: Any, path: str) -> Any:
    current = payload
    segments = parse_json_path_segments(path)
    if not segments:
        raise KeyError("JSON path is empty.")
    for segment in segments:
        if isinstance(segment, int):
            if not isinstance(current, list) or segment >= len(current):
                raise KeyError(path)
            current = current[segment]
            continue
        if not isinstance(current, dict) or segment not in current:
            raise KeyError(path)
        current = current[segment]
    return current


def extract_response_fields(response_body_json: Any, response_mappings: list[dict[str, str]] | None) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    if response_body_json is None:
        return extracted
    for mapping in response_mappings or []:
        path = str(mapping.get("path", "")).strip()
        if not path:
            continue
        key = str(mapping.get("key", "")).strip() or normalize_response_mapping_key(path)
        try:
            extracted[key] = resolve_json_path(response_body_json, path)
        except KeyError:
            extracted[key] = None
    return extracted


def try_parse_json_response_body(response_body: str | None) -> Any | None:
    if not response_body:
        return None
    try:
        return json.loads(response_body)
    except json.JSONDecodeError:
        return None


def parse_optional_structured_input(value: str | None) -> Any:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return ""
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return value


def parse_template_json(template: str | None, context: dict[str, Any]) -> str:
    rendered = render_template_string(template or "{}", context)
    parsed = json.loads(rendered)
    return json.dumps(parsed)


SAFE_PYTHON_SCRIPT_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _build_script_runtime_context(
    context: dict[str, Any],
    *,
    script_input_template: str | None = None,
) -> tuple[dict[str, Any], str]:
    rendered_script_input = render_template_string(script_input_template, context) if script_input_template else ""
    runtime_context = dict(context)
    runtime_context["script_input_raw"] = rendered_script_input
    runtime_context["script_input"] = parse_optional_structured_input(rendered_script_input)
    return runtime_context, rendered_script_input


def _invoke_python_script_run(run_callable: Any, runtime_context: dict[str, Any]) -> Any:
    payload = runtime_context.get("payload")
    script_input = runtime_context.get("script_input")
    try:
        parameters = list(inspect.signature(run_callable).parameters.values())
    except (TypeError, ValueError):
        return run_callable(runtime_context, script_input)

    positional_parameters = [
        parameter
        for parameter in parameters
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    has_varargs = any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters)

    if has_varargs or len(positional_parameters) >= 2:
        return run_callable(runtime_context, script_input)
    if len(positional_parameters) == 1:
        parameter_name = positional_parameters[0].name.lower()
        if "payload" in parameter_name:
            return run_callable(payload)
        return run_callable(runtime_context)
    return run_callable()


def execute_script_step(
    script_row: DatabaseRow,
    context: dict[str, Any],
    *,
    root_dir: Path,
    script_input_template: str | None = None,
) -> RuntimeExecutionResult:
    runtime_context, rendered_script_input = _build_script_runtime_context(
        context,
        script_input_template=script_input_template,
    )
    if script_row["language"] == "python":
        script_globals = {
            "__builtins__": SAFE_PYTHON_SCRIPT_BUILTINS,
            "json": json,
            "re": re,
        }
        local_scope = {
            "context": runtime_context,
            "payload": runtime_context.get("payload"),
            "steps": runtime_context.get("steps", {}),
            "script_input": runtime_context.get("script_input"),
            "script_input_raw": runtime_context.get("script_input_raw"),
            "result": None,
        }
        exec(script_row["code"], script_globals, local_scope)
        if callable(local_scope.get("run")):
            run_result = _invoke_python_script_run(local_scope["run"], runtime_context)
            if run_result is not None:
                local_scope["result"] = run_result
        return RuntimeExecutionResult(
            status="completed",
            response_summary="Python script executed.",
            detail={"script_id": script_row["id"], "script_input_raw": rendered_script_input},
            output=local_scope.get("result"),
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        prefix=".automation-script-",
        dir=get_ui_dir(root_dir),
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        temporary_file.write(
            "(async () => {\n"
            "const context = JSON.parse(process.argv[2]);\n"
            "const scriptInputRaw = process.argv[3] ?? \"\";\n"
            "let scriptInput = scriptInputRaw;\n"
            "try {\n"
            "  scriptInput = scriptInputRaw ? JSON.parse(scriptInputRaw) : \"\";\n"
            "} catch {\n"
            "  scriptInput = scriptInputRaw;\n"
            "}\n"
            "context.script_input_raw = scriptInputRaw;\n"
            "context.script_input = scriptInput;\n"
            "const payload = context.payload;\n"
            "const steps = context.steps || {};\n"
            "let result = null;\n"
            f"{script_row['code']}\n"
            "if (typeof run === 'function') {\n"
            "  const executed = await run(context, scriptInput);\n"
            "  if (executed !== undefined) {\n"
            "    result = executed;\n"
            "  }\n"
            "}\n"
            "process.stdout.write(JSON.stringify(result ?? null));\n"
            "})().catch((error) => {\n"
            "  console.error(error?.stack || error?.message || String(error));\n"
            "  process.exit(1);\n"
            "});\n"
        )
        temporary_path = Path(temporary_file.name)

    try:
        completed = subprocess.run(
            ["node", temporary_path.name, json.dumps(runtime_context), rendered_script_input],
            cwd=get_ui_dir(root_dir),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    finally:
        temporary_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "JavaScript automation step failed.").strip())

    return RuntimeExecutionResult(
        status="completed",
        response_summary="JavaScript script executed.",
        detail={"script_id": script_row["id"], "script_input_raw": rendered_script_input},
        output=json.loads(completed.stdout or "null"),
    )


def _materialize_http_preset_config(
    connection: DatabaseConnection,
    *,
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> AutomationStepDefinition:
    """Materialize HTTP preset into concrete destination_url and payload_template.
    
    If step uses http_preset_id, resolves the preset definition, renders any template
    variables, and returns a new step config with concrete URL and payload.
    If no preset, returns step unchanged.
    """
    if not step.config.http_preset_id:
        return step

    from backend.services.http_presets import get_http_preset

    # Resolve connector provider
    connector_id = step.config.connector_id
    if not connector_id:
        raise RuntimeError(f"HTTP preset step '{step.name}' requires a connector_id.")

    connector_record = find_stored_connector_record(connection, connector_id)
    if not connector_record:
        raise RuntimeError(f"HTTP preset step '{step.name}' references unknown connector '{connector_id}'.")

    provider_id = connector_record.get("provider") or ""
    preset_id = step.config.http_preset_id

    # Look up preset definition
    preset = get_http_preset(provider_id, preset_id)
    if not preset:
        raise RuntimeError(f"HTTP preset step '{step.name}': provider '{provider_id}' does not support preset '{preset_id}'.")

    # Build base endpoint from template
    base_endpoint = "https://www.googleapis.com"  # Google API base for now; can be parameterized later
    endpoint_path = render_template_string(preset.endpoint_path_template, context)
    destination_url = base_endpoint + endpoint_path

    # Materialize payload template with context variables
    payload_template = render_template_string(preset.payload_template, context)

    # Return new step with materialized config
    materialized_config = step.config.model_copy()
    materialized_config.destination_url = destination_url
    materialized_config.payload_template = payload_template
    materialized_config.http_method = preset.http_method
    materialized_config.auth_type = "none"  # Preset mode uses connector auth, not explicit config

    return step.model_copy(update={"config": materialized_config})


def _execute_outbound_request_delivery(
    connection: DatabaseConnection,
    *,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    history_resource_id: str | None = None,
    delivery_executor: Callable[[OutgoingApiTestRequest], OutgoingApiTestResponse] | None = None,
) -> tuple[OutgoingApiTestResponse, Any | None, dict[str, Any]]:
    protection_secret = get_connector_protection_secret(root_dir=root_dir)
    destination_url, auth_type, auth_config = hydrate_outgoing_configuration_from_connector(
        connection,
        connector_id=step.config.connector_id,
        destination_url=render_template_string(step.config.destination_url, context),
        auth_type=step.config.auth_type or "none",
        auth_config=step.config.auth_config,
        protection_secret=protection_secret,
    )
    executor = delivery_executor or execute_outgoing_test_delivery
    started_at = utc_now_iso()
    delivery = executor(
        OutgoingApiTestRequest(
            type="outgoing_scheduled",
            destination_url=destination_url,
            http_method=step.config.http_method or "POST",
            auth_type=auth_type,
            auth_config=auth_config,
            webhook_signing=step.config.webhook_signing,
            payload_template=parse_template_json(step.config.payload_template, context),
            connector_id=step.config.connector_id,
        )
    )
    finished_at = utc_now_iso()
    if history_resource_id:
        record_outgoing_delivery_history(
            connection,
            delivery_id=f"delivery_{uuid4().hex}",
            resource_type="automation_http_step",
            resource_id=history_resource_id,
            status_value="completed" if delivery.ok else "failed",
            http_status_code=delivery.status_code,
            request_summary=f"{step.config.http_method or 'POST'} {destination_url}",
            response_summary=(delivery.response_body or "")[:500] or f"{delivery.status_code} {delivery.destination_url}",
            error_summary=None if delivery.ok else (delivery.response_body or "")[:500],
            started_at=started_at,
            finished_at=finished_at,
        )
        connection.commit()
    response_body_json = try_parse_json_response_body(delivery.response_body)
    extracted_fields = extract_response_fields(response_body_json, step.config.response_mappings)
    return delivery, response_body_json, extracted_fields


def finalize_non_blocking_http_step(
    *,
    database_url: str,
    logger_name: str,
    run_step_id: str,
    automation_id: str,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
    delivery_executor: Callable[[OutgoingApiTestRequest], OutgoingApiTestResponse] | None = None,
) -> None:
    connection = connect(database_url=database_url)
    logger = logging.getLogger(logger_name)
    try:
        delivery, response_body_json, extracted_fields = _execute_outbound_request_delivery(
            connection,
            step=step,
            context=context,
            root_dir=root_dir,
            history_resource_id=run_step_id,
            delivery_executor=delivery_executor,
        )
        detail = delivery.model_dump()
        detail["response_mode"] = "background"
        detail["response_mappings"] = step.config.response_mappings or []
        finalize_automation_run_step(
            connection,
            step_id=run_step_id,
            status_value="completed" if delivery.ok else "failed",
            response_summary=f"{delivery.status_code} {delivery.destination_url}",
            detail=detail,
            response_body_json=response_body_json,
            extracted_fields_json=extracted_fields,
            finished_at=utc_now_iso(),
        )
        write_application_log(
            logger,
            logging.INFO if delivery.ok else logging.WARNING,
            "automation_http_step_background_completed",
            automation_id=automation_id,
            step_name=step.name,
            run_step_id=run_step_id,
            status_code=delivery.status_code,
        )
    except Exception as error:
        finalize_automation_run_step(
            connection,
            step_id=run_step_id,
            status_value="failed",
            response_summary=str(error),
            detail={"error": str(error), "response_mode": "background"},
            finished_at=utc_now_iso(),
        )
        write_application_log(
            logger,
            logging.WARNING,
            "automation_http_step_background_failed",
            automation_id=automation_id,
            step_name=step.name,
            run_step_id=run_step_id,
            error=str(error),
        )
    finally:
        connection.close()


_LOG_DB_PG_TYPE_MAP: dict[str, str] = {
    "text": "TEXT",
    "integer": "INTEGER",
    "real": "DOUBLE PRECISION",
    "boolean": "BOOLEAN",
    "timestamp": "TIMESTAMPTZ",
}

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _assert_safe_identifier(name: str) -> str:
    """Raises RuntimeError if name is not a safe SQL identifier."""
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise RuntimeError(f"Unsafe SQL identifier rejected: {name!r}")
    return name


def _execute_log_db_write(
    connection: DatabaseConnection,
    logger: logging.Logger,
    *,
    automation_id: str,
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> RuntimeExecutionResult:
    """Write a row to a managed log DB table for a Write-to-DB log step."""
    table_id = step.config.log_table_id
    mappings = step.config.log_column_mappings or {}

    table_row = fetch_one(connection, "SELECT * FROM log_db_tables WHERE id = ?", (table_id,))
    if table_row is None:
        raise RuntimeError(f"Log table '{table_id}' not found. Create it before executing.")

    table_name = _assert_safe_identifier(table_row["name"])
    data_table = f"log_data_{table_name}"

    col_rows = fetch_all(
        connection,
        "SELECT column_name, data_type FROM log_db_columns WHERE table_id = ? ORDER BY position",
        (table_id,),
    )
    known_columns = {r["column_name"] for r in col_rows}

    rendered: dict[str, Any] = {}
    for col_name, template in mappings.items():
        _assert_safe_identifier(col_name)
        if col_name not in known_columns:
            raise RuntimeError(f"Column '{col_name}' does not exist in log table '{table_name}'.")
        rendered[col_name] = render_template_string(template, context)

    row_id = f"logrow_{uuid4().hex[:12]}"
    now = utc_now_iso()
    system_cols = ["row_id", "automation_id", "inserted_at"]
    system_vals: list[Any] = [row_id, automation_id, now]

    user_col_names = list(rendered.keys())
    user_col_vals = [rendered[c] for c in user_col_names]

    all_cols = system_cols + user_col_names
    all_vals = system_vals + user_col_vals

    col_list = ", ".join(all_cols)
    placeholders = ", ".join(["?"] * len(all_vals))

    connection.execute(
        f"INSERT INTO {data_table} ({col_list}) VALUES ({placeholders})",
        all_vals,
    )
    connection.commit()

    write_application_log(
        logger,
        logging.INFO,
        "automation_log_db_write",
        automation_id=automation_id,
        step_name=step.name,
        table=table_name,
        row_id=row_id,
    )
    summary = f"Wrote row to {table_name} ({len(rendered)} column(s))"
    return RuntimeExecutionResult(
        status="completed",
        response_summary=summary,
        detail={"table": table_name, "row_id": row_id, "columns_written": list(rendered.keys())},
        output={"table": table_name, "row_id": row_id},
    )


from . import automation_executor as _automation_executor

finalize_non_blocking_http_step = _automation_executor.finalize_non_blocking_http_step
execute_automation_step = _automation_executor.execute_automation_step
fetch_run_detail = _automation_executor.fetch_run_detail
execute_automation_definition = _automation_executor.execute_automation_definition
execute_scheduled_api = _automation_executor.execute_scheduled_api
execute_continuous_api = _automation_executor.execute_continuous_api
refresh_scheduler_jobs = _automation_executor.refresh_scheduler_jobs
run_scheduler_tick = _automation_executor.run_scheduler_tick
