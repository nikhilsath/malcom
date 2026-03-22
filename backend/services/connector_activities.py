from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Callable

from fastapi import HTTPException, status

from backend.schemas import OutgoingAuthConfig

DatabaseConnection = Any
RequestExecutor = Callable[..., tuple[int, Any]]


@dataclass(frozen=True)
class ConnectorActivityDefinition:
    provider_id: str
    activity_id: str
    service: str
    operation_type: str
    label: str
    description: str
    required_scopes: tuple[str, ...]
    input_schema: tuple[dict[str, Any], ...]
    output_schema: tuple[dict[str, Any], ...]
    execution: dict[str, Any]


def _request_json(url: str, headers: dict[str, str], *, method: str = "GET", body: Any | None = None) -> tuple[int, Any]:
    request_body: bytes | None = None
    request_headers = dict(headers)
    if body is not None:
        if isinstance(body, bytes):
            request_body = body
        else:
            request_body = json.dumps(body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=request_body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body_text = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body_text) if body_text else None
    except urllib.error.HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            parsed = {"message": body_text[:500]}
        return error.code, parsed
    except urllib.error.URLError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to reach connector activity endpoint: {error.reason}.") from error
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Connector activity endpoint returned malformed JSON.") from error


def _field(key: str, label: str, type_: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "type": type_, **extra}


def _output(key: str, label: str, type_: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "type": type_, **extra}


UPLOAD_SOURCE_OPTIONS = ["previous_step_output", "local_storage_reference", "cloud_storage_reference", "raw_text"]
VALUE_SOURCE_HINT = "Supports raw values and mapped workflow variables like {{steps.previous.output}}."
JSON_SOURCE_HINT = "Provide structured JSON, or template JSON with mapped workflow variables."


CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("message", "Message", "object")
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("thread", "Thread", "object")
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
            _field("body", "Body", "textarea", required=True, help_text="Plain text body. Supports workflow variable mapping."),
            _field("thread_id", "Reply thread ID", "string", required=False, help_text="Optional Gmail thread ID for replies."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("message_id", "Message ID", "string"), _output("thread_id", "Thread ID", "string"), _output("label_ids", "Label IDs", "array")
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
            _field("body", "Body", "textarea", required=True, help_text="Plain text body. Supports workflow variable mapping."),
            _field("thread_id", "Thread ID", "string", required=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("draft_id", "Draft ID", "string"), _output("message_id", "Message ID", "string"), _output("thread_id", "Thread ID", "string")
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("message_id", "Message ID", "string"), _output("label_ids", "Label IDs", "array")
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("files", "Files", "array"), _output("next_page_token", "Next page token", "string"), _output("count", "Count", "integer")
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("query", "Query", "string"), _output("files", "Files", "array"), _output("count", "Count", "integer")
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file", "File", "object")),
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file_id", "File ID", "string"), _output("download_url", "Download URL", "string"), _output("request_mode", "Request mode", "string")
        ),
        execution={"kind": "google_drive_download_file"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_upload_file",
        service="drive",
        operation_type="write",
        label="Upload file",
        description="Upload file content into Google Drive from a workflow-managed source reference.",
        required_scopes=("https://www.googleapis.com/auth/drive.file",),
        input_schema=(
            _field("file_name", "File name", "string", required=True),
            _field("parent_id", "Folder / parent ID", "string", required=False),
            _field("mime_type", "MIME type", "string", required=False, placeholder="text/plain"),
            _field("upload_source", "Upload source", "select", required=True, default="previous_step_output", options=UPLOAD_SOURCE_OPTIONS),
            _field("upload_reference", "Source reference", "string", required=True, help_text="Reference to prior output, local storage key, cloud storage key, or raw text."),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file", "File", "object"), _output("source", "Source", "string")
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file", "File", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file", "File", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file_id", "File ID", "string"), _output("deleted", "Deleted", "boolean")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("file", "File", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("permission", "Permission", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("storage_quota", "Storage quota", "object"), _output("user", "User", "object")),
        execution={"kind": "google_drive_get_storage_quota"},
    ),
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="sheets_create_spreadsheet",
        service="sheets",
        operation_type="write",
        label="Create spreadsheet",
        description="Create a new Google Sheets spreadsheet.",
        required_scopes=("https://www.googleapis.com/auth/spreadsheets",),
        input_schema=(
            _field("title", "Spreadsheet title", "string", required=True),
            _field("sheet_name", "Initial sheet name", "string", required=False),
        ),
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("spreadsheet", "Spreadsheet", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("spreadsheet", "Spreadsheet", "object")),
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
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("spreadsheet_id", "Spreadsheet ID", "string"), _output("range", "Range", "string"), _output("values", "Values", "array"), _output("row_count", "Row count", "integer")
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("updated_range", "Updated range", "string"), _output("updated_rows", "Updated rows", "integer"), _output("updated_columns", "Updated columns", "integer"), _output("updated_cells", "Updated cells", "integer")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("table_range", "Table range", "string"), _output("updates", "Updates", "object")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("cleared_range", "Cleared range", "string")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("value_ranges", "Value ranges", "array"), _output("count", "Count", "integer")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("total_updated_cells", "Total updated cells", "integer"), _output("responses", "Responses", "array")),
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
        output_schema=(_output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("sheet", "Sheet", "object")),
        execution={"kind": "google_sheets_copy_sheet"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_open_pull_requests",
        service="github",
        operation_type="read",
        label="List open pull requests",
        description="List open pull requests for a repository.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("limit", "Maximum pull requests", "integer", required=False, default=10),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("repository", "Repository", "string"), _output("pull_requests", "Pull requests", "array"), _output("count", "Pull request count", "integer")
        ),
        execution={"kind": "github_list_open_pull_requests"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_assigned_issues",
        service="github",
        operation_type="read",
        label="List assigned issues",
        description="List issues assigned to the authenticated GitHub user.",
        required_scopes=("repo",),
        input_schema=(
            _field("state", "Issue state", "select", required=False, default="open", options=["open", "closed", "all"]),
            _field("limit", "Maximum issues", "integer", required=False, default=10),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("issues", "Issues", "array"), _output("count", "Issue count", "integer")
        ),
        execution={"kind": "github_list_assigned_issues"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="repo_details",
        service="github",
        operation_type="read",
        label="Repository details",
        description="Fetch normalized metadata for a GitHub repository.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"), _output("activity", "Activity", "string"), _output("repository", "Repository", "string"), _output("default_branch", "Default branch", "string"), _output("visibility", "Visibility", "string"), _output("open_issues_count", "Open issues count", "integer"), _output("stars", "Stars", "integer")
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
            "service": item.service,
            "operation_type": item.operation_type,
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
        "service": item.service,
        "operation_type": item.operation_type,
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
        return int(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_inputs(input_schema: list[dict[str, Any]], configured_inputs: dict[str, Any] | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    from backend.services.helpers import render_template_string

    source = configured_inputs or {}
    resolved: dict[str, Any] = {}
    for field in input_schema:
        key = field["key"]
        raw_value = source.get(key, field.get("default"))
        if isinstance(raw_value, str):
            raw_value = render_template_string(raw_value, context or {})
        field_type = field.get("type")
        if field_type == "integer" and raw_value not in (None, ""):
            resolved[key] = _coerce_int(raw_value, int(field.get("default") or 0))
        elif field_type == "boolean":
            resolved[key] = _coerce_bool(raw_value)
        elif field_type == "json" and isinstance(raw_value, str) and raw_value.strip():
            resolved[key] = json.loads(raw_value)
        else:
            resolved[key] = raw_value
        if field.get("required") and str(resolved.get(key) if resolved.get(key) is not None else "").strip() == "":
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


def _execute_request(executor: RequestExecutor, url: str, method: str, headers: dict[str, str], body: Any | None = None) -> tuple[int, Any]:
    try:
        return executor(url, method, headers, body)
    except TypeError:
        return executor(url, method, headers)


def _google_file_fields() -> str:
    return "files(id,name,mimeType,parents,webViewLink,modifiedTime,size),nextPageToken"


def _normalize_drive_files(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "mime_type": item.get("mimeType"),
            "parents": item.get("parents") or [],
            "web_view_link": item.get("webViewLink"),
            "modified_at": item.get("modifiedTime"),
            "size": item.get("size"),
        }
        for item in (payload or {}).get("files") or []
    ]


def _csv_to_list(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _gmail_raw_message(inputs: dict[str, Any]) -> str:
    message = EmailMessage()
    message["To"] = str(inputs.get("recipients") or "")
    if inputs.get("cc"):
        message["Cc"] = str(inputs.get("cc"))
    if inputs.get("bcc"):
        message["Bcc"] = str(inputs.get("bcc"))
    message["Subject"] = str(inputs.get("subject") or "")
    message.set_content(str(inputs.get("body") or ""))
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return encoded.rstrip("=")


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
    executor = request_executor or (lambda url, method, req_headers, body=None: _request_json(url, req_headers, method=method, body=body))
    base_url = (record.get("base_url") or "").rstrip("/")
    kind = definition["execution"]["kind"]

    if kind == "google_gmail_list_messages":
        params = {"maxResults": _coerce_int(resolved_inputs.get("max_results"), 25)}
        labels = _csv_to_list(resolved_inputs.get("labels"))
        if labels:
            params["labelIds"] = labels
        query = str(resolved_inputs.get("search_query") or "").strip()
        if query:
            params["q"] = query
        query_string = urllib.parse.urlencode(params, doseq=True)
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages?{query_string}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        messages = payload.get("messages") or []
        return {"provider": provider_id, "activity": activity_id, "query": query or None, "messages": messages, "next_page_token": payload.get("nextPageToken"), "count": len(messages)}
    if kind == "google_gmail_get_message":
        message_id = urllib.parse.quote(str(resolved_inputs.get("message_id") or ""), safe="")
        fmt = urllib.parse.quote(str(resolved_inputs.get("format") or "full"), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/{message_id}?format={fmt}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "message": payload}
    if kind == "google_gmail_get_thread":
        thread_id = urllib.parse.quote(str(resolved_inputs.get("thread_id") or ""), safe="")
        fmt = urllib.parse.quote(str(resolved_inputs.get("format") or "full"), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/threads/{thread_id}?format={fmt}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "thread": payload}
    if kind == "google_gmail_send_email":
        body = {"raw": _gmail_raw_message(resolved_inputs)}
        if resolved_inputs.get("thread_id"):
            body["threadId"] = resolved_inputs["thread_id"]
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/send", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "message_id": payload.get("id"), "thread_id": payload.get("threadId"), "label_ids": payload.get("labelIds") or []}
    if kind == "google_gmail_create_draft":
        body = {"message": {"raw": _gmail_raw_message(resolved_inputs)}}
        if resolved_inputs.get("thread_id"):
            body["message"]["threadId"] = resolved_inputs["thread_id"]
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/drafts", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        message = payload.get("message") or {}
        return {"provider": provider_id, "activity": activity_id, "draft_id": payload.get("id"), "message_id": message.get("id"), "thread_id": message.get("threadId")}
    if kind == "google_gmail_modify_labels":
        message_id = urllib.parse.quote(str(resolved_inputs.get("message_id") or ""), safe="")
        body = {"addLabelIds": _csv_to_list(resolved_inputs.get("add_label_ids")), "removeLabelIds": _csv_to_list(resolved_inputs.get("remove_label_ids"))}
        status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages/{message_id}/modify", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "message_id": payload.get("id") or resolved_inputs.get("message_id"), "label_ids": payload.get("labelIds") or []}
    if kind in {"google_drive_list_files", "google_drive_search_files"}:
        max_results = _coerce_int(resolved_inputs.get("max_results"), 25)
        query_parts: list[str] = []
        if kind == "google_drive_list_files" and resolved_inputs.get("parent_id"):
            query_parts.append(f"'{resolved_inputs['parent_id']}' in parents")
        if kind == "google_drive_search_files":
            query_parts.append(str(resolved_inputs.get("search_query") or ""))
        query_parts.append("trashed = false")
        params = {
            "pageSize": max_results,
            "fields": _google_file_fields(),
            "q": " and ".join([part for part in query_parts if part]),
        }
        url = f"{base_url}/drive/v3/files?{urllib.parse.urlencode(params)}"
        status_code, payload = _execute_request(executor, url, "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        files = _normalize_drive_files(payload)
        return {"provider": provider_id, "activity": activity_id, "query": params.get("q") or None, "files": files, "next_page_token": (payload or {}).get("nextPageToken"), "count": len(files)}
    if kind == "google_drive_get_file_metadata":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}?fields=id,name,mimeType,parents,webViewLink,modifiedTime,size,permissions", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "file": payload}
    if kind == "google_drive_download_file":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        abuse = "true" if _coerce_bool(resolved_inputs.get("acknowledge_abuse")) else "false"
        return {"provider": provider_id, "activity": activity_id, "file_id": resolved_inputs.get("file_id"), "download_url": f"{base_url}/drive/v3/files/{file_id}?alt=media&acknowledgeAbuse={abuse}", "request_mode": "signed_connector_request"}
    if kind in {"google_drive_upload_file", "google_drive_create_file"}:
        metadata = {"name": resolved_inputs.get("file_name")}
        if resolved_inputs.get("parent_id"):
            metadata["parents"] = [resolved_inputs.get("parent_id")]
        if resolved_inputs.get("mime_type"):
            metadata["mimeType"] = resolved_inputs.get("mime_type")
        if kind == "google_drive_upload_file":
            content = {"source": resolved_inputs.get("upload_source"), "reference": resolved_inputs.get("upload_reference")}
        else:
            content = resolved_inputs.get("content")
        body = {"metadata": metadata, "content": content}
        status_code, payload = _execute_request(executor, f"{base_url}/upload/drive/v3/files?uploadType=multipart", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "file": payload, "source": resolved_inputs.get("upload_source")}
    if kind == "google_drive_update_file_metadata":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        body = {key: value for key, value in {"name": resolved_inputs.get("file_name"), "mimeType": resolved_inputs.get("mime_type")}.items() if value}
        status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}", "PATCH", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "file": payload}
    if kind == "google_drive_delete_file":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        status_code, _ = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}", "DELETE", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "file_id": resolved_inputs.get("file_id"), "deleted": True}
    if kind == "google_drive_move_file":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        params = urllib.parse.urlencode({"addParents": resolved_inputs.get("add_parent_id"), "removeParents": resolved_inputs.get("remove_parent_id") or "", "fields": "id,name,parents"})
        status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}?{params}", "PATCH", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "file": payload}
    if kind == "google_drive_manage_permissions":
        file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
        body = {"type": resolved_inputs.get("permission_type"), "role": resolved_inputs.get("role")}
        if resolved_inputs.get("email_address"):
            body["emailAddress"] = resolved_inputs.get("email_address")
        if resolved_inputs.get("domain"):
            body["domain"] = resolved_inputs.get("domain")
        status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}/permissions", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "permission": payload}
    if kind == "google_drive_get_storage_quota":
        status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/about?fields=storageQuota,user", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "storage_quota": (payload or {}).get("storageQuota") or {}, "user": (payload or {}).get("user") or {}}
    if kind == "google_calendar_upcoming_events":
        calendar_id = urllib.parse.quote(str(resolved_inputs.get("calendar_id") or "primary"), safe="")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        url = (
            f"{base_url}/calendar/v3/calendars/{calendar_id}/events?singleEvents=true&orderBy=startTime"
            f"&maxResults={limit}&timeMin={urllib.parse.quote(str((context or {}).get('timestamp') or ''))}"
        )
        status_code, payload = _execute_request(executor, url, "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        items = payload.get("items") or []
        events = [{"id": item.get("id"), "summary": item.get("summary"), "status": item.get("status"), "start": (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"), "end": (item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date"), "html_link": item.get("htmlLink")} for item in items]
        return {"provider": provider_id, "activity": activity_id, "calendar_id": resolved_inputs.get("calendar_id") or "primary", "events": events, "count": len(events)}
    if kind == "google_sheets_create_spreadsheet":
        body = {"properties": {"title": resolved_inputs.get("title")}}
        if resolved_inputs.get("sheet_name"):
            body["sheets"] = [{"properties": {"title": resolved_inputs.get("sheet_name")}}]
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "spreadsheet": payload}
    if kind == "google_sheets_get_spreadsheet_metadata":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "spreadsheet": payload}
    if kind == "google_sheets_read_range":
        spreadsheet_id = str(resolved_inputs.get("spreadsheet_id") or "")
        encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        values = payload.get("values") or []
        return {"provider": provider_id, "activity": activity_id, "spreadsheet_id": spreadsheet_id, "range": payload.get("range") or resolved_inputs.get("range"), "values": values, "row_count": len(values)}
    if kind == "google_sheets_update_range":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
        option = urllib.parse.quote(str(resolved_inputs.get("value_input_option") or "USER_ENTERED"), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}?valueInputOption={option}", "PUT", headers, {"values": resolved_inputs.get("values_payload")})
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "updated_range": payload.get("updatedRange"), "updated_rows": payload.get("updatedRows"), "updated_columns": payload.get("updatedColumns"), "updated_cells": payload.get("updatedCells")}
    if kind == "google_sheets_append_rows":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
        params = urllib.parse.urlencode({"valueInputOption": resolved_inputs.get("value_input_option") or "USER_ENTERED", "insertDataOption": resolved_inputs.get("insert_data_option") or "INSERT_ROWS"})
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:append?{params}", "POST", headers, {"values": resolved_inputs.get("values_payload")})
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "table_range": payload.get("tableRange"), "updates": payload.get("updates") or {}}
    if kind == "google_sheets_clear_range":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        encoded_range = urllib.parse.quote(str(resolved_inputs.get("range") or ""), safe="")
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values/{encoded_range}:clear", "POST", headers, {})
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "cleared_range": payload.get("clearedRange")}
    if kind == "google_sheets_batch_get_ranges":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        ranges = resolved_inputs.get("ranges") or []
        params = urllib.parse.urlencode([("ranges", str(item)) for item in ranges])
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values:batchGet?{params}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        value_ranges = payload.get("valueRanges") or []
        return {"provider": provider_id, "activity": activity_id, "value_ranges": value_ranges, "count": len(value_ranges)}
    if kind == "google_sheets_batch_update_ranges":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        body = {"valueInputOption": resolved_inputs.get("value_input_option") or "USER_ENTERED", "data": resolved_inputs.get("batch_payload") or []}
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate", "POST", headers, body)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "total_updated_cells": payload.get("totalUpdatedCells") or 0, "responses": payload.get("responses") or []}
    if kind == "google_sheets_copy_sheet":
        spreadsheet_id = urllib.parse.quote(str(resolved_inputs.get("spreadsheet_id") or ""), safe="")
        sheet_id = int(resolved_inputs.get("sheet_id") or 0)
        status_code, payload = _execute_request(executor, f"{base_url}/sheets/v4/spreadsheets/{spreadsheet_id}/sheets/{sheet_id}:copyTo", "POST", headers, {"destinationSpreadsheetId": resolved_inputs.get("destination_spreadsheet_id")})
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "sheet": payload}
    if kind == "github_list_open_pull_requests":
        owner = str(resolved_inputs.get("owner") or "")
        repo = str(resolved_inputs.get("repo") or "")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/pulls?state=open&per_page={limit}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        pulls = [{"number": item.get("number"), "title": item.get("title"), "state": item.get("state"), "html_url": item.get("html_url"), "author": (item.get("user") or {}).get("login")} for item in (payload or [])]
        return {"provider": provider_id, "activity": activity_id, "repository": f"{owner}/{repo}", "pull_requests": pulls, "count": len(pulls)}
    if kind == "github_list_assigned_issues":
        state = str(resolved_inputs.get("state") or "open")
        limit = _coerce_int(resolved_inputs.get("limit"), 10)
        status_code, payload = _execute_request(executor, f"{base_url}/issues?filter=assigned&state={urllib.parse.quote(state)}&per_page={limit}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        issues = [{"number": item.get("number"), "title": item.get("title"), "state": item.get("state"), "repository": (item.get("repository") or {}).get("full_name"), "html_url": item.get("html_url")} for item in (payload or []) if "pull_request" not in item]
        return {"provider": provider_id, "activity": activity_id, "issues": issues, "count": len(issues)}
    if kind == "github_repo_details":
        owner = str(resolved_inputs.get("owner") or "")
        repo = str(resolved_inputs.get("repo") or "")
        status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}", "GET", headers)
        if status_code >= 400:
            raise RuntimeError(f"Connector activity request failed with status {status_code}.")
        return {"provider": provider_id, "activity": activity_id, "repository": payload.get("full_name") or f"{owner}/{repo}", "default_branch": payload.get("default_branch"), "visibility": payload.get("visibility") or ("private" if payload.get("private") else "public"), "open_issues_count": int(payload.get("open_issues_count") or 0), "stars": int(payload.get("stargazers_count") or 0)}

    raise RuntimeError(f"Unsupported connector activity execution mapping '{kind}'.")
