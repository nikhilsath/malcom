from __future__ import annotations

from unittest import mock

from .core import default_invoke


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
