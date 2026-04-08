"""Trello connector OAuth lifecycle helpers.

The public Trello developer docs currently describe a token-based authorize flow
instead of the authorization-code exchange used by the generic connector OAuth
orchestrator. We still provide a deterministic demo path so automated tests can
exercise the guided onboarding contract without reaching the network.
"""
from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException
from fastapi import status


def _demo_token(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"{prefix}{digest[:24]}"


def exchange_trello_oauth_code_for_tokens(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None,
) -> dict[str, str]:
    del code_verifier
    del redirect_uri
    del client_id
    del client_secret

    if code.startswith("demo"):
        return {
            "access_token": _demo_token("trello_token_", code),
            "scope": "read,write",
        }

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Trello callback exchange is only available for demo authorization codes in the current "
            "connector contract."
        ),
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
