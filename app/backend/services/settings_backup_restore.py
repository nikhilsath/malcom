from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import SplitResult, urlsplit, urlunsplit

from backend.database import connect

DEFAULT_BACKUP_DIR = Path(__file__).resolve().parents[3] / "data" / "backups"


def get_backup_dir() -> Path:
    configured_dir = os.environ.get("MALCOM_BACKUP_DIR", "").strip()
    backup_dir = Path(configured_dir).expanduser() if configured_dir else DEFAULT_BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _timestamped_filename(prefix: str = "settings_backup", ext: str = ".dump") -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}{ext}"


def _get_database_url(db_url: Optional[str] = None) -> str:
    if db_url:
        return db_url
    try:
        from backend.database import get_database_url

        resolved = get_database_url()
    except Exception:
        resolved = os.environ.get("MALCOM_DATABASE_URL")

    if not resolved:
        raise RuntimeError("No database URL provided and MALCOM_DATABASE_URL is not set in environment or database.get_database_url() failed")
    return resolved


def _get_database_name(db_url: str) -> str:
    parsed = urlsplit(db_url)
    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise RuntimeError("Database URL must include a database name for backup/restore operations")
    return database_name


def _replace_database_name(db_url: str, database_name: str) -> str:
    parsed = urlsplit(db_url)
    updated = SplitResult(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=f"/{database_name}",
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(updated)


def _maintenance_database_url(db_url: str) -> str:
    parsed = urlsplit(db_url)
    if parsed.path.lstrip("/") == "postgres":
        return db_url
    return _replace_database_name(db_url, "postgres")


def _terminate_other_database_sessions(db_url: str) -> None:
    target_database = _get_database_name(db_url)
    maintenance_connection = connect(database_url=_maintenance_database_url(db_url))
    try:
        maintenance_connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = ?
              AND pid <> pg_backend_pid()
            """,
            (target_database,),
        )
        maintenance_connection.commit()
    finally:
        maintenance_connection.close()


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
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "size_bytes": size,
    }


def list_backups() -> List[Dict]:
    backup_dir = get_backup_dir()
    items = []
    for p in backup_dir.glob("*.dump"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, UTC)
        except OSError:
            mtime = datetime.now(UTC)
        items.append(
            {
                "filename": p.name,
                "path": str(p),
                "created_at": mtime.isoformat().replace("+00:00", "Z"),
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

    _terminate_other_database_sessions(db_url)
    cmd = [
        "pg_restore",
        "--dbname",
        db_url,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("pg_restore not found on PATH; install PostgreSQL client tools") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pg_restore failed: {exc.stderr or exc.stdout}") from exc

    return {
        "filename": filename,
        "restored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
