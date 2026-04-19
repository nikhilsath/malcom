from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.main import create_app


class MainAppFactoryTestCase(unittest.TestCase):
    def test_create_app_registers_platform_routes_and_legacy_ui_compatibility_mounts(self) -> None:
        app = create_app()
        paths = {route.path for route in app.routes}

        self.assertIn("/api/v1/tools", paths)
        self.assertIn("/api/v1/platform/bootstrap", paths)
        self.assertIn("/api/v1/inbound", paths)
        self.assertIn("/settings/workspace.html", paths)
        self.assertIn("/favicon.ico", paths)
        self.assertIn("/assets", paths)
        self.assertIn("/media", paths)
        self.assertIn("/scripts", paths)

    def test_create_app_can_disable_legacy_ui_serving(self) -> None:
        with patch.dict("os.environ", {"MALCOM_BACKEND_SERVE_UI": "false"}, clear=False):
            app = create_app()

        paths = {route.path for route in app.routes}

        self.assertIn("/api/v1/tools", paths)
        self.assertIn("/api/v1/platform/bootstrap", paths)
        self.assertIn("/favicon.ico", paths)
        self.assertIn("/media", paths)
        self.assertNotIn("/settings/workspace.html", paths)
        self.assertNotIn("/assets", paths)
        self.assertNotIn("/scripts", paths)


if __name__ == "__main__":
    unittest.main()
