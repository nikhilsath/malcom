from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from backend.database import DatabaseConnection
from backend.schemas import (
    DashboardLogEntryResponse,
    DashboardLogLevelOptionResponse,
    DashboardLogSettingsResponse,
    DashboardLogsApiResponse,
    DashboardLogsMetadataResponse,
)
from backend.services.logging_service import get_log_file_path
from backend.services.settings import read_stored_settings_section
from backend.services.utils import utc_now_iso

DEFAULT_DASHBOARD_LOG_LEVEL_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "debug", "label": "Debug"},
    {"value": "info", "label": "Info"},
    {"value": "warning", "label": "Warning"},
    {"value": "error", "label": "Error"},
)

DEFAULT_DASHBOARD_LOG_SETTINGS = {
    "max_stored_entries": 250,
    "max_visible_entries": 50,
    "max_detail_characters": 4000,
}

LOG_LINE_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2},\d{3})\s+(?P<level>[A-Z]+)\s*(?P<message>.*)$"
)


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _normalize_dashboard_log_level(level_value: str | None) -> Literal["debug", "info", "warning", "error"]:
    normalized = str(level_value or "").strip().lower()
    if normalized in {"critical", "fatal", "error"}:
        return "error"
    if normalized in {"warn", "warning"}:
        return "warning"
    if normalized == "debug":
        return "debug"
    return "info"


def _get_dashboard_log_settings(connection: DatabaseConnection) -> DashboardLogSettingsResponse:
    stored_settings = read_stored_settings_section(connection, "logging")
    merged_settings = DEFAULT_DASHBOARD_LOG_SETTINGS | (
        stored_settings if isinstance(stored_settings, dict) else {}
    )

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


def _parse_caddy_timestamp(value: Any) -> str:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC).isoformat()
        except (OverflowError, OSError, ValueError):
            return utc_now_iso()
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return utc_now_iso()
        try:
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            return datetime.fromisoformat(candidate).astimezone(UTC).isoformat()
        except ValueError:
            return utc_now_iso()
    return utc_now_iso()


def _build_entry_id(log_kind: str, path: Path, line_number: int, line: str) -> str:
    digest = hashlib.sha1(
        f"{log_kind}:{path}:{line_number}:{line}".encode("utf-8", errors="ignore")
    ).hexdigest()[:12]
    return f"log-{digest}"


def _normalize_application_log_entry(
    *,
    path: Path,
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

    source = "backend.runtime"
    category = "runtime"
    action = "log_line"
    message = message_part.strip() or "Runtime log line recorded."
    details: dict[str, Any] = {"log_file": path.name}
    context: dict[str, Any] = {}

    if isinstance(parsed_payload, dict):
        event_value = parsed_payload.get("event")
        if isinstance(event_value, str) and event_value.strip():
            action = event_value.strip()

        context_value = parsed_payload.get("context")
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

        details |= {
            key: value
            for key, value in parsed_payload.items()
            if key not in {"event", "context"}
        }
    else:
        details["raw_line"] = line

    return DashboardLogEntryResponse(
        id=_build_entry_id("application", path, line_number, line),
        timestamp=timestamp,
        level=level,
        source=source,
        category=category,
        action=action,
        message=message,
        details=details,
        context=context,
    )


def _normalize_caddy_log_entry(
    *,
    path: Path,
    line: str,
    line_number: int,
    date_part: str | None,
    time_part: str | None,
    level_part: str | None,
    message_part: str,
) -> DashboardLogEntryResponse:
    parsed_payload: Any
    try:
        parsed_payload = json.loads(message_part)
    except json.JSONDecodeError:
        parsed_payload = None

    timestamp = _parse_log_timestamp(date_part, time_part)
    level = _normalize_dashboard_log_level(level_part)
    source = "caddy.runtime"
    category = "proxy"
    action = "log_line"
    message = message_part.strip() or "Caddy log line recorded."
    details: dict[str, Any] = {"log_file": path.name}
    context: dict[str, Any] = {}

    if isinstance(parsed_payload, dict):
        timestamp = _parse_caddy_timestamp(parsed_payload.get("ts"))
        level = _normalize_dashboard_log_level(str(parsed_payload.get("level") or level_part or ""))

        logger_value = parsed_payload.get("logger")
        if isinstance(logger_value, str) and logger_value.strip():
            logger_value = logger_value.strip()
            source = logger_value if logger_value.startswith("caddy.") else f"caddy.{logger_value}"
            action = logger_value.split(".")[-1] or action
            if "access" in logger_value:
                category = "access"

        request_value = parsed_payload.get("request")
        if isinstance(request_value, dict):
            context = {
                key: request_value.get(key)
                for key in ("method", "host", "uri", "remote_ip", "proto")
                if request_value.get(key) is not None
            }

        status_value = parsed_payload.get("status")
        if status_value is not None:
            details["status"] = status_value

        duration_value = parsed_payload.get("duration")
        if duration_value is not None:
            details["duration"] = duration_value

        msg_value = parsed_payload.get("msg") or parsed_payload.get("message")
        if isinstance(msg_value, str) and msg_value.strip():
            message = msg_value.strip()
        elif context:
            request_host = context.get("host") or "unknown-host"
            request_uri = context.get("uri") or "/"
            message = f"Caddy request {request_host}{request_uri}"

        details |= {
            key: value
            for key, value in parsed_payload.items()
            if key not in {"ts", "level", "logger", "msg", "message", "request", "status", "duration"}
        }
    else:
        details["raw_line"] = line

    return DashboardLogEntryResponse(
        id=_build_entry_id("caddy", path, line_number, line),
        timestamp=timestamp,
        level=level,
        source=source,
        category=category,
        action=action,
        message=message,
        details=details,
        context=context,
    )


def _read_log_entries(path: Path, *, log_kind: Literal["application", "caddy"]) -> list[DashboardLogEntryResponse]:
    if not path.exists() or not path.is_file():
        return []

    try:
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    entries: list[DashboardLogEntryResponse] = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue

        match = LOG_LINE_PATTERN.match(line)
        date_part = match.group("date") if match else None
        time_part = match.group("time") if match else None
        level_part = match.group("level") if match else None
        message_part = (match.group("message") if match else line) or ""

        if log_kind == "caddy":
            entry = _normalize_caddy_log_entry(
                path=path,
                line=line,
                line_number=line_number,
                date_part=date_part,
                time_part=time_part,
                level_part=level_part,
                message_part=message_part,
            )
        else:
            entry = _normalize_application_log_entry(
                path=path,
                line=line,
                line_number=line_number,
                date_part=date_part,
                time_part=time_part,
                level_part=level_part,
                message_part=message_part,
            )

        entries.append(entry)

    return entries


def _candidate_caddy_log_paths(root_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    configured_path = os.environ.get("MALCOM_CADDY_LOG_PATH")
    if configured_path:
        candidates.append(Path(configured_path).expanduser())

    candidates.extend(
        [
            root_dir / "backend" / "data" / "caddy" / "caddy.log",
            root_dir / "backend" / "data" / "caddy" / "access.log",
            Path("/var/log/caddy/caddy.log"),
            Path("/var/log/caddy/access.log"),
            Path("/opt/homebrew/var/log/caddy/access.log"),
            Path("/usr/local/var/log/caddy/access.log"),
        ]
    )

    unique_candidates: list[Path] = []
    seen_paths: set[str] = set()
    for candidate in candidates:
        candidate_key = str(candidate)
        if candidate_key in seen_paths:
            continue
        seen_paths.add(candidate_key)
        unique_candidates.append(candidate)
    return unique_candidates


def _resolve_caddy_log_path(root_dir: Path) -> Path | None:
    candidates = _candidate_caddy_log_paths(root_dir)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return candidates[0] if candidates else None


def get_runtime_dashboard_logs_response(connection: DatabaseConnection, root_dir: Path) -> DashboardLogsApiResponse:
    settings = _get_dashboard_log_settings(connection)
    metadata = DashboardLogsMetadataResponse(
        allowed_levels=[DashboardLogLevelOptionResponse(**item) for item in DEFAULT_DASHBOARD_LOG_LEVEL_OPTIONS]
    )

    entries = _read_log_entries(get_log_file_path(root_dir), log_kind="application")
    caddy_log_path = _resolve_caddy_log_path(root_dir)
    if caddy_log_path is not None:
        entries.extend(_read_log_entries(caddy_log_path, log_kind="caddy"))

    entries.sort(key=lambda entry: entry.timestamp, reverse=True)
    if len(entries) > settings.max_stored_entries:
        entries = entries[: settings.max_stored_entries]

    return DashboardLogsApiResponse(settings=settings, metadata=metadata, entries=entries)


def clear_runtime_dashboard_logs(root_dir: Path) -> dict[str, Any]:
    targets: list[tuple[str, Path]] = [("application", get_log_file_path(root_dir))]
    caddy_log_path = _resolve_caddy_log_path(root_dir)
    if caddy_log_path is not None:
        targets.append(("caddy", caddy_log_path))

    cleared: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []

    for label, path in targets:
        if not path.exists():
            skipped.append(label)
            continue

        try:
            path.write_text("", encoding="utf-8")
            cleared.append(label)
        except OSError as exc:
            errors.append({"target": label, "path": str(path), "message": str(exc)})

    return {
        "ok": len(errors) == 0,
        "cleared": cleared,
        "skipped": skipped,
        "errors": errors,
    }


__all__ = ["clear_runtime_dashboard_logs", "get_runtime_dashboard_logs_response"]