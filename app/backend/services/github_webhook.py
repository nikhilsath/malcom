"""GitHub webhook helpers: verification, normalization, and dispatch.

This module provides lightweight, well-documented helpers used by the
existing webhook receive flow in `backend/services/apis.py`.

It intentionally keeps business logic minimal: verify signature, extract
delivery id, normalize known GitHub event types, and hand the normalized
event to the automation dispatch pipeline.
"""
from __future__ import annotations

import json
import hmac
import hashlib
import logging
from fnmatch import fnmatchcase
from typing import Any

from backend.database import fetch_all
from backend.services.support import execute_automation_definition
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


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_branch(value: str | None) -> str:
    branch = _normalize_text(value)
    if branch.startswith("refs/heads/"):
        return branch.removeprefix("refs/heads/").strip()
    return branch


def _split_path_filters(value: str | None) -> list[str]:
    raw = _normalize_text(value)
    if not raw:
        return []
    parts: list[str] = []
    for candidate in raw.replace("\n", ",").split(","):
        item = candidate.strip()
        if item:
            parts.append(item)
    return parts


def _matches_branch_filter(filter_value: str | None, ref_value: str | None) -> bool:
    normalized_filter = _normalize_branch(filter_value)
    if not normalized_filter:
        return True
    ref = _normalize_text(ref_value)
    if not ref:
        return False
    return normalized_filter.casefold() == ref.casefold() or normalized_filter.casefold() == _normalize_branch(ref).casefold()


def _matches_path_filter(filter_value: str | None, paths: list[str]) -> bool:
    filters = _split_path_filters(filter_value)
    if not filters:
        return True
    if not paths:
        return False
    for pattern in filters:
        lowered_pattern = pattern.casefold()
        for path in paths:
            normalized_path = _normalize_text(path)
            if not normalized_path:
                continue
            if fnmatchcase(normalized_path.casefold(), lowered_pattern):
                return True
            if lowered_pattern in normalized_path.casefold():
                return True
    return False


def dispatch_normalized_event(connection: Any, logger: Any, normalized_event: dict[str, Any], metadata: dict[str, Any], root_dir: str | None = None, database_url: str | None = None) -> int:
    """Dispatch a normalized GitHub event into matching GitHub-trigger automations."""
    event_type = _normalize_text(normalized_event.get("event_type")).casefold()
    owner = _normalize_text(metadata.get("owner")).casefold()
    repo = _normalize_text(metadata.get("repo")).casefold()
    ref = _normalize_text(metadata.get("ref"))
    paths = [path for path in metadata.get("paths") or [] if _normalize_text(path)]

    if not event_type:
        write_application_log(
            logger,
            logging.INFO,
            "github_webhook_dispatch_skipped",
            reason="missing_event_type",
            owner=metadata.get("owner"),
            repo=metadata.get("repo"),
        )
        return 0

    matched_automation_ids: list[str] = []
    for automation_row in fetch_all(
        connection,
        """
        SELECT id, trigger_config_json
        FROM automations
        WHERE enabled = 1
          AND trigger_type = 'github'
        ORDER BY created_at ASC
        """,
    ):
        try:
            trigger_config = json.loads(automation_row["trigger_config_json"] or "{}")
        except json.JSONDecodeError:
            continue

        configured_owner = _normalize_text(trigger_config.get("github_owner")).casefold()
        configured_repo = _normalize_text(trigger_config.get("github_repo")).casefold()
        configured_event_types = [
            _normalize_text(item).casefold()
            for item in (trigger_config.get("github_events") or [])
            if _normalize_text(item)
        ]
        configured_event_type = _normalize_text(trigger_config.get("github_event_type")).casefold()
        if configured_event_type and configured_event_type not in configured_event_types:
            configured_event_types.append(configured_event_type)

        if configured_owner and configured_owner != owner:
            continue
        if configured_repo and configured_repo != repo:
            continue
        if configured_event_types and event_type not in configured_event_types:
            continue
        if not _matches_branch_filter(trigger_config.get("github_branch_filter"), ref):
            continue
        if not _matches_path_filter(trigger_config.get("github_path_filter"), paths):
            continue

        matched_automation_ids.append(str(automation_row["id"]))

    for automation_id in matched_automation_ids:
        execute_automation_definition(
            connection,
            logger,
            automation_id=automation_id,
            trigger_type="github",
            payload=normalized_event,
            root_dir=root_dir,
            database_url=database_url,
        )

    write_application_log(
        logger,
        logging.INFO,
        "github_webhook_dispatch",
        event_type=normalized_event.get("event_type"),
        owner=metadata.get("owner"),
        repo=metadata.get("repo"),
        matched_automations=len(matched_automation_ids),
    )
    return len(matched_automation_ids)


__all__ = [
    "verify_signature",
    "extract_delivery_id",
    "normalize_github_event",
    "dispatch_normalized_event",
]
