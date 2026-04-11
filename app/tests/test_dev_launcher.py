from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


class ExecIntercept(RuntimeError):
    """Raised when a test intercepts launcher os.execv."""


def load_dev_launcher_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "dev.py"
    spec = importlib.util.spec_from_file_location("malcom_dev_launcher_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load launcher module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DevLauncherTestCase(unittest.TestCase):
    def test_start_backend_execs_uvicorn_from_project_virtualenv(self) -> None:
        launcher = load_dev_launcher_module()
        socket_context = mock.MagicMock()
        probe_socket = socket_context.__enter__.return_value

        with (
            mock.patch.object(launcher.socket, "socket", return_value=socket_context),
            mock.patch.object(launcher.os, "execv", side_effect=ExecIntercept("backend exec intercepted")) as execv_mock,
        ):
            with self.assertRaisesRegex(ExecIntercept, "backend exec intercepted"):
                launcher.start_backend()

        probe_socket.setsockopt.assert_called_once_with(
            launcher.socket.SOL_SOCKET,
            launcher.socket.SO_REUSEADDR,
            1,
        )
        probe_socket.bind.assert_called_once_with(("127.0.0.1", 8000))
        execv_mock.assert_called_once_with(
            str(launcher.VENV_PYTHON),
            [
                str(launcher.VENV_PYTHON),
                "-m",
                "uvicorn",
                "--app-dir",
                str(launcher.APP_DIR),
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ],
        )

    def test_main_reaches_backend_exec_after_bootstrap_steps(self) -> None:
        launcher = load_dev_launcher_module()
        socket_context = mock.MagicMock()
        probe_socket = socket_context.__enter__.return_value

        with (
            mock.patch.object(launcher.os, "chdir") as chdir_mock,
            mock.patch.object(launcher, "ensure_virtualenv") as ensure_virtualenv_mock,
            mock.patch.object(launcher, "reexec_into_virtualenv") as reexec_mock,
            mock.patch.object(launcher, "ensure_backend_dependencies") as backend_deps_mock,
            mock.patch.object(launcher, "ensure_ui_dependencies") as ui_deps_mock,
            mock.patch.object(launcher, "ensure_ui_build") as ui_build_mock,
            mock.patch.object(launcher, "ensure_postgres_running") as postgres_mock,
            mock.patch.object(launcher.socket, "socket", return_value=socket_context),
            mock.patch.object(launcher.os, "execv", side_effect=ExecIntercept("backend exec intercepted")) as execv_mock,
        ):
            with self.assertRaisesRegex(ExecIntercept, "backend exec intercepted"):
                launcher.main()

        chdir_mock.assert_called_once_with(launcher.WORKSPACE_ROOT)
        ensure_virtualenv_mock.assert_called_once_with()
        reexec_mock.assert_called_once_with()
        backend_deps_mock.assert_called_once_with()
        ui_deps_mock.assert_called_once_with()
        ui_build_mock.assert_called_once_with()
        postgres_mock.assert_called_once_with()
        probe_socket.bind.assert_called_once_with(("127.0.0.1", 8000))
        execv_mock.assert_called_once_with(
            str(launcher.VENV_PYTHON),
            [
                str(launcher.VENV_PYTHON),
                "-m",
                "uvicorn",
                "--app-dir",
                str(launcher.APP_DIR),
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ],
        )


if __name__ == "__main__":
    unittest.main()
