"""Managed Coqui TTS installation helpers for the repo virtualenv."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

COQUI_TTS_PACKAGE_NAME = "TTS"
COQUI_TTS_PACKAGE_SPEC_ENV = "MALCOM_COQUI_TTS_PACKAGE_SPEC"
COQUI_TTS_PACKAGE_NAME_ENV = "MALCOM_COQUI_TTS_PACKAGE_NAME"
COQUI_TTS_COMMAND_SOURCE_ENV = "MALCOM_COQUI_TTS_COMMAND_SOURCE"


@dataclass(frozen=True)
class CoquiTtsInstallationState:
    status: Literal["installed", "not_installed", "unavailable"]
    installed: bool
    install_available: bool
    remove_available: bool
    managed_command: str
    message: str


def get_repo_virtualenv_python_path(root_dir: Path) -> Path:
    if os.name == "nt":
        return (root_dir / ".venv" / "Scripts" / "python.exe").resolve()
    return (root_dir / ".venv" / "bin" / "python").resolve()


def get_repo_virtualenv_coqui_command_path(root_dir: Path) -> Path:
    if os.name == "nt":
        return (root_dir / ".venv" / "Scripts" / "tts.exe").resolve()
    return (root_dir / ".venv" / "bin" / "tts").resolve()


def get_coqui_tts_package_spec() -> str:
    return os.getenv(COQUI_TTS_PACKAGE_SPEC_ENV, "").strip() or COQUI_TTS_PACKAGE_NAME


def get_coqui_tts_package_name() -> str:
    return os.getenv(COQUI_TTS_PACKAGE_NAME_ENV, "").strip() or COQUI_TTS_PACKAGE_NAME


def get_coqui_tts_command_source_path() -> Path | None:
    raw_path = os.getenv(COQUI_TTS_COMMAND_SOURCE_ENV, "").strip()
    return Path(raw_path).expanduser().resolve() if raw_path else None


def get_coqui_tts_installation_state(root_dir: Path) -> CoquiTtsInstallationState:
    python_path = get_repo_virtualenv_python_path(root_dir)
    managed_command_path = get_repo_virtualenv_coqui_command_path(root_dir)
    managed_command = str(managed_command_path)

    if not python_path.exists() or not os.access(python_path, os.X_OK):
        return CoquiTtsInstallationState(
            status="unavailable",
            installed=False,
            install_available=False,
            remove_available=False,
            managed_command=managed_command,
            message=f"Repo virtualenv Python is unavailable at {python_path}.",
        )

    is_installed = managed_command_path.exists() and os.access(managed_command_path, os.X_OK)
    if is_installed:
        return CoquiTtsInstallationState(
            status="installed",
            installed=True,
            install_available=False,
            remove_available=True,
            managed_command=managed_command,
            message="Coqui TTS is installed in the repo virtualenv.",
        )

    return CoquiTtsInstallationState(
        status="not_installed",
        installed=False,
        install_available=True,
        remove_available=False,
        managed_command=managed_command,
        message="Coqui TTS is not installed in the repo virtualenv.",
    )


def _run_repo_virtualenv_pip(root_dir: Path, pip_args: list[str], *, action_label: str) -> None:
    python_path = get_repo_virtualenv_python_path(root_dir)
    state = get_coqui_tts_installation_state(root_dir)
    if state.status == "unavailable":
        raise RuntimeError(state.message)

    def _run_pip_command(*, break_system_packages: bool) -> None:
        env = os.environ.copy()
        if break_system_packages:
            # Homebrew-managed Python can still surface PEP 668 during repo-local installs.
            env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

        subprocess.run(
            [str(python_path), "-m", "pip", *pip_args],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root_dir),
            env=env,
        )

    try:
        _run_pip_command(break_system_packages=False)
    except subprocess.CalledProcessError as error:
        detail = "\n".join(
            part.strip() for part in (error.stderr or "", error.stdout or "") if part.strip()
        ) or "Unknown pip failure."
        normalized_detail = detail.lower()
        if "externally-managed-environment" in normalized_detail or "pep 668" in normalized_detail:
            try:
                _run_pip_command(break_system_packages=True)
                return
            except subprocess.CalledProcessError as retry_error:
                error = retry_error
                detail = "\n".join(
                    part.strip() for part in (retry_error.stderr or "", retry_error.stdout or "") if part.strip()
                ) or "Unknown pip failure."

        raise RuntimeError(f"Coqui TTS {action_label} failed: {detail}") from error


def _install_managed_command(root_dir: Path, source_path: Path) -> None:
    state = get_coqui_tts_installation_state(root_dir)
    if state.status == "unavailable":
        raise RuntimeError(state.message)
    if not source_path.exists() or not source_path.is_file():
        raise RuntimeError(f"Coqui TTS command source is unavailable at {source_path}.")

    managed_command_path = get_repo_virtualenv_coqui_command_path(root_dir)
    managed_command_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, managed_command_path)
    managed_command_path.chmod(0o755)


def _remove_managed_command(root_dir: Path) -> None:
    managed_command_path = get_repo_virtualenv_coqui_command_path(root_dir)
    if managed_command_path.exists():
        managed_command_path.unlink()


def install_coqui_tts_runtime(root_dir: Path) -> CoquiTtsInstallationState:
    state = get_coqui_tts_installation_state(root_dir)
    if state.installed:
        return state

    command_source_path = get_coqui_tts_command_source_path()
    if command_source_path is not None:
        _install_managed_command(root_dir, command_source_path)
    else:
        _run_repo_virtualenv_pip(
            root_dir,
            ["install", get_coqui_tts_package_spec()],
            action_label="installation",
        )
    next_state = get_coqui_tts_installation_state(root_dir)
    if not next_state.installed:
        raise RuntimeError("Coqui TTS installation completed, but the managed runtime command was not created.")
    return next_state


def remove_coqui_tts_runtime(root_dir: Path) -> CoquiTtsInstallationState:
    state = get_coqui_tts_installation_state(root_dir)
    if not state.installed:
        raise RuntimeError("Coqui TTS is not installed in the repo virtualenv.")

    if get_coqui_tts_command_source_path() is not None:
        _remove_managed_command(root_dir)
    else:
        _run_repo_virtualenv_pip(
            root_dir,
            ["uninstall", "-y", get_coqui_tts_package_name()],
            action_label="removal",
        )
    next_state = get_coqui_tts_installation_state(root_dir)
    if next_state.installed:
        raise RuntimeError("Coqui TTS removal completed, but the managed runtime command is still present.")
    return next_state
