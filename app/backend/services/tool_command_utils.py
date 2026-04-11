"""Shared command resolution helpers for local tool runtimes."""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path


def verify_local_command_ready(command: str, *, working_dir: Path | None = None, tool_name: str = "Command") -> list[str]:
    command_parts = shlex.split(str(command or "").strip())
    if not command_parts:
        raise RuntimeError(f"{tool_name} command is invalid.")

    executable = command_parts[0]
    executable_path = Path(executable).expanduser()
    has_explicit_path = executable_path.is_absolute() or any(separator in executable for separator in ("/", "\\"))

    if has_explicit_path:
        if not executable_path.is_absolute() and working_dir is not None:
            executable_path = (working_dir / executable_path).resolve()
        if not executable_path.exists() or not os.access(executable_path, os.X_OK):
            raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")
        return command_parts

    if shutil.which(executable) is None:
        raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")

    return command_parts
