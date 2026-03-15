from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import connect, fetch_one
from backend.main import app


class ToolMetadataApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        self.db_path = self.root_dir / "backend" / "data" / "malcom.db"
        tools_dir = self.root_dir / "tools"
        manifest_dir = self.root_dir / "ui" / "scripts"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "convert-audio").mkdir(parents=True, exist_ok=True)
        (tools_dir / "convert-audio" / "tool.json").write_text(
            json.dumps(
                {
                    "id": "convert-audio",
                    "name": "Convert - Audio",
                    "description": "Convert audio files between supported formats for downstream processing.",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        app.state.root_dir = self.root_dir
        app.state.db_path = str(self.db_path)
        app.state.skip_ui_build_check = True
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.skip_ui_build_check = False
        self.tempdir.cleanup()

    def test_updates_tool_db_override_and_manifest(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio",
            json={
                "name": "Convert - Audio Pro",
                "description": "Convert and normalize audio files for downstream processing.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Convert - Audio Pro")
        self.assertEqual(
            body["description"],
            "Convert and normalize audio files for downstream processing.",
        )

        saved_metadata = json.loads((self.root_dir / "tools" / "convert-audio" / "tool.json").read_text(encoding="utf-8"))
        self.assertEqual(saved_metadata["name"], "Convert - Audio")

        connection = connect(self.db_path)
        try:
            saved_row = fetch_one(
                connection,
                """
                SELECT source_name, source_description, name_override, description_override
                FROM tools
                WHERE id = ?
                """,
                ("convert-audio",),
            )
        finally:
            connection.close()

        self.assertIsNotNone(saved_row)
        self.assertEqual(saved_row["source_name"], "Convert - Audio")
        self.assertEqual(saved_row["name_override"], "Convert - Audio Pro")
        self.assertEqual(
            saved_row["description_override"],
            "Convert and normalize audio files for downstream processing.",
        )

        manifest_source = (self.root_dir / "ui" / "scripts" / "tools-manifest.js").read_text(encoding="utf-8")
        self.assertIn("Convert - Audio Pro", manifest_source)
        self.assertIn("Convert and normalize audio files for downstream processing.", manifest_source)

    def test_rejects_empty_updates(self) -> None:
        response = self.client.patch("/api/v1/tools/convert-audio", json={})
        self.assertEqual(response.status_code, 400)

    def test_can_boot_without_built_ui_when_bypass_enabled(self) -> None:
        response = self.client.patch(
            "/api/v1/tools/convert-audio",
            json={"name": "Convert - Audio Runtime"},
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
