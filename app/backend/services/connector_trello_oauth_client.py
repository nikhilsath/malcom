"""Trello connector OAuth lifecycle helpers."""
from __future__ import annotations

import json
import hashlib
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException
from fastapi import status

TRELLO_OAUTH_TOKEN_URL = "https://auth.atlassian.com/oauth/token"


def _demo_token(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"{prefix}{digest[:24]}"


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
    return fallback


def _normalize_token_payload(token_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **token_payload,
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "expires_in": token_payload.get("expires_in"),
        "scope": token_payload.get("scope") if isinstance(token_payload.get("scope"), str) else "",
    }


def _post_token_request(*, payload: dict[str, Any], fallback_detail: str, operation: str) -> dict[str, Any]:
    request = urllib.request.Request(
        TRELLO_OAUTH_TOKEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
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
        detail = _extract_provider_error_detail(body, fallback=fallback_detail)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Trello token {operation} failed ({error.code}): {detail}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Trello token endpoint: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Trello token endpoint returned malformed JSON.",
        ) from error

    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Trello token endpoint returned malformed JSON.")

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Trello token {operation} did not return an access token.",
        )

    return _normalize_token_payload(token_payload)


def exchange_trello_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, Any]:
    if code.startswith("demo"):
        return {
            "access_token": _demo_token("trello_token_", code),
            "refresh_token": _demo_token("trello_refresh_", code),
            "expires_in": 3600,
            "scope": "read write",
        }

    if not (client_secret or "").strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trello OAuth client_secret is required for token exchange.")

    return _post_token_request(
        payload={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
        fallback_detail="Trello rejected the authorization code.",
        operation="exchange",
    )


def refresh_trello_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    if refresh_token.startswith("trello_refresh_"):
        return {
            "access_token": _demo_token("trello_token_", refresh_token),
            "refresh_token": _demo_token("trello_refresh_", refresh_token),
            "expires_in": 3600,
            "scope": "read write",
        }

    if not (client_secret or "").strip():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trello OAuth client_secret is required for token refresh.")

    return _post_token_request(
        payload={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        fallback_detail="Trello rejected the refresh token.",
        operation="refresh",
    )


def revoke_trello_token(*, token: str, client_id: str) -> None:
    if token.startswith("trello_token_") or token.startswith("token_"):
        return

    request = urllib.request.Request(
        (
            f"https://api.trello.com/1/tokens/{urllib.parse.quote(token, safe='')}"
            f"?{urllib.parse.urlencode({'key': client_id, 'token': token})}"
        ),
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass
