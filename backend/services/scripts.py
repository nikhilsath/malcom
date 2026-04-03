from __future__ import annotations

import ast
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from backend.schemas import (
    ScriptResponse,
    ScriptSummaryResponse,
    ScriptValidationIssue,
    ScriptValidationResult,
)
from backend.services.utils import utc_now_iso


DEFAULT_SCRIPT_LIBRARY: tuple[dict[str, str], ...] = (
    {
        "id": "script_seed_change_delimiter",
        "name": "Change Delimiter",
        "description": "Split text on one delimiter and join it with another.",
        "language": "python",
        "sample_input": json.dumps(
            {
                "text": "alpha,beta,gamma",
                "from": ",",
                "to": "|",
                "drop_empty": False,
            },
            indent=2,
        ),
        "code": "\n".join(
            [
                "def run(context, script_input=None):",
                "    params = script_input if isinstance(script_input, dict) else {}",
                "    payload = context.get('payload') if isinstance(context, dict) else {}",
                "    source_text = params.get('text')",
                "    if source_text is None and isinstance(payload, dict):",
                "        source_text = payload.get('text')",
                "    text = str(source_text or '')",
                "    source_delimiter = str(params.get('from') or ',')",
                "    target_delimiter = str(params.get('to') or '|')",
                "    drop_empty = bool(params.get('drop_empty', False))",
                "    output_lines = []",
                "    for raw_line in text.splitlines() or [text]:",
                "        pieces = [piece.strip() for piece in raw_line.split(source_delimiter)]",
                "        if drop_empty:",
                "            pieces = [piece for piece in pieces if piece]",
                "        output_lines.append(target_delimiter.join(pieces))",
                "    transformed = '\\n'.join(output_lines)",
                "    return {",
                "        'text': transformed,",
                "        'line_count': len(output_lines),",
                "        'from': source_delimiter,",
                "        'to': target_delimiter,",
                "    }",
                "",
            ]
        ),
    },
    {
        "id": "script_seed_extract_with_regex",
        "name": "Extract With Regex",
        "description": "Search text with a regex and return the requested capture or all matches.",
        "language": "python",
        "sample_input": json.dumps(
            {
                "text": "Invoice INV-1042 closed for 42.95 GBP",
                "pattern": "INV-(\\d+)",
                "group": 1,
                "flags": "i",
                "all_matches": False,
            },
            indent=2,
        ),
        "code": "\n".join(
            [
                "def run(context, script_input=None):",
                "    params = script_input if isinstance(script_input, dict) else {}",
                "    payload = context.get('payload') if isinstance(context, dict) else {}",
                "    source_text = params.get('text')",
                "    if source_text is None and isinstance(payload, dict):",
                "        source_text = payload.get('text')",
                "    text = str(source_text or '')",
                "    pattern = str(params.get('pattern') or '')",
                "    if not pattern:",
                "        return {'matches': [], 'count': 0}",
                "    flags = 0",
                "    flags_value = str(params.get('flags') or '').lower()",
                "    if 'i' in flags_value:",
                "        flags |= re.IGNORECASE",
                "    if 'm' in flags_value:",
                "        flags |= re.MULTILINE",
                "    if 's' in flags_value:",
                "        flags |= re.DOTALL",
                "    matcher = re.compile(pattern, flags)",
                "    group_value = params.get('group')",
                "    all_matches = bool(params.get('all_matches', True))",
                "    def resolve_match(match):",
                "        if match is None:",
                "            return None",
                "        if group_value in (None, ''):",
                "            if match.groupdict():",
                "                return match.groupdict()",
                "            return match.group(0)",
                "        if isinstance(group_value, str) and not group_value.isdigit():",
                "            return match.group(group_value)",
                "        return match.group(int(group_value))",
                "    if not all_matches:",
                "        value = resolve_match(matcher.search(text))",
                "        return {'match': value, 'count': 0 if value is None else 1}",
                "    matches = [resolve_match(match) for match in matcher.finditer(text)]",
                "    return {'matches': matches, 'count': len(matches)}",
                "",
            ]
        ),
    },
    {
        "id": "script_seed_regex_replace",
        "name": "Regex Replace",
        "description": "Replace text with a regular expression and report how many substitutions ran.",
        "language": "python",
        "sample_input": json.dumps(
            {
                "text": "order-001, order-002, order-003",
                "pattern": "order-(\\d+)",
                "replacement": "ticket-\\1",
                "flags": "",
                "count": 0,
            },
            indent=2,
        ),
        "code": "\n".join(
            [
                "def run(context, script_input=None):",
                "    params = script_input if isinstance(script_input, dict) else {}",
                "    payload = context.get('payload') if isinstance(context, dict) else {}",
                "    source_text = params.get('text')",
                "    if source_text is None and isinstance(payload, dict):",
                "        source_text = payload.get('text')",
                "    text = str(source_text or '')",
                "    pattern = str(params.get('pattern') or '')",
                "    replacement = str(params.get('replacement') or '')",
                "    flags = 0",
                "    flags_value = str(params.get('flags') or '').lower()",
                "    if 'i' in flags_value:",
                "        flags |= re.IGNORECASE",
                "    if 'm' in flags_value:",
                "        flags |= re.MULTILINE",
                "    if 's' in flags_value:",
                "        flags |= re.DOTALL",
                "    replace_count = int(params.get('count') or 0)",
                "    result_text, replacements = re.subn(pattern, replacement, text, count=replace_count, flags=flags)",
                "    return {'text': result_text, 'replacements': replacements}",
                "",
            ]
        ),
    },
)


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
    ui_dir = root_dir / "ui"
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
        return "valid", None, utc_now_iso()

    first_issue = result.issues[0] if result.issues else build_script_validation_issue("Validation failed.")
    location = ""
    if first_issue.line is not None:
        location = f"Line {first_issue.line}"
        if first_issue.column is not None:
            location = f"{location}, column {first_issue.column}"
        location = f"{location}: "
    return "invalid", f"{location}{first_issue.message}", utc_now_iso()


def seed_default_scripts(connection: Any, *, timestamp: str | None = None) -> None:
    now = timestamp or utc_now_iso()
    for script in DEFAULT_SCRIPT_LIBRARY:
        validation_result = validate_script_payload(script["language"], script["code"], root_dir=Path("."))
        validation_status, validation_message, last_validated_at = build_script_validation_fields(validation_result)
        connection.execute(
            """
            INSERT INTO scripts (
                id,
                name,
                description,
                language,
                sample_input,
                code,
                validation_status,
                validation_message,
                last_validated_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                script["id"],
                script["name"],
                script["description"],
                script["language"],
                script["sample_input"],
                script["code"],
                validation_status,
                validation_message,
                last_validated_at,
                now,
                now,
            ),
        )
    connection.commit()


def row_to_script_summary(row: dict[str, Any]) -> ScriptSummaryResponse:
    return ScriptSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        language=row["language"],
        sample_input=row["sample_input"] if "sample_input" in row else "",
        validation_status=row["validation_status"],
        validation_message=row["validation_message"],
        last_validated_at=row["last_validated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_script_response(row: dict[str, Any]) -> ScriptResponse:
    return ScriptResponse(
        **row_to_script_summary(row).model_dump(),
        code=row["code"],
    )


def get_scripts_metadata() -> dict[str, Any]:
    return {
        "languages": [
            {"value": "python", "label": "Python", "description": "Run with the Python script validator and runtime."},
            {
                "value": "javascript",
                "label": "JavaScript",
                "description": "Run with the JavaScript validator and runtime.",
            },
        ]
    }


__all__ = [
    "DEFAULT_SCRIPT_LIBRARY",
    "build_script_validation_fields",
    "build_script_validation_issue",
    "get_scripts_metadata",
    "row_to_script_response",
    "row_to_script_summary",
    "seed_default_scripts",
    "validate_javascript_script",
    "validate_python_script",
    "validate_script_payload",
]
