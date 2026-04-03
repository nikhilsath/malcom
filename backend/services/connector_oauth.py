"""Connector OAuth token lifecycle orchestration service."""
from __future__ import annotations

import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from fastapi import status

from backend.schemas import ConnectorOAuthCallbackResponse, ConnectorOAuthStartResponse, ConnectorRecordResponse
from backend.services.connector_google_oauth_client import (
    exchange_google_oauth_code_for_tokens,
    refresh_google_access_token,
    revoke_google_token,
)
from backend.runtime import parse_iso_datetime

CONNECTOR_OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes


def _get_connector_helpers():
    """Get Connector helper functions using deferred imports to avoid circular dependencies."""
    from backend.routes.connectors import (
        _require_valid_redirect_uri,
        build_connector_oauth_authorization_url,
        build_pkce_code_challenge,
        _extract_provider_error_detail,
        _build_basic_authorization_header,
    )
    from backend.services.support import (
        canonicalize_connector_provider,
        create_connector_record,
        extract_connector_secret_map,
        find_stored_connector_record,
        get_connector_preset,
        normalize_connector_auth_config_for_storage,
        normalize_connector_record_for_storage,
        sanitize_connector_record_for_response,
        save_connector_record,
        utc_now_iso,
        _provider_display_name,
        _provider_metadata,
        _resolve_token_expiry,
    )
    
    return {
        "_require_valid_redirect_uri": _require_valid_redirect_uri,
        "build_connector_oauth_authorization_url": build_connector_oauth_authorization_url,
        "build_pkce_code_challenge": build_pkce_code_challenge,
        "_extract_provider_error_detail": _extract_provider_error_detail,
        "_build_basic_authorization_header": _build_basic_authorization_header,
        "canonicalize_connector_provider": canonicalize_connector_provider,
        "create_connector_record": create_connector_record,
        "extract_connector_secret_map": extract_connector_secret_map,
        "find_stored_connector_record": find_stored_connector_record,
        "get_connector_preset": get_connector_preset,
        "normalize_connector_auth_config_for_storage": normalize_connector_auth_config_for_storage,
        "normalize_connector_record_for_storage": normalize_connector_record_for_storage,
        "sanitize_connector_record_for_response": sanitize_connector_record_for_response,
        "save_connector_record": save_connector_record,
        "utc_now_iso": utc_now_iso,
        "_provider_display_name": _provider_display_name,
        "_provider_metadata": _provider_metadata,
        "_resolve_token_expiry": _resolve_token_expiry,
    }


def _get_provider_oauth_handlers(provider: str) -> tuple[Any, Any]:
    """Get the OAuth code exchange and refresh functions for a provider.
    
    This defers imports to avoid circular dependencies. Provider implementations
    may be defined in routes, services, or other modules.
    """
    from backend.routes.connectors import (
        _exchange_github_oauth_code_for_tokens,
        _exchange_notion_oauth_code_for_tokens,
        _refresh_github_access_token,
        _refresh_notion_access_token,
    )
    
    helpers = _get_connector_helpers()
    canonicalize_connector_provider = helpers["canonicalize_connector_provider"]
    
    canonical = canonicalize_connector_provider(provider)
    if canonical == "github":
        return _exchange_github_oauth_code_for_tokens, _refresh_github_access_token
    elif canonical == "notion":
        return _exchange_notion_oauth_code_for_tokens, _refresh_notion_access_token
    else:
        return None, None


def start_connector_oauth(
    *,
    provider: str,
    connector_id: str,
    name: str | None,
    owner: str | None,
    client_id: str | None,
    client_secret_input: str | None,
    redirect_uri: str | None,
    scopes: list[str] | None,
    connection,
    root_dir: str,
    protection_secret: str,
    oauth_states_dict: dict[str, Any],
) -> ConnectorOAuthStartResponse:
    """Start OAuth authorization flow for a connector."""
    # Defer imports to avoid circular dependencies
    from backend.routes.connectors import (
        _require_valid_redirect_uri,
        build_connector_oauth_authorization_url,
        build_pkce_code_challenge,
    )
    from backend.services.support import (
        canonicalize_connector_provider,
        create_connector_record,
        extract_connector_secret_map,
        find_stored_connector_record,
        get_connector_preset,
        normalize_connector_record_for_storage,
        sanitize_connector_record_for_response,
        save_connector_record,
        utc_now_iso,
        _provider_display_name,
        _provider_metadata,
    )
    
    canonical_provider = canonicalize_connector_provider(provider)
    preset = get_connector_preset(canonical_provider or provider, connection=connection)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector provider not found.")
    provider_contract = _provider_metadata(canonical_provider or provider)
    provider_name = _provider_display_name(canonical_provider or provider)
    if not provider_contract.get("oauth_supported"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{provider_name} uses saved credentials and does not support OAuth browser setup.",
        )

    existing_record = find_stored_connector_record(connection, connector_id) or {}
    existing_auth_config = existing_record.get("auth_config") if isinstance(existing_record.get("auth_config"), dict) else {}
    existing_secret_map = extract_connector_secret_map(existing_auth_config, protection_secret)

    resolved_client_id = (client_id or existing_auth_config.get("client_id") or "").strip()
    resolved_client_secret_input = client_secret_input
    resolved_redirect_uri = _require_valid_redirect_uri(
        redirect_uri or existing_auth_config.get("redirect_uri") or "",
        provider_name=provider_name,
    )

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
            has_stored_secret = bool((existing_secret_map.get("client_secret") or "").strip())
            if not has_stored_secret:
                env_secret = (os.getenv("MALCOM_GOOGLE_OAUTH_CLIENT_SECRET") or "").strip()
                if env_secret:
                    resolved_client_secret_input = env_secret
    elif not resolved_client_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{provider_name} OAuth client_id is required.",
        )

    if canonical_provider in {"github", "notion"}:
        has_client_secret = bool((resolved_client_secret_input or "").strip()) or bool((existing_secret_map.get("client_secret") or "").strip())
        if not has_client_secret:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{provider_name} OAuth client_secret is required.",
            )

    now = utc_now_iso()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = build_pkce_code_challenge(verifier)
    resolved_scopes = scopes or list(preset.get("default_scopes", []))
    next_record = normalize_connector_record_for_storage(
        {
            "id": connector_id,
            "provider": provider,
            "name": name,
            "status": "pending_oauth",
            "auth_type": "oauth2",
            "scopes": resolved_scopes,
            "owner": owner or "Workspace",
            "base_url": preset.get("base_url"),
            "docs_url": preset.get("docs_url"),
            "auth_config": {
                "client_id": resolved_client_id or client_id,
                "client_secret_input": resolved_client_secret_input,
                "redirect_uri": resolved_redirect_uri,
                "scope_preset": canonical_provider or provider,
                "expires_at": None,
            },
        },
        existing_record=existing_record,
        connection=connection,
        protection_secret=protection_secret,
        timestamp=now,
    )
    try:
        if existing_record:
            stored_record = save_connector_record(connection, next_record, protection_secret=protection_secret)
        else:
            stored_record = create_connector_record(connection, next_record, protection_secret=protection_secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    oauth_states_dict[state] = {
        "provider": canonical_provider or provider,
        "connector_id": connector_id,
        "code_verifier": verifier,
        "expires_at": (datetime.now(UTC) + timedelta(seconds=CONNECTOR_OAUTH_STATE_TTL_SECONDS)).isoformat(),
    }
    sanitized = sanitize_connector_record_for_response(stored_record, protection_secret)
    return ConnectorOAuthStartResponse(
        connector=ConnectorRecordResponse(**sanitized),
        authorization_url=build_connector_oauth_authorization_url(
            canonical_provider or provider,
            client_id=resolved_client_id or client_id or "",
            redirect_uri=resolved_redirect_uri,
            scopes=resolved_scopes,
            state=state,
            code_challenge=challenge,
        ),
        state=state,
        expires_at=oauth_states_dict[state]["expires_at"],
        code_challenge_method="S256",
    )


def complete_connector_oauth(
    *,
    provider: str,
    state: str,
    code: str | None,
    error: str | None,
    scope: str | None,
    connection,
    root_dir: str,
    protection_secret: str,
    oauth_states_dict: dict[str, Any],
) -> ConnectorOAuthCallbackResponse:
    """Complete OAuth callback and store credentials.
    
    Args:
        provider: Connector provider name from OAuth callback.
        state: OAuth state for verification.
        code: OAuth authorization code from callback.
        error: OAuth error from callback (if any).
        scope: OAuth scope returned from callback.
        connection: Database connection.
        root_dir: Application root directory.
        protection_secret: Secret for credential protection.
        oauth_states_dict: Shared dictionary for OAuth state tracking (request.app.state.connector_oauth_states).
    
    Returns:
        ConnectorOAuthCallbackResponse with status and updated connector record.
    
    Raises:
        HTTPException: On state validation, code exchange, or database errors.
    """
    from backend.services.support import (
        canonicalize_connector_provider,
        extract_connector_secret_map,
        find_stored_connector_record,
        normalize_connector_auth_config_for_storage,
        sanitize_connector_record_for_response,
        save_connector_record,
        utc_now_iso,
        _provider_display_name,
        _resolve_token_expiry,
    )
    
    state_payload = oauth_states_dict.get(state)
    canonical_provider = canonicalize_connector_provider(provider)
    provider_name = _provider_display_name(canonical_provider or provider)
    if not state_payload or state_payload.get("provider") != (canonical_provider or provider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")

    expires_at = parse_iso_datetime(state_payload.get("expires_at"))
    if expires_at is None or expires_at <= datetime.now(UTC):
        oauth_states_dict.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired.")

    connector_id = state_payload["connector_id"]
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        oauth_states_dict.pop(state, None)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if error:
        record["status"] = "needs_attention"
        record["updated_at"] = utc_now_iso()
        record = save_connector_record(connection, record, protection_secret=protection_secret)
        oauth_states_dict.pop(state, None)
        sanitized_error = sanitize_connector_record_for_response(record, protection_secret)
        return ConnectorOAuthCallbackResponse(
            ok=False,
            message=f"{provider_name} authorization failed: {error}.",
            connector=ConnectorRecordResponse(**sanitized_error),
        )

    if not code:
        oauth_states_dict.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth authorization code.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    client_id = auth_config.get("client_id")
    redirect_uri = auth_config.get("redirect_uri")
    code_verifier = state_payload.get("code_verifier")
    if not client_id or not redirect_uri or not code_verifier:
        oauth_states_dict.pop(state, None)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} OAuth configuration is incomplete.")

    token_payload: dict[str, Any]
    if canonical_provider == "google":
        token_payload = exchange_google_oauth_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
    elif canonical_provider == "github":
        client_secret = secret_map.get("client_secret")
        if not client_secret:
            oauth_states_dict.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub OAuth configuration is incomplete: client_secret is required.")
        exchange_fn, _ = _get_provider_oauth_handlers(canonical_provider)
        if not exchange_fn:
            oauth_states_dict.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support OAuth callback setup.")
        token_payload = exchange_fn(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    elif canonical_provider == "notion":
        client_secret = secret_map.get("client_secret")
        if not client_secret:
            oauth_states_dict.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion OAuth configuration is incomplete: client_secret is required.")
        exchange_fn, _ = _get_provider_oauth_handlers(canonical_provider)
        if not exchange_fn:
            oauth_states_dict.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support OAuth callback setup.")
        token_payload = exchange_fn(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        oauth_states_dict.pop(state, None)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support OAuth callback setup.")

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    resolved_scope = token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else scope
    incoming_scopes = [item for item in re.split(r"[\s,]+", resolved_scope or "") if item]
    if incoming_scopes:
        record["scopes"] = incoming_scopes
    expires_at_str = _resolve_token_expiry(token_payload, default_seconds=3600 if canonical_provider in {"google", "github"} else None)
    refresh_token = token_payload.get("refresh_token") if isinstance(token_payload.get("refresh_token"), str) else None
    access_token = token_payload.get("access_token") if isinstance(token_payload.get("access_token"), str) else None
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **auth_config,
            "access_token_input": access_token,
            "refresh_token_input": refresh_token,
            "expires_at": expires_at_str,
            "has_refresh_token": bool(refresh_token) or bool(auth_config.get("has_refresh_token")),
        },
        auth_config,
        protection_secret,
    )
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    oauth_states_dict.pop(state, None)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorOAuthCallbackResponse(
        ok=True,
        message=f"{provider_name} connector authorized successfully.",
        connector=ConnectorRecordResponse(**sanitized),
    )


def refresh_oauth_token(
    *,
    connector_id: str,
    connection,
    root_dir: str,
    protection_secret: str,
) -> tuple[bool, str, dict[str, Any]]:
    """Refresh an OAuth token for a connector.
    
    Args:
        connector_id: Connector ID to refresh.
        connection: Database connection.
        root_dir: Application root directory.
        protection_secret: Secret for credential protection.
    
    Returns:
        Tuple of (success: bool, message: str, sanitized_connector_dict: dict).
    
    Raises:
        HTTPException: On validation failures or token refresh errors.
    """
    from backend.services.support import (
        canonicalize_connector_provider,
        extract_connector_secret_map,
        find_stored_connector_record,
        normalize_connector_auth_config_for_storage,
        sanitize_connector_record_for_response,
        save_connector_record,
        utc_now_iso,
        _provider_display_name,
        _provider_metadata,
        _resolve_token_expiry,
    )
    
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = _provider_display_name(provider)
    provider_contract = _provider_metadata(provider)
    if record.get("auth_type") != "oauth2" or not provider_contract.get("refresh_supported"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support token refresh.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    if not secret_map.get("refresh_token"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not have a refresh token.")

    auth_config = record.get("auth_config") or {}
    if provider == "google":
        client_id = auth_config.get("client_id")
        if not client_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connector is missing OAuth client id.")
        token_payload = refresh_google_access_token(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
    elif provider == "github":
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub refresh requires both client_id and client_secret.")
        _, refresh_fn = _get_provider_oauth_handlers(provider)
        if not refresh_fn:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support token refresh.")
        token_payload = refresh_fn(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=client_secret,
        )
    elif provider == "notion":
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion refresh requires both client_id and client_secret.")
        _, refresh_fn = _get_provider_oauth_handlers(provider)
        if not refresh_fn:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support token refresh.")
        token_payload = refresh_fn(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support token refresh.")

    access_token = token_payload.get("access_token") if isinstance(token_payload.get("access_token"), str) else None
    refresh_token = token_payload.get("refresh_token") if isinstance(token_payload.get("refresh_token"), str) else None
    expires_at_str = _resolve_token_expiry(token_payload, default_seconds=3600 if provider in {"google", "github"} else None)

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **auth_config,
            "access_token_input": access_token,
            "refresh_token_input": refresh_token,
            "expires_at": expires_at_str,
            "has_refresh_token": True if refresh_token else bool(auth_config.get("has_refresh_token")) or bool(secret_map.get("refresh_token")),
        },
        auth_config,
        protection_secret,
    )
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return True, f"{provider_name} token refreshed.", sanitized
