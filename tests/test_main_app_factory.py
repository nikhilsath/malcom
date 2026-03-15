from __future__ import annotations

import unittest

from backend.main import create_app


class MainAppFactoryTestCase(unittest.TestCase):
    def test_create_app_registers_core_routes_and_static_mounts(self) -> None:
        app = create_app()
        paths = {route.path for route in app.routes}

        self.assertIn("/api/v1/tools", paths)
        self.assertIn("/api/v1/inbound", paths)
        self.assertIn("/settings/workspace.html", paths)
        self.assertIn("/assets", paths)
        self.assertIn("/scripts", paths)


if __name__ == "__main__":
    unittest.main()
