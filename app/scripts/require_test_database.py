#!/usr/bin/env python3
"""Bootstrap script for the test database environment.

Usage:
    python require_test_database.py [--phase {runtime,db_setup,full}]

Phases:
    runtime   Ensure the PostgreSQL server is reachable.
              If no external database URL is configured and the server is not
              running, attempt to start it via Homebrew (macOS local only).
    db_setup  Ensure the test database exists (creating it if needed), then
              reset it to a clean state by running migrations and truncating
              all application tables.  Every invocation produces a fresh
              environment — no prior test data is retained.
    full      Run runtime then db_setup (default when no --phase is given).
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.postgres_test_utils import get_test_database_url, reset_database


# ---------------------------------------------------------------------------
# Phase 1: ensure the PostgreSQL server runtime is reachable
# ---------------------------------------------------------------------------

def _is_postgres_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _start_postgres_via_homebrew() -> bool:
    """Attempt to start PostgreSQL using Homebrew services on macOS."""
    if shutil.which("brew") is None:
        return False

    result = subprocess.run(
        ["brew", "services", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False

    services = [
        line.split()[0]
        for line in result.stdout.splitlines()
        if line.split() and line.split()[0].startswith("postgresql")
    ]
    if not services:
        return False

    for service in services:
        subprocess.run(["brew", "services", "start", service], check=False)
    return True


def ensure_postgres_runtime(database_url: str) -> int:  # pragma: no cover - exercised by shell scripts
    """Return 0 if the Postgres server is reachable, 1 otherwise."""
    parsed = urlparse(database_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432

    # Explicit external URL provided → just verify reachability, no auto-start.
    external_url_set = bool(
        os.getenv("MALCOM_TEST_DATABASE_URL", "").strip()
        or os.getenv("MALCOM_DATABASE_URL", "").strip()
    )

    if _is_postgres_reachable(host, port):
        print(f"PostgreSQL runtime is reachable at {host}:{port}.")
        return 0

    if external_url_set:
        print(
            f"PostgreSQL bootstrap failed: server at {host}:{port} is not reachable. "
            "MALCOM_TEST_DATABASE_URL or MALCOM_DATABASE_URL is set but the server is not responding. "
            "Ensure the database runtime is running before invoking this script.",
            file=sys.stderr,
        )
        return 1

    print(f"PostgreSQL not reachable at {host}:{port}. Attempting Homebrew startup...")
    started = _start_postgres_via_homebrew()
    if not started:
        print(
            f"PostgreSQL bootstrap failed: server at {host}:{port} is not reachable and "
            "Homebrew was not available to start it. "
            "Install PostgreSQL (e.g. brew install postgresql@17) or set MALCOM_TEST_DATABASE_URL.",
            file=sys.stderr,
        )
        return 1

    print("Waiting for PostgreSQL to become responsive...")
    for _ in range(30):
        if _is_postgres_reachable(host, port):
            print(f"PostgreSQL runtime is now reachable at {host}:{port}.")
            return 0
        time.sleep(1)

    print(
        f"PostgreSQL bootstrap failed: server at {host}:{port} did not become reachable "
        "within 30 seconds after Homebrew start. Check 'brew services list'.",
        file=sys.stderr,
    )
    return 1


# ---------------------------------------------------------------------------
# Phase 2: ensure the test database exists and the schema is initialized
# ---------------------------------------------------------------------------

def _get_maintenance_url(database_url: str) -> tuple[str, str]:
    """Return (maintenance_url, db_name) for the given test database URL.

    The maintenance URL points to the 'postgres' system database on the same
    server so we can CREATE DATABASE without requiring the target DB to exist.
    """
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/") or "malcom_test"
    maintenance_parts = parsed._replace(path="/postgres")
    return urlunparse(maintenance_parts), db_name


def ensure_test_database(database_url: str) -> int:  # pragma: no cover - exercised by shell scripts
    """Ensure the test database exists, then reset it to a clean state.

    Every call drops all application data (via truncation) and re-applies
    migrations so each test-system.sh run starts from a deterministic, fresh
    environment.  Creating the database on first use is still handled here.

    Returns 0 on success, 1 on failure.
    """
    maintenance_url, db_name = _get_maintenance_url(database_url)

    # Create the database if it does not exist.
    try:
        import psycopg  # type: ignore[import]

        with psycopg.connect(maintenance_url, autocommit=True) as maint_conn:
            row = maint_conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
            ).fetchone()
            if row is None:
                maint_conn.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Created test database '{db_name}'.")
            else:
                print(f"Test database '{db_name}' exists; will reset to clean state.")
    except Exception as error:  # pragma: no cover
        print(
            f"DB setup failed: could not ensure test database '{db_name}' exists. "
            f"Original error: {error}",
            file=sys.stderr,
        )
        return 1

    # Reset: run migrations to head, then truncate all application tables so
    # every test run starts from a known-clean state.
    try:
        reset_database(database_url)
    except Exception as error:  # pragma: no cover
        print(
            f"DB setup failed while resetting the test database. "
            f"Original error: {error}",
            file=sys.stderr,
        )
        return 1

    print(f"Test database reset to clean state for {database_url}.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the test database environment.")
    parser.add_argument(
        "--phase",
        choices=["runtime", "db_setup", "full"],
        default="full",
        help=(
            "runtime: ensure the Postgres server is reachable (start via Homebrew if needed); "
            "db_setup: ensure the test DB exists and schema is initialized; "
            "full: run both phases in sequence (default)."
        ),
    )
    args = parser.parse_args()
    database_url = get_test_database_url()

    if args.phase in ("runtime", "full"):
        rc = ensure_postgres_runtime(database_url)
        if rc != 0:
            return rc

    if args.phase in ("db_setup", "full"):
        rc = ensure_test_database(database_url)
        if rc != 0:
            return rc

    if args.phase == "full":
        print(f"PostgreSQL test bootstrap complete (fresh environment) for {database_url}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
