"""Automation run lifecycle helpers for creating, updating, and assigning runs.

Primary identifiers: ``calculate_duration_ms``, ``create_automation_run*``,
``finalize_automation_run*``, and ``assign_automation_run_worker``.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.database import fetch_one

DatabaseConnection = Any


def calculate_duration_ms(started_at: str, finished_at: str) -> int:
    started = datetime.fromisoformat(started_at)
    finished = datetime.fromisoformat(finished_at)
    return max(int((finished - started).total_seconds() * 1000), 0)


def create_automation_run(
    connection: DatabaseConnection,
    *,
    run_id: str,
    automation_id: str,
    trigger_type: str,
    status_value: str,
    worker_id: str | None = None,
    worker_name: str | None = None,
    started_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO automation_runs (
            run_id,
            automation_id,
            trigger_type,
            status,
            worker_id,
            worker_name,
            started_at,
            finished_at,
            duration_ms,
            error_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
        """,
        (run_id, automation_id, trigger_type, status_value, worker_id, worker_name, started_at),
    )
    connection.commit()


def create_automation_run_step(
    connection: DatabaseConnection,
    *,
    step_id: str,
    run_id: str,
    step_name: str,
    status_value: str,
    request_summary: str | None,
    started_at: str,
    inputs_json: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO automation_run_steps (
            step_id,
            run_id,
            step_name,
            status,
            request_summary,
            response_summary,
            started_at,
            finished_at,
            duration_ms,
            detail_json,
            inputs_json
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, ?)
        """,
        (step_id, run_id, step_name, status_value, request_summary, started_at, json.dumps(inputs_json) if inputs_json is not None else "{}"),
    )
    connection.commit()


def finalize_automation_run_step(
    connection: DatabaseConnection,
    *,
    step_id: str,
    status_value: str,
    response_summary: str | None,
    detail: dict[str, Any] | None,
    finished_at: str,
    response_body_json: Any | None = None,
    extracted_fields_json: dict[str, Any] | None = None,
) -> None:
    step_row = fetch_one(connection, "SELECT started_at FROM automation_run_steps WHERE step_id = ?", (step_id,))
    if step_row is None:
        return
    duration_ms = calculate_duration_ms(step_row["started_at"], finished_at)
    connection.execute(
        """
        UPDATE automation_run_steps
        SET status = ?,
            response_summary = ?,
            finished_at = ?,
            duration_ms = ?,
            detail_json = ?,
            response_body_json = ?,
            extracted_fields_json = ?
        WHERE step_id = ?
        """,
        (
            status_value,
            response_summary,
            finished_at,
            duration_ms,
            json.dumps(detail) if detail is not None else None,
            json.dumps(response_body_json) if response_body_json is not None else None,
            json.dumps(extracted_fields_json) if extracted_fields_json is not None else None,
            step_id,
        ),
    )
    connection.commit()


def finalize_automation_run(
    connection: DatabaseConnection,
    *,
    run_id: str,
    status_value: str,
    error_summary: str | None,
    finished_at: str,
) -> None:
    run_row = fetch_one(connection, "SELECT started_at FROM automation_runs WHERE run_id = ?", (run_id,))
    if run_row is None:
        return
    duration_ms = calculate_duration_ms(run_row["started_at"], finished_at)
    connection.execute(
        """
        UPDATE automation_runs
        SET status = ?,
            finished_at = ?,
            duration_ms = ?,
            error_summary = ?
        WHERE run_id = ?
        """,
        (status_value, finished_at, duration_ms, error_summary, run_id),
    )
    connection.commit()


def assign_automation_run_worker(connection: DatabaseConnection, *, run_id: str, worker_id: str, worker_name: str) -> None:
    connection.execute(
        """
        UPDATE automation_runs
        SET worker_id = ?, worker_name = ?
        WHERE run_id = ?
        """,
        (worker_id, worker_name, run_id),
    )
    connection.commit()


__all__ = [
    "assign_automation_run_worker",
    "calculate_duration_ms",
    "create_automation_run",
    "create_automation_run_step",
    "finalize_automation_run",
    "finalize_automation_run_step",
]
