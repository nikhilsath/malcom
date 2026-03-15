from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import secrets
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.database import DEFAULT_DB_PATH, connect, fetch_all, fetch_one, initialize
import httpx

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
from backend.tool_registry import get_project_root, update_tool_metadata, write_tools_manifest


INBOUND_SECRET_PREFIX = "malcom_sk_v1_"
INBOUND_SECRET_BYTES = 32
LOGGER_NAME = "malcom"
DEFAULT_LOG_FILE_NAME = "malcom.log"
DEFAULT_LOG_BACKUP_COUNT = 5
LOCAL_WORKER_POLL_INTERVAL_SECONDS = 0.25
REMOTE_WORKER_POLL_INTERVAL_SECONDS = 1.0
SMTP_TOOL_SETTINGS_KEY = "smtp_tool"
DEFAULT_SMTP_TOOL_CONFIG = {
    "enabled": False,
    "target_worker_id": None,
    "bind_host": "127.0.0.1",
    "port": 2525,
    "recipient_email": None,
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


def get_log_dir(root_dir: Path) -> Path:
    return root_dir / "backend" / "data" / "logs"


def get_log_file_path(root_dir: Path) -> Path:
    return get_log_dir(root_dir) / DEFAULT_LOG_FILE_NAME


def mb_to_bytes(size_mb: int) -> int:
    return size_mb * 1024 * 1024


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [json_safe(item) for item in value]
        return str(value)


def configure_application_logger(app: FastAPI, *, root_dir: Path, max_file_size_mb: int) -> logging.Logger:
    log_dir = get_log_dir(root_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = get_log_file_path(root_dir)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    current_handler: RotatingFileHandler | None = getattr(app.state, "log_handler", None)
    desired_max_bytes = mb_to_bytes(max_file_size_mb)
    should_replace_handler = (
        current_handler is None
        or Path(current_handler.baseFilename) != log_file_path
        or current_handler.maxBytes != desired_max_bytes
    )

    if should_replace_handler:
        if current_handler is not None:
            logger.removeHandler(current_handler)
            current_handler.close()

        handler = RotatingFileHandler(
            log_file_path,
            maxBytes=desired_max_bytes,
            backupCount=DEFAULT_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        app.state.log_handler = handler

    app.state.log_file_path = str(log_file_path)
    app.state.log_file_max_bytes = desired_max_bytes
    return logger


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
    payload = {"event": event, **{key: json_safe(value) for key, value in fields.items()}}
    logger.log(level, json.dumps(payload, sort_keys=True))


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
            status,
            schedule_expression,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "scheduled_demo_push",
            "Scheduled Demo Push",
            "Runs every hour in developer mode.",
            "scheduled-demo-push",
            1,
            1,
            "active",
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
            callback_path,
            verification_token,
            signing_secret,
            signature_header,
            event_filter,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "webhook_demo_registry",
            "Demo Webhook Registry",
            "Developer-mode webhook definition.",
            "webhook-demo-registry",
            1,
            1,
            "webhook",
            "/demo/webhooks/orders",
            "demo_verify_token",
            "demo_signing_secret",
            "X-Demo-Signature",
            "order.created,order.updated",
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
        "worker_id": row["worker_id"] if "worker_id" in row.keys() else None,
        "worker_name": row["worker_name"] if "worker_name" in row.keys() else None,
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


def row_to_automation_summary(row: sqlite3.Row) -> dict[str, Any]:
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


def row_to_automation_step(row: sqlite3.Row) -> AutomationStepDefinition:
    return AutomationStepDefinition(
        id=row["step_id"],
        type=row["step_type"],
        name=row["name"],
        config=AutomationStepConfig(**json.loads(row["config_json"])),
    )


def validate_automation_definition(
    payload: AutomationCreate | AutomationUpdate | AutomationDetailResponse,
    *,
    require_steps: bool = False,
) -> list[str]:
    issues: list[str] = []
    trigger_type = payload.trigger_type
    trigger_config = payload.trigger_config
    steps = payload.steps if hasattr(payload, "steps") else None

    if trigger_type == "schedule" and not trigger_config.schedule_time:
        issues.append("Scheduled automations require trigger_config.schedule_time.")
    if trigger_type == "inbound_api" and not trigger_config.inbound_api_id:
        issues.append("Inbound API automations require trigger_config.inbound_api_id.")
    if require_steps and not steps:
        issues.append("Automations require at least one step.")

    for index, step in enumerate(steps or [], start=1):
        if step.type == "log" and not step.config.message:
            issues.append(f"Step {index} requires config.message for log steps.")
        if step.type == "outbound_request":
            if not step.config.destination_url:
                issues.append(f"Step {index} requires config.destination_url.")
            if step.config.payload_template is None:
                issues.append(f"Step {index} requires config.payload_template.")
            else:
                try:
                    json.loads(step.config.payload_template)
                except json.JSONDecodeError as error:
                    issues.append(f"Step {index} has invalid JSON payload_template: {error.msg}.")
        if step.type == "script" and not step.config.script_id:
            issues.append(f"Step {index} requires config.script_id for script steps.")
        if step.type == "tool" and not step.config.tool_id:
            issues.append(f"Step {index} requires config.tool_id for tool steps.")
        if step.type == "condition" and not step.config.expression:
            issues.append(f"Step {index} requires config.expression for condition steps.")

    return issues


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
        "status": row["status"] if "status" in row.keys() else None,
        "endpoint_path": endpoint_path,
        "destination_url": row["destination_url"] if "destination_url" in row.keys() else None,
        "http_method": row["http_method"] if "http_method" in row.keys() else None,
        "auth_type": row["auth_type"] if "auth_type" in row.keys() else None,
        "repeat_enabled": bool(row["repeat_enabled"]) if "repeat_enabled" in row.keys() else None,
        "repeat_interval_minutes": row["repeat_interval_minutes"] if "repeat_interval_minutes" in row.keys() else None,
        "payload_template": row["payload_template"] if "payload_template" in row.keys() else None,
        "scheduled_time": row["scheduled_time"] if "scheduled_time" in row.keys() else None,
        "schedule_expression": row["schedule_expression"] if "schedule_expression" in row.keys() else None,
        "stream_mode": row["stream_mode"] if "stream_mode" in row.keys() else None,
        "callback_path": row["callback_path"] if "callback_path" in row.keys() else None,
        "signature_header": row["signature_header"] if "signature_header" in row.keys() else None,
        "event_filter": row["event_filter"] if "event_filter" in row.keys() else None,
        "has_verification_token": bool(row["verification_token"]) if "verification_token" in row.keys() else None,
        "has_signing_secret": bool(row["signing_secret"]) if "signing_secret" in row.keys() else None,
    }


def row_to_outgoing_detail_response(row: sqlite3.Row, *, api_type: str, endpoint_path: str) -> OutgoingApiDetailResponse:
    resource = row_to_simple_api_resource(row, api_type=api_type, endpoint_path=endpoint_path)
    auth_config_json = row["auth_config_json"] if "auth_config_json" in row.keys() else "{}"

    try:
      auth_config_payload = json.loads(auth_config_json or "{}")
    except json.JSONDecodeError:
      auth_config_payload = {}

    resource["auth_config"] = OutgoingAuthConfig(**auth_config_payload)
    return OutgoingApiDetailResponse(**resource)


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
        "max_file_size_mb": 5,
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


def merge_settings_section(default_value: Any, stored_value: Any) -> Any:
    if not isinstance(default_value, dict) or not isinstance(stored_value, dict):
        return stored_value

    merged_value = dict(default_value)
    merged_value.update(stored_value)
    return merged_value


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
        settings[row["key"]] = merge_settings_section(
            settings[row["key"]],
            json.loads(row["value_json"]),
        )

    return settings


def get_default_smtp_tool_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_SMTP_TOOL_CONFIG))


def get_smtp_tool_config(connection: sqlite3.Connection) -> dict[str, Any]:
    config = get_default_smtp_tool_config()
    row = fetch_one(
        connection,
        """
        SELECT value_json
        FROM settings
        WHERE key = ?
        """,
        (SMTP_TOOL_SETTINGS_KEY,),
    )
    if row is None:
        return config

    stored_value = json.loads(row["value_json"])
    if isinstance(stored_value, dict):
        config.update(stored_value)
    return config


def save_smtp_tool_config(connection: sqlite3.Connection, config: dict[str, Any]) -> dict[str, Any]:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO settings (key, value_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        (SMTP_TOOL_SETTINGS_KEY, json.dumps(config), now, now),
    )
    connection.commit()
    return config


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


def build_script_validation_issue(message: str, *, line: int | None = None, column: int | None = None) -> ScriptValidationIssue:
    return ScriptValidationIssue(message=message, line=line, column=column)


def validate_python_script(code: str) -> ScriptValidationResult:
    try:
        ast.parse(code, mode="exec")
    except SyntaxError as error:
        return ScriptValidationResult(
            valid=False,
            issues=[
                build_script_validation_issue(
                    error.msg or "Invalid Python syntax.",
                    line=error.lineno,
                    column=error.offset,
                )
            ],
        )

    return ScriptValidationResult(valid=True, issues=[])


def validate_javascript_script(code: str, *, root_dir: Path) -> ScriptValidationResult:
    ui_dir = get_ui_dir(root_dir)
    ui_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        prefix=".script-validation-",
        dir=ui_dir,
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        temporary_file.write(code)
        temporary_path = Path(temporary_file.name)

    try:
        result = subprocess.run(
            ["node", "--check", temporary_path.name],
            cwd=ui_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return ScriptValidationResult(
            valid=False,
            issues=[build_script_validation_issue("JavaScript validation requires Node.js to be installed on the server.")],
        )
    except subprocess.TimeoutExpired:
        return ScriptValidationResult(
            valid=False,
            issues=[build_script_validation_issue("JavaScript validation timed out before the syntax check completed.")],
        )
    finally:
        temporary_path.unlink(missing_ok=True)

    if result.returncode == 0:
        return ScriptValidationResult(valid=True, issues=[])

    stderr = (result.stderr or result.stdout).strip()
    issue_lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    issue_message = issue_lines[-1] if issue_lines else "Invalid JavaScript syntax."
    return ScriptValidationResult(valid=False, issues=[build_script_validation_issue(issue_message)])


def validate_script_payload(language: Literal["python", "javascript"], code: str, *, root_dir: Path) -> ScriptValidationResult:
    if language == "python":
        return validate_python_script(code)
    return validate_javascript_script(code, root_dir=root_dir)


def build_script_validation_fields(result: ScriptValidationResult) -> tuple[str, str | None, str | None]:
    if result.valid:
        return "valid", None, utc_now_iso()

    first_issue = result.issues[0] if result.issues else build_script_validation_issue("Validation failed.")
    location = ""
    if first_issue.line is not None:
        location = f"Line {first_issue.line}"
        if first_issue.column is not None:
            location = f"{location}, column {first_issue.column}"
        location = f"{location}: "
    return "invalid", f"{location}{first_issue.message}", utc_now_iso()


def row_to_script_summary(row: sqlite3.Row) -> ScriptSummaryResponse:
    return ScriptSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        language=row["language"],
        validation_status=row["validation_status"],
        validation_message=row["validation_message"],
        last_validated_at=row["last_validated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_script_response(row: sqlite3.Row) -> ScriptResponse:
    return ScriptResponse(
        **row_to_script_summary(row).model_dump(),
        code=row["code"],
    )


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


class OutgoingAuthConfig(BaseModel):
    token: str | None = Field(default=None, max_length=500)
    username: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, max_length=500)
    header_name: str | None = Field(default=None, max_length=120)
    header_value: str | None = Field(default=None, max_length=500)


class ApiResourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    path_slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool = True


class IncomingApiResourceCreate(ApiResourceBase):
    type: Literal["incoming"]


class OutgoingApiResourceBase(ApiResourceBase):
    repeat_enabled: bool = False
    repeat_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    destination_url: str = Field(min_length=1, max_length=2000)
    http_method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str = Field(default="{}", max_length=10000)


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


ApiResourceCreate = Annotated[
    IncomingApiResourceCreate | ScheduledApiResourceCreate | ContinuousApiResourceCreate | WebhookApiResourceCreate,
    Field(discriminator="type"),
]


class OutgoingApiTestRequest(BaseModel):
    type: str = Field(pattern=r"^outgoing_(scheduled|continuous)$")
    destination_url: str = Field(min_length=1, max_length=2000)
    http_method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str = Field(default="{}", max_length=10000)


class OutgoingApiTestResponse(BaseModel):
    ok: bool
    status_code: int
    response_body: str
    sent_headers: dict[str, str]
    destination_url: str


class ApiResourceResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    path_slug: str
    enabled: bool
    created_at: str
    updated_at: str
    status: str | None = None
    endpoint_path: str | None = None
    endpoint_url: str | None = None
    secret: str | None = None
    destination_url: str | None = None
    http_method: str | None = None
    auth_type: str | None = None
    repeat_enabled: bool | None = None
    repeat_interval_minutes: int | None = None
    payload_template: str | None = None
    scheduled_time: str | None = None
    schedule_expression: str | None = None
    stream_mode: str | None = None
    callback_path: str | None = None
    signature_header: str | None = None
    event_filter: str | None = None
    has_verification_token: bool | None = None
    has_signing_secret: bool | None = None


class OutgoingApiDetailResponse(ApiResourceResponse):
    auth_config: OutgoingAuthConfig = Field(default_factory=OutgoingAuthConfig)


class ScheduledApiResourceUpdate(BaseModel):
    type: Literal["outgoing_scheduled"]
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None
    repeat_enabled: bool | None = None
    destination_url: str | None = Field(default=None, min_length=1, max_length=2000)
    http_method: str | None = Field(default=None, pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default=None, pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str | None = Field(default=None, max_length=10000)
    scheduled_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ContinuousApiResourceUpdate(BaseModel):
    type: Literal["outgoing_continuous"]
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None
    repeat_enabled: bool | None = None
    repeat_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    destination_url: str | None = Field(default=None, min_length=1, max_length=2000)
    http_method: str | None = Field(default=None, pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default=None, pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str | None = Field(default=None, max_length=10000)


OutgoingApiUpdate = Annotated[
    ScheduledApiResourceUpdate | ContinuousApiResourceUpdate,
    Field(discriminator="type"),
]


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


class SmtpToolConfigResponse(BaseModel):
    enabled: bool
    target_worker_id: str | None = None
    bind_host: str
    port: int
    recipient_email: str | None = None


class SmtpRuntimeMessageResponse(BaseModel):
    id: str
    received_at: str
    mail_from: str
    recipients: list[str]
    peer: str
    size_bytes: int
    subject: str | None = None
    body_preview: str | None = None


class SmtpToolRuntimeResponse(BaseModel):
    status: Literal["stopped", "running", "assigned", "error"]
    message: str
    listening_host: str | None = None
    listening_port: int | None = None
    selected_machine_id: str | None = None
    selected_machine_name: str | None = None
    last_started_at: str | None = None
    last_stopped_at: str | None = None
    last_error: str | None = None
    session_count: int
    message_count: int
    last_message_at: str | None = None
    last_mail_from: str | None = None
    last_recipient: str | None = None
    recent_messages: list[SmtpRuntimeMessageResponse] = Field(default_factory=list)


class SmtpToolResponse(BaseModel):
    tool_id: Literal["smtp"]
    config: SmtpToolConfigResponse
    runtime: SmtpToolRuntimeResponse
    machines: list[RuntimeMachineResponse]


class SmtpToolUpdate(BaseModel):
    enabled: bool | None = None
    target_worker_id: str | None = Field(default=None, max_length=120)
    bind_host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=0, le=65535)
    recipient_email: str | None = Field(default=None, max_length=320)




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
    worker_id: str | None
    worker_name: str | None
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    error_summary: str | None


class AutomationRunDetailResponse(AutomationRunResponse):
    steps: list[AutomationRunStepResponse]


class AutomationTriggerConfig(BaseModel):
    schedule_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    inbound_api_id: str | None = Field(default=None, max_length=120)


class AutomationStepConfig(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    destination_url: str | None = Field(default=None, max_length=2000)
    http_method: str | None = Field(default="POST", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str | None = Field(default=None, max_length=10000)
    script_id: str | None = Field(default=None, max_length=120)
    tool_id: str | None = Field(default=None, max_length=120)
    expression: str | None = Field(default=None, max_length=500)
    stop_on_false: bool = False


class AutomationStepDefinition(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    type: Literal["log", "outbound_request", "script", "tool", "condition"]
    name: str = Field(min_length=1, max_length=120)
    config: AutomationStepConfig = Field(default_factory=AutomationStepConfig)


class AutomationSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    trigger_type: Literal["manual", "schedule", "inbound_api"]
    trigger_config: AutomationTriggerConfig
    step_count: int
    created_at: str
    updated_at: str
    last_run_at: str | None = None
    next_run_at: str | None = None


class AutomationDetailResponse(AutomationSummaryResponse):
    steps: list[AutomationStepDefinition]


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    enabled: bool = True
    trigger_type: Literal["manual", "schedule", "inbound_api"]
    trigger_config: AutomationTriggerConfig = Field(default_factory=AutomationTriggerConfig)
    steps: list[AutomationStepDefinition] = Field(default_factory=list, max_length=50)


class AutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None
    trigger_type: Literal["manual", "schedule", "inbound_api"] | None = None
    trigger_config: AutomationTriggerConfig | None = None
    steps: list[AutomationStepDefinition] | None = Field(default=None, max_length=50)


class AutomationValidationResponse(BaseModel):
    valid: bool
    issues: list[str]


class RuntimeStatusResponse(BaseModel):
    active: bool
    last_tick_started_at: str | None = None
    last_tick_finished_at: str | None = None
    last_error: str | None = None
    job_count: int


class ToolMetadataResponse(BaseModel):
    id: str
    name: str
    description: str


class ToolMetadataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class ScriptValidationIssue(BaseModel):
    message: str
    line: int | None = None
    column: int | None = None


class ScriptValidationResult(BaseModel):
    valid: bool
    issues: list[ScriptValidationIssue]


class ScriptSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    language: Literal["python", "javascript"]
    validation_status: Literal["valid", "invalid", "unknown"]
    validation_message: str | None = None
    last_validated_at: str | None = None
    created_at: str
    updated_at: str


class ScriptResponse(ScriptSummaryResponse):
    code: str


class ScriptValidationRequest(BaseModel):
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=200000)


class ScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=200000)


class ScriptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    language: Literal["python", "javascript"] | None = None
    code: str | None = Field(default=None, min_length=1, max_length=200000)


class GeneralSettings(BaseModel):
    environment: str = Field(pattern=r"^(staging|production|lab)$")
    timezone: str = Field(pattern=r"^(utc|local|ops)$")
    preview_mode: bool


class LoggingSettings(BaseModel):
    max_stored_entries: int = Field(ge=50, le=5000)
    max_visible_entries: int = Field(ge=10, le=500)
    max_detail_characters: int = Field(ge=500, le=20000)
    max_file_size_mb: int = Field(ge=1, le=100)


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
    if not getattr(app.state, "skip_ui_build_check", False):
        ensure_built_ui(Path(app.state.root_dir))
    app.state.connection = connection
    app.state.smtp_manager = SmtpRuntimeManager()
    configured_settings = get_settings_payload(connection)
    app.state.logger = configure_application_logger(
        app,
        root_dir=Path(app.state.root_dir),
        max_file_size_mb=configured_settings["logging"]["max_file_size_mb"],
    )
    app.state.smtp_manager = SmtpRuntimeManager(app.state.logger)
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


app = FastAPI(title="Malcom API", version="0.1.0", lifespan=lifespan)
app.state.db_path = str(DEFAULT_DB_PATH)
app.state.root_dir = get_project_root()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    started_at = datetime.now(UTC)

    try:
        response = await call_next(request)
    except Exception as error:
        logger = get_application_logger(request)
        duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
        write_application_log(
            logger,
            logging.ERROR,
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            error=str(error),
        )
        raise

    logger = get_application_logger(request)
    duration_ms = max(int((datetime.now(UTC) - started_at).total_seconds() * 1000), 0)
    level = logging.ERROR if response.status_code >= 500 else logging.INFO
    write_application_log(
        logger,
        level,
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else None,
    )
    return response

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
    "/apis/automation.html": "apis/automation.html",
    "/tools/overview.html": "tools/overview.html",
    "/tools/smtp.html": "tools/smtp.html",
    "/tools/sftp.html": "tools/sftp.html",
    "/tools/storage.html": "tools/storage.html",
    "/scripts.html": "scripts.html",
    "/scripts/library.html": "scripts/library.html",
    "/dashboard/overview.html": "dashboard/overview.html",
    "/dashboard/devices.html": "dashboard/devices.html",
    "/dashboard/logs.html": "dashboard/logs.html",
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


@app.get("/scripts")
@app.get("/scripts/")
def redirect_scripts_root() -> RedirectResponse:
    return RedirectResponse(url="/scripts.html")


for route_path, relative_path in UI_HTML_ROUTES.items():
    app.add_api_route(
        route_path,
        build_ui_route(relative_path),
        methods=["GET"],
        include_in_schema=False,
    )


app.mount("/assets", StaticFiles(directory=str(get_ui_dist_dir(get_project_root()) / "assets"), check_dir=False), name="ui-assets")
app.mount("/scripts", StaticFiles(directory=str(get_ui_dir(get_project_root()) / "scripts"), check_dir=False), name="ui-scripts")
app.mount("/styles", StaticFiles(directory=str(get_ui_dir(get_project_root()) / "styles"), check_dir=False), name="ui-styles")
app.mount("/modals", StaticFiles(directory=str(get_ui_dir(get_project_root()) / "modals"), check_dir=False), name="ui-modals")


def get_connection(request: Request) -> sqlite3.Connection:
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
        capabilities=("runtime-trigger-execution", "smtp-server"),
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
                capabilities=tuple(dict.fromkeys((*capabilities, "smtp-server"))),
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


def sync_smtp_tool_runtime(app: FastAPI, connection: sqlite3.Connection) -> None:
    smtp_manager: SmtpRuntimeManager = app.state.smtp_manager
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    smtp_manager.sync(
        enabled=config["enabled"],
        bind_host=config["bind_host"],
        port=config["port"],
        recipient_email=config.get("recipient_email"),
        machine=get_selected_smtp_machine(config, machines),
    )


def build_smtp_tool_response(app: FastAPI, connection: sqlite3.Connection) -> SmtpToolResponse:
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    runtime = app.state.smtp_manager.snapshot()
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
        machines=[machine_assignment_to_response(machine) for machine in machines],
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


def get_outgoing_api_or_404(
    connection: sqlite3.Connection,
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
    *,
    include_mock: bool = True,
) -> sqlite3.Row:
    table_name = "outgoing_scheduled_apis" if api_type == "outgoing_scheduled" else "outgoing_continuous_apis"
    row = fetch_one(
        connection,
        f"SELECT * FROM {table_name} WHERE id = ? AND (? = 1 OR is_mock = 0)",
        (api_id, int(include_mock)),
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


def validate_outgoing_resource_payload(payload: ApiResourceCreate) -> None:
    if payload.type not in {"outgoing_scheduled", "outgoing_continuous"}:
        return

    if not payload.destination_url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL is required.")

    parsed_url = urllib.parse.urlparse(payload.destination_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    if not payload.http_method:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="HTTP method is required.")

    if payload.payload_template is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Payload template is required.")

    try:
        json.loads(payload.payload_template)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    auth_type = payload.auth_type or "none"
    auth_config = payload.auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and not auth_config.token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Bearer authentication requires a token.")
    if auth_type == "basic" and (not auth_config.username or not auth_config.password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Basic authentication requires a username and password.")
    if auth_type == "header" and (not auth_config.header_name or not auth_config.header_value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Header authentication requires a header name and value.")

    if payload.type == "outgoing_scheduled" and not payload.scheduled_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs require a send time.")

    if payload.type == "outgoing_scheduled" and payload.repeat_interval_minutes is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs do not use repeat intervals.")

    if payload.type == "outgoing_continuous":
        if payload.repeat_enabled and payload.repeat_interval_minutes is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Continuous outgoing APIs require an interval when repeating is enabled.")
        if not payload.repeat_enabled and payload.repeat_interval_minutes is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Set repeating on continuous outgoing APIs before providing an interval.")


def validate_outgoing_update_payload(payload: ScheduledApiResourceUpdate | ContinuousApiResourceUpdate) -> None:
    if payload.destination_url is not None:
        if not payload.destination_url:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL is required.")

        parsed_url = urllib.parse.urlparse(payload.destination_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    if payload.payload_template is not None:
        try:
            json.loads(payload.payload_template)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    auth_type = payload.auth_type or "none"
    auth_config = payload.auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and not auth_config.token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Bearer authentication requires a token.")
    if auth_type == "basic" and (not auth_config.username or not auth_config.password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Basic authentication requires a username and password.")
    if auth_type == "header" and (not auth_config.header_name or not auth_config.header_value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Header authentication requires a header name and value.")

    if payload.type == "outgoing_scheduled" and payload.scheduled_time is not None and not payload.scheduled_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs require a send time.")

    if payload.type == "outgoing_continuous" and payload.repeat_enabled is False and payload.repeat_interval_minutes is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Set repeating on continuous outgoing APIs before providing an interval.")


def validate_webhook_resource_payload(payload: ApiResourceCreate) -> None:
    if payload.type != "webhook":
        return

    if not payload.callback_path or not payload.callback_path.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook callback path is required.")

    callback_path = payload.callback_path.strip()
    if not callback_path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook callback path must start with '/'.")

    if not payload.verification_token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook verification token is required.")

    if not payload.signing_secret:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook signing secret is required.")

    if not payload.signature_header or not payload.signature_header.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook signature header is required.")


def build_outgoing_request_headers(
    auth_type: str,
    auth_config: OutgoingAuthConfig | None,
) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    config = auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and config.token:
        headers["Authorization"] = f"Bearer {config.token}"
    elif auth_type == "basic" and config.username and config.password:
        encoded = base64.b64encode(f"{config.username}:{config.password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"
    elif auth_type == "header" and config.header_name and config.header_value:
        headers[config.header_name] = config.header_value

    return headers


def redact_outgoing_request_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted_headers: dict[str, str] = {}

    for key, value in headers.items():
        if key.lower() == "authorization":
            if value.startswith("Bearer "):
                redacted_headers[key] = "Bearer [redacted]"
            elif value.startswith("Basic "):
                redacted_headers[key] = "Basic [redacted]"
            else:
                redacted_headers[key] = "[redacted]"
            continue

        redacted_headers[key] = "[redacted]" if key.lower() != "content-type" else value

    return redacted_headers


def execute_outgoing_test_delivery(payload: OutgoingApiTestRequest) -> OutgoingApiTestResponse:
    try:
        parsed_payload = json.loads(payload.payload_template)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    parsed_url = urllib.parse.urlparse(payload.destination_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    headers = build_outgoing_request_headers(payload.auth_type, payload.auth_config)
    request = urllib.request.Request(
        payload.destination_url,
        data=json.dumps(parsed_payload).encode("utf-8"),
        headers=headers,
        method=payload.http_method,
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return OutgoingApiTestResponse(
                ok=200 <= response.status < 300,
                status_code=response.status,
                response_body=response_body[:2000],
                sent_headers=redact_outgoing_request_headers(headers),
                destination_url=payload.destination_url,
            )
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        return OutgoingApiTestResponse(
            ok=False,
            status_code=error.code,
            response_body=response_body[:2000],
            sent_headers=redact_outgoing_request_headers(headers),
            destination_url=payload.destination_url,
        )
    except urllib.error.URLError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to reach destination URL: {error.reason}.") from error


def log_event(
    connection: sqlite3.Connection,
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
        is_mock=is_mock,
    )




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
    worker_id: str | None = None,
    worker_name: str | None = None,
    started_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO automation_runs (
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
        """,
        (run_id, automation_id, trigger_type, status_value, worker_id, worker_name, started_at),
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


def assign_automation_run_worker(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    worker_id: str,
    worker_name: str,
) -> None:
    connection.execute(
        """
        UPDATE automation_runs
        SET worker_id = ?, worker_name = ?
        WHERE run_id = ?
        """,
        (worker_id, worker_name, run_id),
    )
    connection.commit()


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
    connection: sqlite3.Connection,
    logger: logging.Logger,
    *,
    job: RuntimeTriggerJob,
    worker_id: str,
    worker_name: str,
) -> None:
    finished_at = utc_now_iso()
    runtime_event_bus.record_history(job.trigger)
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

        process_runtime_job(
            connection,
            logger,
            job=job,
            worker_id=worker_id,
            worker_name=worker_name,
        )


def run_remote_worker_loop(app: FastAPI, stop_event: threading.Event, coordinator_url: str) -> None:
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
                            "detail": {
                                "worker_id": worker_id,
                                "worker_name": worker_name,
                                "execution_mode": "remote",
                            },
                        },
                    ).raise_for_status()
        except Exception:
            pass

        stop_event.wait(REMOTE_WORKER_POLL_INTERVAL_SECONDS)


def get_automation_or_404(connection: sqlite3.Connection, automation_id: str) -> sqlite3.Row:
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


def list_automation_steps(connection: sqlite3.Connection, automation_id: str) -> list[AutomationStepDefinition]:
    rows = fetch_all(
        connection,
        """
        SELECT step_id, automation_id, position, step_type, name, config_json, created_at, updated_at
        FROM automation_steps
        WHERE automation_id = ?
        ORDER BY position ASC
        """,
        (automation_id,),
    )
    return [row_to_automation_step(row) for row in rows]


def serialize_automation_detail(connection: sqlite3.Connection, automation_id: str) -> AutomationDetailResponse:
    row = get_automation_or_404(connection, automation_id)
    return AutomationDetailResponse(
        **row_to_automation_summary(row),
        steps=list_automation_steps(connection, automation_id),
    )


def replace_automation_steps(
    connection: sqlite3.Connection,
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
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step_id,
                automation_id,
                index,
                step.type,
                step.name,
                json.dumps(step.config.model_dump()),
                timestamp,
                timestamp,
            ),
        )


def refresh_automation_schedule(connection: sqlite3.Connection, automation_id: str) -> None:
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


def refresh_outgoing_schedule(connection: sqlite3.Connection, api_id: str) -> None:
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


def parse_template_json(template: str | None, context: dict[str, Any]) -> str:
    rendered = render_template_string(template or "{}", context)
    parsed = json.loads(rendered)
    return json.dumps(parsed)


def execute_script_step(script_row: sqlite3.Row, context: dict[str, Any], *, root_dir: Path) -> RuntimeExecutionResult:
    if script_row["language"] == "python":
        local_scope = {
            "context": context,
            "payload": context.get("payload"),
            "steps": context.get("steps", {}),
            "result": None,
        }
        exec(script_row["code"], {"__builtins__": {}}, local_scope)
        return RuntimeExecutionResult(
            status="completed",
            response_summary="Python script executed.",
            detail={"script_id": script_row["id"]},
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
            "const context = JSON.parse(process.argv[2]);\n"
            "const payload = context.payload;\n"
            "const steps = context.steps || {};\n"
            "let result = null;\n"
            f"{script_row['code']}\n"
            "process.stdout.write(JSON.stringify(result ?? null));\n"
        )
        temporary_path = Path(temporary_file.name)

    try:
        completed = subprocess.run(
            ["node", temporary_path.name, json.dumps(context)],
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
        detail={"script_id": script_row["id"]},
        output=json.loads(completed.stdout or "null"),
    )


def execute_automation_step(
    connection: sqlite3.Connection,
    logger: logging.Logger,
    *,
    automation_id: str,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    root_dir: Path,
) -> RuntimeExecutionResult:
    if step.type == "log":
        message = render_template_string(step.config.message, context)
        write_application_log(logger, logging.INFO, "automation_log_step", automation_id=automation_id, step_name=step.name, message=message)
        return RuntimeExecutionResult(status="completed", response_summary=message, detail={"message": message}, output=message)

    if step.type == "outbound_request":
        delivery = execute_outgoing_test_delivery(
            OutgoingApiTestRequest(
                type="outgoing_scheduled",
                destination_url=render_template_string(step.config.destination_url, context),
                http_method=step.config.http_method or "POST",
                auth_type=step.config.auth_type or "none",
                auth_config=step.config.auth_config,
                payload_template=parse_template_json(step.config.payload_template, context),
            )
        )
        return RuntimeExecutionResult(
            status="completed" if delivery.ok else "failed",
            response_summary=f"{delivery.status_code} {delivery.destination_url}",
            detail=delivery.model_dump(),
            output=delivery.model_dump(),
        )

    if step.type == "script":
        script_row = fetch_one(connection, "SELECT * FROM scripts WHERE id = ?", (step.config.script_id,))
        if script_row is None:
            raise RuntimeError(f"Script '{step.config.script_id}' was not found.")
        return execute_script_step(script_row, context, root_dir=root_dir)

    if step.type == "tool":
        tool_row = fetch_one(
            connection,
            """
            SELECT id, COALESCE(name_override, source_name) AS name, COALESCE(description_override, source_description) AS description
            FROM tools
            WHERE id = ?
            """,
            (step.config.tool_id,),
        )
        if tool_row is None:
            raise RuntimeError(f"Tool '{step.config.tool_id}' was not found.")
        detail = {"tool_id": tool_row["id"], "name": tool_row["name"], "description": tool_row["description"]}
        return RuntimeExecutionResult(status="completed", response_summary=f"Loaded tool {tool_row['name']}.", detail=detail, output=detail)

    compiled = ast.parse(step.config.expression or "", mode="eval")
    result = bool(eval(compile(compiled, "<automation-condition>", "eval"), {"__builtins__": {}}, {"context": context, "payload": context.get("payload"), "steps": context.get("steps", {})}))
    return RuntimeExecutionResult(
        status="completed",
        response_summary="Condition matched." if result else "Condition evaluated to false.",
        detail={"expression": step.config.expression, "result": result, "stop_on_false": step.config.stop_on_false},
        output=result,
    )


def fetch_run_detail(connection: sqlite3.Connection, run_id: str) -> AutomationRunDetailResponse:
    run_row = fetch_one(connection, "SELECT run_id, automation_id, trigger_type, status, started_at, finished_at, duration_ms, error_summary FROM automation_runs WHERE run_id = ?", (run_id,))
    if run_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation run not found.")
    step_rows = fetch_all(
        connection,
        """
        SELECT step_id, run_id, step_name, status, request_summary, response_summary, started_at, finished_at, duration_ms, detail_json
        FROM automation_run_steps
        WHERE run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )
    return AutomationRunDetailResponse(**row_to_run(run_row), steps=[AutomationRunStepResponse(**row_to_run_step(row)) for row in step_rows])


def execute_automation_definition(
    connection: sqlite3.Connection,
    logger: logging.Logger,
    *,
    automation_id: str,
    trigger_type: str,
    payload: dict[str, Any] | None,
    root_dir: Path,
) -> AutomationRunDetailResponse:
    automation = serialize_automation_detail(connection, automation_id)
    run_id = f"run_{uuid4().hex}"
    started_at = utc_now_iso()
    create_automation_run(
        connection,
        run_id=run_id,
        automation_id=automation_id,
        trigger_type=trigger_type,
        status_value="running",
        started_at=started_at,
    )
    context: dict[str, Any] = {
        "automation": automation.model_dump(exclude={"steps"}),
        "payload": payload or {},
        "steps": {},
        "timestamp": started_at,
    }
    run_status = "completed"
    error_summary: str | None = None

    for index, step in enumerate(automation.steps):
        runtime_step_id = f"step_{uuid4().hex}"
        create_automation_run_step(
            connection,
            step_id=runtime_step_id,
            run_id=run_id,
            step_name=step.name,
            status_value="running",
            request_summary=f"{step.type} step #{index + 1}",
            started_at=utc_now_iso(),
        )
        try:
            result = execute_automation_step(
                connection,
                logger,
                automation_id=automation_id,
                step=step,
                context=context,
                root_dir=root_dir,
            )
            context["steps"][step.id or step.name] = result.output
            finalize_automation_run_step(
                connection,
                step_id=runtime_step_id,
                status_value=result.status,
                response_summary=result.response_summary,
                detail=result.detail,
                finished_at=utc_now_iso(),
            )
            if step.type == "condition" and result.output is False and step.config.stop_on_false:
                break
            if result.status != "completed":
                run_status = "failed"
                error_summary = result.response_summary or f"Step '{step.name}' failed."
                break
        except Exception as error:
            run_status = "failed"
            error_summary = str(error)
            finalize_automation_run_step(
                connection,
                step_id=runtime_step_id,
                status_value="failed",
                response_summary=str(error),
                detail={"error": str(error)},
                finished_at=utc_now_iso(),
            )
            break

    finished_at = utc_now_iso()
    finalize_automation_run(connection, run_id=run_id, status_value=run_status, error_summary=error_summary, finished_at=finished_at)
    connection.execute(
        "UPDATE automations SET last_run_at = ?, updated_at = ? WHERE id = ?",
        (finished_at, finished_at, automation_id),
    )
    if automation.trigger_type == "schedule" and automation.trigger_config.schedule_time:
        connection.execute(
            "UPDATE automations SET next_run_at = ? WHERE id = ?",
            (next_daily_run_at(automation.trigger_config.schedule_time), automation_id),
        )
    connection.commit()
    return fetch_run_detail(connection, run_id)


def execute_scheduled_api(connection: sqlite3.Connection, logger: logging.Logger, *, api_id: str) -> None:
    row = fetch_one(connection, "SELECT * FROM outgoing_scheduled_apis WHERE id = ?", (api_id,))
    if row is None:
        return

    run_id = f"run_{uuid4().hex}"
    started_at = utc_now_iso()
    create_automation_run(connection, run_id=run_id, automation_id=api_id, trigger_type="schedule", status_value="running", started_at=started_at)
    runtime_step_id = f"step_{uuid4().hex}"
    create_automation_run_step(
        connection,
        step_id=runtime_step_id,
        run_id=run_id,
        step_name="outgoing_scheduled_delivery",
        status_value="running",
        request_summary=row["destination_url"],
        started_at=started_at,
    )
    result = execute_outgoing_test_delivery(
        OutgoingApiTestRequest(
            type="outgoing_scheduled",
            destination_url=row["destination_url"],
            http_method=row["http_method"],
            auth_type=row["auth_type"],
            auth_config=OutgoingAuthConfig(**json.loads(row["auth_config_json"])),
            payload_template=row["payload_template"],
        )
    )
    finished_at = utc_now_iso()
    finalize_automation_run_step(
        connection,
        step_id=runtime_step_id,
        status_value="completed" if result.ok else "failed",
        response_summary=f"{result.status_code} {result.destination_url}",
        detail=result.model_dump(),
        finished_at=finished_at,
    )
    finalize_automation_run(
        connection,
        run_id=run_id,
        status_value="completed" if result.ok else "failed",
        error_summary=None if result.ok else result.response_body,
        finished_at=finished_at,
    )
    connection.execute(
        "UPDATE outgoing_scheduled_apis SET last_run_at = ?, next_run_at = ?, updated_at = ? WHERE id = ?",
        (finished_at, next_daily_run_at(row["scheduled_time"]), finished_at, api_id),
    )
    connection.commit()
    write_application_log(logger, logging.INFO if result.ok else logging.WARNING, "scheduled_outgoing_api_executed", api_id=api_id, status_code=result.status_code)


def refresh_scheduler_jobs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for row in fetch_all(connection, "SELECT id, name, trigger_config_json, next_run_at FROM automations WHERE enabled = 1 AND trigger_type = 'schedule' ORDER BY created_at ASC"):
        trigger_config = json.loads(row["trigger_config_json"])
        jobs.append(
            {
                "id": row["id"],
                "kind": "automation",
                "name": row["name"],
                "schedule_time": trigger_config.get("schedule_time"),
                "next_run_at": row["next_run_at"] or next_daily_run_at(trigger_config["schedule_time"]),
            }
        )

    for row in fetch_all(connection, "SELECT id, name, scheduled_time, next_run_at FROM outgoing_scheduled_apis WHERE enabled = 1 ORDER BY created_at ASC"):
        jobs.append(
            {
                "id": row["id"],
                "kind": "outgoing_scheduled",
                "name": row["name"],
                "schedule_time": row["scheduled_time"],
                "next_run_at": row["next_run_at"] or next_daily_run_at(row["scheduled_time"]),
            }
        )
    runtime_scheduler.update_jobs(jobs)
    return jobs


def run_scheduler_tick(app: FastAPI) -> None:
    connection = app.state.connection
    logger = app.state.logger
    now = datetime.now(UTC)
    refresh_scheduler_jobs(connection)

    for row in fetch_all(connection, "SELECT id, next_run_at FROM automations WHERE enabled = 1 AND trigger_type = 'schedule' AND next_run_at IS NOT NULL"):
        scheduled_at = parse_iso_datetime(row["next_run_at"])
        if scheduled_at is not None and scheduled_at <= now:
            execute_automation_definition(
                connection,
                logger,
                automation_id=row["id"],
                trigger_type="schedule",
                payload=None,
                root_dir=Path(app.state.root_dir),
            )

    for row in fetch_all(connection, "SELECT id, next_run_at FROM outgoing_scheduled_apis WHERE enabled = 1 AND next_run_at IS NOT NULL"):
        scheduled_at = parse_iso_datetime(row["next_run_at"])
        if scheduled_at is not None and scheduled_at <= now:
            execute_scheduled_api(connection, logger, api_id=row["id"])
@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/runtime/status", response_model=RuntimeStatusResponse)
def get_runtime_status() -> RuntimeStatusResponse:
    return RuntimeStatusResponse(**runtime_scheduler.status())


@app.get("/api/v1/scheduler/jobs")
def get_scheduler_jobs(request: Request) -> list[dict[str, Any]]:
    refresh_scheduler_jobs(get_connection(request))
    return runtime_scheduler.jobs()


@app.get("/api/v1/automations", response_model=list[AutomationSummaryResponse])
def list_automations(request: Request) -> list[AutomationSummaryResponse]:
    rows = fetch_all(
        get_connection(request),
        """
        SELECT
            automations.*,
            COUNT(automation_steps.step_id) AS step_count
        FROM automations
        LEFT JOIN automation_steps ON automation_steps.automation_id = automations.id
        GROUP BY automations.id
        ORDER BY automations.created_at DESC
        """,
    )
    return [AutomationSummaryResponse(**row_to_automation_summary(row)) for row in rows]


@app.post("/api/v1/automations", response_model=AutomationDetailResponse, status_code=status.HTTP_201_CREATED)
def create_automation(payload: AutomationCreate, request: Request) -> AutomationDetailResponse:
    issues = validate_automation_definition(payload, require_steps=True)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))

    connection = get_connection(request)
    now = utc_now_iso()
    automation_id = f"automation_{uuid4().hex[:10]}"
    trigger_config = payload.trigger_config.model_dump()
    next_run_at = None
    if payload.enabled and payload.trigger_type == "schedule" and payload.trigger_config.schedule_time:
        next_run_at = next_daily_run_at(payload.trigger_config.schedule_time)

    connection.execute(
        """
        INSERT INTO automations (
            id,
            name,
            description,
            enabled,
            trigger_type,
            trigger_config_json,
            created_at,
            updated_at,
            last_run_at,
            next_run_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (
            automation_id,
            payload.name,
            payload.description,
            int(payload.enabled),
            payload.trigger_type,
            json.dumps(trigger_config),
            now,
            now,
            next_run_at,
        ),
    )
    replace_automation_steps(connection, automation_id, payload.steps, timestamp=now)
    connection.commit()
    refresh_scheduler_jobs(connection)
    return serialize_automation_detail(connection, automation_id)


@app.get("/api/v1/automations/{automation_id}", response_model=AutomationDetailResponse)
def get_automation(automation_id: str, request: Request) -> AutomationDetailResponse:
    return serialize_automation_detail(get_connection(request), automation_id)


@app.patch("/api/v1/automations/{automation_id}", response_model=AutomationDetailResponse)
def update_automation(automation_id: str, payload: AutomationUpdate, request: Request) -> AutomationDetailResponse:
    connection = get_connection(request)
    current = serialize_automation_detail(connection, automation_id)
    next_payload = AutomationCreate(
        name=payload.name if payload.name is not None else current.name,
        description=payload.description if payload.description is not None else current.description,
        enabled=payload.enabled if payload.enabled is not None else current.enabled,
        trigger_type=payload.trigger_type if payload.trigger_type is not None else current.trigger_type,
        trigger_config=payload.trigger_config if payload.trigger_config is not None else current.trigger_config,
        steps=payload.steps if payload.steps is not None else current.steps,
    )
    issues = validate_automation_definition(next_payload, require_steps=True)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=" ".join(issues))

    now = utc_now_iso()
    next_run_at = None
    if next_payload.enabled and next_payload.trigger_type == "schedule" and next_payload.trigger_config.schedule_time:
        next_run_at = next_daily_run_at(next_payload.trigger_config.schedule_time)
    connection.execute(
        """
        UPDATE automations
        SET name = ?, description = ?, enabled = ?, trigger_type = ?, trigger_config_json = ?, updated_at = ?, next_run_at = ?
        WHERE id = ?
        """,
        (
            next_payload.name,
            next_payload.description,
            int(next_payload.enabled),
            next_payload.trigger_type,
            json.dumps(next_payload.trigger_config.model_dump()),
            now,
            next_run_at,
            automation_id,
        ),
    )
    replace_automation_steps(connection, automation_id, next_payload.steps, timestamp=now)
    connection.commit()
    refresh_scheduler_jobs(connection)
    return serialize_automation_detail(connection, automation_id)


@app.delete("/api/v1/automations/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation(automation_id: str, request: Request) -> Response:
    connection = get_connection(request)
    get_automation_or_404(connection, automation_id)
    connection.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
    connection.commit()
    refresh_scheduler_jobs(connection)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/v1/automations/{automation_id}/validate", response_model=AutomationValidationResponse)
def validate_automation_endpoint(automation_id: str, request: Request) -> AutomationValidationResponse:
    automation = serialize_automation_detail(get_connection(request), automation_id)
    issues = validate_automation_definition(automation, require_steps=True)
    return AutomationValidationResponse(valid=not issues, issues=issues)


@app.post("/api/v1/automations/{automation_id}/execute", response_model=AutomationRunDetailResponse)
def execute_automation(automation_id: str, request: Request) -> AutomationRunDetailResponse:
    connection = get_connection(request)
    automation = serialize_automation_detail(connection, automation_id)
    if not automation.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Automation is disabled.")
    return execute_automation_definition(
        connection,
        get_application_logger(request),
        automation_id=automation_id,
        trigger_type="manual",
        payload=None,
        root_dir=get_root_dir(request),
    )


@app.get("/api/v1/automations/{automation_id}/runs", response_model=list[AutomationRunResponse])
def list_automation_runs_for_automation(automation_id: str, request: Request) -> list[AutomationRunResponse]:
    get_automation_or_404(get_connection(request), automation_id)
    rows = fetch_all(
        get_connection(request),
        """
        SELECT run_id, automation_id, trigger_type, status, started_at, finished_at, duration_ms, error_summary
        FROM automation_runs
        WHERE automation_id = ?
        ORDER BY started_at DESC
        """,
        (automation_id,),
    )
    return [AutomationRunResponse(**row_to_run(row)) for row in rows]


@app.get("/api/v1/settings", response_model=AppSettingsResponse)
def get_app_settings(request: Request) -> AppSettingsResponse:
    payload = get_settings_payload(get_connection(request))
    return AppSettingsResponse(**payload)


@app.post("/api/v1/scripts/validate", response_model=ScriptValidationResult)
def validate_script(request_payload: ScriptValidationRequest, request: Request) -> ScriptValidationResult:
    return validate_script_payload(
        request_payload.language,
        request_payload.code,
        root_dir=get_root_dir(request),
    )


@app.get("/api/v1/scripts", response_model=list[ScriptSummaryResponse])
def list_scripts(request: Request) -> list[ScriptSummaryResponse]:
    rows = fetch_all(
        get_connection(request),
        """
        SELECT id, name, description, language, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        ORDER BY updated_at DESC, name COLLATE NOCASE ASC
        """,
    )
    return [row_to_script_summary(row) for row in rows]


@app.get("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def get_script(script_id: str, request: Request) -> ScriptResponse:
    row = fetch_one(
        get_connection(request),
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    return row_to_script_response(row)


@app.post("/api/v1/scripts", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(payload: ScriptCreate, request: Request) -> ScriptResponse:
    validation_result = validate_script_payload(payload.language, payload.code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    now = utc_now_iso()
    script_id = f"script_{uuid4().hex[:12]}"
    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    connection = get_connection(request)
    connection.execute(
        """
        INSERT INTO scripts (
            id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            script_id,
            payload.name.strip(),
            payload.description.strip(),
            payload.language,
            payload.code,
            validation_status,
            validation_message,
            last_validated_at,
            now,
            now,
        ),
    )
    connection.commit()
    row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(row)


@app.patch("/api/v1/scripts/{script_id}", response_model=ScriptResponse)
def update_script(script_id: str, payload: ScriptUpdate, request: Request) -> ScriptResponse:
    connection = get_connection(request)
    existing_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    if existing_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row_to_script_response(existing_row)

    next_name = (changes.get("name") if "name" in changes else existing_row["name"]).strip()
    next_description = (changes.get("description") if "description" in changes else existing_row["description"]).strip()
    next_language = changes.get("language", existing_row["language"])
    next_code = changes.get("code", existing_row["code"])

    validation_result = validate_script_payload(next_language, next_code, root_dir=get_root_dir(request))
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_result.model_dump(),
        )

    validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
    updated_at = utc_now_iso()
    connection.execute(
        """
        UPDATE scripts
        SET name = ?, description = ?, language = ?, code = ?, validation_status = ?, validation_message = ?, last_validated_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            next_name,
            next_description,
            next_language,
            next_code,
            validation_status,
            validation_message,
            last_validated_at,
            updated_at,
            script_id,
        ),
    )
    connection.commit()
    saved_row = fetch_one(
        connection,
        """
        SELECT id, name, description, language, code, validation_status, validation_message, last_validated_at, created_at, updated_at
        FROM scripts
        WHERE id = ?
        """,
        (script_id,),
    )
    return row_to_script_response(saved_row)


@app.get("/api/v1/dashboard/devices", response_model=DashboardDevicesApiResponse)
def get_dashboard_devices() -> DashboardDevicesApiResponse:
    return get_runtime_devices_response()


@app.get("/api/v1/workers", response_model=list[WorkerResponse])
def list_workers() -> list[WorkerResponse]:
    return [worker_to_response(worker) for worker in runtime_event_bus.list_workers()]


@app.post("/api/v1/workers/register", response_model=WorkerResponse)
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


@app.post("/api/v1/workers/claim-trigger", response_model=WorkerClaimResponse)
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


@app.post("/api/v1/workers/complete-trigger", response_model=AutomationRunDetailResponse)
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
    return get_automation_run(completed_job.run_id, request)


@app.patch("/api/v1/settings", response_model=AppSettingsResponse)
def patch_app_settings(payload: AppSettingsUpdate, request: Request) -> AppSettingsResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
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
    settings_payload = get_settings_payload(connection)
    if "logging" in changes:
        request.app.state.logger = configure_application_logger(
            request.app,
            root_dir=get_root_dir(request),
            max_file_size_mb=settings_payload["logging"]["max_file_size_mb"],
        )
        logger = request.app.state.logger
    write_application_log(
        logger,
        logging.INFO,
        "settings_updated",
        changed_sections=sorted(changes.keys()),
        logging=settings_payload.get("logging"),
    )
    return AppSettingsResponse(**settings_payload)


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
    logger = get_application_logger(request)
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
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_created",
        api_id=api_id,
        path_slug=payload.path_slug,
        enabled=payload.enabled,
    )
    return InboundApiCreated(**created)


@app.get("/api/v1/outgoing/scheduled", response_model=list[ApiResourceResponse])
def list_outgoing_scheduled_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, repeat_enabled, destination_url, http_method, auth_type,
               payload_template, scheduled_time, schedule_expression, status, created_at, updated_at
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
        SELECT id, name, description, path_slug, enabled, repeat_enabled, repeat_interval_minutes, destination_url, http_method, auth_type,
               payload_template, stream_mode, created_at, updated_at
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


@app.get("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def get_outgoing_api_detail(
    api_id: str,
    api_type: Literal["outgoing_scheduled", "outgoing_continuous"],
    request: Request,
) -> OutgoingApiDetailResponse:
    connection = get_connection(request)
    row = get_outgoing_api_or_404(connection, api_id, api_type, include_mock=developer_mode_enabled(request))
    endpoint_path = "/api/v1/outgoing/scheduled" if api_type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    return row_to_outgoing_detail_response(row, api_type=api_type, endpoint_path=endpoint_path)


@app.get("/api/v1/webhooks", response_model=list[ApiResourceResponse])
def list_webhook_apis(request: Request) -> list[ApiResourceResponse]:
    connection = get_connection(request)
    include_mock = developer_mode_enabled(request)
    rows = fetch_all(
        connection,
        """
        SELECT id, name, description, path_slug, enabled, callback_path, signature_header, event_filter, verification_token, signing_secret, created_at, updated_at
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
    validate_outgoing_resource_payload(payload)
    validate_webhook_resource_payload(payload)

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
                    status,
                    repeat_enabled,
                    destination_url,
                    http_method,
                    auth_type,
                    auth_config_json,
                    payload_template,
                    scheduled_time,
                    schedule_expression,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    "active" if payload.enabled else "paused",
                    int(payload.repeat_enabled),
                    payload.destination_url,
                    payload.http_method,
                    payload.auth_type or "none",
                    json.dumps((payload.auth_config or OutgoingAuthConfig()).model_dump()),
                    payload.payload_template,
                    payload.scheduled_time,
                    build_schedule_expression(payload.scheduled_time or "09:00"),
                    now,
                    now,
                ),
            )
            refresh_outgoing_schedule(connection, api_id)
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
                    repeat_enabled,
                    repeat_interval_minutes,
                    destination_url,
                    http_method,
                    auth_type,
                    auth_config_json,
                    payload_template,
                    stream_mode,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    int(payload.repeat_enabled),
                    payload.repeat_interval_minutes,
                    payload.destination_url,
                    payload.http_method,
                    payload.auth_type or "none",
                    json.dumps((payload.auth_config or OutgoingAuthConfig()).model_dump()),
                    payload.payload_template,
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
                    callback_path,
                    verification_token,
                    signing_secret,
                    signature_header,
                    event_filter,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    api_id,
                    payload.name,
                    payload.description,
                    payload.path_slug,
                    0,
                    int(payload.enabled),
                    "webhook",
                    payload.callback_path.strip() if payload.callback_path else "",
                    payload.verification_token,
                    payload.signing_secret,
                    payload.signature_header.strip() if payload.signature_header else "",
                    payload.event_filter.strip() if payload.event_filter else "",
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
        SELECT *
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


@app.post("/api/v1/apis/test-delivery", response_model=OutgoingApiTestResponse)
def test_outgoing_api_delivery(payload: OutgoingApiTestRequest) -> OutgoingApiTestResponse:
    return execute_outgoing_test_delivery(payload)


@app.get("/api/v1/inbound/{api_id}", response_model=InboundApiDetail)
def get_inbound_api(api_id: str, request: Request) -> InboundApiDetail:
    connection = get_connection(request)
    return serialize_api_detail(connection, api_id, request)


@app.patch("/api/v1/inbound/{api_id}", response_model=InboundApiResponse)
def update_inbound_api(api_id: str, payload: InboundApiUpdate, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
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
    write_application_log(
        logger,
        logging.INFO,
        "inbound_api_updated",
        api_id=api_id,
        changed_fields=sorted(changes.keys()),
    )
    return InboundApiResponse(**updated)


@app.patch("/api/v1/outgoing/{api_id}", response_model=OutgoingApiDetailResponse)
def update_outgoing_api(api_id: str, payload: OutgoingApiUpdate, request: Request) -> OutgoingApiDetailResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    current = get_outgoing_api_or_404(connection, api_id, payload.type, include_mock=True)
    validate_outgoing_update_payload(payload)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        endpoint_path = "/api/v1/outgoing/scheduled" if payload.type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
        return row_to_outgoing_detail_response(current, api_type=payload.type, endpoint_path=endpoint_path)

    assignments = []
    values: list[Any] = []

    for key, value in changes.items():
        if key == "type":
            continue

        if key == "auth_config":
            assignments.append("auth_config_json = ?")
            values.append(json.dumps((value or OutgoingAuthConfig()).model_dump()))
            continue

        if key == "repeat_enabled":
            assignments.append("repeat_enabled = ?")
            values.append(int(value))
            continue

        if key == "enabled":
            assignments.append("enabled = ?")
            values.append(int(value))
            if payload.type == "outgoing_scheduled":
                assignments.append("status = ?")
                values.append("active" if value else "paused")
            continue

        if key == "scheduled_time" and payload.type == "outgoing_scheduled" and value is not None:
            assignments.append("scheduled_time = ?")
            values.append(value)
            assignments.append("schedule_expression = ?")
            values.append(build_schedule_expression(value))
            continue

        assignments.append(f"{key} = ?")
        values.append(value)

    if payload.type == "outgoing_continuous" and changes.get("repeat_enabled") is False and "repeat_interval_minutes" not in changes:
        assignments.append("repeat_interval_minutes = ?")
        values.append(None)

    assignments.append("updated_at = ?")
    values.append(utc_now_iso())
    values.append(api_id)
    table_name = "outgoing_scheduled_apis" if payload.type == "outgoing_scheduled" else "outgoing_continuous_apis"

    try:
        connection.execute(
            f"UPDATE {table_name} SET {', '.join(assignments)} WHERE id = ?",
            tuple(values),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Path slug already exists.") from error

    updated = get_outgoing_api_or_404(connection, api_id, payload.type, include_mock=True)
    endpoint_path = "/api/v1/outgoing/scheduled" if payload.type == "outgoing_scheduled" else "/api/v1/outgoing/continuous"
    write_application_log(
        logger,
        logging.INFO,
        "outgoing_api_updated",
        api_id=api_id,
        api_type=payload.type,
        changed_fields=sorted(key for key in changes.keys() if key != "type"),
    )
    return row_to_outgoing_detail_response(updated, api_type=payload.type, endpoint_path=endpoint_path)


@app.post("/api/v1/inbound/{api_id}/rotate-secret", response_model=InboundSecretResponse)
def rotate_inbound_api_secret(api_id: str, request: Request) -> InboundSecretResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    api_row = get_api_or_404(connection, api_id, include_mock=True)
    secret = generate_secret()
    connection.execute(
        "UPDATE inbound_apis SET secret_hash = ?, updated_at = ? WHERE id = ?",
        (hash_secret(secret), utc_now_iso(), api_row["id"]),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_secret_rotated",
        api_id=api_id,
    )
    return InboundSecretResponse(
        id=api_id,
        secret=secret,
        endpoint_url=str(request.base_url).rstrip("/") + f"/api/v1/inbound/{api_id}",
    )


@app.post("/api/v1/inbound/{api_id}/disable", response_model=InboundApiResponse)
def disable_inbound_api(api_id: str, request: Request) -> InboundApiResponse:
    connection = get_connection(request)
    logger = get_application_logger(request)
    get_api_or_404(connection, api_id, include_mock=True)
    connection.execute(
        "UPDATE inbound_apis SET enabled = 0, updated_at = ? WHERE id = ?",
        (utc_now_iso(), api_id),
    )
    connection.commit()
    write_application_log(
        logger,
        logging.WARNING,
        "inbound_api_disabled",
        api_id=api_id,
    )
    return InboundApiResponse(**row_to_api_summary(get_api_or_404(connection, api_id)))


@app.get("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def get_smtp_tool(request: Request) -> SmtpToolResponse:
    return build_smtp_tool_response(request.app, get_connection(request))


@app.patch("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def patch_smtp_tool(payload: SmtpToolUpdate, request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No SMTP tool changes provided.")

    next_config = get_smtp_tool_config(connection)
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "target_worker_id" in changes:
        next_config["target_worker_id"] = changes["target_worker_id"] or None
    if "bind_host" in changes:
        next_config["bind_host"] = str(changes["bind_host"]).strip()
    if "port" in changes:
        next_config["port"] = int(changes["port"])
    if "recipient_email" in changes:
        next_config["recipient_email"] = (str(changes["recipient_email"]).strip().lower() or None) if changes["recipient_email"] is not None else None

    save_smtp_tool_config(connection, next_config)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@app.post("/api/v1/tools/smtp/start", response_model=SmtpToolResponse)
def start_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = True
    save_smtp_tool_config(connection, config)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@app.post("/api/v1/tools/smtp/stop", response_model=SmtpToolResponse)
def stop_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = False
    save_smtp_tool_config(connection, config)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ToolMetadataResponse(**updated)


@app.post("/api/v1/inbound/{api_id}", response_model=InboundReceiveAccepted, status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound_event(api_id: str, request: Request, response: Response) -> InboundReceiveAccepted:
    connection = get_connection(request)
    logger = get_application_logger(request)
    event_id = f"evt_{uuid4().hex[:10]}"
    received_at = utc_now_iso()
    headers = header_subset(request.headers)
    source_ip = request.client.host if request.client else None
    api_row = get_api_or_404(connection, api_id, include_mock=True)

    if not api_row["enabled"]:
        log_event(
            connection,
            logger,
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
            logger,
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
            logger,
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
            logger,
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
            logger,
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
        logger,
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
    job_id = f"job_{uuid4().hex}"
    create_automation_run(
        connection,
        run_id=run_id,
        automation_id=api_id,
        trigger_type=trigger.type,
        status_value="queued",
        started_at=received_at,
    )
    create_automation_run_step(
        connection,
        step_id=step_id,
        run_id=run_id,
        step_name="emit_runtime_trigger",
        status_value="pending",
        request_summary=f"event_id={event_id}",
        started_at=received_at,
    )
    runtime_event_bus.emit(trigger, job_id=job_id, run_id=run_id, step_id=step_id)
    write_application_log(
        logger,
        logging.INFO,
        "runtime_trigger_queued",
        api_id=api_id,
        event_id=event_id,
        trigger_type=trigger.type,
        run_id=run_id,
        job_id=job_id,
    )
    matching_automations = fetch_all(
        connection,
        """
        SELECT id
        FROM automations
        WHERE enabled = 1
          AND trigger_type = 'inbound_api'
          AND json_extract(trigger_config_json, '$.inbound_api_id') = ?
        ORDER BY created_at ASC
        """,
        (api_id,),
    )
    for automation_row in matching_automations:
        execute_automation_definition(
            connection,
            logger,
            automation_id=automation_row["id"],
            trigger_type="inbound_api",
            payload=payload if isinstance(payload, dict) else {"payload": payload},
            root_dir=get_root_dir(request),
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
            worker_id,
            worker_name,
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
            worker_id,
            worker_name,
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
