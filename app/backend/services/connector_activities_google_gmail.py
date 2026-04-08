from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, VALUE_SOURCE_HINT, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_bool, _coerce_int, _csv_to_list, _execute_request, _gmail_raw_message


GOOGLE_GMAIL_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="google",
        activity_id="gmail_list_messages",
        service="gmail",
        operation_type="read",
        label="List emails",
        description="List Gmail messages with optional q, labelIds[], pageToken, and includeSpamTrash filters.",
        required_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
        input_schema=(
            _field("q", "q", "string", required=False, placeholder="from:alerts@example.com is:unread", help_text=VALUE_SOURCE_HINT),
            _field("labels", "labelIds[]", "string", required=False, placeholder="INBOX,IMPORTANT", help_text="Comma-separated Gmail label IDs.", value_hint="csv"),
            _field("max_results", "maxResults", "integer", required=False, default=100, help_text="Defaults to 100. Gmail allows up to 500."),
            _field("page_token", "pageToken", "string", required=False, help_text=VALUE_SOURCE_HINT),
            _field("include_spam_trash", "includeSpamTrash", "boolean", required=False, default=False),
        ),
        output_schema=(
            _output("messages", "Messages", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("result_size_estimate", "Result size estimate", "integer"),
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
            _field("labels", "labelIds[]", "string", required=False, placeholder="INBOX,UNREAD", help_text="Optional comma-separated label IDs."),
            _field("max_results", "maxResults", "integer", required=False, default=100, help_text="Defaults to 100. Gmail allows up to 500."),
        ),
        output_schema=(
            _output("query", "Query", "string"),
            _output("messages", "Messages", "array"),
            _output("next_page_token", "Next page token", "string"),
            _output("result_size_estimate", "Result size estimate", "integer"),
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
            _field("metadata_headers", "metadataHeaders[]", "string", required=False, placeholder="Subject,From,To", help_text="Optional comma-separated header names when format is metadata.", value_hint="csv"),
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
            _field("metadata_headers", "metadataHeaders[]", "string", required=False, placeholder="Subject,From,To", help_text="Optional comma-separated header names when format is metadata.", value_hint="csv"),
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


def google_gmail_list_messages(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    params = {"maxResults": _coerce_int(_first_populated_input(resolved_inputs, "max_results", "maxResults"), 100)}
    labels = _csv_to_list(_first_populated_input(resolved_inputs, "labels", "label_ids", "labelIds"))
    if labels:
        params["labelIds"] = labels
    page_token = str(_first_populated_input(resolved_inputs, "page_token", "pageToken") or "").strip()
    if page_token:
        params["pageToken"] = page_token
    query = str(_first_populated_input(resolved_inputs, "q", "search_query") or "").strip()
    if query:
        params["q"] = query
    include_spam_trash = _first_populated_input(resolved_inputs, "include_spam_trash", "includeSpamTrash")
    if include_spam_trash is not None:
        params["includeSpamTrash"] = "true" if _coerce_bool(include_spam_trash) else "false"
    query_string = urllib.parse.urlencode(params, doseq=True)
    status_code, payload = _execute_request(executor, f"{base_url}/gmail/v1/users/me/messages?{query_string}", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    messages = payload.get("messages") or []
    result = {
        "provider": provider_id,
        "activity": activity_id,
        "messages": messages,
        "next_page_token": payload.get("nextPageToken"),
        "result_size_estimate": payload.get("resultSizeEstimate"),
    }
    if activity_id == "gmail_search_messages":
        result["query"] = query or None
    return result


def google_gmail_get_message(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    message_id = urllib.parse.quote(str(resolved_inputs.get("message_id") or ""), safe="")
    params: dict[str, Any] = {"format": str(resolved_inputs.get("format") or "full")}
    metadata_headers = _csv_to_list(_first_populated_input(resolved_inputs, "metadata_headers", "metadataHeaders"))
    if metadata_headers:
        params["metadataHeaders"] = metadata_headers
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/gmail/v1/users/me/messages/{message_id}?{urllib.parse.urlencode(params, doseq=True)}",
        "GET",
        headers,
    )
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "message": payload}


def google_gmail_get_thread(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    thread_id = urllib.parse.quote(str(resolved_inputs.get("thread_id") or ""), safe="")
    params: dict[str, Any] = {"format": str(resolved_inputs.get("format") or "full")}
    metadata_headers = _csv_to_list(_first_populated_input(resolved_inputs, "metadata_headers", "metadataHeaders"))
    if metadata_headers:
        params["metadataHeaders"] = metadata_headers
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/gmail/v1/users/me/threads/{thread_id}?{urllib.parse.urlencode(params, doseq=True)}",
        "GET",
        headers,
    )
    _raise_for_status(status_code)
    return {"provider": provider_id, "activity": activity_id, "thread": payload}


def google_gmail_send_email(
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


def google_gmail_create_draft(
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


def google_gmail_modify_labels(
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


GOOGLE_GMAIL_HANDLER_REGISTRY = {
    "google_gmail_list_messages": google_gmail_list_messages,
    "google_gmail_get_message": google_gmail_get_message,
    "google_gmail_get_thread": google_gmail_get_thread,
    "google_gmail_send_email": google_gmail_send_email,
    "google_gmail_create_draft": google_gmail_create_draft,
    "google_gmail_modify_labels": google_gmail_modify_labels,
}
