from __future__ import annotations

import hashlib
import hmac
from unittest import mock

from .core import default_invoke
from .resources import SMOKE_WEBHOOK_SIGNATURE_HEADER, SMOKE_WEBHOOK_SIGNING_SECRET


def invoke_with_urlopen_mock(case, context, state):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    with mock.patch("backend.routes.apis.urllib.request.urlopen", return_value=FakeResponse()):
        return default_invoke(case, context, state)


def invoke_worker_smtp_send_mock(case, context, state):
    class FakeSmtpClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def send_message(self, message, from_addr=None, to_addrs=None):
            del from_addr, to_addrs
            state["sent_message"] = {
                "id": "smoke-smtp-message",
                "subject": str(message.get("Subject") or ""),
            }

    class FakeSmtpManager:
        def snapshot(self):
            return {"recent_messages": [state.get("sent_message", {"id": "smoke-smtp-message"})]}

    app = context.client.app
    previous_manager = getattr(app.state, "smtp_manager", None)
    app.state.smtp_manager = FakeSmtpManager()
    try:
        with mock.patch("backend.routes.workers.get_local_smtp_runtime_or_400", return_value={"listening_host": "127.0.0.1", "listening_port": 2525}):
            with mock.patch("backend.routes.workers.smtplib.SMTP", return_value=FakeSmtpClient()):
                return default_invoke(case, context, state)
    finally:
        app.state.smtp_manager = previous_manager


def invoke_worker_image_magic_mock(case, context, state):
    del state
    with mock.patch(
        "backend.routes.workers.get_image_magic_tool_config",
        return_value={"enabled": True, "command": "magick"},
    ):
        with mock.patch(
            "backend.routes.workers.normalize_image_magic_tool_config",
            return_value={"enabled": True, "command": "magick"},
        ):
            with mock.patch(
                "backend.routes.workers.execute_image_magic_conversion_request",
                return_value={"output_file_path": "/tmp/smoke-output.jpg"},
            ):
                return default_invoke(case, context, {})


def invoke_webhook_callback(case, context, state):
    path = case.path(context, state) if callable(case.path) else case.path
    params = case.params(context, state) if callable(case.params) else (case.params or {})
    payload = '{"event":"smoke"}'
    secret = SMOKE_WEBHOOK_SIGNING_SECRET.encode("utf-8")
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        SMOKE_WEBHOOK_SIGNATURE_HEADER: f"sha256={signature}",
    }
    return context.client.request(case.method.upper(), path, params=params, headers=headers, content=payload)
