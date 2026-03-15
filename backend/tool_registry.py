from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.database import connect, fetch_all, fetch_one, initialize

REQUIRED_FIELDS = ("id", "name", "description")
DEFAULT_TOOL_CATALOG: tuple[dict, ...] = (
    {
        "id": "coqui-tts",
        "name": "Coqui TTS",
        "description": "Generate speech audio from workflow text using a locally installed Coqui TTS runtime.",
        "inputs": [
            {"key": "text", "label": "Text to Speak", "type": "text", "required": True},
            {"key": "output_filename", "label": "Output Filename", "type": "string", "required": False},
            {"key": "speaker", "label": "Speaker Override", "type": "string", "required": False},
            {"key": "language", "label": "Language Override", "type": "string", "required": False},
        ],
        "outputs": [
            {"key": "audio_file_path", "label": "Audio File Path", "type": "string"},
        ],
    },
    {
        "id": "llm-deepl",
        "name": "Local LLM",
        "description": "Run a locally hosted language model through configurable OpenAI-compatible or LM Studio endpoints.",
        "inputs": [
            {"key": "system_prompt", "label": "System Prompt", "type": "text", "required": False},
            {"key": "user_prompt", "label": "User Prompt", "type": "text", "required": True},
            {"key": "model_identifier", "label": "Model Identifier Override", "type": "string", "required": False},
        ],
        "outputs": [
            {"key": "response_text", "label": "Response Text", "type": "string"},
            {"key": "model_used", "label": "Model Used", "type": "string"},
        ],
    },
    {
        "id": "smtp",
        "name": "SMTP",
        "description": "Send an email through an external SMTP relay from within a workflow step.",
        "inputs": [
            {"key": "relay_host", "label": "Relay Host", "type": "string", "required": True},
            {"key": "relay_port", "label": "Relay Port", "type": "number", "required": True},
            {"key": "relay_security", "label": "Security", "type": "select", "required": False, "options": ["none", "starttls", "tls"]},
            {"key": "relay_username", "label": "Username", "type": "string", "required": False},
            {"key": "relay_password", "label": "Password", "type": "string", "required": False},
            {"key": "from_address", "label": "From Address", "type": "string", "required": True},
            {"key": "to", "label": "To", "type": "string", "required": True},
            {"key": "subject", "label": "Subject", "type": "string", "required": True},
            {"key": "body", "label": "Body", "type": "text", "required": True},
        ],
        "outputs": [
            {"key": "status", "label": "Status", "type": "string"},
            {"key": "message", "label": "Message", "type": "string"},
        ],
    },
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_manifest_path(root_dir: Path) -> Path:
    return root_dir / "ui" / "scripts" / "tools-manifest.js"


def validate_tool_metadata(metadata: dict[str, object], directory_name: str) -> dict:
    validated: dict = {}

    for field in REQUIRED_FIELDS:
        value = metadata.get(field)
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f'Missing required field "{field}" for tool "{directory_name}"')
        validated[field] = value

    if validated["id"] != directory_name:
        raise ValueError(f'Tool id "{validated["id"]}" must match folder name "{directory_name}"')

    validated["inputs"] = metadata.get("inputs") or []
    validated["outputs"] = metadata.get("outputs") or []

    return validated


def discover_tools(root_dir: Path | None = None) -> list[dict[str, str]]:
    _ = root_dir
    seen_ids: set[str] = set()
    tools: list[dict[str, str]] = []

    for metadata in DEFAULT_TOOL_CATALOG:
        validated = validate_tool_metadata(metadata, str(metadata.get("id") or ""))
        if validated["id"] in seen_ids:
            raise ValueError(f'Duplicate tool id "{validated["id"]}" in default tool catalog')
        seen_ids.add(validated["id"])
        tools.append(validated)

    return tools


def row_to_tool_metadata(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name_override"] or row["source_name"],
        "description": row["description_override"] or row["source_description"],
        "pageHref": f"tools/{row['id']}.html",
        "inputs": json.loads(row["inputs_schema_json"] or "[]"),
        "outputs": json.loads(row["outputs_schema_json"] or "[]"),
    }


def row_to_tool_directory_entry(row: sqlite3.Row, *, enabled: bool | None = None) -> dict[str, object]:
    resolved_enabled = bool(row["enabled"]) if enabled is None else enabled
    return {
        "id": row["id"],
        "name": row["name_override"] or row["source_name"],
        "description": row["description_override"] or row["source_description"],
        "enabled": resolved_enabled,
        "page_href": f"/tools/{row['id']}.html",
    }


def sync_tools_to_database(root_dir: Path, connection: sqlite3.Connection) -> list[dict[str, str]]:
    discovered_tools = discover_tools(root_dir)
    known_tool_ids = [tool["id"] for tool in discovered_tools]
    now = utc_now_iso()

    for tool in discovered_tools:
        existing = fetch_one(
            connection,
            """
            SELECT id, source_name, source_description,
                   inputs_schema_json, outputs_schema_json
            FROM tools
            WHERE id = ?
            """,
            (tool["id"],),
        )

        inputs_json = json.dumps(tool.get("inputs") or [])
        outputs_json = json.dumps(tool.get("outputs") or [])

        if existing is None:
            connection.execute(
                """
                INSERT INTO tools (
                    id,
                    source_name,
                    source_description,
                    enabled,
                    name_override,
                    description_override,
                    inputs_schema_json,
                    outputs_schema_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, 0, NULL, NULL, ?, ?, ?, ?)
                """,
                (tool["id"], tool["name"], tool["description"], inputs_json, outputs_json, now, now),
            )
            continue

        if (
            existing["source_name"] != tool["name"]
            or existing["source_description"] != tool["description"]
            or existing["inputs_schema_json"] != inputs_json
            or existing["outputs_schema_json"] != outputs_json
        ):
            connection.execute(
                """
                UPDATE tools
                SET source_name = ?, source_description = ?,
                    inputs_schema_json = ?, outputs_schema_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (tool["name"], tool["description"], inputs_json, outputs_json, now, tool["id"]),
            )

    if known_tool_ids:
        placeholders = ", ".join("?" for _ in known_tool_ids)
        connection.execute(
            f"DELETE FROM tools WHERE id NOT IN ({placeholders})",
            tuple(known_tool_ids),
        )
    else:
        connection.execute("DELETE FROM tools")

    connection.commit()
    return discovered_tools


def load_tools_manifest(root_dir: Path, connection: sqlite3.Connection | None = None) -> list[dict[str, str]]:
    managed_connection = connection is None
    db = connection or connect()

    try:
        initialize(db)
        sync_tools_to_database(root_dir, db)
        rows = fetch_all(
            db,
            """
            SELECT id, source_name, source_description, name_override, description_override,
                   enabled, inputs_schema_json, outputs_schema_json
            FROM tools
            ORDER BY id
            """,
        )
        return [row_to_tool_metadata(row) for row in rows]
    finally:
        if managed_connection:
            db.close()


def write_tools_manifest(root_dir: Path, connection: sqlite3.Connection | None = None) -> list[dict[str, str]]:
    tools = load_tools_manifest(root_dir, connection)
    manifest_source = [
        f"export const toolsManifest = Object.freeze({json.dumps(tools, indent=2)});",
        "",
        'if (typeof window !== "undefined") {',
        "  window.TOOLS_MANIFEST = toolsManifest;",
        "}",
        "",
    ]
    get_manifest_path(root_dir).write_text("\n".join(manifest_source), encoding="utf-8")
    return tools


def update_tool_metadata(
    root_dir: Path,
    connection: sqlite3.Connection,
    tool_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, str]:
    sync_tools_to_database(root_dir, connection)
    row = fetch_one(
        connection,
        """
        SELECT id, source_name, source_description, name_override, description_override,
               enabled, inputs_schema_json, outputs_schema_json
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )

    if row is None:
        raise FileNotFoundError(tool_id)

    next_name_override = row["name_override"]
    next_description_override = row["description_override"]

    if name is not None:
        next_name_override = None if name == row["source_name"] else name

    if description is not None:
        next_description_override = None if description == row["source_description"] else description

    connection.execute(
        """
        UPDATE tools
        SET name_override = ?, description_override = ?, updated_at = ?
        WHERE id = ?
        """,
        (next_name_override, next_description_override, utc_now_iso(), tool_id),
    )
    connection.commit()
    write_tools_manifest(root_dir, connection)

    updated_row = fetch_one(
        connection,
        """
        SELECT id, source_name, source_description, name_override, description_override,
               enabled, inputs_schema_json, outputs_schema_json
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )

    if updated_row is None:
        raise FileNotFoundError(tool_id)

    return row_to_tool_metadata(updated_row)


def set_tool_enabled(
    root_dir: Path,
    connection: sqlite3.Connection,
    tool_id: str,
    *,
    enabled: bool,
) -> dict[str, object]:
    sync_tools_to_database(root_dir, connection)
    row = fetch_one(
        connection,
        """
        SELECT id
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )

    if row is None:
        raise FileNotFoundError(tool_id)

    connection.execute(
        """
        UPDATE tools
        SET enabled = ?, updated_at = ?
        WHERE id = ?
        """,
        (int(enabled), utc_now_iso(), tool_id),
    )
    connection.commit()

    updated_row = fetch_one(
        connection,
        """
        SELECT id, source_name, source_description, name_override, description_override, enabled
        FROM tools
        WHERE id = ?
        """,
        (tool_id,),
    )
    if updated_row is None:
        raise FileNotFoundError(tool_id)

    return row_to_tool_directory_entry(updated_row)


def load_tool_directory(root_dir: Path, connection: sqlite3.Connection | None = None) -> list[dict[str, object]]:
    managed_connection = connection is None
    db = connection or connect()

    try:
        initialize(db)
        sync_tools_to_database(root_dir, db)
        rows = fetch_all(
            db,
            """
            SELECT id, source_name, source_description, name_override, description_override, enabled
            FROM tools
            ORDER BY id
            """,
        )
        return [row_to_tool_directory_entry(row) for row in rows]
    finally:
        if managed_connection:
            db.close()
