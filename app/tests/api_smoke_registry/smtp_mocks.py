from __future__ import annotations

from typing import Any
from unittest import mock

from backend.main import app

from .core import default_invoke


def invoke_smtp_runtime_sync(case, context, state):
    with mock.patch("backend.routes.tools.sync_smtp_tool_runtime", return_value=None):
        return default_invoke(case, context, state)


def invoke_smtp_send_test(case, context, state):
    class FakeSmtpClient:
        def __enter__(self) -> "FakeSmtpClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def send_message(self, *args: Any, **kwargs: Any) -> None:
            return None

    with mock.patch(
        "backend.routes.tools.get_local_smtp_runtime_or_400",
        return_value={"listening_host": "127.0.0.1", "listening_port": 2525},
    ), mock.patch("backend.routes.tools.smtplib.SMTP", return_value=FakeSmtpClient()), mock.patch.object(
        app.state.smtp_manager,
        "snapshot",
        return_value={"recent_messages": [{"id": "message_smoke"}]},
    ):
        return default_invoke(case, context, state)


def invoke_smtp_send_relay(case, context, state):
    with mock.patch("backend.routes.tools.send_smtp_relay_message", return_value=None):
        return default_invoke(case, context, state)
