from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_catalog import (
    JSON_SOURCE_HINT,
    UPLOAD_SOURCE_OPTIONS,
    VALUE_SOURCE_HINT,
    ConnectorActivityDefinition,
    _field,
    _output,
)
from .connector_activities_runtime import (
    RequestExecutor,
    _coerce_bool,
    _coerce_int,
    _csv_to_list,
    _execute_request,
    _gmail_raw_message,
    _google_file_fields,
    _normalize_drive_files,
)


GOOGLE_CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_list_messages",
        service="gmail",
        operation_type="read",
        label="List emails",
        description="List Gmail messages with optional labels and result limits.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(
            _field("labels", "Labels", "string", required=False, placeholder="INBOX,IMPORTANT", help_text="Comma-separated Gmail label IDs.", value_hint="csv"),
            _field("max_results", "Max results", "integer", required=False, default=25),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("messages", "Messages", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_gmail_list_messages"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_search_messages",
        service="gmail",
        operation_type="read",
        label="Search emails",
        description="Search Gmail with Gmail query syntax and optional labels.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(
            _field("search_query", "Search query", "string", required=True, placeholder="from:alerts@example.com newer_than:7d", help_text=VALUE_SOURCE_HINT),
            _field("labels", "Labels", "string", required=False, placeholder="INBOX,UNREAD", help_text="Optional comma-separated label IDs."),
            _field("max_results", "Max results", "integer", required=False, default=25),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("query", "Query", "string"),
            _output("messages", "Messages", "array"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_gmail_list_messages", "force_query": True},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_get_message",
        service="gmail",
        operation_type="read",
        label="Get specific email",
        description="Fetch a single Gmail message by message ID.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(
            _field("message_id", "Message ID", "string", required=True, help_text=VALUE_SOURCE_HINT),
            _field("format", "Response format", "select", required=False, default="full", options=["minimal", "full", "metadata", "raw"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("message", "Message", "object"),
        ),
        execution={"kind": "google_gmail_get_message"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_get_thread",
        service="gmail",
        operation_type="read",
        label="Get thread / conversation",
        description="Fetch a Gmail conversation thread by thread ID.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(
            _field("thread_id", "Thread ID", "string", required=True, help_text=VALUE_SOURCE_HINT),
            _field("format", "Message format", "select", required=False, default="full", options=["minimal", "full", "metadata"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("thread", "Thread", "object"),
        ),
        execution={"kind": "google_gmail_get_thread"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_send_email",
        service="gmail",
        operation_type="write",
        label="Send email",
        description="Compose and send an email through Gmail.",
        required_scopes=("https://www.googleapis.com/auth/gmail.send",),
        input_schema=(
            _field("recipients", "Recipients", "string", required=True, placeholder="user@example.com,team@example.com", help_text="Comma-separated recipient list."),
            _field("cc", "CC", "string", required=False),
            _field("bcc", "BCC", "string", required=False),
            _field("subject", "Subject", "string", required=True, help_text=VALUE_SOURCE_HINT),
            _field("body", "Body", "textarea", required=True, help_text="Plain text body. Supports automation variable mapping."),
            _field("thread_id", "Reply thread ID", "string", required=False, help_text="Optional Gmail thread ID for replies."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("message_id", "Message ID", "string"),
            _output("thread_id", "Thread ID", "string"),
            _output("label_ids", "Label IDs", "array"),
        ),
        execution={"kind": "google_gmail_send_email"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_create_draft",
        service="gmail",
        operation_type="write",
        label="Create draft",
        description="Create a Gmail draft from recipients, subject, and body.",
        required_scopes=("https://www.googleapis.com/auth/gmail.compose",),
        input_schema=(
            _field("recipients", "Recipients", "string", required=True, placeholder="user@example.com"),
            _field("cc", "CC", "string", required=False),
            _field("bcc", "BCC", "string", required=False),
            _field("subject", "Subject", "string", required=True),
            _field("body", "Body", "textarea", required=True, help_text="Plain text body. Supports automation variable mapping."),
            _field("thread_id", "Thread ID", "string", required=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("draft_id", "Draft ID", "string"),
            _output("message_id", "Message ID", "string"),
            _output("thread_id", "Thread ID", "string"),
        ),
        execution={"kind": "google_gmail_create_draft"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_modify_labels",
        service="gmail",
        operation_type="write",
        label="Update labels / organise email",
        description="Add or remove Gmail labels from a message.",
        required_scopes=("https://www.googleapis.com/auth/gmail.modify",),
        input_schema=(
            _field("message_id", "Message ID", "string", required=True),
            _field("add_label_ids", "Add labels", "string", required=False, placeholder="STARRED,IMPORTANT"),
            _field("remove_label_ids", "Remove labels", "string", required=False, placeholder="UNREAD"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("message_id", "Message ID", "string"),
            _output("label_ids", "Label IDs", "array"),
        ),
        execution={"kind": "google_gmail_modify_labels"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_list_files",
        service="drive",
        operation_type="read",
        label="List files",
        description="List Google Drive files with optional folder filtering.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(
            _field("parent_id", "Folder / parent ID", "string", required=False, help_text="Optional folder to list from."),
            _field("max_results", "Max results", "integer", required=False, default=25),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("files", "Files", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_drive_list_files"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_search_files",
        service="drive",
        operation_type="read",
        label="Search files",
        description="Search Google Drive files with Drive query syntax.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(
            _field("search_query", "Search query", "string", required=True, placeholder="name contains 'invoice' and trashed = false"),
            _field("max_results", "Max results", "integer", required=False, default=25),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("query", "Query", "string"),
            _output("files", "Files", "array"),
            _output("count", "Count", "integer"),
        ),
        execution={"kind": "google_drive_search_files"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_get_file_metadata",
        service="drive",
        operation_type="read",
        label="Get file metadata",
        description="Fetch Google Drive file metadata by file ID.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(_field("file_id", "File ID", "string", required=True),),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file", "File", "object"),
        ),
        execution={"kind": "google_drive_get_file_metadata"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_download_file",
        service="drive",
        operation_type="read",
        label="Download / fetch file",
        description="Fetch file content metadata for a Google Drive file download request.",
        required_scopes=("https://www.googleapis.com/auth/drive.readonly",),
        input_schema=(
            _field("file_id", "File ID", "string", required=True),
            _field("acknowledge_abuse", "Acknowledge abuse warning", "boolean", required=False, default=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file_id", "File ID", "string"),
            _output("download_url", "Download URL", "string"),
            _output("request_mode", "Request mode", "string"),
        ),
        execution={"kind": "google_drive_download_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_upload_file",
        service="drive",
        operation_type="write",
        label="Upload file",
        description="Upload file content into Google Drive from an automation-managed source reference.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(
            _field("file_name", "File name", "string", required=True),
            _field("parent_id", "Folder / parent ID", "string", required=False),
            _field("mime_type", "MIME type", "string", required=False, placeholder="text/plain"),
            _field("upload_source", "Upload source", "select", required=True, default="previous_step_output", options=UPLOAD_SOURCE_OPTIONS),
            _field("upload_reference", "Source reference", "string", required=True, help_text="Reference to prior output, local storage key, cloud storage key, or raw text."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file", "File", "object"),
            _output("source", "Source", "string"),
        ),
        execution={"kind": "google_drive_upload_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_create_file",
        service="drive",
        operation_type="write",
        label="Create file",
        description="Create a Google Drive file record with optional inline content.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(
            _field("file_name", "File name", "string", required=True),
            _field("parent_id", "Folder / parent ID", "string", required=False),
            _field("mime_type", "MIME type", "string", required=False),
            _field("content", "Initial content", "textarea", required=False, help_text="Optional plain-text content for text-like files."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file", "File", "object"),
        ),
        execution={"kind": "google_drive_create_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_update_file_metadata",
        service="drive",
        operation_type="write",
        label="Update file metadata",
        description="Patch Google Drive file metadata like name or MIME type.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(
            _field("file_id", "File ID", "string", required=True),
            _field("file_name", "File name", "string", required=False),
            _field("mime_type", "MIME type", "string", required=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file", "File", "object"),
        ),
        execution={"kind": "google_drive_update_file_metadata"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_delete_file",
        service="drive",
        operation_type="write",
        label="Delete file",
        description="Delete a Google Drive file by ID.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(_field("file_id", "File ID", "string", required=True),),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file_id", "File ID", "string"),
            _output("deleted", "Deleted", "boolean"),
        ),
        execution={"kind": "google_drive_delete_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_move_file",
        service="drive",
        operation_type="write",
        label="Move file / change parent",
        description="Move a file between Google Drive folders by changing parent references.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(
            _field("file_id", "File ID", "string", required=True),
            _field("add_parent_id", "New parent ID", "string", required=True),
            _field("remove_parent_id", "Previous parent ID", "string", required=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("file", "File", "object"),
        ),
        execution={"kind": "google_drive_move_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_manage_permissions",
        service="drive",
        operation_type="write",
        label="Manage permissions / sharing",
        description="Create a Google Drive permission entry for a file.",
        required_scopes=("https://www.googleapis.com/auth/drive",),
        input_schema=(
            _field("file_id", "File ID", "string", required=True),
            _field("permission_type", "Permission type", "select", required=True, default="user", options=["user", "group", "domain", "anyone"]),
            _field("role", "Role", "select", required=True, default="reader", options=["reader", "commenter", "writer", "fileOrganizer", "organizer", "owner"]),
            _field("email_address", "Email address", "string", required=False),
            _field("domain", "Domain", "string", required=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("permission", "Permission", "object"),
        ),
        execution={"kind": "google_drive_manage_permissions"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_get_storage_quota",
        service="drive",
        operation_type="read",
        label="Read storage / quota info",
        description="Fetch Drive storage quota information for the authenticated account.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("storage_quota", "Storage quota", "object"),
            _output("user", "User", "object"),
        ),
        execution={"kind": "google_drive_get_storage_quota"},
    ),
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
            _field("initial_data_reference", "Data reference or content", "text", required=False, placeholder='{"headers": ["Name", "Age"], "rows": [["Alice", 30], ["Bob", 25]]}', help_text=f"Provide structured data: raw JSON for 'raw_json' source, or reference to previous step output like {{{{steps.step_name.spreadsheet_data}}}}. {JSON_SOURCE_HINT}"),
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
        description="Read values from a Google Sheets range.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        input_schema=(
            _field("spreadsheet_id", "Spreadsheet ID", "string", required=True),
            _field("range", "A1 range", "string", required=True, placeholder="Sheet1!A1:C10"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("spreadsheet_id", "Spreadsheet ID", "string"),
            _output("range", "Range", "string"),
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
            _field("values_payload", "Values payload", "json", required=True, placeholder='[["a",1],["b",2]]', help_text=JSON_SOURCE_HINT),
            _field("value_input_option", "Input mode", "select", required=False, default="USER_ENTERED", options=["RAW", "USER_ENTERED"], help_text="RAW preserves exact values. USER_ENTERED lets Sheets parse formulas and dates."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("updated_range", "Updated range", "string"),
            _output("updated_rows", "Updated rows", "integer"),
            _output("updated_columns", "Updated columns", "integer"),
            _output("updated_cells", "Updated cells", "integer"),
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
            _field("values_payload", "Values payload", "json", required=True, placeholder='[["a",1],["b",2]]', help_text=JSON_SOURCE_HINT),
            _field("value_input_option", "Input mode", "select", required=False, default="USER_ENTERED", options=["RAW", "USER_ENTERED"]),
            _field("insert_data_option", "Append mode", "select", required=False, default="INSERT_ROWS", options=["INSERT_ROWS", "OVERWRITE"]),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
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
            _field("ranges", "Ranges JSON", "json", required=True, placeholder='["Sheet1!A1:B10","Sheet2!A1:A5"]', help_text="Provide a JSON array of A1 ranges."),
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
            _field("batch_payload", "Batch payload", "json", required=True, placeholder='[{"range":"Sheet1!A1:B2","values":[[1,2],[3,4]]}]', help_text="Provide a JSON array of {range, values} objects."),
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


def _google_gmail_list_messages(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    params = {"maxResults": _coerce_int(resolved_inputs.get("max_results"), 25)}
    labels = _csv_to_list(resolved_inputs.get("labels"))
    if labels:
        params["labelIds"] = labels
    query = str(resolved_inputs.get("search_query") or "").strip()
    if query:
        params["q"] = query
    query_string = urllib.parse.urlencode(params, doseq=True)
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages?{query_string}", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    messages = payload.get("messages") or []
    return {
        "provider": provider_id,
        "activity": activity_id,
        "query": query or None,
        "messages": messages,
        "next_page_token": payload.get("nextPageToken"),
        "count": len(messages),
    }


def _google_gmail_get_message(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    message_id = urllib.parse.quote(str(resolved_inputs.get("message_id") or ""), safe="")
    fmt = urllib.parse.quote(str(resolved_inputs.get("format") or "full"), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/{message_id}?format={fmt}", "GET", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "message": payload}


def _google_gmail_get_thread(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    thread_id = urllib.parse.quote(str(resolved_inputs.get("thread_id") or ""), safe="")
    fmt = urllib.parse.quote(str(resolved_inputs.get("format") or "full"), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/threads/{thread_id}?format={fmt}", "GET", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "thread": payload}


def _google_gmail_send_email(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    body = {"raw": _gmail_raw_message(resolved_inputs)}
    if resolved_inputs.get("thread_id"):
        body["threadId"] = resolved_inputs["thread_id"]
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/send", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "message_id": payload.get("id"),
        "thread_id": payload.get("threadId"),
        "label_ids": payload.get("labelIds") or [],
    }


def _google_gmail_create_draft(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    body = {"message": {"raw": _gmail_raw_message(resolved_inputs)}}
    if resolved_inputs.get("thread_id"):
        body["message"]["threadId"] = resolved_inputs["thread_id"]
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/drafts", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    message = payload.get("message") or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "draft_id": payload.get("id"),
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
    }


def _google_gmail_modify_labels(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    message_id = urllib.parse.quote(str(resolved_inputs.get("message_id") or ""), safe="")
    body = {
        "addLabelIds": _csv_to_list(resolved_inputs.get("add_label_ids")),
        "removeLabelIds": _csv_to_list(resolved_inputs.get("remove_label_ids")),
    }
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/{message_id}/modify", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "message_id": payload.get("id") or resolved_inputs.get("message_id"),
        "label_ids": payload.get("labelIds") or [],
    }


def _google_drive_list_or_search_files(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
    *,
    search_mode: bool,
) -> dict[str, Any]:
    max_results = _coerce_int(resolved_inputs.get("max_results"), 25)
    query_parts: list[str] = []
    if not search_mode and resolved_inputs.get("parent_id"):
        query_parts.append(f"'{resolved_inputs['parent_id']}' in parents")
    if search_mode:
        query_parts.append(str(resolved_inputs.get("search_query") or ""))
    query_parts.append("trashed = false")
    params = {
        "pageSize": max_results,
        "fields": _google_file_fields(),
        "q": " and ".join([part for part in query_parts if part]),
    }
    url = f"{base_url}/drive/v3/files?{urllib.parse.urlencode(params)}"
    status_code, payload = _execute_request(executor, url, "GET", headers)
    _raise_for_status(status_code)
    files = _normalize_drive_files(payload)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "query": params.get("q") or None,
        "files": files,
        "next_page_token": (payload or {}).get("nextPageToken"),
        "count": len(files),
    }


def _google_drive_get_file_metadata(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}?fields=id,name,mimeType,parents,webViewLink,modifiedTime,size,permissions", "GET", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file": payload}


def _google_drive_download_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    _headers: dict[str, str],
    _context: dict[str, Any] | None,
    _executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    abuse = "true" if _coerce_bool(resolved_inputs.get("acknowledge_abuse")) else "false"
    return {
        "provider": provider_id,
        "activity": activity_id,
        "file_id": resolved_inputs.get("file_id"),
        "download_url": f"{base_url}/drive/v3/files/{file_id}?alt=media&acknowledgeAbuse={abuse}",
        "request_mode": "signed_connector_request",
    }


def _google_drive_upload_or_create_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
    *,
    upload_mode: bool,
) -> dict[str, Any]:
    metadata = {"name": resolved_inputs.get("file_name")}
    if resolved_inputs.get("parent_id"):
        metadata["parents"] = [resolved_inputs.get("parent_id")]
    if resolved_inputs.get("mime_type"):
        metadata["mimeType"] = resolved_inputs.get("mime_type")
    if upload_mode:
        content = {"source": resolved_inputs.get("upload_source"), "reference": resolved_inputs.get("upload_reference")}
    else:
        content = resolved_inputs.get("content")
    body = {"metadata": metadata, "content": content}
    status_code, payload = _execute_request(executor, f"{base_url}/upload/drive/v3/files?uploadType=multipart", "POST", headers, body)
    _raise_for_status(status_code)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "file": payload,
        "source": resolved_inputs.get("upload_source"),
    }


def _google_drive_update_file_metadata(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    body = {
        key: value
        for key, value in {
            "name": resolved_inputs.get("file_name"),
            "mimeType": resolved_inputs.get("mime_type"),
        }.items()
        if value
    }
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}", "PATCH", headers, body)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file": payload}


def _google_drive_delete_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    status_code, _ = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}", "DELETE", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file_id": resolved_inputs.get("file_id"), "deleted": True}


def _google_drive_move_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    params = urllib.parse.urlencode(
        {
            "addParents": resolved_inputs.get("add_parent_id"),
            "removeParents": resolved_inputs.get("remove_parent_id") or "",
            "fields": "id,name,parents",
        }
    )
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}?{params}", "PATCH", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file": payload}


def _google_drive_manage_permissions(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    body = {"type": resolved_inputs.get("permission_type"), "role": resolved_inputs.get("role")}
    if resolved_inputs.get("email_address"):
        body["emailAddress"] = resolved_inputs.get("email_address")
    if resolved_inputs.get("domain"):
        body["domain"] = resolved_inputs.get("domain")
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}/permissions", "POST", headers, body)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "permission": payload}


def _google_drive_get_storage_quota(
    provider_id: str,
    activity_id: str,
    _resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/about?fields=storageQuota,user", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "storage_quota": payload.get("storageQuota") or {},
        "user": payload.get("user") or {},
    }


def _google_calendar_upcoming_events(
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


def _google_sheets_create_spreadsheet(
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


def _google_sheets_get_spreadsheet_metadata(
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


def _google_sheets_read_range(
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
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    values = payload.get("values") or []
    return {
        "provider": provider_id,
        "activity": activity_id,
        "spreadsheet_id": spreadsheet_id,
        "range": payload.get("range") or resolved_inputs.get("range"),
        "values": values,
        "row_count": len(values),
    }


def _google_sheets_update_range(
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
    option = urllib.parse.quote(str(resolved_inputs.get("value_input_option") or "USER_ENTERED"), safe="")
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}?valueInputOption={option}", "PUT", headers, {"values": resolved_inputs.get("values_payload")})
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "updated_range": payload.get("updatedRange"),
        "updated_rows": payload.get("updatedRows"),
        "updated_columns": payload.get("updatedColumns"),
        "updated_cells": payload.get("updatedCells"),
    }


def _google_sheets_append_rows(
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
    params = urllib.parse.urlencode(
        {
            "valueInputOption": resolved_inputs.get("value_input_option") or "USER_ENTERED",
            "insertDataOption": resolved_inputs.get("insert_data_option") or "INSERT_ROWS",
        }
    )
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:append?{params}", "POST", headers, {"values": resolved_inputs.get("values_payload")})
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "table_range": payload.get("tableRange"),
        "updates": payload.get("updates") or {},
    }


def _google_sheets_clear_range(
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


def _google_sheets_batch_get_ranges(
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


def _google_sheets_batch_update_ranges(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
    body = {
        "valueInputOption": resolved_inputs.get("value_input_option") or "USER_ENTERED",
        "data": resolved_inputs.get("batch_payload") or [],
    }
    status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "total_updated_cells": payload.get("totalUpdatedCells") or 0,
        "responses": payload.get("responses") or [],
    }


def _google_sheets_copy_sheet(
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


GOOGLE_HANDLER_REGISTRY = {
    "google_gmail_list_messages": _google_gmail_list_messages,
    "google_gmail_get_message": _google_gmail_get_message,
    "google_gmail_get_thread": _google_gmail_get_thread,
    "google_gmail_send_email": _google_gmail_send_email,
    "google_gmail_create_draft": _google_gmail_create_draft,
    "google_gmail_modify_labels": _google_gmail_modify_labels,
    "google_drive_list_files": lambda provider_id, activity_id, resolved_inputs, base_url, headers, context, executor: _google_drive_list_or_search_files(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, search_mode=False),
    "google_drive_search_files": lambda provider_id, activity_id, resolved_inputs, base_url, headers, context, executor: _google_drive_list_or_search_files(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, search_mode=True),
    "google_drive_get_file_metadata": _google_drive_get_file_metadata,
    "google_drive_download_file": _google_drive_download_file,
    "google_drive_upload_file": lambda provider_id, activity_id, resolved_inputs, base_url, headers, context, executor: _google_drive_upload_or_create_file(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, upload_mode=True),
    "google_drive_create_file": lambda provider_id, activity_id, resolved_inputs, base_url, headers, context, executor: _google_drive_upload_or_create_file(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, upload_mode=False),
    "google_drive_update_file_metadata": _google_drive_update_file_metadata,
    "google_drive_delete_file": _google_drive_delete_file,
    "google_drive_move_file": _google_drive_move_file,
    "google_drive_manage_permissions": _google_drive_manage_permissions,
    "google_drive_get_storage_quota": _google_drive_get_storage_quota,
    "google_calendar_upcoming_events": _google_calendar_upcoming_events,
    "google_sheets_create_spreadsheet": _google_sheets_create_spreadsheet,
    "google_sheets_get_spreadsheet_metadata": _google_sheets_get_spreadsheet_metadata,
    "google_sheets_read_range": _google_sheets_read_range,
    "google_sheets_update_range": _google_sheets_update_range,
    "google_sheets_append_rows": _google_sheets_append_rows,
    "google_sheets_clear_range": _google_sheets_clear_range,
    "google_sheets_batch_get_ranges": _google_sheets_batch_get_ranges,
    "google_sheets_batch_update_ranges": _google_sheets_batch_update_ranges,
    "google_sheets_copy_sheet": _google_sheets_copy_sheet,
}
