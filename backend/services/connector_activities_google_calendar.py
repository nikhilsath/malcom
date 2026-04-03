from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GOOGLE_CALENDAR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="calendar_upcoming_events",
        service="calendar",
        operation_type="read",
        label="Upcoming events",
        description="List upcoming Google Calendar events for a calendar.",
        required_scopes=("https://www.googleapis.com/auth/calendar.readonly",),
        input_schema=(
            _field("calendar_id", "Calendar ID", "string", required=False, default="primary"),
            _field("limit", "Maximum events", "integer", required=False, default=10),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("calendar_id", "Calendar ID", "string"),
            _output("events", "Events", "array"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_calendar_upcoming_events"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


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
    limit = _coerce_int(resolved_inputs.get("limit"), 10)
    url = (
        f"{base_url}/calendar/v3/calendars/{calendar_id}/events?singleEvents=true&orderBy=startTime"
        f"&maxResults={limit}&timeMin={urllib.parse.quote(str((context or {}).get('timestamp') or ''))}"
    )
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
        "count": len(events),
    }


GOOGLE_CALENDAR_HANDLER_REGISTRY = {
    "google_calendar_upcoming_events": google_calendar_upcoming_events,
}
