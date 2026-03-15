from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class UiHtmlRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "tools").mkdir(parents=True, exist_ok=True)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        dist_dir = self.root_dir / "ui" / "dist"
        (dist_dir / "assets").mkdir(parents=True, exist_ok=True)

        html_pages = {
            "index.html": "<html><body>Home</body></html>",
            "dashboard/overview.html": "<html><body>Dashboard</body></html>",
            "dashboard/devices.html": "<html><body>Devices</body></html>",
            "dashboard/logs.html": "<html><body>Logs</body></html>",
            "scripts.html": "<html><body>Scripts Redirect</body></html>",
            "scripts/library.html": "<html><body>Script Library</body></html>",
            "apis/automation.html": "<html><body>API Automation</body></html>",
        }

        for relative_path, content in html_pages.items():
            destination = dist_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

        app.state.root_dir = self.root_dir
        app.state.db_path = str(self.root_dir / "backend" / "data" / "malcom.db")
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_serves_registered_html_pages_for_scripts_and_api_automation(self) -> None:
        for path in ("/scripts.html", "/scripts/library.html", "/apis/automation.html"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_redirects_scripts_root_to_scripts_html(self) -> None:
        response = self.client.get("/scripts", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers.get("location"), "/scripts.html")


if __name__ == "__main__":
    unittest.main()
