from __future__ import annotations

import ast
import shlex
import sqlite3
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from backend.schemas import (
    ScriptResponse,
    ScriptSummaryResponse,
    ScriptValidationIssue,
    ScriptValidationResult,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_ui_dir(root_dir: Path) -> Path:
    return root_dir / "ui"


def build_script_validation_issue(message: str, *, line: int | None = None, column: int | None = None) -> ScriptValidationIssue:
    return ScriptValidationIssue(message=message, line=line, column=column)


def validate_python_script(code: str) -> ScriptValidationResult:
    try:
        ast.parse(code, mode="exec")
    except SyntaxError as error:
        return ScriptValidationResult(
            valid=False,
            issues=[
                build_script_validation_issue(
                    error.msg or "Invalid Python syntax.",
                    line=error.lineno,
                    column=error.offset,
                )
            ],
        )

    return ScriptValidationResult(valid=True, issues=[])


def validate_javascript_script(code: str, *, root_dir: Path) -> ScriptValidationResult:
    ui_dir = _get_ui_dir(root_dir)
    ui_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        prefix=".script-validation-",
        dir=ui_dir,
        encoding="utf-8",
        delete=False,
    ) as temporary_file:
        temporary_file.write(code)
        temporary_path = Path(temporary_file.name)

    try:
        result = subprocess.run(
            ["node", "--check", temporary_path.name],
            cwd=ui_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return ScriptValidationResult(
            valid=False,
            issues=[build_script_validation_issue("JavaScript validation requires Node.js to be installed on the server.")],
        )
    except subprocess.TimeoutExpired:
        return ScriptValidationResult(
            valid=False,
            issues=[build_script_validation_issue("JavaScript validation timed out before the syntax check completed.")],
        )
    finally:
        temporary_path.unlink(missing_ok=True)

    if result.returncode == 0:
        return ScriptValidationResult(valid=True, issues=[])

    stderr = (result.stderr or result.stdout).strip()
    issue_lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    issue_message = issue_lines[-1] if issue_lines else "Invalid JavaScript syntax."
    return ScriptValidationResult(valid=False, issues=[build_script_validation_issue(issue_message)])


def validate_script_payload(language: Literal["python", "javascript"], code: str, *, root_dir: Path) -> ScriptValidationResult:
    if language == "python":
        return validate_python_script(code)
    return validate_javascript_script(code, root_dir=root_dir)


def build_script_validation_fields(result: ScriptValidationResult) -> tuple[str, str | None, str | None]:
    if result.valid:
        return "valid", None, _utc_now_iso()

    first_issue = result.issues[0] if result.issues else build_script_validation_issue("Validation failed.")
    location = ""
    if first_issue.line is not None:
        location = f"Line {first_issue.line}"
        if first_issue.column is not None:
            location = f"{location}, column {first_issue.column}"
        location = f"{location}: "
    return "invalid", f"{location}{first_issue.message}", _utc_now_iso()


def row_to_script_summary(row: sqlite3.Row) -> ScriptSummaryResponse:
    return ScriptSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        language=row["language"],
        validation_status=row["validation_status"],
        validation_message=row["validation_message"],
        last_validated_at=row["last_validated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_script_response(row: sqlite3.Row) -> ScriptResponse:
    return ScriptResponse(
        **row_to_script_summary(row).model_dump(),
        code=row["code"],
    )


__all__ = [
    "build_script_validation_fields",
    "build_script_validation_issue",
    "row_to_script_response",
    "row_to_script_summary",
    "validate_javascript_script",
    "validate_python_script",
    "validate_script_payload",
]
