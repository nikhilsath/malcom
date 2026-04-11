from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.database import connect
from tests.postgres_test_utils import get_test_database_url, reset_database


class StartupLifecycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace_root = Path(__file__).resolve().parents[2]
        self.app_dir = self.workspace_root / "app"
        self.database_url = get_test_database_url()
        logs_root = self.workspace_root / "data" / "logs"
        logs_root.mkdir(parents=True, exist_ok=True)
        self.log_tempdir = tempfile.TemporaryDirectory(dir=str(logs_root))
        self.log_dir = Path(self.log_tempdir.name)
        self.backup_tempdir = tempfile.TemporaryDirectory()
        self.backup_dir = Path(self.backup_tempdir.name)
        self.http_interactions: list[dict[str, object]] = []

        try:
            reset_database(self.database_url)
        except Exception as error:
            raise unittest.SkipTest(f"PostgreSQL test database is unavailable: {error}") from error

    def tearDown(self) -> None:
        self.backup_tempdir.cleanup()
        self.log_tempdir.cleanup()

    def _reserve_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _launch_backend(self, *, port: int, database_url: str) -> subprocess.Popen[str]:
        environment = os.environ.copy()
        environment["MALCOM_DATABASE_URL"] = database_url
        environment["MALCOM_SKIP_UI_BUILD_CHECK"] = "1"
        environment["MALCOM_BACKUP_DIR"] = str(self.backup_dir)

        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "--app-dir",
                str(self.app_dir),
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=self.workspace_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def _wait_for_health(self, *, port: int, timeout_seconds: float = 20.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1.0) as response:
                    if response.status == 200:
                        return True
            except URLError:
                pass
            time.sleep(0.2)
        return False

    def _stop_process(self, process: subprocess.Popen[str]) -> str:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        stdout, _ = process.communicate(timeout=10)
        return stdout or ""

    def _write_log_artifact(self, *, test_name: str, output: str) -> Path:
        artifact_path = self.log_dir / f"{test_name}.log"
        artifact_path.write_text(output, encoding="utf-8")
        return artifact_path

    def _write_json_artifact(self, *, test_name: str, payload: object) -> Path:
        artifact_path = self.log_dir / f"{test_name}.json"
        artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return artifact_path

    def _assert_backup_binaries_available(self) -> None:
        self.assertIsNotNone(
            shutil.which("pg_dump"),
            "pg_dump is required for real backup coverage. Install PostgreSQL client tools before running this suite.",
        )
        self.assertIsNotNone(
            shutil.which("pg_restore"),
            "pg_restore is required for real restore coverage. Install PostgreSQL client tools before running this suite.",
        )

    def _request_json(
        self,
        *,
        port: int,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        timeout_seconds: float = 10.0,
    ) -> tuple[int, dict[str, object], dict[str, str]]:
        body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = Request(
            f"http://127.0.0.1:{port}{path}",
            data=body_bytes,
            headers=headers,
            method=method.upper(),
        )
        response_status = 0
        response_body = ""
        response_headers: dict[str, str] = {}
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_status = response.status
                response_body = response.read().decode("utf-8")
                response_headers = dict(response.headers.items())
        except HTTPError as error:
            response_status = error.code
            response_body = error.read().decode("utf-8")
            response_headers = dict(error.headers.items())

        try:
            parsed_body = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError:
            parsed_body = {"raw_body": response_body}

        interaction = {
            "method": method.upper(),
            "path": path,
            "payload": payload,
            "status": response_status,
            "response_headers": response_headers,
            "response_body": parsed_body,
        }
        self.http_interactions.append(interaction)
        return response_status, parsed_body, response_headers

    def _wait_for_general_timezone(self, *, port: int, expected_timezone: str, timeout_seconds: float = 10.0) -> dict[str, object]:
        deadline = time.time() + timeout_seconds
        last_body: dict[str, object] = {}
        while time.time() < deadline:
            status, body, _ = self._request_json(port=port, method="GET", path="/api/v1/settings")
            if status == 200:
                general = body.get("general")
                if isinstance(general, dict) and general.get("timezone") == expected_timezone:
                    return body
                last_body = body
            time.sleep(0.2)
        self.fail(f"Timed out waiting for settings.general.timezone={expected_timezone!r}. Last response: {last_body}")

    def _read_general_settings_from_db(self) -> dict[str, object]:
        connection = connect(database_url=self.database_url)
        try:
            row = connection.execute("SELECT value_json FROM settings WHERE key = 'general'").fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row, "Expected a persisted general settings row in the test database")
        value_json = row["value_json"] if isinstance(row, dict) else None
        return json.loads(value_json or "{}")

    def test_launcher_starts_real_uvicorn_and_serves_health(self) -> None:
        port = self._reserve_port()
        process = self._launch_backend(port=port, database_url=self.database_url)
        output = ""

        try:
            started = self._wait_for_health(port=port)
            if not started:
                output = self._stop_process(process)
                artifact = self._write_log_artifact(
                    test_name="startup-launcher-health-failure",
                    output=output,
                )
                self.fail(
                    "Real startup launcher did not reach /health within timeout. "
                    f"Captured process output: {artifact}"
                )
        finally:
            if process.poll() is None:
                output = self._stop_process(process)
            if output.strip():
                self._write_log_artifact(test_name="startup-launcher-health-output", output=output)

    def test_launcher_can_create_and_restore_real_backup_while_running(self) -> None:
        self._assert_backup_binaries_available()
        port = self._reserve_port()
        process = self._launch_backend(port=port, database_url=self.database_url)
        output = ""

        try:
            started = self._wait_for_health(port=port)
            if not started:
                output = self._stop_process(process)
                artifact = self._write_log_artifact(
                    test_name="startup-launcher-live-restore-health-failure",
                    output=output,
                )
                self.fail(
                    "Real startup launcher did not reach /health before the live restore workflow. "
                    f"Captured process output: {artifact}"
                )

            patch_status, patch_body, _ = self._request_json(
                port=port,
                method="PATCH",
                path="/api/v1/settings",
                payload={"general": {"environment": "live", "timezone": "utc"}},
            )
            self.assertEqual(patch_status, 200, patch_body)
            self.assertEqual(patch_body["general"]["timezone"], "utc")

            create_status, create_body, _ = self._request_json(
                port=port,
                method="POST",
                path="/api/v1/settings/data/backups",
            )
            self.assertEqual(create_status, 200, create_body)
            self.assertTrue(create_body.get("ok"), create_body)
            backup = create_body.get("backup")
            self.assertIsInstance(backup, dict, create_body)
            backup_filename = str(backup.get("filename") or "")
            self.assertTrue(backup_filename, create_body)
            backup_path = Path(str(backup.get("path") or ""))
            self.assertTrue(backup_path.exists(), f"Expected backup file to exist: {backup_path}")
            self.assertEqual(backup_path.parent.resolve(), self.backup_dir.resolve())

            mutate_status, mutate_body, _ = self._request_json(
                port=port,
                method="PATCH",
                path="/api/v1/settings",
                payload={"general": {"environment": "live", "timezone": "local"}},
            )
            self.assertEqual(mutate_status, 200, mutate_body)
            self.assertEqual(mutate_body["general"]["timezone"], "local")

            live_body = self._wait_for_general_timezone(port=port, expected_timezone="local")
            self.assertEqual(live_body["general"]["timezone"], "local")

            restore_status, restore_body, _ = self._request_json(
                port=port,
                method="POST",
                path="/api/v1/settings/data/backups/restore",
                payload={"backup_id": backup_filename},
                timeout_seconds=30.0,
            )
            self.assertEqual(restore_status, 200, restore_body)
            self.assertTrue(restore_body.get("ok"), restore_body)
            self.assertIsNotNone(restore_body.get("restored_at"), restore_body)

            restored_body = self._wait_for_general_timezone(port=port, expected_timezone="utc")
            self.assertEqual(restored_body["general"]["timezone"], "utc")
        except Exception:
            self._write_json_artifact(
                test_name="startup-launcher-live-restore-http-interactions",
                payload=self.http_interactions,
            )
            raise
        finally:
            if process.poll() is None:
                output = self._stop_process(process)
            if output.strip():
                self._write_log_artifact(test_name="startup-launcher-live-restore-output", output=output)

        persisted_general = self._read_general_settings_from_db()
        self.assertEqual(persisted_general["timezone"], "utc")

    def test_launcher_captures_startup_errors_when_boot_fails(self) -> None:
        port = self._reserve_port()
        process = self._launch_backend(
            port=port,
            database_url="postgresql://postgres:postgres@127.0.0.1:1/malcom_startup_failure",
        )

        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired as error:
            output = self._stop_process(process)
            artifact = self._write_log_artifact(test_name="startup-launcher-boot-timeout", output=output)
            self.fail(
                "Expected startup launcher to fail with an unreachable database, but it stayed alive. "
                f"Captured process output: {artifact} ({error})"
            )
        output = self._stop_process(process)
        artifact = self._write_log_artifact(test_name="startup-launcher-boot-failure", output=output)

        self.assertNotEqual(
            process.returncode,
            0,
            "Expected startup launcher to fail when database URL is unreachable.",
        )
        self.assertRegex(
            output,
            r"(?is)(error|exception|traceback|connection refused|could not connect|operationalerror)",
            f"Startup failure output did not include error details. Captured process output: {artifact}",
        )


if __name__ == "__main__":
    unittest.main()
