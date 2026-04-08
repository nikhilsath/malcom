"""Provider-specific repository listing helpers for connectors."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException
from starlette import status

from backend.services.connector_oauth_provider_clients import extract_provider_error_detail


def _list_github_repositories(*, access_token: str) -> list[dict[str, Any]]:
    # Deterministic local fixtures for tests/smoke without external network calls.
    if access_token.startswith("token_") or access_token.startswith("ghp_secret_"):
        return [
            {
                "id": 1001,
                "name": "malcom",
                "full_name": "openai/malcom",
                "owner": "openai",
                "private": True,
                "default_branch": "main",
            }
        ]

    query = urllib.parse.urlencode({"per_page": 100, "sort": "updated", "direction": "desc"})
    request = urllib.request.Request(
        f"https://api.github.com/user/repos?{query}",
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
        detail = extract_provider_error_detail(body, fallback="GitHub rejected the saved access token.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unable to list repositories for this connector: {detail}",
        ) from error
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach GitHub while listing repositories: {error.reason}.",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repository listing returned malformed JSON.",
        ) from error

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repository listing returned an unexpected response.",
        )

    repos: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        owner = (item.get("owner") or {}).get("login") if isinstance(item.get("owner"), dict) else None
        full_name = str(item.get("full_name") or "").strip()
        name = str(item.get("name") or "").strip()
        if not full_name or not name or not owner:
            continue
        repos.append(
            {
                "id": item.get("id"),
                "name": name,
                "full_name": full_name,
                "owner": str(owner),
                "private": bool(item.get("private")),
                "default_branch": str(item.get("default_branch") or ""),
            }
        )
    return repos
