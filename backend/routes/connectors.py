from __future__ import annotations

import urllib.parse
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from backend.schemas import *
from backend.services.support import *
from backend.runtime import parse_iso_datetime
from backend.services.connectors import _provider_display_name
from backend.services.http_presets import list_http_preset_catalog
from backend.services.connector_google_oauth_client import (
    revoke_google_token,
)
from backend.services.connector_oauth import (
    start_connector_oauth as service_start_connector_oauth,
    complete_connector_oauth as service_complete_connector_oauth,
    refresh_oauth_token as service_refresh_oauth_token,
)
from backend.services.connector_oauth_provider_clients import (
    revoke_notion_token,
    revoke_trello_token,
)
from backend.services.connector_health import (
    _google_probe_failure_message,
    _probe_google_access_token,
    _probe_github_access_token,
    _probe_notion_access_token,
    _probe_trello_credentials,
    _inspect_github_scopes_from_payload,
)
from backend.services.connector_repositories import _list_github_repositories

router = APIRouter()


@router.get("/api/v1/connectors/activity-catalog", response_model=list[ConnectorActivityDefinitionResponse])
def list_connector_activity_catalog(request: Request) -> list[ConnectorActivityDefinitionResponse]:
    connection = get_connection(request)
    return [ConnectorActivityDefinitionResponse(**item) for item in build_connector_activity_catalog(connection)]


@router.get("/api/v1/connectors/http-presets")
def list_http_presets(request: Request) -> list[dict[str, Any]]:
    """List all available HTTP request presets for workflow builder automation steps.
    """
    connection = get_connection(request)
    return list_http_preset_catalog(connection)


@router.get("/api/v1/connectors", response_model=ConnectorSettingsResponse)
def list_connectors(request: Request) -> ConnectorSettingsResponse:
    # Data lineage: connectors table is the authoritative source. Records are read via
    # get_stored_connector_settings() and sanitized (secrets masked) before response.
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    raw_settings = get_stored_connector_settings(connection)
    return ConnectorSettingsResponse(
        **sanitize_connector_settings_for_response(raw_settings, protection_secret, connection=connection)
    )


@router.post("/api/v1/connectors", response_model=ConnectorRecordResponse, status_code=status.HTTP_201_CREATED)
def create_connector(payload: ConnectorCreateRequest, request: Request) -> ConnectorRecordResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    create_payload = payload.model_dump(exclude_unset=True)
    provider = canonicalize_connector_provider(create_payload.get("provider"))
    create_payload = _inspect_github_scopes_from_payload(provider=provider or "", changes=create_payload)

    try:
        record = create_connector_record(
            connection,
            create_payload,
            protection_secret=protection_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorRecordResponse(**sanitized)


@router.patch("/api/v1/connectors/auth-policy", response_model=ConnectorSettingsResponse)
def patch_connector_auth_policy(payload: ConnectorAuthPolicyUpdateRequest, request: Request) -> ConnectorSettingsResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    write_connector_auth_policy(connection, payload.auth_policy.model_dump())
    raw_settings = get_stored_connector_settings(connection)
    return ConnectorSettingsResponse(
        **sanitize_connector_settings_for_response(raw_settings, protection_secret, connection=connection)
    )


@router.patch("/api/v1/connectors/{connector_id}", response_model=ConnectorRecordResponse)
def patch_connector(connector_id: str, payload: ConnectorUpdateRequest, request: Request) -> ConnectorRecordResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    changes = payload.model_dump(exclude_unset=True)

    existing_record = find_stored_connector_record(connection, connector_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")
    provider = canonicalize_connector_provider(existing_record.get("provider")) or ""
    changes = _inspect_github_scopes_from_payload(provider=provider, changes=changes)

    try:
        if changes:
            record = update_connector_record(
                connection,
                connector_id,
                changes,
                protection_secret=protection_secret,
            )
        else:
            record = existing_record
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.") from exc

    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorRecordResponse(**sanitized)


@router.delete("/api/v1/connectors/{connector_id}", response_model=ConnectorDeleteResponse)
def remove_connector(connector_id: str, request: Request) -> ConnectorDeleteResponse:
    connection = get_connection(request)

    try:
        deleted_record = delete_connector_record(connection, connector_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.") from exc

    return ConnectorDeleteResponse(ok=True, message="Connector deleted.", connector_id=deleted_record["id"])


@router.get("/api/v1/connectors/{connector_id}/github/repositories")
def list_github_connector_repositories(connector_id: str, request: Request) -> dict[str, Any]:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    provider = canonicalize_connector_provider(record.get("provider"))
    if provider != "github":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository listing is only available for GitHub connectors.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    access_token = secret_map.get("access_token") or ""
    if not access_token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="GitHub connector is missing an access token.")

    repositories = _list_github_repositories(access_token=access_token)
    return {"repositories": repositories}

@router.post("/api/v1/connectors/{connector_id}/revoke", response_model=ConnectorActionResponse)
def revoke_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = _provider_display_name(provider)
    auth_config = record.get("auth_config") or {}
    message = f"{provider_name} connector revoked and credentials cleared."
    if provider == "google":
        token = secret_map.get("access_token") or secret_map.get("refresh_token") or ""
        if token:
            revoke_google_token(token=token)
    elif provider == "github":
        message = "GitHub credentials cleared locally. Save a new personal access token to reconnect."
    elif provider == "notion":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if token and client_id and client_secret:
            revoke_notion_token(token=token, client_id=client_id, client_secret=client_secret)
        else:
            message = "Notion credentials cleared locally. Configure a client secret to revoke the upstream token as well."
    elif provider == "trello":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        if token and client_id:
            revoke_trello_token(token=token, client_id=client_id)
            message = "Trello connector revoked and credentials cleared."
        else:
            message = "Trello credentials cleared locally. Configure a client ID to revoke the upstream token as well."

    now = utc_now_iso()
    record["status"] = "revoked"
    record["updated_at"] = now
    record["auth_config"] = {
        **record.get("auth_config", {}),
        "access_token_input": None,
        "refresh_token_input": None,
        "client_secret_input": None,
        "api_key_input": None,
        "password_input": None,
        "header_value_input": None,
        "has_refresh_token": False,
        "clear_credentials": True,
    }
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    if isinstance(record.get("auth_config"), dict):
        record["auth_config"]["has_refresh_token"] = False
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message=message, connector=ConnectorRecordResponse(**sanitized))


@router.post("/api/v1/connectors/{connector_id}/test", response_model=ConnectorActionResponse)
def test_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = _provider_display_name(provider)
    if record.get("status") == "revoked":
        record["status"] = "revoked"
        message = f"{provider_name} connector is revoked."
        ok = False
    elif record.get("auth_config", {}).get("expires_at") and parse_iso_datetime(record["auth_config"]["expires_at"]) and parse_iso_datetime(record["auth_config"]["expires_at"]) <= datetime.now(UTC):
        record["status"] = "expired"
        message = f"{provider_name} token has expired."
        ok = False
    elif provider == "google":
        access_token = secret_map.get("access_token")
        if not access_token:
            record["status"] = "needs_attention"
            message = "Google connector is missing an access token. Reconnect Google to continue."
            ok = False
        else:
            ok, message = _probe_google_access_token(access_token=access_token)
            record["status"] = "connected" if ok else "needs_attention"
    elif provider == "github":
        access_token = secret_map.get("access_token")
        if not access_token:
            record["status"] = "needs_attention"
            message = "GitHub connector is missing an access token. Reconnect GitHub to continue."
            ok = False
        else:
            ok, message, detected_scopes = _probe_github_access_token(access_token=access_token)
            if detected_scopes:
                record["scopes"] = detected_scopes
            record["status"] = "connected" if ok else "needs_attention"
    elif provider == "notion":
        access_token = secret_map.get("access_token")
        if not access_token:
            record["status"] = "needs_attention"
            message = "Notion connector is missing an access token. Reconnect Notion to continue."
            ok = False
        else:
            ok, message = _probe_notion_access_token(access_token=access_token)
            record["status"] = "connected" if ok else "needs_attention"
    elif provider == "trello":
        api_key = secret_map.get("api_key") or auth_config.get("client_id")
        access_token = secret_map.get("access_token")
        if not api_key or not access_token:
            record["status"] = "needs_attention"
            message = "Trello connector is missing its client ID or access token. Reconnect Trello and try again."
            ok = False
        else:
            ok, message = _probe_trello_credentials(api_key=api_key, token=access_token)
            record["status"] = "connected" if ok else "needs_attention"
    elif any(secret_map.values()) or record.get("auth_type") == "oauth2":
        record["status"] = "connected"
        message = "Connector credentials look complete."
        ok = True
    else:
        record["status"] = "needs_attention"
        message = "Connector is missing credential material."
        ok = False

    record["last_tested_at"] = utc_now_iso()
    record["updated_at"] = record["last_tested_at"]
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=ok, message=message, connector=ConnectorRecordResponse(**sanitized))


@router.post("/api/v1/connectors/{provider}/oauth/start", response_model=ConnectorOAuthStartResponse)
def start_connector_oauth(provider: str, payload: ConnectorOAuthStartRequest, request: Request) -> ConnectorOAuthStartResponse:
    connection = get_connection(request)
    root_dir = get_root_dir(request)
    protection_secret = get_connector_protection_secret(root_dir=root_dir, db_path=request.app.state.db_path)
    oauth_states_dict = getattr(request.app.state, "connector_oauth_states", {})
    
    return service_start_connector_oauth(
        provider=provider,
        connector_id=payload.connector_id,
        name=payload.name,
        owner=payload.owner,
        client_id=payload.client_id,
        client_secret_input=payload.client_secret_input,
        redirect_uri=payload.redirect_uri,
        scopes=payload.scopes,
        connection=connection,
        root_dir=root_dir,
        protection_secret=protection_secret,
        oauth_states_dict=oauth_states_dict,
    )


@router.get("/api/v1/connectors/{provider}/oauth/callback", response_model=ConnectorOAuthCallbackResponse)
def complete_connector_oauth(
    provider: str,
    state: str,
    request: Request,
    code: str | None = None,
    error: str | None = None,
    scope: str | None = None,
) -> ConnectorOAuthCallbackResponse | RedirectResponse:
    accepts_html = "text/html" in (request.headers.get("accept") or "").lower()

    connection = get_connection(request)
    root_dir = get_root_dir(request)
    protection_secret = get_connector_protection_secret(root_dir=root_dir, db_path=request.app.state.db_path)
    oauth_states_dict = getattr(request.app.state, "connector_oauth_states", {})

    try:
        callback_result = service_complete_connector_oauth(
            provider=provider,
            state=state,
            code=code,
            error=error,
            scope=scope,
            connection=connection,
            root_dir=root_dir,
            protection_secret=protection_secret,
            oauth_states_dict=oauth_states_dict,
        )
    except HTTPException as exc:
        if not accepts_html:
            raise
        detail = exc.detail if isinstance(exc.detail, str) else "OAuth authorization failed."
        target = f"/settings/connectors.html?{urllib.parse.urlencode({'oauth_status': 'error', 'oauth_message': detail})}"
        return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    if accepts_html:
        target = f"/settings/connectors.html?{urllib.parse.urlencode({'oauth_status': 'success' if callback_result.ok else 'warning', 'oauth_message': callback_result.message, 'connector_id': callback_result.connector.id})}"
        return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    return callback_result


@router.post("/api/v1/connectors/{connector_id}/refresh", response_model=ConnectorActionResponse)
def refresh_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    root_dir = get_root_dir(request)
    protection_secret = get_connector_protection_secret(root_dir=root_dir, db_path=request.app.state.db_path)
    
    success, message, sanitized = service_refresh_oauth_token(
        connector_id=connector_id,
        connection=connection,
        root_dir=root_dir,
        protection_secret=protection_secret,
    )
    return ConnectorActionResponse(ok=success, message=message, connector=ConnectorRecordResponse(**sanitized))
