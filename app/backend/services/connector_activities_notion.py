from __future__ import annotations

from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, JSON_SOURCE_HINT, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


NOTION_CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="notion",
        activity_id="notion_query_database",
        service="databases",
        operation_type="read",
        label="Query database",
        description="Query a Notion database and return normalized page summaries.",
        required_scopes=(),
        input_schema=(
            _field("database_id", "Database ID", "string", required=True),
            _field("page_size", "Page size", "integer", required=False, default=100),
            _field("start_cursor", "Start cursor", "string", required=False),
            _field("filter_json", "Filter JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
            _field("sorts_json", "Sorts JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("database_id", "Database ID", "string"),
            _output("results", "Results", "array"),
            _output("next_cursor", "Next cursor", "string"),
            _output("has_more", "Has more", "boolean"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "notion_query_database"},
    ),
    ConnectorActivityDefinition(
        provider_id="notion",
        activity_id="notion_create_page",
        service="pages",
        operation_type="write",
        label="Create page",
        description="Create a Notion page in a database and return the new page metadata.",
        required_scopes=(),
        input_schema=(
            _field("database_id", "Database ID", "string", required=True),
            _field("properties_json", "Properties JSON", "json", required=True, value_hint=JSON_SOURCE_HINT),
            _field("children_json", "Children JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
            _field("icon_json", "Icon JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
            _field("cover_json", "Cover JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("page_id", "Page ID", "string"),
            _output("url", "URL", "string"),
            _output("page", "Page", "object"),
        ),
        execution={"kind": "notion_create_page"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _notion_headers(headers: dict[str, str]) -> dict[str, str]:
    notion_headers = dict(headers)
    notion_headers.setdefault("Notion-Version", "2022-06-28")
    return notion_headers


def _normalize_notion_page(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "url": item.get("url"),
        "created_time": item.get("created_time"),
        "last_edited_time": item.get("last_edited_time"),
        "archived": bool(item.get("archived")),
        "properties": item.get("properties") or {},
    }


def notion_query_database(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    database_id = str(resolved_inputs.get("database_id") or "")
    body: dict[str, Any] = {
        "page_size": _coerce_int(resolved_inputs.get("page_size"), 100),
    }
    start_cursor = str(resolved_inputs.get("start_cursor") or "").strip()
    if start_cursor:
        body["start_cursor"] = start_cursor
    filter_json = resolved_inputs.get("filter_json")
    if isinstance(filter_json, dict) and filter_json:
        body["filter"] = filter_json
    sorts_json = resolved_inputs.get("sorts_json")
    if isinstance(sorts_json, list) and sorts_json:
        body["sorts"] = sorts_json
    status_code, payload = _execute_request(executor, f"{base_url}/databases/{database_id}/query", "POST", _notion_headers(headers), body)
    _raise_for_status(status_code)
    results = [_normalize_notion_page(item) for item in ((payload or {}).get("results") or [])]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "database_id": database_id,
        "results": results,
        "next_cursor": (payload or {}).get("next_cursor"),
        "has_more": bool((payload or {}).get("has_more")),
        "count": len(results),
    }


def notion_create_page(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    database_id = str(resolved_inputs.get("database_id") or "")
    body: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": resolved_inputs.get("properties_json") or {},
    }
    for field_name in ("children_json", "icon_json", "cover_json"):
        value = resolved_inputs.get(field_name)
        if value not in (None, "", [], {}):
            body[field_name.removesuffix("_json")] = value
    status_code, payload = _execute_request(executor, f"{base_url}/pages", "POST", _notion_headers(headers), body)
    _raise_for_status(status_code)
    payload = payload or {}
    page = _normalize_notion_page(payload)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "page_id": page.get("id"),
        "url": page.get("url"),
        "page": page,
    }


NOTION_HANDLER_REGISTRY = {
    "notion_query_database": notion_query_database,
    "notion_create_page": notion_create_page,
}
