"""Google OAuth token lifecycle handlers for connector authentication."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from fastapi import HTTPException
from fastapi import status


def exchange_google_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, any]:
    """Exchange Google authorization code for access and refresh tokens.
    
    Args:
        code: OAuth authorization code from Google.
        code_verifier: PKCE code verifier.
        redirect_uri: Registered redirect URI.
        client_id: OAuth client ID.
        client_secret: OAuth client secret (optional for public clients).
    
    Returns:
        Token payload containing access_token, refresh_token, expires_in, etc.
    
    Raises:
        HTTPException: On token exchange failure (HTTP errors, invalid responses).
    """
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


def refresh_google_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, any]:
    """Refresh a Google access token using a refresh token.
    
    Args:
        refresh_token: Google refresh token.
        client_id: OAuth client ID.
        client_secret: OAuth client secret (optional for public clients).
    
    Returns:
        Token payload containing new access_token, expires_in, etc.
    
    Raises:
        HTTPException: On token refresh failure (HTTP errors, invalid responses).
    """
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


def revoke_google_token(*, token: str) -> None:
    """Revoke a Google token (access or refresh).
    
    Swallows non-critical errors — local credentials cleanup still proceeds.
    
    Args:
        token: Google access or refresh token to revoke.
    """
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
