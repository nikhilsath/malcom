"""Workflow file storage helpers.

Handles writing automation step payloads to files under the configured
workflow_storage_path setting.  CSV/table targets append rows to a single
canonical file; JSON targets create a new timestamped file by default, or
append newline-delimited JSON when storage_new_file is False.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKFLOW_STORAGE_LOCK = threading.Lock()


def _resolve_storage_dir(root_dir: Path, storage_path_setting: str) -> Path:
    """Return the absolute storage directory, creating it if needed."""
    if os.path.isabs(storage_path_setting):
        storage_dir = Path(storage_path_setting)
    else:
        storage_dir = root_dir / storage_path_setting
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def _atomic_write(dest: Path, data: bytes) -> None:
    """Write *data* to *dest* atomically using a temp file + rename."""
    fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def write_csv_row(
    storage_dir: Path,
    target: str,
    row: list[Any],
    *,
    headers: list[str] | None = None,
) -> Path:
    """Append *row* to <storage_dir>/<target>.csv, writing headers on first write."""
    dest = storage_dir / f"{target}.csv"
    with WORKFLOW_STORAGE_LOCK:
        write_headers = not dest.exists() and headers is not None
        with dest.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if write_headers:
                writer.writerow(headers)
            writer.writerow(row)
    return dest


def write_json_file(
    storage_dir: Path,
    target: str,
    payload: Any,
    *,
    new_file: bool = True,
) -> Path:
    """Write *payload* as JSON.

    When *new_file* is True (default) a new timestamped file is created for
    each call.  When False the payload is appended as a newline-delimited JSON
    record to a single canonical file.
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    if new_file:
        dest = storage_dir / f"{target}-{ts}.json"
        _atomic_write(dest, (json.dumps(payload, ensure_ascii=False) + "\n").encode())
    else:
        dest = storage_dir / f"{target}.json"
        with WORKFLOW_STORAGE_LOCK:
            with dest.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return dest


def write_other_file(storage_dir: Path, target: str, payload: Any) -> Path:
    """Fallback: write raw payload as a timestamped JSON file with a warning."""
    logger.warning(
        "workflow_storage: unknown storage_type; falling back to timestamped file for target %r",
        target,
    )
    return write_json_file(storage_dir, target, payload, new_file=True)


def execute_workflow_write(
    root_dir: Path,
    storage_path_setting: str,
    storage_type: str,
    target: str,
    payload: Any,
    *,
    new_file: bool = True,
) -> dict[str, str]:
    """Dispatch a file-write operation and return a result summary dict."""
    storage_dir = _resolve_storage_dir(root_dir, storage_path_setting)
    if storage_type in ("csv", "table"):
        row: list[Any]
        headers: list[str] | None = None
        if isinstance(payload, dict) and "row" in payload:
            row = list(payload["row"])
            headers = list(payload.get("headers", [])) or None
        elif isinstance(payload, list):
            row = payload
        else:
            row = [str(payload)]
        dest = write_csv_row(storage_dir, target, row, headers=headers)
    elif storage_type == "json":
        dest = write_json_file(storage_dir, target, payload, new_file=new_file)
    else:
        dest = write_other_file(storage_dir, target, payload)
    return {"file": str(dest), "storage_type": storage_type, "target": target}
