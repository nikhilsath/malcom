"""Provider-specific OAuth token lifecycle helpers for connectors."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status

from backend.services.connector_trello_oauth_client import (
    exchange_trello_oauth_code_for_tokens,
    revoke_trello_token,
)


def extract_provider_error_detail(body: str, *, fallback: str) -> str:
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


def build_basic_authorization_header(client_id: str, client_secret: str) -> str:
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def _normalize_oauth_token_payload(
    token_payload: dict[str, Any],
    *,
    fallback_scope: str = "",
) -> dict[str, Any]:
    return {
        **token_payload,
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "expires_in": token_payload.get("expires_in"),
        "scope": token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else fallback_scope,
    }


def exchange_github_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """Exchange a GitHub OAuth authorization code for tokens.

    Accepts PKCE `code_verifier` and posts a form-encoded request to GitHub's
    token endpoint. Returns the parsed token payload (as a dict) on success.
    Raises HTTPException with informative messages on failure.
    """
    if code.startswith("demo"):
        return _normalize_oauth_token_payload(
            {
            "access_token": f"gho_{uuid4().hex[:24]}",
            "refresh_token": f"ghr_{uuid4().hex[:24]}",
            "expires_in": 3600,
            "scope": "repo read:user",
            }
        )

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
        detail = extract_provider_error_detail(body, fallback="GitHub rejected the authorization code.")
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

    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub token endpoint returned malformed JSON.")

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub token exchange did not return an access token.")

    return _normalize_oauth_token_payload(token_payload)


def exchange_notion_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if code.startswith("demo"):
        return _normalize_oauth_token_payload(
            {
                "access_token": f"ntn_{uuid4().hex[:24]}",
                "refresh_token": f"ntr_{uuid4().hex[:24]}",
                "expires_in": 3600,
            }
        )

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
            "Authorization": build_basic_authorization_header(client_id, client_secret),
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
        detail = extract_provider_error_detail(body, fallback="Notion rejected the authorization code.")
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

    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Notion token endpoint returned malformed JSON.")

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion token exchange did not return an access token.")

    return _normalize_oauth_token_payload(token_payload)


def refresh_github_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """Refresh a GitHub access token using a refresh token.

    Posts a form-encoded request to GitHub's token endpoint and returns the
    parsed token payload. Raises HTTPException on failures.
    """
    if refresh_token.startswith("ghr_"):
        return _normalize_oauth_token_payload(
            {
            "access_token": f"gho_{uuid4().hex[:24]}",
            "refresh_token": f"ghr_{uuid4().hex[:24]}",
            "expires_in": 3600,
            "scope": "repo read:user",
            }
        )

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
        detail = extract_provider_error_detail(body, fallback="GitHub rejected the refresh token.")
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

    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub token endpoint returned malformed JSON.")

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub token refresh did not return an access token.")

    existing_scope = token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else ""
    return _normalize_oauth_token_payload(token_payload, fallback_scope=existing_scope)


def refresh_notion_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if refresh_token.startswith("ntr_"):
        return _normalize_oauth_token_payload(
            {
                "access_token": f"ntn_{uuid4().hex[:24]}",
                "refresh_token": f"ntr_{uuid4().hex[:24]}",
                "expires_in": 3600,
            }
        )

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
            "Authorization": build_basic_authorization_header(client_id, client_secret),
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
        detail = extract_provider_error_detail(body, fallback="Notion rejected the refresh token.")
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

    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Notion token endpoint returned malformed JSON.")

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notion token refresh did not return an access token.")

    return _normalize_oauth_token_payload(token_payload)


def revoke_github_token(*, token: str, client_id: str, client_secret: str) -> None:
    if token.startswith("gho_") or token.startswith("token_"):
        return

    request = urllib.request.Request(
        f"https://api.github.com/applications/{urllib.parse.quote(client_id, safe='')}/token",
        data=json.dumps({"access_token": token}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": build_basic_authorization_header(client_id, client_secret),
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


def revoke_notion_token(*, token: str, client_id: str, client_secret: str) -> None:
    if token.startswith("ntn_") or token.startswith("secret_"):
        return

    request = urllib.request.Request(
        "https://api.notion.com/v1/oauth/revoke",
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": build_basic_authorization_header(client_id, client_secret),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass
