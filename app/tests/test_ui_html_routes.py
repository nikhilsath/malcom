from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.main import app
from backend.page_registry import get_redirect_ui_routes, get_served_ui_pages
from tests.postgres_test_utils import ensure_test_ui_scripts_dir, setup_postgres_test_app


class UiHtmlRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "tools").mkdir(parents=True, exist_ok=True)
        ensure_test_ui_scripts_dir(self.root_dir)
        (self.root_dir / "data" / "media").mkdir(parents=True, exist_ok=True)
        dist_dir = self.root_dir / "app" / "ui" / "dist"
        (dist_dir / "assets").mkdir(parents=True, exist_ok=True)
        (self.root_dir / "data" / "media" / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")

        for entry in get_served_ui_pages():
            destination = dist_dir / entry.source_html_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                f"<html><body>{entry.route_path}</body></html>",
                encoding="utf-8",
            )

        setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.tempdir.cleanup()

    def test_serves_registered_html_pages_for_canonical_routes(self) -> None:
        for entry in get_served_ui_pages():
            response = self.client.get(entry.route_path)
            self.assertEqual(response.status_code, 200, entry.route_path)
            self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_redirects_legacy_and_root_routes_from_registry(self) -> None:
        for route_path, expected_location in get_redirect_ui_routes():
            response = self.client.get(route_path, follow_redirects=False)
            self.assertEqual(response.status_code, 307, route_path)
            self.assertEqual(response.headers.get("location"), expected_location, route_path)

    def test_registry_is_the_only_source_of_ui_page_routes(self) -> None:
        expected_paths = {
            entry.route_path for entry in get_served_ui_pages()
        } | {route_path for route_path, _ in get_redirect_ui_routes()} | {"/favicon.ico"}

        actual_paths = {
            route.path
            for route in app.routes
            if isinstance(route, APIRoute)
            and "GET" in route.methods
            and not route.path.startswith("/api/")
            and route.path not in {"/docs", "/openapi.json", "/redoc", "/health"}
        }

        self.assertEqual(actual_paths, expected_paths)

    def test_registry_source_html_paths_match_real_ui_files(self) -> None:
        repo_ui_dir = Path(__file__).resolve().parents[2] / "app" / "ui"
        for entry in get_served_ui_pages():
            self.assertTrue((repo_ui_dir / entry.source_html_path).exists(), entry.source_html_path)

    def test_serves_favicon_from_media_directory(self) -> None:
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)


if __name__ == "__main__":
    unittest.main()
