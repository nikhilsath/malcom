"""
HTTP request action presets for workflow builder automation steps.

Presets provide templated request definitions with auto-filled method, endpoint, and payload
for common provider API operations. They eliminate the need for users to manually construct
destination URLs and payload templates.

Presets are provider-aware and can be filtered by connector provider.
"""

from __future__ import annotations

from typing import Any

from backend.database import fetch_all, fetch_one


class HttpRequestPreset:
    """HTTP request preset definition with templated fields."""

    def __init__(
        self,
        preset_id: str,
        provider_id: str,
        service: str,
        operation: str,
        label: str,
        description: str,
        http_method: str,
        endpoint_path_template: str,
        payload_template: str,
        query_params: dict[str, str] | None = None,
        required_scopes: list[str] | None = None,
        input_schema: list[dict[str, Any]] | None = None,
    ):
        """
        Args:
            preset_id: machine-readable preset identifier (e.g., 'gmail_list_messages_http')
            provider_id: provider name (e.g., 'google')
            service: service name (e.g., 'gmail', 'drive', 'sheets')
            operation: operation type (e.g., 'read', 'write')
            label: human-readable label shown in workflow builder
            description: what this preset does
            http_method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint_path_template: endpoint path; may contain {{variable}} placeholders
            payload_template: default JSON payload template; may contain {{variable}} placeholders
            query_params: default query parameters; may contain {{variable}} placeholders
            required_scopes: required Google API scopes
            input_schema: optional input field definitions for user customization of template variables
        """
        self.preset_id = preset_id
        self.provider_id = provider_id
        self.service = service
        self.operation = operation
        self.label = label
        self.description = description
        self.http_method = http_method
        self.endpoint_path_template = endpoint_path_template
        self.payload_template = payload_template
        self.query_params = query_params or {}
        self.required_scopes = required_scopes or []
        self.input_schema = input_schema or []

    def to_dict(self) -> dict[str, Any]:
        """Export preset as dict for API serialization."""
        return {
            "preset_id": self.preset_id,
            "provider_id": self.provider_id,
            "service": self.service,
            "operation": self.operation,
            "label": self.label,
            "description": self.description,
            "http_method": self.http_method,
            "endpoint_path_template": self.endpoint_path_template,
            "payload_template": self.payload_template,
            "query_params": self.query_params,
            "required_scopes": self.required_scopes,
            "input_schema": self.input_schema,
        }


# ── Google HTTP Presets ────────────────────────────────────────────────────

GMAIL_LIST_MESSAGES_PRESET = HttpRequestPreset(
    preset_id="gmail_list_messages_http",
    provider_id="google",
    service="gmail",
    operation="read",
    label="List emails",
    description="Retrieve Gmail messages with optional q, labelIds[], pageToken, and includeSpamTrash filters.",
    http_method="GET",
    endpoint_path_template="/gmail/v1/users/me/messages",
    payload_template="{}",
    query_params={"maxResults": "100"},
    required_scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    input_schema=[
        {
            "key": "q",
            "label": "q",
            "type": "string",
            "required": False,
            "help_text": "Gmail search query (for example: from:someone@example.com)",
            "placeholder": "from: or subject: or is:unread",
        },
        {
            "key": "labelIds",
            "label": "labelIds[]",
            "type": "string",
            "required": False,
            "help_text": "Comma-separated Gmail label IDs",
            "placeholder": "INBOX, SENT_MAIL, or custom label ID",
        },
        {
            "key": "maxResults",
            "label": "maxResults",
            "type": "integer",
            "required": False,
            "default": 100,
            "help_text": "Maximum number of messages to return. Gmail defaults to 100 and allows up to 500.",
        },
        {
            "key": "pageToken",
            "label": "pageToken",
            "type": "string",
            "required": False,
            "help_text": "Page token returned by the previous response.",
        },
        {
            "key": "includeSpamTrash",
            "label": "includeSpamTrash",
            "type": "boolean",
            "required": False,
            "default": False,
            "help_text": "Include messages from SPAM and TRASH in the results.",
        },
    ],
)

GMAIL_SEND_EMAIL_PRESET = HttpRequestPreset(
    preset_id="gmail_send_email_http",
    provider_id="google",
    service="gmail",
    operation="write",
    label="Send email",
    description="Compose and send an email message through Gmail.",
    http_method="POST",
    endpoint_path_template="/gmail/v1/users/me/messages/send",
    payload_template='{"raw": ""}',
    required_scopes=["https://www.googleapis.com/auth/gmail.send"],
    input_schema=[
        {
            "key": "to",
            "label": "To",
            "type": "string",
            "required": True,
            "help_text": "Recipient email address",
        },
        {
            "key": "subject",
            "label": "Subject",
            "type": "string",
            "required": True,
            "help_text": "Email subject line",
        },
        {
            "key": "body",
            "label": "Body",
            "type": "text",
            "required": True,
            "help_text": "Email body content (plain text)",
        },
    ],
)

DRIVE_LIST_FILES_PRESET = HttpRequestPreset(
    preset_id="drive_list_files_http",
    provider_id="google",
    service="drive",
    operation="read",
    label="List Drive files",
    description="Retrieve Google Drive files with pagination, corpus, and shared-drive query controls.",
    http_method="GET",
    endpoint_path_template="/drive/v3/files",
    payload_template="{}",
    query_params={"pageSize": "100", "fields": "files(id,name,mimeType,parents)"},
    required_scopes=["https://www.googleapis.com/auth/drive.readonly"],
    input_schema=[
        {
            "key": "q",
            "label": "q",
            "type": "string",
            "required": False,
            "help_text": "Drive search query (e.g., \"name='filename'\")",
            "placeholder": "name='file.txt' or mimeType='image/png'",
        },
        {
            "key": "corpora",
            "label": "corpora",
            "type": "select",
            "required": False,
            "options": ["user", "domain", "drive", "allDrives"],
            "default": "user",
            "help_text": "Where to search for files",
        },
        {
            "key": "pageSize",
            "label": "pageSize",
            "type": "integer",
            "required": False,
            "default": 100,
            "help_text": "Maximum number of files to return",
        },
        {
            "key": "pageToken",
            "label": "pageToken",
            "type": "string",
            "required": False,
        },
        {
            "key": "driveId",
            "label": "driveId",
            "type": "string",
            "required": False,
        },
        {
            "key": "includeItemsFromAllDrives",
            "label": "includeItemsFromAllDrives",
            "type": "boolean",
            "required": False,
            "default": False,
        },
        {
            "key": "orderBy",
            "label": "orderBy",
            "type": "string",
            "required": False,
            "placeholder": "folder,modifiedTime desc,name",
        },
        {
            "key": "spaces",
            "label": "spaces",
            "type": "string",
            "required": False,
            "default": "drive",
            "placeholder": "drive,appDataFolder",
        },
        {
            "key": "supportsAllDrives",
            "label": "supportsAllDrives",
            "type": "boolean",
            "required": False,
            "default": False,
        },
    ],
)

DRIVE_UPLOAD_FILE_PRESET = HttpRequestPreset(
    preset_id="drive_upload_file_http",
    provider_id="google",
    service="drive",
    operation="write",
    label="Upload file to Drive",
    description="Upload a file to Google Drive with optional folder destination and metadata.",
    http_method="POST",
    endpoint_path_template="/upload/drive/v3/files",
    payload_template='{"name": "", "parents": []}',
    query_params={"uploadType": "multipart"},
    required_scopes=["https://www.googleapis.com/auth/drive.file"],
    input_schema=[
        {
            "key": "name",
            "label": "File Name",
            "type": "string",
            "required": True,
            "help_text": "Name to give the uploaded file",
        },
        {
            "key": "parents",
            "label": "Parent Folder IDs (JSON array)",
            "type": "text",
            "required": False,
            "help_text": "JSON array of folder IDs where file should be placed",
            "placeholder": '["folder-id-here"]',
        },
        {
            "key": "description",
            "label": "File Description",
            "type": "string",
            "required": False,
            "help_text": "Optional description for the file",
        },
    ],
)

SHEETS_UPDATE_RANGE_PRESET = HttpRequestPreset(
    preset_id="sheets_update_range_http",
    provider_id="google",
    service="sheets",
    operation="write",
    label="Update Sheets range",
    description="Write values to a range in a Google Sheet.",
    http_method="PUT",
    endpoint_path_template="/sheets/v4/spreadsheets/{{spreadsheet_id}}/values/{{range_name}}",
    payload_template='{"values": [], "majorDimension": "ROWS"}',
    query_params={"valueInputOption": "USER_ENTERED"},
    required_scopes=["https://www.googleapis.com/auth/spreadsheets"],
    input_schema=[
        {
            "key": "spreadsheet_id",
            "label": "Spreadsheet ID",
            "type": "string",
            "required": True,
            "help_text": "Google Sheets ID (from URL)",
        },
        {
            "key": "range_name",
            "label": "Range Name",
            "type": "string",
            "required": True,
            "help_text": "Sheet and range (e.g., Sheet1!A1:C10)",
            "placeholder": "Sheet1!A1:B100",
        },
        {
            "key": "values",
            "label": "Values (JSON array of arrays)",
            "type": "text",
            "required": True,
            "help_text": "Row-major JSON array of values",
            "placeholder": '[["A1", "B1"], ["A2", "B2"]]',
        },
        {
            "key": "valueInputOption",
            "label": "valueInputOption",
            "type": "select",
            "required": False,
            "options": ["RAW", "USER_ENTERED"],
            "default": "USER_ENTERED",
        },
        {
            "key": "includeValuesInResponse",
            "label": "includeValuesInResponse",
            "type": "boolean",
            "required": False,
            "default": False,
        },
        {
            "key": "responseValueRenderOption",
            "label": "responseValueRenderOption",
            "type": "select",
            "required": False,
            "options": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
        },
        {
            "key": "responseDateTimeRenderOption",
            "label": "responseDateTimeRenderOption",
            "type": "select",
            "required": False,
            "options": ["SERIAL_NUMBER", "FORMATTED_STRING"],
        },
    ],
)

SHEETS_READ_RANGE_PRESET = HttpRequestPreset(
    preset_id="sheets_read_range_http",
    provider_id="google",
    service="sheets",
    operation="read",
    label="Read Sheets range",
    description="Read values from a range in a Google Sheet.",
    http_method="GET",
    endpoint_path_template="/sheets/v4/spreadsheets/{{spreadsheet_id}}/values/{{range_name}}",
    payload_template="{}",
    required_scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    input_schema=[
        {
            "key": "spreadsheet_id",
            "label": "Spreadsheet ID",
            "type": "string",
            "required": True,
            "help_text": "Google Sheets ID (from URL)",
        },
        {
            "key": "range_name",
            "label": "Range Name",
            "type": "string",
            "required": True,
            "help_text": "Sheet and range (e.g., Sheet1!A1:C10)",
            "placeholder": "Sheet1!A1:B100",
        },
        {
            "key": "majorDimension",
            "label": "majorDimension",
            "type": "select",
            "required": False,
            "options": ["ROWS", "COLUMNS"],
        },
        {
            "key": "valueRenderOption",
            "label": "valueRenderOption",
            "type": "select",
            "required": False,
            "options": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
        },
        {
            "key": "dateTimeRenderOption",
            "label": "dateTimeRenderOption",
            "type": "select",
            "required": False,
            "options": ["SERIAL_NUMBER", "FORMATTED_STRING"],
        },
    ],
)

# ── GitHub HTTP Presets ───────────────────────────────────────────────────

GITHUB_LIST_REPOSITORY_ISSUES_PRESET = HttpRequestPreset(
    preset_id="issues_list_repository_http",
    provider_id="github",
    service="issues",
    operation="read",
    label="List repository issues",
    description="Retrieve repository issues with optional state and label filters.",
    http_method="GET",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/issues",
    payload_template="{}",
    query_params={"state": "open", "per_page": "20"},
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "state", "label": "state", "type": "select", "required": False, "options": ["open", "closed", "all"], "default": "open"},
        {"key": "labels", "label": "labels", "type": "string", "required": False, "placeholder": "bug,triage"},
        {"key": "per_page", "label": "per_page", "type": "integer", "required": False, "default": 20},
    ],
)

GITHUB_CREATE_ISSUE_PRESET = HttpRequestPreset(
    preset_id="issues_create_http",
    provider_id="github",
    service="issues",
    operation="write",
    label="Create issue",
    description="Create a new GitHub issue in a repository.",
    http_method="POST",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/issues",
    payload_template='{"title":"{{title}}","body":"{{body}}"}',
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "title", "label": "Issue title", "type": "string", "required": True},
        {"key": "body", "label": "Issue body", "type": "text", "required": False},
    ],
)

GITHUB_ADD_ISSUE_COMMENT_PRESET = HttpRequestPreset(
    preset_id="issues_add_comment_http",
    provider_id="github",
    service="issues",
    operation="write",
    label="Add issue comment",
    description="Add a comment to a GitHub issue.",
    http_method="POST",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/issues/{{issue_number}}/comments",
    payload_template='{"body":"{{body}}"}',
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "issue_number", "label": "Issue number", "type": "integer", "required": True},
        {"key": "body", "label": "Comment body", "type": "text", "required": True},
    ],
)

GITHUB_LIST_OPEN_PULL_REQUESTS_PRESET = HttpRequestPreset(
    preset_id="pulls_list_open_http",
    provider_id="github",
    service="pulls",
    operation="read",
    label="List open pull requests",
    description="Retrieve open pull requests for a repository.",
    http_method="GET",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/pulls",
    payload_template="{}",
    query_params={"state": "open", "per_page": "20"},
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "per_page", "label": "per_page", "type": "integer", "required": False, "default": 20},
    ],
)

GITHUB_LIST_REPOSITORY_WORKFLOWS_PRESET = HttpRequestPreset(
    preset_id="actions_list_workflows_http",
    provider_id="github",
    service="actions",
    operation="read",
    label="List workflows",
    description="Retrieve Actions workflows available in a repository.",
    http_method="GET",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/actions/workflows",
    payload_template="{}",
    query_params={"per_page": "20"},
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "per_page", "label": "per_page", "type": "integer", "required": False, "default": 20},
    ],
)

GITHUB_LIST_WORKFLOW_RUNS_PRESET = HttpRequestPreset(
    preset_id="actions_list_workflow_runs_http",
    provider_id="github",
    service="actions",
    operation="read",
    label="List workflow runs",
    description="Retrieve workflow runs with optional branch, event, and status filters.",
    http_method="GET",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/actions/runs",
    payload_template="{}",
    query_params={"per_page": "20"},
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "branch", "label": "branch", "type": "string", "required": False},
        {"key": "event", "label": "event", "type": "string", "required": False},
        {"key": "status", "label": "status", "type": "string", "required": False},
        {"key": "per_page", "label": "per_page", "type": "integer", "required": False, "default": 20},
    ],
)

GITHUB_TRIGGER_WORKFLOW_DISPATCH_PRESET = HttpRequestPreset(
    preset_id="actions_trigger_workflow_dispatch_http",
    provider_id="github",
    service="actions",
    operation="write",
    label="Trigger workflow dispatch",
    description="Dispatch a workflow_dispatch event for a GitHub Actions workflow.",
    http_method="POST",
    endpoint_path_template="/repos/{{owner}}/{{repo}}/actions/workflows/{{workflow_id}}/dispatches",
    payload_template='{"ref":"{{ref}}","inputs":{}}',
    required_scopes=["repo"],
    input_schema=[
        {"key": "owner", "label": "Repository owner", "type": "string", "required": True},
        {"key": "repo", "label": "Repository name", "type": "string", "required": True},
        {"key": "workflow_id", "label": "Workflow ID or file name", "type": "string", "required": True},
        {"key": "ref", "label": "Git ref", "type": "string", "required": True, "placeholder": "main"},
        {"key": "inputs_payload", "label": "Inputs JSON", "type": "text", "required": False, "placeholder": "{}"},
    ],
)

# ── Preset Catalog ────────────────────────────────────────────────────────

GOOGLE_HTTP_PRESETS = (
    GMAIL_LIST_MESSAGES_PRESET,
    GMAIL_SEND_EMAIL_PRESET,
    DRIVE_LIST_FILES_PRESET,
    DRIVE_UPLOAD_FILE_PRESET,
    SHEETS_UPDATE_RANGE_PRESET,
    SHEETS_READ_RANGE_PRESET,
)

GITHUB_HTTP_PRESETS = (
    GITHUB_LIST_REPOSITORY_ISSUES_PRESET,
    GITHUB_CREATE_ISSUE_PRESET,
    GITHUB_ADD_ISSUE_COMMENT_PRESET,
    GITHUB_LIST_OPEN_PULL_REQUESTS_PRESET,
    GITHUB_LIST_REPOSITORY_WORKFLOWS_PRESET,
    GITHUB_LIST_WORKFLOW_RUNS_PRESET,
    GITHUB_TRIGGER_WORKFLOW_DISPATCH_PRESET,
)

DEFAULT_HTTP_PRESET_CATALOG = (
    *GOOGLE_HTTP_PRESETS,
    *GITHUB_HTTP_PRESETS,
)


def _default_http_preset_catalog() -> list[dict[str, Any]]:
    return [preset.to_dict() for preset in DEFAULT_HTTP_PRESET_CATALOG]


def _decode_json_field(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            import json

            return json.loads(value)
        except Exception:
            return fallback
    return fallback


def _serialize_http_preset_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = _decode_json_field(row.get("metadata_json"), {})
    return {
        "preset_id": metadata.get("preset_id") or str(row.get("endpoint_id") or "").rsplit(":", 1)[-1],
        "provider_id": row["provider_id"],
        "service": row["service"],
        "operation": row["operation_type"],
        "label": row["label"],
        "description": row.get("description") or "",
        "http_method": row["http_method"],
        "endpoint_path_template": row["endpoint_path_template"],
        "payload_template": row.get("payload_template") or "",
        "query_params": _decode_json_field(row.get("query_params_json"), {}),
        "required_scopes": _decode_json_field(row.get("required_scopes_json"), []),
        "input_schema": _decode_json_field(row.get("input_schema_json"), []),
    }


def _preset_from_payload(payload: dict[str, Any]) -> HttpRequestPreset:
    return HttpRequestPreset(
        preset_id=payload["preset_id"],
        provider_id=payload["provider_id"],
        service=payload["service"],
        operation=payload["operation"],
        label=payload["label"],
        description=payload["description"],
        http_method=payload["http_method"],
        endpoint_path_template=payload["endpoint_path_template"],
        payload_template=payload["payload_template"],
        query_params=payload.get("query_params") or {},
        required_scopes=payload.get("required_scopes") or [],
        input_schema=payload.get("input_schema") or [],
    )


def list_http_preset_catalog(connection: Any | None = None) -> list[dict[str, Any]]:
    if connection is None:
        return _default_http_preset_catalog()

    rows = fetch_all(
        connection,
        """
        SELECT endpoint_id, provider_id, service, operation_type, label, description,
               http_method, endpoint_path_template, payload_template, query_params_json,
               required_scopes_json, input_schema_json, metadata_json
        FROM connector_endpoint_definitions
        WHERE endpoint_kind = 'http_preset'
        ORDER BY provider_id ASC, service ASC, operation_type ASC, label ASC
        """,
    )
    if not rows:
        return _default_http_preset_catalog()
    return [_serialize_http_preset_row(dict(row)) for row in rows]


def get_http_presets_by_provider(provider_id: str, connection: Any | None = None) -> list[HttpRequestPreset]:
    """Get all HTTP presets available for a given provider."""
    if connection is None:
        return [p for p in DEFAULT_HTTP_PRESET_CATALOG if p.provider_id == provider_id]
    return [
        _preset_from_payload(payload)
        for payload in list_http_preset_catalog(connection)
        if payload["provider_id"] == provider_id
    ]


def get_http_preset(provider_id: str, preset_id: str, connection: Any | None = None) -> HttpRequestPreset | None:
    """Get a single HTTP preset by provider and preset ID."""
    if connection is not None:
        row = fetch_one(
            connection,
            """
            SELECT endpoint_id, provider_id, service, operation_type, label, description,
                   http_method, endpoint_path_template, payload_template, query_params_json,
                   required_scopes_json, input_schema_json, metadata_json
            FROM connector_endpoint_definitions
            WHERE endpoint_kind = 'http_preset' AND provider_id = ? AND endpoint_id = ?
            LIMIT 1
            """,
            (provider_id, f"http_preset:{provider_id}:{preset_id}"),
        )
        if row is not None:
            return _preset_from_payload(_serialize_http_preset_row(dict(row)))

    for preset in DEFAULT_HTTP_PRESET_CATALOG:
        if preset.provider_id == provider_id and preset.preset_id == preset_id:
            return preset
    return None


__all__ = [
    "HttpRequestPreset",
    "DEFAULT_HTTP_PRESET_CATALOG",
    "list_http_preset_catalog",
    "get_http_presets_by_provider",
    "get_http_preset",
]
