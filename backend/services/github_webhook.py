"""GitHub webhook helpers: verification, normalization, and dispatch.

This module provides lightweight, well-documented helpers used by the
existing webhook receive flow in `backend/services/apis.py`.

It intentionally keeps business logic minimal: verify signature, extract
delivery id, normalize known GitHub event types, and hand the normalized
event to the automation dispatch pipeline.
"""
from __future__ import annotations

import hmac
import hashlib
from typing import Any

from backend.services.support import utc_now_iso, write_application_log


def verify_signature(headers: dict[str, str], body: bytes, secret: str) -> bool:
    """Verify GitHub HMAC-SHA256 signature.

    Accepts header values that include the `sha256=` prefix.
    """
    header = headers.get("x-hub-signature-256", "") or headers.get("x-hub-signature", "")
    if not header:
        return False
    sig = header.strip()
    if sig.startswith("sha256="):
        sig = sig.split("=", 1)[1]
    try:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    except Exception:
        return False
    return hmac.compare_digest(sig, expected)


def extract_delivery_id(headers: dict[str, str]) -> str | None:
    """Return the X-GitHub-Delivery header value if present."""
    return headers.get("x-github-delivery") or headers.get("X-GitHub-Delivery")


def normalize_github_event(payload: Any, event_type: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normalize core GitHub events into Malcom's internal trigger shape.

    Returns (normalized_event, metadata) where `metadata` contains
    fields useful for binding matching (owner, repo, ref, paths).
    This is intentionally minimal and can be extended for more event types.
    """
    normalized: dict[str, Any] = {
        "source": "github",
        "event_type": event_type,
        "raw": payload,
    }
    metadata: dict[str, Any] = {"owner": None, "repo": None, "ref": None, "paths": []}

    if event_type == "push":
        repo = payload.get("repository", {})
        metadata["owner"] = repo.get("owner", {}).get("login") if isinstance(repo, dict) else None
        metadata["repo"] = repo.get("name") if isinstance(repo, dict) else None
        metadata["ref"] = payload.get("ref")
        commits = payload.get("commits") or []
        paths = []
        for c in commits:
            paths.extend(c.get("added", []) or [])
            paths.extend(c.get("modified", []) or [])
            paths.extend(c.get("removed", []) or [])
        metadata["paths"] = paths
        normalized.update({"ref": metadata["ref"], "commits": commits, "actor": payload.get("pusher")})

    elif event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        repo = payload.get("repository", {})
        metadata["owner"] = repo.get("owner", {}).get("login") if isinstance(repo, dict) else None
        metadata["repo"] = repo.get("name") if isinstance(repo, dict) else None
        metadata["ref"] = pr.get("head", {}).get("ref")
        normalized.update({"action": payload.get("action"), "pr": pr, "actor": payload.get("sender")})

    else:
        # Generic fallback: populate minimal metadata when possible
        repo = payload.get("repository") if isinstance(payload, dict) else None
        if isinstance(repo, dict):
            metadata["owner"] = repo.get("owner", {}).get("login")
            metadata["repo"] = repo.get("name")

    normalized["metadata"] = metadata
    normalized["received_at"] = utc_now_iso()
    return normalized, metadata


def dispatch_normalized_event(connection: Any, logger: Any, normalized_event: dict[str, Any], metadata: dict[str, Any], root_dir: str | None = None, database_url: str | None = None) -> None:
    """Dispatch normalized event into Malcom's automation execution pipeline.

    This function is a small adapter that enqueues or calls the appropriate
    runtime trigger dispatcher. For now it logs the dispatch intent as a
    placeholder; later implementations should call into
    `execute_automation_definition` or the runtime queue.
    """
    write_application_log(
        logger,
        "info",
        "github_webhook_dispatch",
        event_type=normalized_event.get("event_type"),
        owner=metadata.get("owner"),
        repo=metadata.get("repo"),
    )
    # Placeholder: integrate with runtime trigger queue / execute_automation_definition
    return


__all__ = [
    "verify_signature",
    "extract_delivery_id",
    "normalize_github_event",
    "dispatch_normalized_event",
]
