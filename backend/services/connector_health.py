"""Provider-specific connection health probe helpers for connectors."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException
from starlette import status

from backend.services.connector_oauth_provider_clients import extract_provider_error_detail
from backend.services.connector_postgres import probe_postgres_connection


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
        detail = extract_provider_error_detail(body, fallback="Google rejected the saved access token.")
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


def _probe_github_access_token(*, access_token: str) -> tuple[bool, str, list[str]]:
    if access_token.startswith("gho_"):
        return True, "GitHub connection verified.", []
    if access_token.startswith("token_"):
        return True, "GitHub connection verified.", ["repo"]

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
            scope_header = str(response.headers.get("X-OAuth-Scopes") or "")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = extract_provider_error_detail(body, fallback="GitHub rejected the saved access token.")
        lowered = detail.lower()
        if "bad credentials" in lowered or "expired" in lowered or "revoked" in lowered:
            return False, "GitHub rejected the saved access token as invalid or revoked. Reconnect GitHub and try again.", []
        return False, f"{detail} Reconnect GitHub and try again.", []
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
        return False, "GitHub token validation did not return the expected account details. Reconnect GitHub and try again.", []

    detected_scopes = [scope.strip() for scope in scope_header.split(",") if scope.strip()]
    return True, "GitHub connection verified.", sorted(set(detected_scopes))


def _inspect_github_scopes_from_payload(
    *,
    provider: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    if provider != "github":
        return changes

    next_changes = dict(changes)
    fallback_scopes = [
        str(scope).strip()
        for scope in (next_changes.get("scopes") or [])
        if str(scope).strip()
    ]
    auth_config = next_changes.get("auth_config")
    if not isinstance(auth_config, dict):
        return next_changes

    token_candidate = str(auth_config.get("access_token_input") or "").strip()
    if not token_candidate:
        return next_changes

    try:
        ok, _, detected_scopes = _probe_github_access_token(access_token=token_candidate)
    except HTTPException:
        # Allow saving while offline; users can run Check connection later.
        return next_changes

    next_changes["scopes"] = detected_scopes or fallback_scopes
    if "status" not in next_changes:
        next_changes["status"] = "connected" if ok else "needs_attention"
    return next_changes


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
        detail = extract_provider_error_detail(body, fallback="Notion rejected the saved access token.")
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
    if api_key.startswith("trello_key_") or token.startswith("trello_token_") or token.startswith("token_"):
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
        detail = extract_provider_error_detail(body, fallback="Trello rejected the saved API key or token.")
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


def _probe_cpanel_postgres_credentials(*, host: str, port: int | str, database: str, username: str, password: str, sslmode: str | None = None) -> tuple[bool, str]:
    auth_config = {
        "host": host,
        "port": int(port) if port is not None and str(port).strip() else 5432,
        "database": database,
        "username": username,
        "password": password,
    }
    if sslmode:
        auth_config["sslmode"] = sslmode

    try:
        ok, message = probe_postgres_connection(auth_config)
    except HTTPException:
        # Allow saving while offline; callers may surface network errors as 502.
        raise
    except Exception as error:
        return False, f"{str(error)} Reconnect or verify settings and try again."

    return ok, message
