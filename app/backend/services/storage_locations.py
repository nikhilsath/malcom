"""Storage locations service.

Manages persisted storage destination rows (`storage_locations`) and
provides resolution logic used by the automation executor at runtime.

Location types:
  local       — directory on the local filesystem
  google_drive — folder on Google Drive, backed by a connector row
  repo        — local directory managed as a Git checkout root
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.services.utils import utc_now_iso

_VALID_LOCATION_TYPES = {"local", "google_drive", "repo"}


# ── CRUD helpers ──────────────────────────────────────────────────────────────


def list_storage_locations(connection: Any) -> list[dict[str, Any]]:
    """Return all storage location rows ordered by name."""
    rows = connection.execute(
        "SELECT * FROM storage_locations ORDER BY name"
    ).fetchall()
    return [dict(row) for row in rows]


def get_storage_location(connection: Any, location_id: str) -> dict[str, Any] | None:
    """Return a single storage location row or None."""
    row = connection.execute(
        "SELECT * FROM storage_locations WHERE id = ?",
        (location_id,),
    ).fetchone()
    return dict(row) if row else None


def create_storage_location(connection: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a new storage location row and return it.

    Raises ValueError for missing or invalid fields.
    """
    location_id = payload.get("id") or f"loc_{os.urandom(5).hex()}"
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")

    location_type = (payload.get("location_type") or "").strip().lower()
    if location_type not in _VALID_LOCATION_TYPES:
        raise ValueError(f"location_type must be one of: {', '.join(sorted(_VALID_LOCATION_TYPES))}")

    connector_id = payload.get("connector_id") or None
    if location_type == "google_drive" and not connector_id:
        raise ValueError("connector_id is required for google_drive locations")

    path = payload.get("path") or None
    folder_template = payload.get("folder_template") or None
    file_name_template = payload.get("file_name_template") or None
    max_size_mb = payload.get("max_size_mb")
    if max_size_mb is not None:
        max_size_mb = int(max_size_mb)
    is_default_logs = int(bool(payload.get("is_default_logs", False)))

    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO storage_locations (
            id, name, location_type, path, connector_id,
            folder_template, file_name_template, max_size_mb, is_default_logs,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            location_id, name, location_type, path, connector_id,
            folder_template, file_name_template, max_size_mb, is_default_logs,
            now, now,
        ),
    )
    connection.commit()
    result = get_storage_location(connection, location_id)
    if result is None:
        raise RuntimeError("Storage location was not found after insert")
    return result


def update_storage_location(
    connection: Any, location_id: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply a partial update to a storage location row.

    Returns the updated row, or None if the row does not exist.
    """
    row = get_storage_location(connection, location_id)
    if row is None:
        return None

    fields: dict[str, Any] = {}
    if "name" in payload:
        name = (payload["name"] or "").strip()
        if not name:
            raise ValueError("name cannot be empty")
        fields["name"] = name

    if "location_type" in payload:
        location_type = (payload["location_type"] or "").strip().lower()
        if location_type not in _VALID_LOCATION_TYPES:
            raise ValueError(f"location_type must be one of: {', '.join(sorted(_VALID_LOCATION_TYPES))}")
        fields["location_type"] = location_type

    for key in ("path", "connector_id", "folder_template", "file_name_template"):
        if key in payload:
            fields[key] = payload[key] or None

    if "max_size_mb" in payload:
        fields["max_size_mb"] = int(payload["max_size_mb"]) if payload["max_size_mb"] is not None else None

    if "is_default_logs" in payload:
        fields["is_default_logs"] = int(bool(payload["is_default_logs"]))

    if not fields:
        return row

    fields["updated_at"] = utc_now_iso()
    set_clause = ", ".join(f"{col} = ?" for col in fields)
    connection.execute(
        f"UPDATE storage_locations SET {set_clause} WHERE id = ?",
        (*fields.values(), location_id),
    )
    connection.commit()
    return get_storage_location(connection, location_id)


def delete_storage_location(connection: Any, location_id: str) -> bool:
    """Delete a storage location row. Returns True if a row was deleted."""
    connection.execute("DELETE FROM storage_locations WHERE id = ?", (location_id,))
    connection.commit()
    result = get_storage_location(connection, location_id)
    return result is None


# ── Resolution and quota ──────────────────────────────────────────────────────


def resolve_storage_location(
    connection: Any, location_id: str, *, root_dir: Path | None = None
) -> dict[str, Any]:
    """Resolve a storage location to its effective path or Drive folder ID.

    Returns a dict with:
      - ``location_type``: the row's location_type
      - ``path``: resolved absolute path (local/repo) or Drive folder ID (google_drive)
      - ``connector_id``: connector_id (google_drive only, else None)
      - ``folder_template``: folder template string or None
      - ``file_name_template``: file name template string or None
      - ``max_size_mb``: per-location quota or None
      - ``row``: the full original DB row dict
    """
    row = get_storage_location(connection, location_id)
    if row is None:
        raise ValueError(f"Storage location '{location_id}' does not exist")

    location_type = row["location_type"]
    raw_path = row.get("path") or ""

    if location_type == "google_drive":
        resolved_path = raw_path  # Drive folder ID
    else:
        # local or repo — make path absolute
        if raw_path and os.path.isabs(raw_path):
            resolved_path = raw_path
        elif raw_path and root_dir is not None:
            resolved_path = str(root_dir / raw_path)
        else:
            resolved_path = raw_path

    return {
        "location_type": location_type,
        "path": resolved_path,
        "connector_id": row.get("connector_id"),
        "folder_template": row.get("folder_template"),
        "file_name_template": row.get("file_name_template"),
        "max_size_mb": row.get("max_size_mb"),
        "row": row,
    }


def check_location_quota(
    connection: Any,
    location_id: str,
    bytes_to_write: int,
    *,
    root_dir: Path | None = None,
) -> None:
    """Raise RuntimeError if writing *bytes_to_write* would exceed the per-location quota.

    If the location has no ``max_size_mb`` set (None), the check passes unconditionally.
    Only enforced for local and repo location types (Google Drive quotas are managed
    by the Drive API itself).
    """
    resolved = resolve_storage_location(connection, location_id, root_dir=root_dir)
    max_mb = resolved.get("max_size_mb")
    if not max_mb:
        return

    location_type = resolved["location_type"]
    if location_type not in ("local", "repo"):
        return

    path = resolved["path"]
    if not path:
        return

    p = Path(path)
    if not p.exists():
        return

    current_bytes = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    limit_bytes = max_mb * 1024 * 1024
    if current_bytes + bytes_to_write > limit_bytes:
        raise RuntimeError(
            f"Storage location '{location_id}' would exceed its {max_mb} MB quota "
            f"(current: {current_bytes / (1024*1024):.1f} MB, "
            f"writing: {bytes_to_write / 1024:.1f} KB)"
        )


def get_current_location_usage(
    connection: Any,
    location_id: str,
    *,
    root_dir: Path | None = None,
) -> dict[str, Any]:
    """Return current disk usage stats for a storage location.

    Returns a dict with:
      - ``location_id``: the location id
      - ``size_bytes``: current size of all files under the path
      - ``size_mb``: size in megabytes (float)
      - ``max_size_mb``: quota or None
      - ``quota_used_pct``: percentage of quota used or None
    """
    resolved = resolve_storage_location(connection, location_id, root_dir=root_dir)
    max_mb = resolved.get("max_size_mb")
    path = resolved["path"]
    location_type = resolved["location_type"]

    size_bytes = 0
    if location_type in ("local", "repo") and path:
        p = Path(path)
        if p.exists():
            size_bytes = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    size_mb = size_bytes / (1024 * 1024)
    quota_used_pct = round((size_mb / max_mb) * 100, 1) if max_mb else None

    return {
        "location_id": location_id,
        "size_bytes": size_bytes,
        "size_mb": round(size_mb, 2),
        "max_size_mb": max_mb,
        "quota_used_pct": quota_used_pct,
    }


__all__ = [
    "check_location_quota",
    "create_storage_location",
    "delete_storage_location",
    "get_current_location_usage",
    "get_storage_location",
    "list_storage_locations",
    "resolve_storage_location",
    "update_storage_location",
]
