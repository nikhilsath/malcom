from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_bool, _coerce_int, _execute_request


GOOGLE_CALENDAR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="calendar_upcoming_events",
        service="calendar",
        operation_type="read",
        label="Upcoming events",
        description="List Google Calendar events with pagination, q, and time-window filters.",
        required_scopes=("https://www.googleapis.com/auth/calendar.readonly",),
        input_schema=(
            _field("calendar_id", "Calendar ID", "string", required=False, default="primary"),
            _field("limit", "maxResults", "integer", required=False, default=10),
            _field("page_token", "pageToken", "string", required=False),
            _field("search_query", "q", "string", required=False),
            _field("show_deleted", "showDeleted", "boolean", required=False, default=False),
            _field("time_max", "timeMax", "string", required=False, placeholder="2026-04-03T12:00:00Z"),
            _field("updated_min", "updatedMin", "string", required=False, placeholder="2026-04-03T10:00:00Z"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("calendar_id", "Calendar ID", "string"),
            _output("events", "Events", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("next_sync_token", "Next sync token", "string"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_calendar_upcoming_events"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _first_populated_input(resolved_inputs: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in resolved_inputs:
            continue
        value = resolved_inputs.get(key)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        if value is not None:
            return value
    return None


def google_calendar_upcoming_events(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    calendar_id = urllib.parse.quote(str(resolved_inputs.get("calendar_id") or "primary"), safe="")
    limit = _coerce_int(_first_populated_input(resolved_inputs, "limit", "maxResults"), 10)
    params: dict[str, Any] = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": limit,
        "timeMin": str(_first_populated_input(resolved_inputs, "time_min", "timeMin") or (context or {}).get("timestamp") or "").strip(),
    }
    page_token = str(_first_populated_input(resolved_inputs, "page_token", "pageToken") or "").strip()
    if page_token:
        params["pageToken"] = page_token
    search_query = str(_first_populated_input(resolved_inputs, "search_query", "q") or "").strip()
    if search_query:
        params["q"] = search_query
    show_deleted = _first_populated_input(resolved_inputs, "show_deleted", "showDeleted")
    if show_deleted is not None:
        params["showDeleted"] = "true" if _coerce_bool(show_deleted) else "false"
    time_max = str(_first_populated_input(resolved_inputs, "time_max", "timeMax") or "").strip()
    if time_max:
        params["timeMax"] = time_max
    updated_min = str(_first_populated_input(resolved_inputs, "updated_min", "updatedMin") or "").strip()
    if updated_min:
        params["updatedMin"] = updated_min
    url = f"{base_url}/calendar/v3/calendars/{calendar_id}/events?{urllib.parse.urlencode(params)}"
    status_code, payload = _execute_request(executor, url, "GET", headers)
    _raise_for_status(status_code)
    items = (payload or {}).get("items") or []
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
    return {
        "provider": provider_id,
        "activity": activity_id,
        "calendar_id": resolved_inputs.get("calendar_id") or "primary",
        "events": events,
        "next_page_token": (payload or {}).get("nextPageToken"),
        "next_sync_token": (payload or {}).get("nextSyncToken"),
        "count": len(events),
    }


GOOGLE_CALENDAR_HANDLER_REGISTRY = {
    "google_calendar_upcoming_events": google_calendar_upcoming_events,
}
