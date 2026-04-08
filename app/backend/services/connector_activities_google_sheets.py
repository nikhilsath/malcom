from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, JSON_SOURCE_HINT, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_bool, _execute_request


GOOGLE_SHEETS_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_create_spreadsheet",
        service="sheets",
        operation_type="write",
        label="Create spreadsheet",
        description="Create a new Google Sheets spreadsheet with optional initial data.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"),
        input_schema=(
            _field("title", "Spreadsheet title", "string", required=True, help_text="Name of the new spreadsheet."),
            _field("parent_id", "Save location (Drive folder ID)", "string", required=False, help_text="Optional Drive folder ID where the spreadsheet will be saved. Leave empty to save to root."),
            _field("sheet_name", "Initial sheet name", "string", required=False, help_text="Custom name for the first sheet. Defaults to 'Sheet1' if not specified."),
            _field("initial_data_source", "Initial data source", "select", required=False, default="empty", options=["empty", "raw_json", "previous_step_output"], help_text="How to populate initial data in the spreadsheet."),
            _field("initial_data_reference", "Data reference or content", "text", required=False, placeholder='{\"headers\": [\"Name\", \"Age\"], \"rows\": [[\"Alice\", 30], [\"Bob\", 25]]}', help_text=f"Provide structured data: raw JSON for 'raw_json' source, or reference to previous step output like {{{{steps.step_name.spreadsheet_data}}}}. {JSON_SOURCE_HINT}"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet", "Spreadsheet", "object"),
            _output("spreadsheet_id", "Spreadsheet ID", "string"),
            _output("sheet_id", "Initial sheet ID", "string"),
        ),
        execution={"kind": "google_sheets_create_spreadsheet"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_get_spreadsheet_metadata",
        service="sheets",
        operation_type="read",
        label="Get spreadsheet metadata",
        description="Fetch spreadsheet metadata and sheet definitions.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        input_schema=(_field("spreadsheet_id", "Spreadsheet ID", "string", required=True),),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet", "Spreadsheet", "object"),
        ),
        execution={"kind": "google_sheets_get_spreadsheet_metadata"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_read_range",
        service="sheets",
        operation_type="read",
        label="Read range",
        description="Read values from a Google Sheets range with render and dimension options.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("range", "A1 range", "string", required=True, placeholder="Sheet1!A1:C10"),
            _field("major_dimension", "majorDimension", "select", required=False, options=["ROWS", "COLUMNS"]),
            _field("value_render_option", "valueRenderOption", "select", required=False, options=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"]),
            _field("date_time_render_option", "dateTimeRenderOption", "select", required=False, options=["SERIAL_NUMBER", "FORMATTED_STRING"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet_id", "Spreadsheet ID", "string"),
            _output("range", "Range", "string"),
            _output("major_dimension", "Major dimension", "string"),
            _output("values", "Values", "array"),
            _output("row_count", "Row count", "integer"),
        ),
        execution={"kind": "google_sheets_read_range"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_update_range",
        service="sheets",
        operation_type="write",
        label="Update range",
        description="Write values into a Google Sheets range.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("range", "A1 range", "string", required=True),
            _field("values_payload", "Values payload", "json", required=True, placeholder='[[\"a\",1],[\"b\",2]]', help_text=JSON_SOURCE_HINT),
            _field("value_input_option", "Input mode", "select", required=False, default="USER_ENTERED", options=["RAW", "USER_ENTERED"], help_text="RAW preserves exact values. USER_ENTERED lets Sheets parse formulas and dates."),
            _field("include_values_in_response", "includeValuesInResponse", "boolean", required=False, default=False),
            _field("response_value_render_option", "responseValueRenderOption", "select", required=False, options=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"]),
            _field("response_date_time_render_option", "responseDateTimeRenderOption", "select", required=False, options=["SERIAL_NUMBER", "FORMATTED_STRING"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet_id", "Spreadsheet ID", "string"),
            _output("updated_range", "Updated range", "string"),
            _output("updated_rows", "Updated rows", "integer"),
            _output("updated_columns", "Updated columns", "integer"),
            _output("updated_cells", "Updated cells", "integer"),
            _output("updated_data", "Updated data", "object"),
        ),
        execution={"kind": "google_sheets_update_range"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_append_rows",
        service="sheets",
        operation_type="write",
        label="Append rows",
        description="Append rows to a Google Sheets range.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("range", "A1 range", "string", required=True, placeholder="Sheet1!A:C"),
            _field("values_payload", "Values payload", "json", required=True, placeholder='[[\"a\",1],[\"b\",2]]', help_text=JSON_SOURCE_HINT),
            _field("value_input_option", "Input mode", "select", required=False, default="USER_ENTERED", options=["RAW", "USER_ENTERED"]),
            _field("insert_data_option", "Append mode", "select", required=False, default="INSERT_ROWS", options=["INSERT_ROWS", "OVERWRITE"]),
            _field("include_values_in_response", "includeValuesInResponse", "boolean", required=False, default=False),
            _field("response_value_render_option", "responseValueRenderOption", "select", required=False, options=["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"]),
            _field("response_date_time_render_option", "responseDateTimeRenderOption", "select", required=False, options=["SERIAL_NUMBER", "FORMATTED_STRING"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet_id", "Spreadsheet ID", "string"),
            _output("table_range", "Table range", "string"),
            _output("updates", "Updates", "object"),
        ),
        execution={"kind": "google_sheets_append_rows"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_clear_range",
        service="sheets",
        operation_type="write",
        label="Clear range",
        description="Clear values from a Google Sheets range.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("range", "A1 range", "string", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("cleared_range", "Cleared range", "string"),
        ),
        execution={"kind": "google_sheets_clear_range"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_batch_get_ranges",
        service="sheets",
        operation_type="read",
        label="Batch get ranges",
        description="Read multiple A1 ranges from a spreadsheet in one request.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("ranges", "Ranges JSON", "json", required=True, placeholder='[\"Sheet1!A1:B10\",\"Sheet2!A1:A5\"]', help_text="Provide a JSON array of A1 ranges."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("value_ranges", "Value ranges", "array"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_sheets_batch_get_ranges"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_batch_update_ranges",
        service="sheets",
        operation_type="write",
        label="Batch update ranges",
        description="Write multiple value ranges to a spreadsheet.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("batch_payload", "Batch payload", "json", required=True, placeholder='[{\"range\":\"Sheet1!A1:B2\",\"values\":[[1,2],[3,4]]}]', help_text="Provide a JSON array of {range, values} objects."),
            _field("value_input_option", "Input mode", "select", required=False, default="USER_ENTERED", options=["RAW", "USER_ENTERED"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("total_updated_cells", "Total updated cells", "integer"),
            _output("responses", "Responses", "array"),
        ),
        execution={"kind": "google_sheets_batch_update_ranges"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_copy_sheet",
        service="sheets",
        operation_type="write",
        label="Copy sheet / tab",
        description="Copy a sheet tab within a spreadsheet or into another spreadsheet.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("sheet_id", "Sheet ID", "integer", required=True),
            _field("destination_spreadsheet_id", "Destination spreadsheet ID", "string", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("sheet", "Sheet", "object"),
        ),
        execution={"kind": "google_sheets_copy_sheet"},
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


def google_sheets_create_spreadsheet(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    body = {"properties": {"title": resolved_inputs.get("title")}}
    if resolved_inputs.get("sheet_name"):
        body["sheets"] = [{"properties": {"title": resolved_inputs.get("sheet_name")}}]
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets", "POST", headers, body)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "spreadsheet": payload}


def google_sheets_get_spreadsheet_metadata(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}", "GET", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "spreadsheet": payload}


def google_sheets_read_range(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = str(resolved_inputs.get("spreadsheet_id") or "")
    encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
    params: dict[str, Any] = {}
    major_dimension = str(_first_populated_input(resolved_inputs, "major_dimension", "majorDimension") or "").strip()
    if major_dimension:
        params["majorDimension"] = major_dimension
    value_render_option = str(_first_populated_input(resolved_inputs, "value_render_option", "valueRenderOption") or "").strip()
    if value_render_option:
        params["valueRenderOption"] = value_render_option
    date_time_render_option = str(_first_populated_input(resolved_inputs, "date_time_render_option", "dateTimeRenderOption") or "").strip()
    if date_time_render_option:
        params["dateTimeRenderOption"] = date_time_render_option
    query_suffix = f"?{urllib.parse.urlencode(params)}" if params else ""
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}{query_suffix}", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    values = payload.get("values") or []
    return {
        "provider": provider_id,
        "activity": activity_id,
        "spreadsheet_id": spreadsheet_id,
        "range": payload.get("range") or resolved_inputs.get("range"),
        "major_dimension": payload.get("majorDimension"),
        "values": values,
        "row_count": len(values),
    }


def google_sheets_update_range(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
    params: dict[str, Any] = {"valueInputOption": str(_first_populated_input(resolved_inputs, "value_input_option", "valueInputOption") or "USER_ENTERED")}
    include_values_in_response = _first_populated_input(resolved_inputs, "include_values_in_response", "includeValuesInResponse")
    if include_values_in_response is not None:
        params["includeValuesInResponse"] = "true" if _coerce_bool(include_values_in_response) else "false"
    response_value_render_option = str(_first_populated_input(resolved_inputs, "response_value_render_option", "responseValueRenderOption") or "").strip()
    if response_value_render_option:
        params["responseValueRenderOption"] = response_value_render_option
    response_date_time_render_option = str(_first_populated_input(resolved_inputs, "response_date_time_render_option", "responseDateTimeRenderOption") or "").strip()
    if response_date_time_render_option:
        params["responseDateTimeRenderOption"] = response_date_time_render_option
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}?{urllib.parse.urlencode(params)}",
        "PUT",
        headers,
        {"values": resolved_inputs.get("values_payload")},
    )
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "spreadsheet_id": payload.get("spreadsheetId") or resolved_inputs.get("spreadsheet_id"),
        "updated_range": payload.get("updatedRange"),
        "updated_rows": payload.get("updatedRows"),
        "updated_columns": payload.get("updatedColumns"),
        "updated_cells": payload.get("updatedCells"),
        "updated_data": payload.get("updatedData"),
    }


def google_sheets_append_rows(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
    params: dict[str, Any] = {
        "valueInputOption": str(_first_populated_input(resolved_inputs, "value_input_option", "valueInputOption") or "USER_ENTERED"),
        "insertDataOption": str(_first_populated_input(resolved_inputs, "insert_data_option", "insertDataOption") or "INSERT_ROWS"),
    }
    include_values_in_response = _first_populated_input(resolved_inputs, "include_values_in_response", "includeValuesInResponse")
    if include_values_in_response is not None:
        params["includeValuesInResponse"] = "true" if _coerce_bool(include_values_in_response) else "false"
    response_value_render_option = str(_first_populated_input(resolved_inputs, "response_value_render_option", "responseValueRenderOption") or "").strip()
    if response_value_render_option:
        params["responseValueRenderOption"] = response_value_render_option
    response_date_time_render_option = str(_first_populated_input(resolved_inputs, "response_date_time_render_option", "responseDateTimeRenderOption") or "").strip()
    if response_date_time_render_option:
        params["responseDateTimeRenderOption"] = response_date_time_render_option
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:append?{urllib.parse.urlencode(params)}",
        "POST",
        headers,
        {"values": resolved_inputs.get("values_payload")},
    )
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "spreadsheet_id": payload.get("spreadsheetId") or resolved_inputs.get("spreadsheet_id"),
        "table_range": payload.get("tableRange"),
        "updates": payload.get("updates") or {},
    }


def google_sheets_clear_range(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:clear", "POST", headers, {})
    _raise_for_status(status_code)
    payload = payload or {}
    return {"provider": provider_id, "activity": activity_id, "cleared_range": payload.get("clearedRange")}


def google_sheets_batch_get_ranges(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    ranges = resolved_inputs.get("ranges") or []
    params = urllib.parse.urlencode([("ranges", str(item)) for item in ranges])
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values:batchGet?{params}", "GET", headers)
    _raise_for_status(status_code)
    value_ranges = (payload or {}).get("valueRanges") or []
    return {"provider": provider_id, "activity": activity_id, "value_ranges": value_ranges, "count": len(value_ranges)}


def google_sheets_batch_update_ranges(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    body = {"valueInputOption": resolved_inputs.get("value_input_option") or "USER_ENTERED", "data": resolved_inputs.get("batch_payload") or []}
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "total_updated_cells": payload.get("totalUpdatedCells") or 0,
        "responses": payload.get("responses") or [],
    }


def google_sheets_copy_sheet(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    sheet_id = int(resolved_inputs.get("sheet_id") or 0)
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/sheets/{sheet_id}:copyTo", "POST", headers, {"destinationSpreadsheetId": resolved_inputs.get("destination_spreadsheet_id")})
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "sheet": payload}


GOOGLE_SHEETS_HANDLER_REGISTRY = {
    "google_sheets_create_spreadsheet": google_sheets_create_spreadsheet,
    "google_sheets_get_spreadsheet_metadata": google_sheets_get_spreadsheet_metadata,
    "google_sheets_read_range": google_sheets_read_range,
    "google_sheets_update_range": google_sheets_update_range,
    "google_sheets_append_rows": google_sheets_append_rows,
    "google_sheets_clear_range": google_sheets_clear_range,
    "google_sheets_batch_get_ranges": google_sheets_batch_get_ranges,
    "google_sheets_batch_update_ranges": google_sheets_batch_update_ranges,
    "google_sheets_copy_sheet": google_sheets_copy_sheet,
}
