from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.database import fetch_one
from backend.services.automation_execution import execute_script_step, write_application_log
from backend.services.repo_checkout_service import clone_or_pull_repo, get_checkout_path, record_checkout_size


def execute_script_step_wrapper(connection: Any, logger: logging.Logger, *, automation_id: str, step: Any, context: dict[str, Any], root_dir: Path) -> dict:
    script_row = fetch_one(connection, "SELECT * FROM scripts WHERE id = ?", (step.config.script_id,))
    if script_row is None:
        return {"error": f"Script '{step.config.script_id}' was not found."}

    effective_root_dir = root_dir
    repo_checkout_id = getattr(step.config, "repo_checkout_id", None)
    if repo_checkout_id:
        try:
            clone_or_pull_repo(connection, repo_checkout_id)
        except (ValueError, RuntimeError) as exc:
            write_application_log(
                logger,
                logging.WARNING,
                "repo_checkout_sync_failed",
                automation_id=automation_id,
                step_name=step.name,
                checkout_id=repo_checkout_id,
                error=str(exc),
            )
        try:
            checkout_path = get_checkout_path(connection, repo_checkout_id)
            working_dir = getattr(step.config, "working_directory", None)
            if working_dir:
                effective_root_dir = checkout_path / working_dir.lstrip("/")
            else:
                effective_root_dir = checkout_path
        except ValueError:
            pass

    result = execute_script_step(
        script_row,
        context,
        root_dir=effective_root_dir,
        script_input_template=step.config.script_input_template,
    )

    if repo_checkout_id:
        try:
            record_checkout_size(connection, repo_checkout_id)
        except (ValueError, RuntimeError):
            pass

    return {"runtime_result": result}
