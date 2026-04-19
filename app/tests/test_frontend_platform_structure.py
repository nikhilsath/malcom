from __future__ import annotations

import json
import unittest
from pathlib import Path


class FrontendPlatformStructureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace_root = Path(__file__).resolve().parents[2]
        self.frontend_root = self.workspace_root / "frontend"

    def test_separate_frontend_workspace_exists_with_host_sdk_and_plugins(self) -> None:
        self.assertTrue(self.frontend_root.exists(), "Expected a separate frontend workspace at frontend/")
        self.assertTrue((self.frontend_root / "apps" / "host" / "index.html").exists())
        self.assertTrue((self.frontend_root / "apps" / "host" / "main.js").exists())
        self.assertTrue((self.frontend_root / "packages" / "sdk" / "src" / "index.mjs").exists())
        self.assertTrue((self.frontend_root / "packages" / "host" / "src" / "plugin-runtime.mjs").exists())
        self.assertTrue((self.frontend_root / "plugins" / "index.mjs").exists())

    def test_frontend_workspace_declares_monorepo_packages(self) -> None:
        package_json = json.loads((self.frontend_root / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package_json["name"], "malcom-frontend-platform")
        self.assertIn("packages/*", package_json["workspaces"])
        self.assertIn("plugins/*", package_json["workspaces"])
        self.assertIn("test", package_json["scripts"])
        self.assertTrue((self.frontend_root / "apps").is_dir())
        self.assertTrue((self.frontend_root / "packages").is_dir())
        self.assertTrue((self.frontend_root / "plugins").is_dir())

    def test_first_party_plugin_packages_cover_core_product_areas(self) -> None:
        expected_plugins = {"dashboard", "automations", "apis", "tools", "scripts", "settings", "docs"}
        plugin_root = self.frontend_root / "plugins"
        actual_plugins = {
            path.name
            for path in plugin_root.iterdir()
            if path.is_dir() and (path / "package.json").exists()
        }
        self.assertEqual(actual_plugins, expected_plugins)

        plugin_index = (plugin_root / "index.mjs").read_text(encoding="utf-8")
        for plugin_name in sorted(expected_plugins):
            self.assertIn(f'./{plugin_name}/src/index.mjs', plugin_index)

    def test_workspace_packages_keep_root_package_metadata_needed_by_tooling(self) -> None:
        package_json_paths = sorted(self.frontend_root.glob("packages/*/package.json")) + sorted(
            self.frontend_root.glob("plugins/*/package.json")
        )
        self.assertGreater(len(package_json_paths), 0)

        for package_json_path in package_json_paths:
            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
            self.assertIn("name", package_json, f"Missing package name in {package_json_path}")
            self.assertTrue(package_json["name"], f"Empty package name in {package_json_path}")
            self.assertEqual(package_json.get("type"), "module", f"Expected ESM package in {package_json_path}")


if __name__ == "__main__":
    unittest.main()
