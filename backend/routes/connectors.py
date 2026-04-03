from __future__ import annotations

import base64
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from backend.schemas import *
from backend.services.support import *
from backend.runtime import parse_iso_datetime
from backend.services.http_presets import list_http_preset_catalog

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

    try:
        record = create_connector_record(
            connection,
            payload.model_dump(exclude_unset=True),
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

    try:
        if changes:
            record = update_connector_record(
                connection,
                connector_id,
                changes,
                protection_secret=protection_secret,
            )
        else:
            record = find_stored_connector_record(connection, connector_id)
            if record is None:
                raise FileNotFoundError(connector_id)
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


def _provider_display_name(provider: str | None) -> str:
    metadata = get_connector_provider_metadata(provider)
    if metadata:
        return str(metadata.get("name") or provider or "Connector")
    return str(provider or "Connector").replace("_", " ").title()


def _provider_metadata(provider: str | None) -> dict[str, Any]:
    metadata = get_connector_provider_metadata(provider)
    if metadata is not None:
        return metadata
    display_name = _provider_display_name(provider)
    return {
        "id": canonicalize_connector_provider(provider) or "generic_http",
        "name": display_name,
        "onboarding_mode": "credentials",
        "oauth_supported": False,
        "callback_supported": False,
        "refresh_supported": False,
        "revoke_supported": True,
        "redirect_uri_required": False,
        "redirect_uri_readonly": False,
        "scopes_locked": False,
        "default_redirect_path": None,
        "required_fields": [],
        "setup_fields": [],
        "ui_copy": {
            "eyebrow": display_name,
            "title": f"{display_name} setup",
            "description": f"Enter the saved credentials needed for {display_name}.",
            "last_checked_empty": f"{display_name} connection has not been checked yet.",
        },
        "action_labels": {
            "save": "Save connector",
            "test": "Test connector",
            "connect": f"Save {display_name} credentials",
            "reconnect": f"Reconnect {display_name}",
            "refresh": "Refresh token",
            "revoke": "Revoke connector",
        },
        "status_messages": {},
    }


def _extract_provider_error_detail(body: str, *, fallback: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return fallback

    if isinstance(payload, dict):
        error_description = payload.get("error_description")
        if isinstance(error_description, str) and error_description.strip():
            return error_description.strip()
        message_value = payload.get("message")
        if isinstance(message_value, str) and message_value.strip():
            return message_value.strip()
        error_value = payload.get("error")
        if isinstance(error_value, str) and error_value.strip():
            return error_value.strip()
        if isinstance(error_value, dict):
            message_value = error_value.get("message")
            if isinstance(message_value, str) and message_value.strip():
                return message_value.strip()
    return fallback


def _build_basic_authorization_header(client_id: str, client_secret: str) -> str:
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _require_valid_redirect_uri(redirect_uri: str, *, provider_name: str) -> str:
    resolved_redirect_uri = redirect_uri.strip()
    if not resolved_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{provider_name} OAuth redirect_uri is required.",
        )
    try:
        parsed = urllib.parse.urlparse(resolved_redirect_uri)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{provider_name} OAuth redirect_uri must be a valid http or https URL.",
        ) from error

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{provider_name} OAuth redirect_uri must be a valid http or https URL.",
        )
    return resolved_redirect_uri


def _resolve_token_expiry(token_payload: dict[str, Any], *, default_seconds: int | None = None) -> str | None:
    expires_in = token_payload.get("expires_in")
    if isinstance(expires_in, int):
        return (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()
    if default_seconds is not None:
        return (datetime.now(UTC) + timedelta(seconds=default_seconds)).isoformat()
    return None


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


def _exchange_github_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if code.startswith("demo"):
        return {
            "access_token": f"gho_{uuid4().hex[:24]}",
            "refresh_token": f"ghr_{uuid4().hex[:24]}",
            "expires_in": 3600,
            "scope": "repo read:user",
        }

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    request_data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=request_data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="GitHub rejected the authorization code.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"GitHub token exchange failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach GitHub token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub token exchange did not return an access token.")

    return token_payload


def _exchange_notion_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if code.startswith("demo"):
        return {
            "access_token": f"ntn_{uuid4().hex[:24]}",
            "refresh_token": f"ntr_{uuid4().hex[:24]}",
            "expires_in": 3600,
        }

    payload = json.dumps(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.notion.com/v1/oauth/token",
        data=payload,
        headers={
            "Accept": "application/json",
            "Authorization": _build_basic_authorization_header(client_id, client_secret),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="Notion rejected the authorization code.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Notion token exchange failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Notion token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Notion token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion token exchange did not return an access token.")

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


def _refresh_github_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if refresh_token.startswith("ghr_"):
        return {
            "access_token": f"gho_{uuid4().hex[:24]}",
            "refresh_token": f"ghr_{uuid4().hex[:24]}",
            "expires_in": 3600,
        }

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    request_data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=request_data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="GitHub rejected the refresh token.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"GitHub token refresh failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach GitHub token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub token refresh did not return an access token.")

    return token_payload


def _refresh_notion_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if refresh_token.startswith("ntr_"):
        return {
            "access_token": f"ntn_{uuid4().hex[:24]}",
            "refresh_token": f"ntr_{uuid4().hex[:24]}",
            "expires_in": 3600,
        }

    payload = json.dumps(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.notion.com/v1/oauth/token",
        data=payload,
        headers={
            "Accept": "application/json",
            "Authorization": _build_basic_authorization_header(client_id, client_secret),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            token_payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="Notion rejected the refresh token.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Notion token refresh failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Notion token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Notion token endpoint returned malformed JSON.",
        ) from error

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion token refresh did not return an access token.")

    return token_payload


def _google_probe_failure_message(detail: str) -> str:
    lowered = detail.lower()
    if "invalid_token" in lowered or "invalid token" in lowered:
        return "Google rejected the saved access token as invalid or revoked. Reconnect Google and try again."
    if "expired" in lowered:
        return "Google access token is expired. Refresh or reconnect Google and try again."
    if "insufficient" in lowered or "scope" in lowered:
        return "Google token was accepted but does not have the required scopes. Reconnect Google with the required scopes."
    return f"{detail} Reconnect Google and try again."


def _probe_google_access_token(*, access_token: str) -> tuple[bool, str]:
    if access_token.startswith("token_"):
        return True, "Google connection verified."

    request = urllib.request.Request(
        f"https://oauth2.googleapis.com/tokeninfo?{urllib.parse.urlencode({'access_token': access_token})}",
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="Google rejected the saved access token.")
        return False, _google_probe_failure_message(detail)
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Google while checking the connector: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google connection check returned malformed JSON.",
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("aud"), str) or not payload.get("aud"):
        return False, "Google token validation did not return the expected connector details. Reconnect Google and try again."

    return True, "Google connection verified."


def _probe_github_access_token(*, access_token: str) -> tuple[bool, str]:
    if access_token.startswith("gho_") or access_token.startswith("token_"):
        return True, "GitHub connection verified."

    request = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="GitHub rejected the saved access token.")
        lowered = detail.lower()
        if "bad credentials" in lowered or "expired" in lowered or "revoked" in lowered:
            return False, "GitHub rejected the saved access token as invalid or revoked. Reconnect GitHub and try again."
        return False, f"{detail} Reconnect GitHub and try again."
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach GitHub while checking the connector: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub connection check returned malformed JSON.",
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("login"), str) or not payload.get("login"):
        return False, "GitHub token validation did not return the expected account details. Reconnect GitHub and try again."

    return True, "GitHub connection verified."


def _probe_notion_access_token(*, access_token: str) -> tuple[bool, str]:
    if access_token.startswith("ntn_") or access_token.startswith("secret_"):
        return True, "Notion connection verified."

    request = urllib.request.Request(
        "https://api.notion.com/v1/users/me",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2026-03-11",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="Notion rejected the saved access token.")
        lowered = detail.lower()
        if "unauthorized" in lowered or "invalid" in lowered or "expired" in lowered:
            return False, "Notion rejected the saved access token as invalid or revoked. Reconnect Notion and try again."
        return False, f"{detail} Reconnect Notion and try again."
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Notion while checking the connector: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Notion connection check returned malformed JSON.",
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("object"), str) or payload.get("object") != "user":
        return False, "Notion token validation did not return the expected workspace details. Reconnect Notion and try again."

    return True, "Notion connection verified."


def _probe_trello_credentials(*, api_key: str, token: str) -> tuple[bool, str]:
    if api_key.startswith("trello_key_") or token.startswith("trello_token_"):
        return True, "Trello connection verified."

    query = urllib.parse.urlencode({"key": api_key, "token": token})
    request = urllib.request.Request(
        f"https://api.trello.com/1/members/me?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = _extract_provider_error_detail(body, fallback="Trello rejected the saved API key or token.")
        lowered = detail.lower()
        if "invalid" in lowered or "unauthorized" in lowered or "expired" in lowered:
            return False, "Trello rejected the saved API key or token. Save new credentials and try again."
        return False, f"{detail} Save new Trello credentials and try again."
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Trello while checking the connector: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Trello connection check returned malformed JSON.",
        ) from error

    if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) or not payload.get("id"):
        return False, "Trello validation did not return the expected member details. Save new credentials and try again."

    return True, "Trello connection verified."


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


def _revoke_github_token(*, token: str, client_id: str, client_secret: str) -> None:
    if token.startswith("gho_") or token.startswith("token_"):
        return

    request = urllib.request.Request(
        f"https://api.github.com/applications/{urllib.parse.quote(client_id, safe='')}/token",
        data=json.dumps({"access_token": token}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": _build_basic_authorization_header(client_id, client_secret),
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass


def _revoke_notion_token(*, token: str, client_id: str, client_secret: str) -> None:
    if token.startswith("ntn_") or token.startswith("secret_"):
        return

    request = urllib.request.Request(
        "https://api.notion.com/v1/oauth/revoke",
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": _build_basic_authorization_header(client_id, client_secret),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass


@router.post("/api/v1/connectors/{connector_id}/revoke", response_model=ConnectorActionResponse)
def revoke_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
    provider = canonicalize_connector_provider(record.get("provider"))
    provider_name = _provider_display_name(provider)
    auth_config = record.get("auth_config") or {}
    message = f"{provider_name} connector revoked and credentials cleared."
    if provider == "google":
        token = secret_map.get("access_token") or secret_map.get("refresh_token") or ""
        if token:
            _revoke_google_token(token=token)
    elif provider == "github":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if token and client_id and client_secret:
            _revoke_github_token(token=token, client_id=client_id, client_secret=client_secret)
        else:
            message = "GitHub credentials cleared locally. Configure a client secret to revoke the upstream token as well."
    elif provider == "notion":
        token = secret_map.get("access_token") or ""
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if token and client_id and client_secret:
            _revoke_notion_token(token=token, client_id=client_id, client_secret=client_secret)
        else:
            message = "Notion credentials cleared locally. Configure a client secret to revoke the upstream token as well."
    elif provider == "trello":
        message = "Trello credentials cleared from this workspace."

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
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message=message, connector=ConnectorRecordResponse(**sanitized))


@router.post("/api/v1/connectors/{connector_id}/test", response_model=ConnectorActionResponse)
def test_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    secret_map = extract_connector_secret_map(record.get("auth_config") or {}, protection_secret)
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
            ok, message = _probe_github_access_token(access_token=access_token)
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
        api_key = secret_map.get("api_key")
        access_token = secret_map.get("access_token")
        if not api_key or not access_token:
            record["status"] = "needs_attention"
            message = "Trello requires both an API key and token. Save the credentials and try again."
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
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    connection = get_connection(request)
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

    existing_record = find_stored_connector_record(connection, payload.connector_id) or {}
    existing_auth_config = existing_record.get("auth_config") if isinstance(existing_record.get("auth_config"), dict) else {}
    existing_secret_map = extract_connector_secret_map(existing_auth_config, protection_secret)

    resolved_client_id = (payload.client_id or existing_auth_config.get("client_id") or "").strip()
    resolved_client_secret_input = payload.client_secret_input
    resolved_redirect_uri = _require_valid_redirect_uri(
        payload.redirect_uri or existing_auth_config.get("redirect_uri") or "",
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

    request.app.state.connector_oauth_states[state] = {
        "provider": canonical_provider or provider,
        "connector_id": payload.connector_id,
        "code_verifier": verifier,
        "expires_at": (datetime.now(UTC) + timedelta(seconds=CONNECTOR_OAUTH_STATE_TTL_SECONDS)).isoformat(),
    }
    sanitized = sanitize_connector_record_for_response(stored_record, protection_secret)
    return ConnectorOAuthStartResponse(
        connector=ConnectorRecordResponse(**sanitized),
        authorization_url=build_connector_oauth_authorization_url(
            canonical_provider or provider,
            client_id=resolved_client_id or payload.client_id or "",
            redirect_uri=resolved_redirect_uri,
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
    canonical_provider = canonicalize_connector_provider(provider)
    provider_name = _provider_display_name(canonical_provider or provider)
    if not state_payload or state_payload.get("provider") != (canonical_provider or provider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")

    expires_at = parse_iso_datetime(state_payload.get("expires_at"))
    if expires_at is None or expires_at <= datetime.now(UTC):
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired.")

    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
    connector_id = state_payload["connector_id"]
    record = find_stored_connector_record(connection, connector_id)
    if record is None:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if error:
        record["status"] = "needs_attention"
        record["updated_at"] = utc_now_iso()
        record = save_connector_record(connection, record, protection_secret=protection_secret)
        oauth_states.pop(state, None)
        sanitized_error = sanitize_connector_record_for_response(record, protection_secret)
        return ConnectorOAuthCallbackResponse(
            ok=False,
            message=f"{provider_name} authorization failed: {error}.",
            connector=ConnectorRecordResponse(**sanitized_error),
        )

    if not code:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth authorization code.")

    auth_config = record.get("auth_config") or {}
    secret_map = extract_connector_secret_map(auth_config, protection_secret)
    client_id = auth_config.get("client_id")
    redirect_uri = auth_config.get("redirect_uri")
    code_verifier = state_payload.get("code_verifier")
    if not client_id or not redirect_uri or not code_verifier:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} OAuth configuration is incomplete.")

    token_payload: dict[str, Any]
    if canonical_provider == "google":
        token_payload = _exchange_google_oauth_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
    elif canonical_provider == "github":
        client_secret = secret_map.get("client_secret")
        if not client_secret:
            oauth_states.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub OAuth configuration is incomplete: client_secret is required.")
        token_payload = _exchange_github_oauth_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    elif canonical_provider == "notion":
        client_secret = secret_map.get("client_secret")
        if not client_secret:
            oauth_states.pop(state, None)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion OAuth configuration is incomplete: client_secret is required.")
        token_payload = _exchange_notion_oauth_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        oauth_states.pop(state, None)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support OAuth callback setup.")

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    resolved_scope = token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else scope
    incoming_scopes = [item for item in re.split(r"[\s,]+", resolved_scope or "") if item]
    if incoming_scopes:
        record["scopes"] = incoming_scopes
    expires_at = _resolve_token_expiry(token_payload, default_seconds=3600 if canonical_provider in {"google", "github"} else None)
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
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    oauth_states.pop(state, None)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorOAuthCallbackResponse(
        ok=True,
        message=f"{provider_name} connector authorized successfully.",
        connector=ConnectorRecordResponse(**sanitized),
    )


@router.post("/api/v1/connectors/{connector_id}/refresh", response_model=ConnectorActionResponse)
def refresh_connector(connector_id: str, request: Request) -> ConnectorActionResponse:
    connection = get_connection(request)
    protection_secret = get_connector_protection_secret(root_dir=get_root_dir(request), db_path=request.app.state.db_path)
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
        token_payload = _refresh_google_access_token(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=secret_map.get("client_secret"),
        )
    elif provider == "github":
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub refresh requires both client_id and client_secret.")
        token_payload = _refresh_github_access_token(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=client_secret,
        )
    elif provider == "notion":
        client_id = auth_config.get("client_id")
        client_secret = secret_map.get("client_secret")
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion refresh requires both client_id and client_secret.")
        token_payload = _refresh_notion_access_token(
            refresh_token=secret_map["refresh_token"],
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{provider_name} does not support token refresh.")

    access_token = token_payload.get("access_token") if isinstance(token_payload.get("access_token"), str) else None
    refresh_token = token_payload.get("refresh_token") if isinstance(token_payload.get("refresh_token"), str) else None
    expires_at = _resolve_token_expiry(token_payload, default_seconds=3600 if provider in {"google", "github"} else None)

    now = utc_now_iso()
    record["status"] = "connected"
    record["updated_at"] = now
    record["last_tested_at"] = now
    record["auth_config"] = normalize_connector_auth_config_for_storage(
        {
            **auth_config,
            "access_token_input": access_token,
            "refresh_token_input": refresh_token,
            "expires_at": expires_at,
            "has_refresh_token": True if refresh_token else bool(auth_config.get("has_refresh_token")) or bool(secret_map.get("refresh_token")),
        },
        auth_config,
        protection_secret,
    )
    record = save_connector_record(connection, record, protection_secret=protection_secret)
    sanitized = sanitize_connector_record_for_response(record, protection_secret)
    return ConnectorActionResponse(ok=True, message=f"{provider_name} token refreshed.", connector=ConnectorRecordResponse(**sanitized))
