from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Any, Callable

from fastapi import HTTPException, status

from backend.schemas import OutgoingAuthConfig

DatabaseConnection = Any
RequestExecutor = Callable[..., tuple[int, Any]]
ConnectorActivityHandler = Callable[
    [str, str, dict[str, Any], str, dict[str, str], dict[str, Any] | None, RequestExecutor],
    dict[str, Any],
]


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
            body_bytes = response.read()
            if not body_bytes:
                return response.status, None
            body_text = body_bytes.decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(body_text)
            except json.JSONDecodeError:
                # Preserve non-JSON payloads (for example archives) as base64 bytes.
                return response.status, {
                    "_raw_bytes_b64": base64.b64encode(body_bytes).decode("ascii"),
                    "_raw_content_type": response.headers.get("Content-Type", ""),
                }
    except urllib.error.HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            parsed = {"message": body_text[:500]}
        return error.code, parsed
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach connector activity endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Connector activity endpoint returned malformed JSON.",
        ) from error


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(str(value or default).strip())
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_inputs(
    input_schema: list[dict[str, Any]],
    configured_inputs: dict[str, Any] | None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
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


def _get_connector_activity_context(
    connection: DatabaseConnection,
    *,
    connector_id: str,
    root_dir: Any,
) -> tuple[dict[str, Any], dict[str, str]]:
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


# Broader Google OAuth scopes that implicitly satisfy narrower ones.
# Key = broader scope; value = set of narrower scopes it covers.
_GOOGLE_SCOPE_IMPLIES: dict[str, set[str]] = {
    "https://www.googleapis.com/auth/spreadsheets": {
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    },
    "https://www.googleapis.com/auth/drive": {
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    },
    "https://www.googleapis.com/auth/drive.readonly": {
        "https://www.googleapis.com/auth/drive.metadata.readonly",
    },
    "https://www.googleapis.com/auth/gmail.modify": {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    },
    "https://www.googleapis.com/auth/gmail.compose": {
        "https://www.googleapis.com/auth/gmail.send",
    },
}


def _expand_granted_scopes(granted: set[str]) -> set[str]:
    """Return *granted* plus any narrower scopes implied by broader ones the connector holds."""
    expanded = set(granted)
    for broad_scope, implied in _GOOGLE_SCOPE_IMPLIES.items():
        if broad_scope in granted:
            expanded |= implied
    return expanded


def get_missing_connector_activity_scopes(
    connector_record: dict[str, Any] | None,
    activity_definition: dict[str, Any] | None,
) -> list[str]:
    if connector_record is None or activity_definition is None:
        return []
    granted = _expand_granted_scopes(set(connector_record.get("scopes") or []))
    return [scope for scope in activity_definition.get("required_scopes", []) if scope not in granted]


def _execute_request(
    executor: RequestExecutor,
    url: str,
    method: str,
    headers: dict[str, str],
    body: Any | None = None,
) -> tuple[int, Any]:
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
    from .connector_activities_catalog import get_connector_activity_definition
    from .connector_activities_github import GITHUB_HANDLER_REGISTRY
    from .connector_activities_google import GOOGLE_HANDLER_REGISTRY

    record, headers = _get_connector_activity_context(connection, connector_id=connector_id, root_dir=root_dir)
    provider_id = record.get("provider") or ""
    definition = get_connector_activity_definition(provider_id, activity_id)
    if definition is None:
        raise RuntimeError(f"Connector provider '{provider_id}' does not support activity '{activity_id}'.")

    missing_scopes = get_missing_connector_activity_scopes(record, definition)
    if missing_scopes:
        raise RuntimeError(f"Connector is missing required scopes: {', '.join(missing_scopes)}.")

    runtime_context = dict(context or {})
    runtime_context.setdefault("_root_dir", str(root_dir))
    resolved_inputs = _resolve_inputs(definition["input_schema"], inputs, runtime_context)
    executor = request_executor or (
        lambda url, method, req_headers, body=None: _request_json(url, req_headers, method=method, body=body)
    )
    base_url = (record.get("base_url") or "").rstrip("/")
    kind = definition["execution"]["kind"]
    handler_registry: dict[str, ConnectorActivityHandler] = {
        **GOOGLE_HANDLER_REGISTRY,
        **GITHUB_HANDLER_REGISTRY,
    }
    handler = handler_registry.get(kind)
    if handler is None:
        raise RuntimeError(f"Unsupported connector activity execution mapping '{kind}'.")
    return handler(provider_id, activity_id, resolved_inputs, base_url, headers, runtime_context, executor)
