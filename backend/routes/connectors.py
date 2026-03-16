from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


@router.post("/api/v1/connectors/{connector_id}/test", response_model=ConnectorActionResponse)
def test_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    if record.get("status") == "revoked":
        record["status"] = "revoked"
        message = "Connector is revoked."
        ok = False
    elif record.get("auth_config", {}).get("expires_at") and parse_iso_datetime(record["auth_config"]["expires_at"]) and parse_iso_datetime(record["auth_config"]["expires_at"]) <= datetime.now(UTC):
        record["status"] = "expired"
        message = "Connector token has expired."
        ok = False
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
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=ok, message=message, connector=ConnectorRecordResponse(**sanitized))


@router.post("/api/v1/connectors/{provider}/oauth/start", response_model=ConnectorOAuthStartResponse)
def start_connector_oauth(provider: str, payload: ConnectorOAuthStartRequest, request: Request) -> ConnectorOAuthStartResponse:
    if provider not in SUPPORTED_CONNECTOR_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector provider not found.")

    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    connection = get_connection(request)
    settings = get_stored_connector_settings(connection)
    existing_records = {item["id"]: item for item in settings["records"]}
    now = utc_now_iso()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = build_pkce_code_challenge(verifier)
    preset = get_connector_preset(provider) or {}
    scopes = payload.scopes or list(preset.get("default_scopes", []))
    next_record = normalize_connector_record_for_storage(
        {
            "id": payload.connector_id,
            "provider": provider,
            "name": payload.name,
            "status": "pending_oauth",
            "auth_type": "oauth2",
            "scopes": scopes,
            "owner": payload.owner or "Workspace",
            "base_url": preset.get("base_url"),
            "docs_url": preset.get("docs_url"),
            "auth_config": {
                "client_id": payload.client_id,
                "client_secret_input": payload.client_secret_input,
                "redirect_uri": payload.redirect_uri,
                "scope_preset": provider,
                "expires_at": None,
            },
        },
        existing_record=existing_records.get(payload.connector_id),
        protection_secret=protection_secret,
        timestamp=now,
    )
    settings["records"] = [item for item in settings["records"] if item.get("id") != payload.connector_id] + [next_record]
    write_settings_section(connection, "connectors", settings)
    request.app.state.connector_oauth_states[state] = {
        "provider": provider,
        "connector_id": payload.connector_id,
        "code_verifier": verifier,
        "expires_at": (datetime.now(UTC) + timedelta(seconds=CONNECTOR_OAUTH_STATE_TTL_SECONDS)).isoformat(),
    }
    sanitized = sanitize_connector_record_for_response(next_record, protection_secret)
    return ConnectorOAuthStartResponse(
        connector=ConnectorRecordResponse(**sanitized),
        authorization_url=build_connector_oauth_authorization_url(
            provider,
            client_id=payload.client_id or "missing-client-id",
            redirect_uri=payload.redirect_uri,
            scopes=scopes,
            state=state,
            code_challenge=challenge,
        ),
        state=state,
        expires_at=request.app.state.connector_oauth_states[state]["expires_at"],
        code_challenge_method="S256",
    )


@router.get("/api/v1/connectors/{provider}/oauth/callback", response_model=ConnectorOAuthCallbackResponse)
def complete_connector_oauth(
    provider: str,
    state: str,
    request: Request,
    code: str | None = None,
    error: str | None = None,
    scope: str | None = None,
) -> ConnectorOAuthCallbackResponse:
    oauth_states = getattr(request.app.state, "connector_oauth_states", {})
    state_payload = oauth_states.get(state)
    if not state_payload or state_payload.get("provider") != provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")

    expires_at = parse_iso_datetime(state_payload.get("expires_at"))
    if expires_at is None or expires_at <= datetime.now(UTC):
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired.")

    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    connector_id = state_payload["connector_id"]
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if error:
        record["status"] = "needs_attention"
        record["updated_at"] = utc_now_iso()
        write_settings_section(connection, "connectors", settings)
        oauth_states.pop(state, None)
        sanitized_error = sanitize_connector_record_for_response(record, protection_secret)
        return ConnectorOAuthCallbackResponse(
            ok=False,
            message=f"OAuth authorization failed: {error}.",
            connector=ConnectorRecordResponse(**sanitized_error),
        )

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    incoming_scopes = [item for item in re.split(r"[\s,]+", scope or "") if item]
    if incoming_scopes:
        record["scopes"] = incoming_scopes
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **(record.get("auth_config") or {}),
            "access_token_input": f"token_{(code or 'demo')[:24]}",
            "refresh_token_input": f"refresh_{uuid4().hex[:24]}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "has_refresh_token": True,
        },
        record.get("auth_config"),
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    oauth_states.pop(state, None)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorOAuthCallbackResponse(
        ok=True,
        message="Connector authorized successfully.",
        connector=ConnectorRecordResponse(**sanitized),
    )


@router.post("/api/v1/connectors/{connector_id}/refresh", response_model=ConnectorActionResponse)
def refresh_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if record.get("auth_type") != "oauth2":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only OAuth connectors support refresh.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    if not secret_map.get("refresh_token"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector does not have a refresh token.")

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **(record.get("auth_config") or {}),
            "access_token_input": f"token_{uuid4().hex[:24]}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "has_refresh_token": True,
        },
        record.get("auth_config"),
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message="Connector token refreshed.", connector=ConnectorRecordResponse(**sanitized))
