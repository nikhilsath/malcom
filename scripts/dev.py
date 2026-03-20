#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
REQUIREMENTS_PATH = ROOT_DIR / "requirements.txt"
UI_DIR = ROOT_DIR / "ui"
UI_PACKAGE_LOCK = UI_DIR / "package-lock.json"
UI_PACKAGE_JSON = UI_DIR / "package.json"
UI_NODE_MODULES = UI_DIR / "node_modules"
UI_DIST_DIR = UI_DIR / "dist"
BACKEND_STAMP = VENV_DIR / ".malcom-requirements.sha256"
UI_DEPS_STAMP = UI_NODE_MODULES / ".malcom-package-lock.sha256"
UI_BUILD_STAMP = UI_DIST_DIR / ".malcom-build.sha256"


def print_status(message: str) -> None:
    print(f"[malcom] {message}", flush=True)


def run_command(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT_DIR, check=True)


def read_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_stamp(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def ensure_command_available(command_name: str) -> None:
    if shutil.which(command_name) is None:
        raise SystemExit(
            f"Required command '{command_name}' was not found in PATH. "
            f"Install it and run './malcom' again."
        )


def ensure_virtualenv() -> None:
    if VENV_PYTHON.exists():
        return

    ensure_command_available("python3")
    print_status("Creating root virtual environment.")
    run_command(["python3", "-m", "venv", str(VENV_DIR)])


def reexec_into_virtualenv() -> None:
    current_python = Path(sys.executable).resolve()

    if current_python == VENV_PYTHON.resolve():
        return

    print_status("Re-entering launcher with the project virtual environment.")
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


def ensure_backend_dependencies() -> None:
    requirements_hash = read_sha256(REQUIREMENTS_PATH)
    stored_hash = BACKEND_STAMP.read_text(encoding="utf-8").strip() if BACKEND_STAMP.exists() else ""

    if stored_hash == requirements_hash:
        print_status("Backend dependencies already up to date.")
        return

    print_status("Installing backend dependencies.")
    run_command([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    write_stamp(BACKEND_STAMP, requirements_hash)


def ensure_ui_dependencies() -> None:
    ensure_command_available("npm")
    ui_dependency_hash = hashlib.sha256(
        (read_sha256(UI_PACKAGE_JSON) + read_sha256(UI_PACKAGE_LOCK)).encode("utf-8")
    ).hexdigest()
    stored_hash = UI_DEPS_STAMP.read_text(encoding="utf-8").strip() if UI_DEPS_STAMP.exists() else ""

    if UI_NODE_MODULES.exists() and stored_hash == ui_dependency_hash:
        print_status("UI dependencies already up to date.")
        return

    print_status("Installing UI dependencies.")
    run_command(["npm", "ci"], cwd=UI_DIR)
    write_stamp(UI_DEPS_STAMP, ui_dependency_hash)


def iter_ui_build_inputs() -> list[Path]:
    paths: list[Path] = [UI_PACKAGE_JSON, UI_PACKAGE_LOCK]
    build_roots = [
        UI_DIR / "src",
        UI_DIR / "styles",
        UI_DIR / "scripts",
        UI_DIR / "dashboard",
        UI_DIR / "apis",
        UI_DIR / "tools",
    ]

    for candidate in sorted(UI_DIR.glob("*.html")):
        paths.append(candidate)

    for root in build_roots:
        if not root.exists():
            continue
        for candidate in sorted(path for path in root.rglob("*") if path.is_file()):
            paths.append(candidate)

    return paths


def ensure_ui_build() -> None:
    build_hash_source = "".join(
        f"{path.relative_to(UI_DIR)}:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        for path in iter_ui_build_inputs()
    )
    build_hash = hashlib.sha256(build_hash_source.encode("utf-8")).hexdigest()
    stored_hash = UI_BUILD_STAMP.read_text(encoding="utf-8").strip() if UI_BUILD_STAMP.exists() else ""

    if UI_DIST_DIR.exists() and stored_hash == build_hash:
        print_status("UI build already up to date.")
        return

    print_status("Building UI.")
    run_command(["npm", "run", "build"], cwd=UI_DIR)
    write_stamp(UI_BUILD_STAMP, build_hash)


def ensure_postgres_running() -> None:
    def is_postgres_responsive() -> bool:
        """Check if PostgreSQL is accepting connections."""
        try:
            sock = socket.create_connection(("127.0.0.1", 5432), timeout=2)
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def discover_brew_postgres_services() -> list[str]:
        result = subprocess.run(
            ["brew", "services", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        services: list[str] = []
        for line in result.stdout.splitlines():
            columns = line.split()
            if not columns:
                continue
            service_name = columns[0]
            if service_name.startswith("postgresql"):
                services.append(service_name)
        return services

    if is_postgres_responsive():
        print_status("PostgreSQL is already running.")
        return

    print_status("Starting PostgreSQL via Homebrew services...")

    if shutil.which("brew") is None:
        raise SystemExit(
            "Homebrew was not found in PATH. Install Homebrew and PostgreSQL, then run './malcom' again."
        )

    postgres_services = discover_brew_postgres_services()
    if not postgres_services:
        raise SystemExit(
            "PostgreSQL Homebrew service was not found. Install it with:\n"
            "  brew install postgresql@17\n"
            "Then run:\n"
            "  brew services start postgresql@17"
        )

    for service_name in postgres_services:
        subprocess.run(["brew", "services", "start", service_name], check=False)

    print_status("Waiting for PostgreSQL to be ready...")
    for attempt in range(30):
        if is_postgres_responsive():
            print_status("PostgreSQL is now responsive.")
            return
        if attempt < 29:
            time.sleep(1)

    raise SystemExit(
        "PostgreSQL failed to become responsive after 30 seconds.\n"
        "Try checking service status with: brew services list"
    )


def start_backend() -> None:
    print_status("Starting backend at http://127.0.0.1:8000")
    os.execv(
        str(VENV_PYTHON),
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
    )


def main() -> None:
    os.chdir(ROOT_DIR)
    ensure_virtualenv()
    reexec_into_virtualenv()
    ensure_backend_dependencies()
    ensure_ui_dependencies()
    ensure_ui_build()
    ensure_postgres_running()
    start_backend()


if __name__ == "__main__":
    main()
