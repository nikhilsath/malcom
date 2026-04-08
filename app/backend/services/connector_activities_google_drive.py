from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, UPLOAD_SOURCE_OPTIONS, _field, _output
from .connector_activities_runtime import (
    RequestExecutor,
    _coerce_bool,
    _coerce_int,
    _execute_request,
    _google_file_fields,
    _normalize_drive_files,
)


GOOGLE_DRIVE_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="drive_list_files",
        service="drive",
        operation_type="read",
        label="List files",
        description="List Google Drive files with pagination, corpus, and shared-drive filters.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(
            _field("parent_id", "Folder / parent ID", "string", required=False, help_text="Optional folder to list from."),
            _field("max_results", "pageSize", "integer", required=False, default=100),
            _field("page_token", "pageToken", "string", required=False),
            _field("corpora", "corpora", "select", required=False, default="user", options=["user", "domain", "drive", "allDrives"]),
            _field("drive_id", "driveId", "string", required=False),
            _field("include_items_from_all_drives", "includeItemsFromAllDrives", "boolean", required=False, default=False),
            _field("order_by", "orderBy", "string", required=False, placeholder="folder,modifiedTime desc,name"),
            _field("spaces", "spaces", "string", required=False, default="drive", placeholder="drive,appDataFolder"),
            _field("supports_all_drives", "supportsAllDrives", "boolean", required=False, default=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("files", "Files", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("incomplete_search", "Incomplete search", "boolean"),
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
        description="Search Google Drive files with Drive query syntax plus pagination and shared-drive filters.",
        required_scopes=("https://www.googleapis.com/auth/drive.metadata.readonly",),
        input_schema=(
            _field("search_query", "q", "string", required=True, placeholder="name contains 'invoice' and trashed = false"),
            _field("max_results", "pageSize", "integer", required=False, default=100),
            _field("page_token", "pageToken", "string", required=False),
            _field("corpora", "corpora", "select", required=False, default="user", options=["user", "domain", "drive", "allDrives"]),
            _field("drive_id", "driveId", "string", required=False),
            _field("include_items_from_all_drives", "includeItemsFromAllDrives", "boolean", required=False, default=False),
            _field("order_by", "orderBy", "string", required=False, placeholder="folder,modifiedTime desc,name"),
            _field("spaces", "spaces", "string", required=False, default="drive", placeholder="drive,appDataFolder"),
            _field("supports_all_drives", "supportsAllDrives", "boolean", required=False, default=False),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("query", "Query", "string"),
            _output("files", "Files", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("incomplete_search", "Incomplete search", "boolean"),
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
    max_results = _coerce_int(_first_populated_input(resolved_inputs, "max_results", "pageSize"), 100)
    query_parts: list[str] = []
    if not search_mode and resolved_inputs.get("parent_id"):
        query_parts.append(f"'{resolved_inputs['parent_id']}' in parents")
    if search_mode:
        query_parts.append(str(_first_populated_input(resolved_inputs, "search_query", "q") or ""))
    query_parts.append("trashed = false")
    params = {
        "pageSize": max_results,
        "fields": _google_file_fields(),
        "q": " and ".join([part for part in query_parts if part]),
    }
    page_token = str(_first_populated_input(resolved_inputs, "page_token", "pageToken") or "").strip()
    if page_token:
        params["pageToken"] = page_token
    corpora = str(_first_populated_input(resolved_inputs, "corpora") or "").strip()
    if corpora:
        params["corpora"] = corpora
    drive_id = str(_first_populated_input(resolved_inputs, "drive_id", "driveId") or "").strip()
    if drive_id:
        params["driveId"] = drive_id
    include_items_from_all_drives = _first_populated_input(
        resolved_inputs,
        "include_items_from_all_drives",
        "includeItemsFromAllDrives",
    )
    if include_items_from_all_drives is not None:
        params["includeItemsFromAllDrives"] = "true" if _coerce_bool(include_items_from_all_drives) else "false"
    order_by = str(_first_populated_input(resolved_inputs, "order_by", "orderBy") or "").strip()
    if order_by:
        params["orderBy"] = order_by
    spaces = str(_first_populated_input(resolved_inputs, "spaces") or "").strip()
    if spaces:
        params["spaces"] = spaces
    supports_all_drives = _first_populated_input(resolved_inputs, "supports_all_drives", "supportsAllDrives")
    if supports_all_drives is not None:
        params["supportsAllDrives"] = "true" if _coerce_bool(supports_all_drives) else "false"
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
        "incomplete_search": (payload or {}).get("incompleteSearch"),
        "count": len(files),
    }


def google_drive_list_files(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    return _google_drive_list_or_search_files(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, search_mode=False)


def google_drive_search_files(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    return _google_drive_list_or_search_files(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, search_mode=True)


def google_drive_get_file_metadata(
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


def google_drive_download_file(
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
    content = {"source": resolved_inputs.get("upload_source"), "reference": resolved_inputs.get("upload_reference")} if upload_mode else resolved_inputs.get("content")
    body = {"metadata": metadata, "content": content}
    status_code, payload = _execute_request(executor, f"{base_url}/upload/drive/v3/files?uploadType=multipart", "POST", headers, body)
    _raise_for_status(status_code)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "file": payload,
        "source": resolved_inputs.get("upload_source"),
    }


def google_drive_upload_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    return _google_drive_upload_or_create_file(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, upload_mode=True)


def google_drive_create_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    return _google_drive_upload_or_create_file(provider_id, activity_id, resolved_inputs, base_url, headers, context, executor, upload_mode=False)


def google_drive_update_file_metadata(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    body = {key: value for key, value in {"name": resolved_inputs.get("file_name"), "mimeType": resolved_inputs.get("mime_type")}.items() if value}
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}", "PATCH", headers, body)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file": payload}


def google_drive_delete_file(
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


def google_drive_move_file(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    file_id = urllib.parse.quote(str(resolved_inputs.get("file_id") or ""), safe="")
    params = urllib.parse.urlencode({"addParents": resolved_inputs.get("add_parent_id"), "removeParents": resolved_inputs.get("remove_parent_id") or "", "fields": "id,name,parents"})
    status_code, payload = _execute_request(executor, f"{base_url}/drive/v3/files/{file_id}?{params}", "PATCH", headers)
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "file": payload}


def google_drive_manage_permissions(
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


def google_drive_get_storage_quota(
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


GOOGLE_DRIVE_HANDLER_REGISTRY = {
    "google_drive_list_files": google_drive_list_files,
    "google_drive_search_files": google_drive_search_files,
    "google_drive_get_file_metadata": google_drive_get_file_metadata,
    "google_drive_download_file": google_drive_download_file,
    "google_drive_upload_file": google_drive_upload_file,
    "google_drive_create_file": google_drive_create_file,
    "google_drive_update_file_metadata": google_drive_update_file_metadata,
    "google_drive_delete_file": google_drive_delete_file,
    "google_drive_move_file": google_drive_move_file,
    "google_drive_manage_permissions": google_drive_manage_permissions,
    "google_drive_get_storage_quota": google_drive_get_storage_quota,
}
