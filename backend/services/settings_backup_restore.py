from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_BACKUP_DIR = Path(__file__).resolve().parents[1] / "data" / "backups"


def get_backup_dir() -> Path:
    DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_BACKUP_DIR


def _timestamped_filename(prefix: str = "settings_backup", ext: str = ".dump") -> str:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}{ext}"


def _get_database_url(db_url: Optional[str] = None) -> str:
    resolved = db_url or os.environ.get("MALCOM_DATABASE_URL")
    if not resolved:
        raise RuntimeError("No database URL provided and MALCOM_DATABASE_URL is not set in environment")
    return resolved


def create_backup(db_url: Optional[str] = None, filename: Optional[str] = None) -> Dict:
    db_url = _get_database_url(db_url)
    backup_dir = get_backup_dir()
    filename = filename or _timestamped_filename()
    out_path = backup_dir / filename

    cmd = ["pg_dump", "--format=custom", "--file", str(out_path), "--dbname", db_url]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("pg_dump not found on PATH; install PostgreSQL client tools") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pg_dump failed: {exc.stderr or exc.stdout}") from exc

    size = out_path.stat().st_size if out_path.exists() else 0
    return {
        "filename": filename,
        "path": str(out_path),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "size_bytes": size,
    }


def list_backups() -> List[Dict]:
    backup_dir = get_backup_dir()
    items = []
    for p in backup_dir.glob("*.dump"):
        try:
            mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
        except OSError:
            mtime = datetime.utcnow()
        items.append(
            {
                "filename": p.name,
                "path": str(p),
                "created_at": mtime.isoformat() + "Z",
                "size_bytes": p.stat().st_size,
            }
        )
    items.sort(key=lambda i: i["created_at"], reverse=True)
    return items


def restore_backup(filename: str, db_url: Optional[str] = None) -> Dict:
    db_url = _get_database_url(db_url)
    backup_dir = get_backup_dir()
    path = backup_dir / filename
    if not path.exists():
        raise RuntimeError(f"Backup file not found: {path}")

    cmd = ["pg_restore", "--dbname", db_url, "--clean", "--if-exists", str(path)]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("pg_restore not found on PATH; install PostgreSQL client tools") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pg_restore failed: {exc.stderr or exc.stdout}") from exc

    return {"filename": filename, "restored_at": datetime.utcnow().isoformat() + "Z", "stdout": proc.stdout, "stderr": proc.stderr}
