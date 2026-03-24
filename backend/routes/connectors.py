from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from backend.schemas import *
from backend.services.support import *

router = APIRouter()


@router.get("/api/v1/connectors/activity-catalog", response_model=list[ConnectorActivityDefinitionResponse])
def list_connector_activity_catalog() -> list[ConnectorActivityDefinitionResponse]:
    return [ConnectorActivityDefinitionResponse(**item) for item in build_connector_activity_catalog()]


@router.get("/api/v1/connectors/http-presets")
def list_http_presets() -> list[dict[str, Any]]:
    """List all available HTTP request presets for workflow builder automation steps.
    
    Returns presets grouped by provider and service, with templates and input schemas.
    """
    from backend.services.http_presets import DEFAULT_HTTP_PRESET_CATALOG

    return [preset.to_dict() for preset in DEFAULT_HTTP_PRESET_CATALOG]


def _exchange_google_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, Any]:
    if code.startswith("demo"):
        return {
            "access_token": f"token_{code[:24]}",
            "refresh_token": f"refresh_{uuid4().hex[:24]}",
            "expires_in": 3600,
            "scope": None,
        }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    request_data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=request_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Google token exchange failed ({error.code}): {body[:400]}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Google token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google token exchange did not return an access token.")

    return token_payload


def _refresh_google_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, Any]:
    if refresh_token.startswith("refresh_"):
        return {
            "access_token": f"token_{uuid4().hex[:24]}",
            "expires_in": 3600,
        }

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    request_data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=request_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Google token refresh failed ({error.code}): {body[:400]}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Google token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google token refresh did not return an access token.")

    return token_payload


def _revoke_google_token(*, token: str) -> None:
    """Call Google's token revocation endpoint. Swallows non-critical errors — local cleanup still proceeds."""
    if token.startswith("token_") or token.startswith("refresh_"):
        return

    request_data = urllib.parse.urlencode({"token": token}).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/revoke",
        data=request_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass  # Best-effort; local credentials are cleared regardless


@router.post("/api/v1/connectors/{connector_id}/revoke", response_model=ConnectorActionResponse)
def revoke_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    settings = get_stored_connector_settings(connection)
    record = next((item for item in settings["records"] if item.get("id") == connector_id), None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    if provider == "google":
        token = secret_map.get("access_token") or secret_map.get("refresh_token") or ""
        if token:
            _revoke_google_token(token=token)

    now = utc_now_iso()
    record["status"] = "revoked"
    record["updated_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **record.get("auth_config", {}),
            "access_token_input": None,
            "refresh_token_input": None,
            "client_secret_input": None,
            "api_key_input": None,
            "password_input": None,
            "header_value_input": None,
            "has_refresh_token": False,
            "clear_credentials": True,
        },
        record.get("auth_config") or {},
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message="Connector revoked and credentials cleared.", connector=ConnectorRecordResponse(**sanitized))


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
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    connection = get_connection(request)
    canonical_provider = canonicalize_connector_provider(provider)
    preset = get_connector_preset(canonical_provider or provider, connection=connection)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector provider not found.")

    settings = get_stored_connector_settings(connection)
    existing_records = {item["id"]: item for item in settings["records"]}
    existing_record = existing_records.get(payload.connector_id) or {}
    existing_auth_config = existing_record.get("auth_config") if isinstance(existing_record.get("auth_config"), dict) else {}

    resolved_client_id = (payload.client_id or existing_auth_config.get("client_id") or "").strip()
    resolved_client_secret_input = payload.client_secret_input

    if canonical_provider == "google":
        if not resolved_client_id:
            resolved_client_id = (os.getenv("MALCOM_GOOGLE_OAUTH_CLIENT_ID") or "").strip()
        if not resolved_client_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Google OAuth client_id is required. Configure connector client_id, "
                    "or set MALCOM_GOOGLE_OAUTH_CLIENT_ID."
                ),
            )

        if not (resolved_client_secret_input or "").strip():
            existing_secret_map = extract_connector_secret_map(existing_auth_config, protection_secret)
            has_stored_secret = bool((existing_secret_map.get("client_secret") or "").strip())
            if not has_stored_secret:
                env_secret = (os.getenv("MALCOM_GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
                if env_secret:
                    resolved_client_secret_input = env_secret

    now = utc_now_iso()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = build_pkce_code_challenge(verifier)
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
                "client_id": resolved_client_id or payload.client_id,
                "client_secret_input": resolved_client_secret_input,
                "redirect_uri": payload.redirect_uri,
                "scope_preset": canonicalize_connector_provider(provider),
                "expires_at": None,
            },
        },
        existing_record=existing_record,
        connection=connection,
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
            canonical_provider or provider,
            client_id=resolved_client_id or payload.client_id or "",
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
) -> ConnectorOAuthCallbackResponse | RedirectResponse:
    accepts_html = "text/html" in (request.headers.get("accept") or "").lower()

    try:
        callback_result = _complete_connector_oauth_result(
            provider=provider,
            state=state,
            request=request,
            code=code,
            error=error,
            scope=scope,
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


def _complete_connector_oauth_result(
    *,
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

    if not code:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth authorization code.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    token_payload: dict[str, Any]
    if canonicalize_connector_provider(provider) == "google":
        client_id = auth_config.get("client_id")
        redirect_uri = auth_config.get("redirect_uri")
        code_verifier = state_payload.get("code_verifier")
        if not client_id or not redirect_uri or not code_verifier:
            oauth_states.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector OAuth configuration is incomplete.")

        token_payload = _exchange_google_oauth_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
    else:
        token_payload = {
            "access_token": f"token_{code[:24]}",
            "refresh_token": f"refresh_{uuid4().hex[:24]}",
            "expires_in": 3600,
            "scope": scope,
        }

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    resolved_scope = token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else scope
    incoming_scopes = [item for item in re.split(r"[\s,]+", resolved_scope or "") if item]
    if incoming_scopes:
        record["scopes"] = incoming_scopes
    expires_in = token_payload.get("expires_in")
    expires_at = (
        (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()
        if isinstance(expires_in, int)
        else (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    )
    refresh_token = token_payload.get("refresh_token") if isinstance(token_payload.get("refresh_token"), str) else None
    access_token = token_payload.get("access_token") if isinstance(token_payload.get("access_token"), str) else None
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **auth_config,
            "access_token_input": access_token,
            "refresh_token_input": refresh_token,
            "expires_at": expires_at,
            "has_refresh_token": bool(refresh_token) or bool(auth_config.get("has_refresh_token")),
        },
        auth_config,
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

    provider = canonicalize_connector_provider(record.get("provider"))
    auth_config = record.get("auth_config") or {}
    if provider == "google":
        client_id = auth_config.get("client_id")
        if not client_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is missing OAuth client id.")
        token_payload = _refresh_google_access_token(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
        access_token = token_payload.get("access_token") if isinstance(token_payload.get("access_token"), str) else None
        expires_in = token_payload.get("expires_in")
        expires_at = (
            (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()
            if isinstance(expires_in, int)
            else (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        )
    else:
        access_token = f"token_{uuid4().hex[:24]}"
        expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **auth_config,
            "access_token_input": access_token,
            "expires_at": expires_at,
            "has_refresh_token": True,
        },
        auth_config,
        protection_secret,
    )
    write_settings_section(connection, "connectors", settings)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message="Connector token refreshed.", connector=ConnectorRecordResponse(**sanitized))
