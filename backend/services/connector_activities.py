from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException, status

from backend.schemas import OutgoingAuthConfig

DatabaseConnection = Any
RequestExecutor = Callable[[str, str, dict[str, str]], tuple[int, Any]]


@dataclass(frozen=True)
class ConnectorActivityDefinition:
    provider_id: str
    activity_id: str
    label: str
    description: str
    required_scopes: tuple[str, ...]
    input_schema: tuple[dict[str, Any], ...]
    output_schema: tuple[dict[str, Any], ...]
    execution: dict[str, Any]


def _request_json(url: str, headers: dict[str, str], *, method: str = "GET") -> tuple[int, Any]:
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = {"message": body[:500]}
        return error.code, parsed
    except urllib.error.URLError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to reach connector activity endpoint: {error.reason}.") from error
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Connector activity endpoint returned malformed JSON.") from error


CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_unread_count",
        label="Gmail unread count",
        description="Return the unread message count for the connected Gmail mailbox.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "unread_count", "label": "Unread count", "type": "integer"},
            {"key": "threads", "label": "Thread count", "type": "integer"},
        ),
        execution={"kind": "google_gmail_unread_count"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="calendar_upcoming_events",
        label="Calendar upcoming events",
        description="List the next events from a Google Calendar.",
        required_scopes=("https://www.googleapis.com/auth/calendar.readonly",),
        input_schema=(
            {"key": "calendar_id", "label": "Calendar ID", "type": "string", "required": False, "default": "primary", "help_text": "Defaults to the primary calendar."},
            {"key": "limit", "label": "Maximum events", "type": "integer", "required": False, "default": 10},
        ),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "calendar_id", "label": "Calendar ID", "type": "string"},
            {"key": "events", "label": "Events", "type": "array"},
            {"key": "count", "label": "Event count", "type": "integer"},
        ),
        execution={"kind": "google_calendar_upcoming_events"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_read_range",
        label="Sheets read range",
        description="Read values from a Google Sheets range.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        input_schema=(
            {"key": "spreadsheet_id", "label": "Spreadsheet ID", "type": "string", "required": True},
            {"key": "range", "label": "A1 range", "type": "string", "required": True, "placeholder": "Sheet1!A1:C10"},
        ),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "spreadsheet_id", "label": "Spreadsheet ID", "type": "string"},
            {"key": "range", "label": "Range", "type": "string"},
            {"key": "values", "label": "Values", "type": "array"},
            {"key": "row_count", "label": "Row count", "type": "integer"},
        ),
        execution={"kind": "google_sheets_read_range"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_open_pull_requests",
        label="List open pull requests",
        description="List open pull requests for a repository.",
        required_scopes=("repo",),
        input_schema=(
            {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
            {"key": "repo", "label": "Repository name", "type": "string", "required": True},
            {"key": "limit", "label": "Maximum pull requests", "type": "integer", "required": False, "default": 10},
        ),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "repository", "label": "Repository", "type": "string"},
            {"key": "pull_requests", "label": "Pull requests", "type": "array"},
            {"key": "count", "label": "Pull request count", "type": "integer"},
        ),
        execution={"kind": "github_list_open_pull_requests"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_assigned_issues",
        label="List assigned issues",
        description="List issues assigned to the authenticated GitHub user.",
        required_scopes=("repo",),
        input_schema=(
            {"key": "state", "label": "Issue state", "type": "select", "required": False, "default": "open", "options": ["open", "closed", "all"]},
            {"key": "limit", "label": "Maximum issues", "type": "integer", "required": False, "default": 10},
        ),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "issues", "label": "Issues", "type": "array"},
            {"key": "count", "label": "Issue count", "type": "integer"},
        ),
        execution={"kind": "github_list_assigned_issues"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="repo_details",
        label="Repository details",
        description="Fetch normalized metadata for a GitHub repository.",
        required_scopes=("repo",),
        input_schema=(
            {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
            {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        ),
        output_schema=(
            {"key": "provider", "label": "Provider", "type": "string"},
            {"key": "activity", "label": "Activity", "type": "string"},
            {"key": "repository", "label": "Repository", "type": "string"},
            {"key": "default_branch", "label": "Default branch", "type": "string"},
            {"key": "visibility", "label": "Visibility", "type": "string"},
            {"key": "open_issues_count", "label": "Open issues count", "type": "integer"},
            {"key": "stars", "label": "Stars", "type": "integer"},
        ),
        execution={"kind": "github_repo_details"},
    ),
)

_ACTIVITY_INDEX = {(item.provider_id, item.activity_id): item for item in CONNECTOR_ACTIVITY_DEFINITIONS}


def build_connector_activity_catalog() -> list[dict[str, Any]]:
    return [
        {
            "provider_id": item.provider_id,
            "activity_id": item.activity_id,
            "label": item.label,
            "description": item.description,
            "required_scopes": list(item.required_scopes),
            "input_schema": list(item.input_schema),
            "output_schema": list(item.output_schema),
            "execution": dict(item.execution),
        }
        for item in CONNECTOR_ACTIVITY_DEFINITIONS
    ]


def get_connector_activity_definition(provider_id: str, activity_id: str) -> dict[str, Any] | None:
    item = _ACTIVITY_INDEX.get((provider_id, activity_id))
    if item is None:
        return None
    return {
        "provider_id": item.provider_id,
        "activity_id": item.activity_id,
        "label": item.label,
        "description": item.description,
        "required_scopes": list(item.required_scopes),
        "input_schema": list(item.input_schema),
        "output_schema": list(item.output_schema),
        "execution": dict(item.execution),
    }


def get_provider_activities(provider_id: str) -> list[dict[str, Any]]:
    return [item for item in build_connector_activity_catalog() if item["provider_id"] == provider_id]


def _coerce_int(value: Any, default: int) -> int:
    try:
        return max(1, int(str(value or default).strip()))
    except (TypeError, ValueError):
        return default


def _resolve_inputs(input_schema: list[dict[str, Any]], configured_inputs: dict[str, Any] | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    from backend.services.helpers import render_template_string

    source = configured_inputs or {}
    resolved: dict[str, Any] = {}
    for field in input_schema:
        key = field["key"]
        raw_value = source.get(key, field.get("default"))
        if isinstance(raw_value, str):
            raw_value = render_template_string(raw_value, context or {})
        if field.get("type") == "integer" and raw_value not in (None, ""):
            resolved[key] = _coerce_int(raw_value, int(field.get("default") or 1))
        else:
            resolved[key] = raw_value
        if field.get("required") and str(resolved.get(key) or "").strip() == "":
            raise RuntimeError(f"Connector activity input '{field['label']}' is required.")
    return resolved


def _build_connector_headers(auth_type: str, auth_config: OutgoingAuthConfig | None, provider_id: str) -> dict[str, str]:
    from backend.services.network import build_outgoing_request_headers

    headers = build_outgoing_request_headers(auth_type, auth_config)
    headers.setdefault("Accept", "application/json")
    if provider_id == "github":
        headers.setdefault("X-GitHub-Api-Version", "2022-11-28")
        headers.setdefault("User-Agent", "malcom-connector-activity")
    return headers


def _get_connector_activity_context(connection: DatabaseConnection, *, connector_id: str, root_dir: Any) -> tuple[dict[str, Any], dict[str, str]]:
    from backend.services.helpers import (
        build_outgoing_auth_config_from_connector,
        find_stored_connector_record,
        get_connector_protection_secret,
    )

    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")
    if record.get("status") == "revoked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is revoked.")
    protection_secret = get_connector_protection_secret(root_dir=root_dir)
    auth_config = build_outgoing_auth_config_from_connector(record, protection_secret)
    auth_type = record.get("auth_type") or "none"
    request_auth_type = "bearer" if auth_type == "oauth2" else ("header" if auth_type == "api_key" else auth_type)
    headers = _build_connector_headers(request_auth_type, auth_config, record.get("provider") or "")
    return record, headers


def get_missing_connector_activity_scopes(connector_record: dict[str, Any] | None, activity_definition: dict[str, Any] | None) -> list[str]:
    if connector_record is None or activity_definition is None:
        return []
    granted = set(connector_record.get("scopes") or [])
    return [scope for scope in activity_definition.get("required_scopes", []) if scope not in granted]


def execute_connector_activity(
    connection: DatabaseConnection,
    *,
    connector_id: str,
    activity_id: str,
    inputs: dict[str, Any] | None,
    root_dir: Any,
    context: dict[str, Any] | None = None,
    request_executor: RequestExecutor | None = None,
) -> dict[str, Any]:
    record, headers = _get_connector_activity_context(connection, connector_id=connector_id, root_dir=root_dir)
    provider_id = record.get("provider") or ""
    definition = get_connector_activity_definition(provider_id, activity_id)
    if definition is None:
        raise RuntimeError(f"Connector provider '{provider_id}' does not support activity '{activity_id}'.")

    missing_scopes = get_missing_connector_activity_scopes(record, definition)
    if missing_scopes:
        raise RuntimeError(f"Connector is missing required scopes: {', '.join(missing_scopes)}.")

    resolved_inputs = _resolve_inputs(definition["input_schema"], inputs, context)
    executor = request_executor or (lambda url, method, req_headers: _request_json(url, req_headers, method=method))
    base_url = (record.get("base_url") or "").rstrip("/")
    kind = definition["execution"]["kind"]

    if kind == "google_gmail_unread_count":
        status_code, payload = executor(f"{base_url}/gmail/v1/users/me/labels/INBOX", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {
            "provider": provider_id,
            "activity": activity_id,
            "unread_count": int(payload.get("messagesUnread") or 0),
            "threads": int(payload.get("threadsUnread") or 0),
        }
    if kind == "google_calendar_upcoming_events":
        calendar_id = urllib.parse.quote(str(resolved_inputs.get("calendar_id") or "primary"), safe="")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        url = (
            f"{base_url}/calendar/v3/calendars/{calendar_id}/events?singleEvents=true&orderBy=startTime"
            f"&maxResults={limit}&timeMin={urllib.parse.quote(str((context or {}).get('timestamp') or ''))}"
        )
        status_code, payload = executor(url, "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        items = payload.get("items") or []
        events = [
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "status": item.get("status"),
                "start": (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"),
                "end": (item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date"),
                "html_link": item.get("htmlLink"),
            }
            for item in items
        ]
        return {"provider": provider_id, "activity": activity_id, "calendar_id": resolved_inputs.get("calendar_id") or "primary", "events": events, "count": len(events)}
    if kind == "google_sheets_read_range":
        spreadsheet_id = str(resolved_inputs.get("spreadsheet_id") or "")
        encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
        status_code, payload = executor(f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        values = payload.get("values") or []
        return {"provider": provider_id, "activity": activity_id, "spreadsheet_id": spreadsheet_id, "range": payload.get("range") or resolved_inputs.get("range"), "values": values, "row_count": len(values)}
    if kind == "github_list_open_pull_requests":
        owner = str(resolved_inputs.get("owner") or "")
        repo = str(resolved_inputs.get("repo") or "")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        status_code, payload = executor(f"{base_url}/repos/{owner}/{repo}/pulls?state=open&per_page={limit}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        pulls = [
            {"number": item.get("number"), "title": item.get("title"), "state": item.get("state"), "html_url": item.get("html_url"), "author": (item.get("user") or {}).get("login")}
            for item in (payload or [])
        ]
        return {"provider": provider_id, "activity": activity_id, "repository": f"{owner}/{repo}", "pull_requests": pulls, "count": len(pulls)}
    if kind == "github_list_assigned_issues":
        state = str(resolved_inputs.get("state") or "open")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        status_code, payload = executor(f"{base_url}/issues?filter=assigned&state={urllib.parse.quote(state)}&per_page={limit}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        issues = [
            {"number": item.get("number"), "title": item.get("title"), "state": item.get("state"), "repository": (item.get("repository") or {}).get("full_name"), "html_url": item.get("html_url")}
            for item in (payload or [])
            if "pull_request" not in item
        ]
        return {"provider": provider_id, "activity": activity_id, "issues": issues, "count": len(issues)}
    if kind == "github_repo_details":
        owner = str(resolved_inputs.get("owner") or "")
        repo = str(resolved_inputs.get("repo") or "")
        status_code, payload = executor(f"{base_url}/repos/{owner}/{repo}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {
            "provider": provider_id,
            "activity": activity_id,
            "repository": payload.get("full_name") or f"{owner}/{repo}",
            "default_branch": payload.get("default_branch"),
            "visibility": payload.get("visibility") or ("private" if payload.get("private") else "public"),
            "open_issues_count": int(payload.get("open_issues_count") or 0),
            "stars": int(payload.get("stargazers_count") or 0),
        }

    raise RuntimeError(f"Unsupported connector activity execution mapping '{kind}'.")
