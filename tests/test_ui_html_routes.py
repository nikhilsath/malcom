from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from tests.postgres_test_utils import setup_postgres_test_app


class UiHtmlRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "tools").mkdir(parents=True, exist_ok=True)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        dist_dir = self.root_dir / "ui" / "dist"
        (dist_dir / "assets").mkdir(parents=True, exist_ok=True)

        html_pages = {
            "dashboard/home.html": "<html><body>Dashboard</body></html>",
            "settings/workspace.html": "<html><body>Settings Workspace</body></html>",
            "settings/access.html": "<html><body>Settings Access</body></html>",
            "settings/connectors.html": "<html><body>Settings Connectors</body></html>",
            "apis/registry.html": "<html><body>APIs Registry</body></html>",
            "tools/catalog.html": "<html><body>Tools Catalog</body></html>",
            "scripts.html": "<html><body>Scripts Redirect</body></html>",
            "scripts/library.html": "<html><body>Script Library</body></html>",
            "apis/automation.html": "<html><body>API Automation</body></html>",
            "docs/search.html": "<html><body>Docs Search</body></html>",
            "docs/browse.html": "<html><body>Docs Browse</body></html>",
            "docs/create.html": "<html><body>Docs Create</body></html>",
        }

        for relative_path, content in html_pages.items():
            destination = dist_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

        setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_serves_registered_html_pages_for_canonical_routes(self) -> None:
        for path in (
            "/dashboard/home.html",
            "/settings/workspace.html",
            "/settings/access.html",
            "/settings/connectors.html",
            "/apis/registry.html",
            "/tools/catalog.html",
            "/scripts.html",
            "/scripts/library.html",
            "/apis/automation.html",
            "/docs/search.html",
            "/docs/browse.html",
            "/docs/create.html",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_redirects_legacy_and_root_routes_to_canonical_paths(self) -> None:
        redirect_expectations = {
            "/": "/dashboard/home.html",
            "/index.html": "/dashboard/home.html",
            "/dashboard": "/dashboard/home.html",
            "/dashboard/overview.html": "/dashboard/home.html",
            "/dashboard/devices.html": "/dashboard/home.html#/devices",
            "/dashboard/logs.html": "/dashboard/home.html#/logs",
            "/dashboard/queue.html": "/dashboard/home.html#/queue",
            "/settings": "/settings/workspace.html",
            "/settings.html": "/settings/workspace.html",
            "/settings/general.html": "/settings/workspace.html",
            "/settings/security.html": "/settings/access.html",
            "/apis": "/apis/registry.html",
            "/apis.html": "/apis/registry.html",
            "/apis/overview.html": "/apis/registry.html",
            "/tools": "/tools/catalog.html",
            "/tools.html": "/tools/catalog.html",
            "/tools/overview.html": "/tools/catalog.html",
            "/scripts": "/scripts.html",
            "/docs": "/docs/search.html",
            "/docs/": "/docs/search.html",
        }

        for path, expected_location in redirect_expectations.items():
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 307, path)
            self.assertEqual(response.headers.get("location"), expected_location, path)


if __name__ == "__main__":
    unittest.main()
