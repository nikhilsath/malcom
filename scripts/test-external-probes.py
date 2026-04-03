#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import connect, get_database_url, initialize
from backend.services.connectors import build_connector_catalog
from backend.tool_registry import DEFAULT_TOOL_CATALOG


CONNECTOR_PROBES: dict[str, dict[str, Any]] = {
    "google_calendar": {
        "probe_type": "external_endpoint",
        "probe_candidate": "GET /users/me/calendarList",
        "confidence": "inferred",
        "credentials": ["oauth2 access token"],
        "notes": "Uses the provider base URL and a low-impact list/read pattern.",
    },
    "google_sheets": {
        "probe_type": "no_safe_generic_endpoint",
        "probe_candidate": None,
        "confidence": "high",
        "credentials": ["oauth2 access token", "spreadsheet id"],
        "notes": "No provider-agnostic sheet probe is available without a target spreadsheet.",
    },
    "github": {
        "probe_type": "external_endpoint",
        "probe_candidate": "GET /user",
        "confidence": "high",
        "credentials": ["oauth2 access token or bearer token"],
        "notes": "Common authenticated identity probe for GitHub REST APIs.",
    },
    "notion": {
        "probe_type": "external_endpoint",
        "probe_candidate": "GET /users/me",
        "confidence": "high",
        "credentials": ["oauth2 access token or bearer token"],
        "notes": "Low-impact identity probe for Notion integrations.",
    },
    "trello": {
        "probe_type": "external_endpoint",
        "probe_candidate": "GET /members/me",
        "confidence": "high",
        "credentials": ["api key plus token or header credential"],
        "notes": "Standard identity probe for Trello REST integrations.",
    },
}

TOOL_PROBES: dict[str, dict[str, Any]] = {
    "smtp": {
        "probe_type": "internal_route",
        "probe_candidate": "POST /api/v1/tools/smtp/send-relay",
        "confidence": "high",
        "credentials": ["relay host", "relay port", "mail_from", "recipients"],
        "notes": "Best exercised against a disposable inbox or non-production relay.",
    },
    "llm-deepl": {
        "probe_type": "external_endpoint",
        "probe_candidate": "GET configured models endpoint",
        "confidence": "inferred",
        "credentials": ["local model server base URL"],
        "notes": "Use the configured models endpoint such as /v1/models or /api/v1/models.",
    },
    "coqui-tts": {
        "probe_type": "local_runtime",
        "probe_candidate": "configured command --help",
        "confidence": "high",
        "credentials": ["local CLI installed"],
        "notes": "This is a local CLI/runtime check rather than an external HTTP probe.",
    },
}


def load_runtime_state() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    connector_records: dict[str, dict[str, Any]] = {}
    tool_records: dict[str, dict[str, Any]] = {}

    try:
        connection = connect(database_url=get_database_url())
        initialize(connection)
    except Exception:
        return connector_records, tool_records

    try:
        connector_row = connection.execute(
            """
            SELECT value_json
            FROM settings
            WHERE key = 'connectors'
            """
        ).fetchone()
        if connector_row and connector_row["value_json"]:
            payload = json.loads(connector_row["value_json"])
            for record in payload.get("records", []):
                connector_records[str(record.get("id") or "")] = record

        tool_rows = connection.execute(
            """
            SELECT id, enabled, name_override, description_override, source_name, source_description
            FROM tools
            ORDER BY id
            """
        ).fetchall()
        for row in tool_rows:
            tool_records[str(row["id"])] = {
                "enabled": bool(row["enabled"]),
                "name": row["name_override"] or row["source_name"],
                "description": row["description_override"] or row["source_description"],
            }
    finally:
        connection.close()

    return connector_records, tool_records


def build_report() -> dict[str, Any]:
    connector_records, tool_records = load_runtime_state()

    connectors = []
    for preset in build_connector_catalog():
        probe = CONNECTOR_PROBES.get(preset["id"], {})
        configured_records = [
            {
                "id": record.get("id"),
                "status": record.get("status"),
                "auth_type": record.get("auth_type"),
                "last_tested_at": record.get("last_tested_at"),
            }
            for record in connector_records.values()
            if record.get("provider") == preset["id"]
        ]
        connectors.append(
            {
                "id": preset["id"],
                "name": preset["name"],
                "base_url": preset["base_url"],
                "docs_url": preset["docs_url"],
                "configured_records": configured_records,
                "probe": probe or None,
            }
        )

    tools = []
    for tool in DEFAULT_TOOL_CATALOG:
        tool_state = tool_records.get(tool["id"], {})
        tools.append(
            {
                "id": tool["id"],
                "name": tool_state.get("name", tool["name"]),
                "enabled": bool(tool_state.get("enabled", False)),
                "probe": TOOL_PROBES.get(tool["id"]) or None,
            }
        )

    return {
        "database_url": get_database_url(),
        "connectors": connectors,
        "tools": tools,
        "notes": [
            "Probe candidates are informational and do not block commits.",
            "Confidence values marked 'inferred' come from existing repo metadata and common provider patterns.",
        ],
    }


def main() -> int:
    print(json.dumps(build_report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
