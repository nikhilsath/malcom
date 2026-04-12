from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class RealTestRunnerContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace_root = Path(__file__).resolve().parents[2]

    def _run_runner(self, script_path: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        artifact_dir = Path(tempfile.mkdtemp(prefix="runner-artifacts-"))
        environment = os.environ.copy()
        environment["MALCOM_TEST_ARTIFACT_DIR"] = str(artifact_dir)
        environment["MALCOM_TEST_DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:1/malcom_test"
        environment["SKIP_BROWSER_SUITE"] = "1"

        result = subprocess.run(
            ["bash", script_path],
            cwd=self.workspace_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

        return result, artifact_dir

    def _read_result_artifact(self, artifact_dir: Path) -> dict[str, object]:
        artifact_path = artifact_dir / "system-result.json"
        self.assertTrue(artifact_path.exists(), f"Missing canonical artifact: {artifact_path}")
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    def test_system_runner_writes_bootstrap_artifact_for_runtime_failure(self) -> None:
        result, artifact_dir = self._run_runner("app/scripts/test-system.sh")

        self.assertNotEqual(result.returncode, 0)
        data = self._read_result_artifact(artifact_dir)

        self.assertEqual(
            set(data),
            {"step", "exit_code", "command", "first_error_lines"},
        )
        self.assertEqual(data["step"], "bootstrap")
        self.assertEqual(
            data["command"],
            ".venv/bin/python app/scripts/require_test_database.py --phase runtime",
        )
        self.assertIsInstance(data["first_error_lines"], list)
        self.assertGreater(len(data["first_error_lines"]), 0)

    def test_failfast_wrapper_preserves_canonical_artifact_on_delegated_failure(self) -> None:
        result, artifact_dir = self._run_runner("app/scripts/test-real-failfast.sh")

        self.assertNotEqual(result.returncode, 0)
        data = self._read_result_artifact(artifact_dir)

        self.assertEqual(
            set(data),
            {"step", "exit_code", "command", "first_error_lines"},
        )
        self.assertEqual(data["step"], "bootstrap")
        self.assertFalse((artifact_dir / "failfast-result.json").exists())


if __name__ == "__main__":
    unittest.main()
