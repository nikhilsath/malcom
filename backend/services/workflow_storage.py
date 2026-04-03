from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.runtime import RuntimeExecutionResult
import re


def slugify_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "runtime"


def _resolve_storage_dir(root_dir: Path, configured: str | None) -> Path:
    configured = str(configured or "backend/data/workflows")
    p = Path(configured)
    if not p.is_absolute():
        p = (root_dir / p).resolve()
    return p


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: bytes) -> None:
    dirpath = path.parent
    _ensure_dir(dirpath)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dirpath)) as tf:
        tf.write(data)
        tempname = Path(tf.name)
    os.replace(str(tempname), str(path))


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S")


def execute_file_write(
    logger,
    *,
    automation_id: str,
    step: Any,
    context: dict[str, Any],
    root_dir: Path,
    configured_path: str | None = None,
) -> RuntimeExecutionResult:
    storage_type = (step.config.storage_type or "json").lower()
    target_raw = (step.config.storage_target or step.name or "workflow-output").strip()
    target = slugify_identifier(target_raw)
    storage_dir = _resolve_storage_dir(root_dir, configured_path)
    _ensure_dir(storage_dir)

    payload = context.get("payload") or context

    try:
        if storage_type in ("csv", "table"):
            file_path = storage_dir / f"{target}.csv"
            is_new = not file_path.exists()
            # Determine headers from payload dict
            if isinstance(payload, dict):
                headers = list(payload.keys())
                row = [payload.get(h) for h in headers]
            else:
                # Fallback: single column 'value'
                headers = ["value"]
                row = [json.dumps(payload)]

            # Write/append atomically by building content then appending or writing
            if is_new:
                # write full CSV
                with tempfile.NamedTemporaryFile(delete=False, dir=str(storage_dir), mode="w", newline="", encoding="utf-8") as tf:
                    writer = csv.writer(tf)
                    writer.writerow(headers)
                    writer.writerow(row)
                    tempname = Path(tf.name)
                os.replace(str(tempname), str(file_path))
            else:
                # append row
                with open(file_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)

            logger.info("automation_file_write", extra={"automation_id": automation_id, "step_name": step.name, "path": str(file_path)})
            summary = f"Wrote CSV to {file_path.name} ({'created' if is_new else 'appended'})"
            return RuntimeExecutionResult(status="completed", response_summary=summary, detail={"path": str(file_path)}, output={})

        elif storage_type == "json":
            new_file_flag = True if step.config.storage_new_file is None else bool(step.config.storage_new_file)
            if new_file_flag:
                filename = f"{target}-{_timestamp()}.json"
            else:
                filename = f"{target}.json"
            file_path = storage_dir / filename

            data = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
            if new_file_flag:
                # atomic write of the single JSON file
                _atomic_write(file_path, data)
            else:
                # append newline-delimited JSON
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, default=str, ensure_ascii=False))
                    f.write("\n")

            logger.info("automation_file_write", extra={"automation_id": automation_id, "step_name": step.name, "path": str(file_path)})
            summary = f"Wrote JSON to {file_path.name}"
            return RuntimeExecutionResult(status="completed", response_summary=summary, detail={"path": str(file_path)}, output={})

        else:
            # Unknown type: dump raw payload to timestamped file
            filename = f"{target}-{_timestamp()}.bin"
            file_path = storage_dir / filename
            data = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
            _atomic_write(file_path, data)
            logger.warning("automation_file_write_unknown_type", extra={"automation_id": automation_id, "step_name": step.name, "path": str(file_path), "storage_type": storage_type})
            summary = f"Wrote payload to {file_path.name} (unknown storage_type: {storage_type})"
            return RuntimeExecutionResult(status="completed", response_summary=summary, detail={"path": str(file_path), "storage_type": storage_type}, output={})

    except Exception as e:
        logger.exception("automation_file_write_failed", extra={"automation_id": automation_id, "step_name": step.name, "error": str(e)})
        return RuntimeExecutionResult(status="failed", response_summary=str(e), detail={"error": str(e)}, output={})
