"""Repo checkout service.

Manages Git repository clones associated with `repo` type storage locations.
Provides clone/pull operations, path resolution, and size tracking.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.services.utils import utc_now_iso

logger = logging.getLogger(__name__)


# ── CRUD helpers ──────────────────────────────────────────────────────────────


def list_repo_checkouts(connection: Any) -> list[dict[str, Any]]:
    """Return all repo checkout rows."""
    rows = connection.execute(
        "SELECT * FROM repo_checkouts ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_repo_checkout(connection: Any, checkout_id: str) -> dict[str, Any] | None:
    """Return a single repo checkout row or None."""
    row = connection.execute(
        "SELECT * FROM repo_checkouts WHERE id = ?",
        (checkout_id,),
    ).fetchone()
    return dict(row) if row else None


def create_repo_checkout(connection: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a new repo checkout row and return it.

    Raises ValueError for missing or invalid fields.
    """
    checkout_id = payload.get("id") or f"repo_{os.urandom(5).hex()}"
    storage_location_id = (payload.get("storage_location_id") or "").strip()
    if not storage_location_id:
        raise ValueError("storage_location_id is required")

    repo_url = (payload.get("repo_url") or "").strip()
    if not repo_url:
        raise ValueError("repo_url is required")

    local_path = (payload.get("local_path") or "").strip()
    if not local_path:
        raise ValueError("local_path is required")

    branch = (payload.get("branch") or "main").strip() or "main"
    now = utc_now_iso()

    connection.execute(
        """
        INSERT INTO repo_checkouts (
            id, storage_location_id, repo_url, local_path, branch,
            last_synced_at, size_bytes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
        """,
        (checkout_id, storage_location_id, repo_url, local_path, branch, now, now),
    )
    connection.commit()
    result = get_repo_checkout(connection, checkout_id)
    if result is None:
        raise RuntimeError("Repo checkout was not found after insert")
    return result


def delete_repo_checkout(connection: Any, checkout_id: str) -> bool:
    """Delete a repo checkout row. Returns True if a row was deleted."""
    connection.execute("DELETE FROM repo_checkouts WHERE id = ?", (checkout_id,))
    connection.commit()
    return get_repo_checkout(connection, checkout_id) is None


# ── Checkout path resolution ──────────────────────────────────────────────────


def get_checkout_path(connection: Any, checkout_id: str) -> Path:
    """Return the local_path for a checkout as an absolute Path.

    Raises ValueError if the checkout row does not exist.
    """
    row = get_repo_checkout(connection, checkout_id)
    if row is None:
        raise ValueError(f"Repo checkout '{checkout_id}' does not exist")
    return Path(row["local_path"])


# ── Clone / pull logic ────────────────────────────────────────────────────────


def clone_or_pull_repo(
    connection: Any,
    checkout_id: str,
    *,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Clone the repo if missing or pull if it already exists.

    Returns a result dict with:
      - ``action``: ``"cloned"`` or ``"pulled"``
      - ``local_path``: path used
      - ``branch``: branch that was checked out
      - ``size_bytes``: measured size after operation
    """
    row = get_repo_checkout(connection, checkout_id)
    if row is None:
        raise ValueError(f"Repo checkout '{checkout_id}' does not exist")

    repo_url = row["repo_url"]
    local_path = Path(row["local_path"])
    branch = row.get("branch") or "main"

    git_dir = local_path / ".git"
    if git_dir.exists():
        action = "pulled"
        _git_pull(local_path, branch, timeout_seconds=timeout_seconds)
    else:
        action = "cloned"
        local_path.mkdir(parents=True, exist_ok=True)
        _git_clone(repo_url, local_path, branch, timeout_seconds=timeout_seconds)

    size_bytes = _measure_dir_bytes(local_path)
    now = utc_now_iso()

    connection.execute(
        """
        UPDATE repo_checkouts
        SET last_synced_at = ?, size_bytes = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, size_bytes, now, checkout_id),
    )
    connection.commit()

    return {
        "action": action,
        "local_path": str(local_path),
        "branch": branch,
        "size_bytes": size_bytes,
    }


def record_checkout_size(connection: Any, checkout_id: str) -> int:
    """Re-measure and persist the checkout size. Returns the measured byte count."""
    row = get_repo_checkout(connection, checkout_id)
    if row is None:
        raise ValueError(f"Repo checkout '{checkout_id}' does not exist")

    local_path = Path(row["local_path"])
    size_bytes = _measure_dir_bytes(local_path)
    now = utc_now_iso()

    connection.execute(
        "UPDATE repo_checkouts SET size_bytes = ?, updated_at = ? WHERE id = ?",
        (size_bytes, now, checkout_id),
    )
    connection.commit()
    return size_bytes


# ── Internal helpers ──────────────────────────────────────────────────────────


def _git_clone(repo_url: str, target: Path, branch: str, *, timeout_seconds: int) -> None:
    """Run git clone into *target* directory."""
    cmd = ["git", "clone", "--branch", branch, "--single-branch", repo_url, str(target)]
    logger.info("repo_checkout: cloning %s (branch=%s) → %s", repo_url, branch, target)
    try:
        subprocess.run(cmd, check=True, timeout=timeout_seconds, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git clone failed: {exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git clone timed out after {timeout_seconds}s") from exc


def _git_pull(local_path: Path, branch: str, *, timeout_seconds: int) -> None:
    """Run git pull in an existing checkout."""
    cmd = ["git", "-C", str(local_path), "pull", "origin", branch]
    logger.info("repo_checkout: pulling %s (branch=%s)", local_path, branch)
    try:
        subprocess.run(cmd, check=True, timeout=timeout_seconds, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git pull failed: {exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git pull timed out after {timeout_seconds}s") from exc


def _measure_dir_bytes(path: Path) -> int:
    """Return total bytes of all files under *path*."""
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


__all__ = [
    "clone_or_pull_repo",
    "create_repo_checkout",
    "delete_repo_checkout",
    "get_checkout_path",
    "get_repo_checkout",
    "list_repo_checkouts",
    "record_checkout_size",
]
