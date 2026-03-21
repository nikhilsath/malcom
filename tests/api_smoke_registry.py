from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.main import LocalLlmChatResponse, app
from tests.postgres_test_utils import setup_postgres_test_app


SetupFn = Callable[["SmokeContext"], dict[str, Any]]
Resolver = Callable[["SmokeContext", dict[str, Any]], Any]
ResponseAssert = Callable[[Any, "SmokeContext", dict[str, Any]], None]
InvokeFn = Callable[["RouteSmokeCase", "SmokeContext", dict[str, Any]], Any]


@dataclass(frozen=True)
class RouteSmokeCase:
    name: str
    method: str
    path: str | Resolver
    expected_status: int
    route_path: str | None = None
    setup: SetupFn | None = None
    payload: dict[str, Any] | Resolver | None = None
    headers: dict[str, str] | Resolver | None = None
    params: dict[str, Any] | Resolver | None = None
    teardown: SetupFn | None = None
    response_assert: ResponseAssert | None = None
    invoke: InvokeFn | None = None


class SmokeContext:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.tempdir.name)
        (self.root_dir / "ui" / "scripts").mkdir(parents=True, exist_ok=True)
        self.previous_root_dir = app.state.root_dir
        self.previous_db_path = app.state.db_path
        self.previous_database_url = app.state.database_url
        self.previous_skip_ui_build_check = getattr(app.state, "skip_ui_build_check", False)
        setup_postgres_test_app(app=app, root_dir=self.root_dir)
        self.client = TestClient(app)
        self.client.__enter__()

    def close(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.root_dir = self.previous_root_dir
        app.state.db_path = self.previous_db_path
        app.state.database_url = self.previous_database_url
        app.state.skip_ui_build_check = self.previous_skip_ui_build_check
        self.tempdir.cleanup()


def _resolve(value: Any, context: SmokeContext, state: dict[str, Any]) -> Any:
    return value(context, state) if callable(value) else value


def create_smoke_context() -> SmokeContext:
    return SmokeContext()


def get_internal_api_route_signatures() -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path != "/health" and not route.path.startswith("/api/v1/"):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            signatures.add((method.upper(), route.path))
    return signatures


def create_inbound_api(context: SmokeContext, *, slug: str = "smoke-inbound") -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/inbound",
        json={
            "name": f"{slug} inbound",
            "description": "Smoke inbound endpoint.",
            "path_slug": slug,
            "enabled": True,
        },
    )
    response.raise_for_status()
    return response.json()


def create_script(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/scripts",
        json={
            "name": "Smoke Script",
            "description": "Script detail smoke test.",
            "language": "python",
            "code": "def run(payload):\n    return payload\n",
        },
    )
    response.raise_for_status()
    return response.json()


def create_automation(context: SmokeContext, *, name: str = "Smoke automation") -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/automations",
        json={
            "name": name,
            "description": "Route smoke automation.",
            "enabled": True,
            "trigger_type": "manual",
            "trigger_config": {},
            "steps": [
                {
                    "type": "log",
                    "name": "Log payload",
                    "config": {"message": "Smoke"},
                }
            ],
        },
    )
    response.raise_for_status()
    return response.json()


def create_outgoing_api(context: SmokeContext, *, api_type: str) -> dict[str, Any]:
    payload = {
        "type": api_type,
        "name": f"{api_type} api",
        "description": "Created for route smoke coverage.",
        "path_slug": api_type.replace("_", "-"),
        "enabled": True,
        "destination_url": "https://example.com/hooks/smoke",
        "http_method": "POST",
        "auth_type": "none",
        "payload_template": "{\"smoke\":true}",
    }
    if api_type == "outgoing_scheduled":
        payload["scheduled_time"] = "09:30"
    if api_type == "outgoing_continuous":
        payload["repeat_enabled"] = True
        payload["repeat_interval_minutes"] = 15
    response = context.client.post("/api/v1/apis", json=payload)
    response.raise_for_status()
    return response.json()


def create_connector_record(context: SmokeContext, *, auth_type: str = "bearer") -> dict[str, Any]:
    payload = {
        "connectors": {
            "records": [
                {
                    "id": "github-primary",
                    "provider": "github",
                    "name": "GitHub",
                    "status": "draft",
                    "auth_type": auth_type,
                    "scopes": ["repo"],
                    "base_url": "https://api.github.com",
                    "owner": "Workspace",
                    "auth_config": {
                        "access_token_input": "ghp_secret_token",
                        "refresh_token_input": "ghr_secret_refresh" if auth_type == "oauth2" else None,
                    },
                }
            ]
        }
    }
    response = context.client.patch("/api/v1/settings", json=payload)
    response.raise_for_status()
    return response.json()["connectors"]["records"][0]


def start_google_oauth(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/connectors/google_calendar/oauth/start",
        json={
            "connector_id": "google-calendar-primary",
            "name": "Google Calendar",
            "redirect_uri": "http://localhost:8000/api/v1/connectors/google_calendar/oauth/callback",
            "owner": "Workspace",
            "client_id": "calendar-client-id",
            "client_secret_input": "calendar-client-secret",
        },
    )
    response.raise_for_status()
    return response.json()


def create_worker_job(context: SmokeContext) -> dict[str, Any]:
    inbound = create_inbound_api(context, slug="smoke-worker-source")
    context.client.post(
        f"/api/v1/inbound/{inbound['id']}",
        headers={
            "Authorization": f"Bearer {inbound['secret']}",
            "Content-Type": "application/json",
        },
        json={"id": 999},
    ).raise_for_status()
    context.client.post(
        "/api/v1/workers/register",
        json={
            "worker_id": "worker_smoke_01",
            "name": "Smoke Worker",
            "hostname": "smoke-worker.local",
            "address": "127.0.0.1",
            "capabilities": ["runtime-trigger-execution"],
        },
    ).raise_for_status()
    claim = context.client.post("/api/v1/workers/claim-trigger", json={"worker_id": "worker_smoke_01"})
    claim.raise_for_status()
    return {"job": claim.json()["job"]}


def create_inbound_event(context: SmokeContext) -> dict[str, Any]:
    inbound = create_inbound_api(context, slug="smoke-trigger-source")
    response = context.client.post(
        f"/api/v1/inbound/{inbound['id']}",
        headers={
            "Authorization": f"Bearer {inbound['secret']}",
            "Content-Type": "application/json",
        },
        json={"id": 42},
    )
    response.raise_for_status()
    return {"inbound": inbound}


def configure_local_llm(context: SmokeContext) -> dict[str, Any]:
    response = context.client.patch(
        "/api/v1/tools/llm-deepl/local-llm",
        json={
            "enabled": True,
            "provider": "lm_studio_api_v1",
            "server_base_url": "http://127.0.0.1:1234",
            "model_identifier": "qwen/qwen3.5-9b",
            "endpoints": {
                "models": "/api/v1/models",
                "chat": "/api/v1/chat",
                "model_load": "/api/v1/models/load",
                "model_download": "/api/v1/models/download",
                "model_download_status": "/api/v1/models/download/status/:job_id",
            },
        },
    )
    response.raise_for_status()
    return response.json()


def configure_smtp_tool(context: SmokeContext) -> dict[str, Any]:
    response = context.client.patch(
        "/api/v1/tools/smtp",
        json={
            "enabled": True,
            "bind_host": "127.0.0.1",
            "port": 2525,
            "recipient_email": "recipient@example.com",
        },
    )
    response.raise_for_status()
    return response.json()


def _assert_json_response(response: Any, _: SmokeContext, __: dict[str, Any]) -> None:
    assert response.headers["content-type"].startswith("application/json")


def _invoke_with_urlopen_mock(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    with mock.patch("backend.routes.apis.urllib.request.urlopen", return_value=FakeResponse()):
        return _default_invoke(case, context, state)


def _invoke_local_llm_chat(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    with mock.patch(
        "backend.routes.tools.execute_local_llm_chat_request",
        return_value=LocalLlmChatResponse(
            ok=True,
            model_identifier="qwen/qwen3.5-9b",
            response_text="Smoke response.",
            response_id="response_smoke",
        ),
    ):
        return _default_invoke(case, context, state)


def _invoke_local_llm_stream(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    with mock.patch(
        "backend.routes.tools.build_local_llm_stream",
        return_value=iter(
            [
                b'event: delta\ndata: {"content": "Smoke "}\n\n',
                b'event: done\ndata: {"response_text": "Smoke stream"}\n\n',
            ]
        ),
    ):
        return _default_invoke(case, context, state)


def _invoke_smtp_runtime_sync(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    with mock.patch("backend.routes.tools.sync_smtp_tool_runtime", return_value=None):
        return _default_invoke(case, context, state)


def _invoke_smtp_send_test(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
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
    ), mock.patch(
        "backend.routes.tools.smtplib.SMTP",
        return_value=FakeSmtpClient(),
    ), mock.patch.object(
        app.state.smtp_manager,
        "snapshot",
        return_value={"recent_messages": [{"id": "message_smoke"}]},
    ):
        return _default_invoke(case, context, state)


def _invoke_smtp_send_relay(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    with mock.patch("backend.routes.tools.send_smtp_relay_message", return_value=None):
        return _default_invoke(case, context, state)


def _default_invoke(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    path = _resolve(case.path, context, state)
    payload = _resolve(case.payload, context, state)
    headers = _resolve(case.headers, context, state)
    params = _resolve(case.params, context, state)
    request_kwargs: dict[str, Any] = {"headers": headers, "params": params}
    if payload is not None and case.method.upper() not in {"GET", "DELETE"}:
        request_kwargs["json"] = payload
    return context.client.request(case.method.upper(), path, **request_kwargs)


def invoke_smoke_case(case: RouteSmokeCase, context: SmokeContext) -> Any:
    state = case.setup(context) if case.setup else {}
    response = None
    try:
        response = (case.invoke or _default_invoke)(case, context, state)
        assert response.status_code == case.expected_status, f"{case.name}: expected {case.expected_status}, got {response.status_code}"
        if case.response_assert:
            case.response_assert(response, context, state)
        return response
    finally:
        if case.teardown:
            case.teardown(context)


SMOKE_CASES: tuple[RouteSmokeCase, ...] = (
    RouteSmokeCase("healthcheck", "GET", "/health", 200, response_assert=_assert_json_response),
    RouteSmokeCase("runtime-status", "GET", "/api/v1/runtime/status", 200, response_assert=_assert_json_response),
    RouteSmokeCase("scheduler-jobs", "GET", "/api/v1/scheduler/jobs", 200, response_assert=_assert_json_response),
    RouteSmokeCase("dashboard-devices", "GET", "/api/v1/dashboard/devices", 200, response_assert=_assert_json_response),
    RouteSmokeCase("dashboard-queue", "GET", "/api/v1/dashboard/queue", 200, response_assert=_assert_json_response),
    RouteSmokeCase("dashboard-queue-pause", "POST", "/api/v1/dashboard/queue/pause", 200, response_assert=_assert_json_response),
    RouteSmokeCase("dashboard-queue-unpause", "POST", "/api/v1/dashboard/queue/unpause", 200, response_assert=_assert_json_response),
    RouteSmokeCase("runtime-triggers", "GET", "/api/v1/runtime/triggers", 200, setup=create_inbound_event, response_assert=_assert_json_response),
    RouteSmokeCase("workers-list", "GET", "/api/v1/workers", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "workers-register",
        "POST",
        "/api/v1/workers/register",
        200,
        payload={
            "worker_id": "worker_smoke_01",
            "name": "Smoke Worker",
            "hostname": "smoke-worker.local",
            "address": "127.0.0.1",
            "capabilities": ["runtime-trigger-execution"],
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "workers-claim-trigger",
        "POST",
        "/api/v1/workers/claim-trigger",
        200,
        setup=create_worker_job,
        payload={"worker_id": "worker_smoke_01"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "workers-complete-trigger",
        "POST",
        "/api/v1/workers/complete-trigger",
        200,
        setup=create_worker_job,
        payload=lambda _context, state: {
            "worker_id": "worker_smoke_01",
            "job_id": state["job"]["job_id"],
            "status": "completed",
            "response_summary": "Route smoke completed trigger.",
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "scripts-validate",
        "POST",
        "/api/v1/scripts/validate",
        200,
        payload={"language": "python", "code": "def run(payload):\n    return payload\n"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("scripts-list", "GET", "/api/v1/scripts", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "scripts-detail",
        "GET",
        lambda _context, state: f"/api/v1/scripts/{state['script']['id']}",
        200,
        route_path="/api/v1/scripts/{script_id}",
        setup=lambda context: {"script": create_script(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "scripts-create",
        "POST",
        "/api/v1/scripts",
        201,
        payload={
            "name": "Smoke Create",
            "description": "Create via route smoke.",
            "language": "python",
            "code": "def run(payload):\n    return payload\n",
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "scripts-update",
        "PATCH",
        lambda _context, state: f"/api/v1/scripts/{state['script']['id']}",
        200,
        route_path="/api/v1/scripts/{script_id}",
        setup=lambda context: {"script": create_script(context)},
        payload={"code": "def run(payload):\n    payload['updated'] = True\n    return payload\n"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("settings-get", "GET", "/api/v1/settings", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "settings-patch",
        "PATCH",
        "/api/v1/settings",
        200,
        payload={"general": {"environment": "live", "timezone": "utc"}},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("automations-list", "GET", "/api/v1/automations", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "automations-create",
        "POST",
        "/api/v1/automations",
        201,
        payload={
            "name": "Smoke automation create",
            "description": "Created through route smoke.",
            "enabled": True,
            "trigger_type": "manual",
            "trigger_config": {},
            "steps": [{"type": "log", "name": "Route smoke", "config": {"message": "Smoke"}}],
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "automations-detail",
        "GET",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}",
        200,
        route_path="/api/v1/automations/{automation_id}",
        setup=lambda context: {"automation": create_automation(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "automations-patch",
        "PATCH",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}",
        200,
        route_path="/api/v1/automations/{automation_id}",
        setup=lambda context: {"automation": create_automation(context)},
        payload={"name": "Updated smoke automation"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "automations-delete",
        "DELETE",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}",
        204,
        route_path="/api/v1/automations/{automation_id}",
        setup=lambda context: {"automation": create_automation(context)},
    ),
    RouteSmokeCase(
        "automations-validate",
        "POST",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}/validate",
        200,
        route_path="/api/v1/automations/{automation_id}/validate",
        setup=lambda context: {"automation": create_automation(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "automations-execute",
        "POST",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}/execute",
        200,
        route_path="/api/v1/automations/{automation_id}/execute",
        setup=lambda context: {"automation": create_automation(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "automations-runs",
        "GET",
        lambda _context, state: f"/api/v1/automations/{state['automation']['id']}/runs",
        200,
        route_path="/api/v1/automations/{automation_id}/runs",
        setup=lambda context: {"automation": create_automation(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("runs-list", "GET", "/api/v1/runs", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "runs-detail",
        "GET",
        lambda context, state: f"/api/v1/runs/{state['run_id']}",
        200,
        route_path="/api/v1/runs/{run_id}",
        setup=lambda context: {
            "run_id": context.client.post(
                f"/api/v1/automations/{create_automation(context)['id']}/execute"
            ).json()["run_id"]
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "connectors-test",
        "POST",
        "/api/v1/connectors/github-primary/test",
        200,
        route_path="/api/v1/connectors/{connector_id}/test",
        setup=lambda context: {"connector": create_connector_record(context)},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "connectors-oauth-start",
        "POST",
        "/api/v1/connectors/google_calendar/oauth/start",
        200,
        route_path="/api/v1/connectors/{provider}/oauth/start",
        payload={
            "connector_id": "google-calendar-primary",
            "name": "Google Calendar",
            "redirect_uri": "http://localhost:8000/api/v1/connectors/google_calendar/oauth/callback",
            "owner": "Workspace",
            "client_id": "calendar-client-id",
            "client_secret_input": "calendar-client-secret",
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "connectors-oauth-callback",
        "GET",
        lambda _context, state: f"/api/v1/connectors/google_calendar/oauth/callback",
        200,
        route_path="/api/v1/connectors/{provider}/oauth/callback",
        setup=lambda context: {"oauth": start_google_oauth(context)},
        params=lambda _context, state: {"state": state["oauth"]["state"], "code": "demo"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "connectors-refresh",
        "POST",
        "/api/v1/connectors/google-calendar-primary/refresh",
        200,
        route_path="/api/v1/connectors/{connector_id}/refresh",
        setup=lambda context: {
            "callback": context.client.get(
                "/api/v1/connectors/google_calendar/oauth/callback",
                params={"state": start_google_oauth(context)["state"], "code": "demo"},
            ).json()
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("tools-smtp-get", "GET", "/api/v1/tools/smtp", 200, response_assert=_assert_json_response),
    RouteSmokeCase("tools-local-llm-get", "GET", "/api/v1/tools/llm-deepl/local-llm", 200, response_assert=_assert_json_response),
    RouteSmokeCase("tools-coqui-get", "GET", "/api/v1/tools/coqui-tts", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "tools-local-llm-chat",
        "POST",
        "/api/v1/tools/llm-deepl/chat",
        200,
        setup=configure_local_llm,
        payload={"messages": [{"role": "user", "content": "Smoke hello"}]},
        response_assert=_assert_json_response,
        invoke=_invoke_local_llm_chat,
    ),
    RouteSmokeCase(
        "tools-local-llm-stream",
        "POST",
        "/api/v1/tools/llm-deepl/chat/stream",
        200,
        setup=configure_local_llm,
        payload={"messages": [{"role": "user", "content": "Smoke hello"}]},
        invoke=_invoke_local_llm_stream,
    ),
    RouteSmokeCase("tools-directory-list", "GET", "/api/v1/tools", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "tools-smtp-patch",
        "PATCH",
        "/api/v1/tools/smtp",
        200,
        payload={"enabled": True, "bind_host": "127.0.0.1", "port": 2525, "recipient_email": "recipient@example.com"},
        response_assert=_assert_json_response,
        invoke=_invoke_smtp_runtime_sync,
    ),
    RouteSmokeCase(
        "tools-local-llm-patch",
        "PATCH",
        "/api/v1/tools/llm-deepl/local-llm",
        200,
        payload={
            "enabled": True,
            "provider": "lm_studio_api_v1",
            "server_base_url": "http://127.0.0.1:1234",
            "model_identifier": "qwen/qwen3.5-9b",
            "endpoints": {"chat": "/api/v1/chat"},
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "tools-coqui-patch",
        "PATCH",
        "/api/v1/tools/coqui-tts",
        200,
        payload={
            "enabled": True,
            "command": "tts",
            "model_name": "tts_models/en/ljspeech/tacotron2-DDC",
            "speaker": "ljspeech",
            "language": "en",
            "output_directory": "generated-audio",
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "tools-smtp-start",
        "POST",
        "/api/v1/tools/smtp/start",
        200,
        setup=configure_smtp_tool,
        response_assert=_assert_json_response,
        invoke=_invoke_smtp_runtime_sync,
    ),
    RouteSmokeCase(
        "tools-smtp-stop",
        "POST",
        "/api/v1/tools/smtp/stop",
        200,
        setup=configure_smtp_tool,
        response_assert=_assert_json_response,
        invoke=_invoke_smtp_runtime_sync,
    ),
    RouteSmokeCase(
        "tools-smtp-send-test",
        "POST",
        "/api/v1/tools/smtp/send-test",
        200,
        setup=configure_smtp_tool,
        payload={
            "mail_from": "smtp-test@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Smoke test",
            "body": "hello",
        },
        response_assert=_assert_json_response,
        invoke=_invoke_smtp_send_test,
    ),
    RouteSmokeCase(
        "tools-smtp-send-relay",
        "POST",
        "/api/v1/tools/smtp/send-relay",
        200,
        payload={
            "host": "smtp.example.com",
            "port": 587,
            "security": "starttls",
            "auth_mode": "password",
            "username": "demo",
            "password": "demo",
            "mail_from": "relay@example.com",
            "recipients": ["recipient@example.com"],
            "subject": "Smoke relay",
            "body": "hello",
        },
        response_assert=_assert_json_response,
        invoke=_invoke_smtp_send_relay,
    ),
    RouteSmokeCase(
        "tools-directory-patch",
        "PATCH",
        "/api/v1/tools/convert-audio/directory",
        200,
        route_path="/api/v1/tools/{tool_id}/directory",
        payload={"name": "Convert - Audio Smoke", "enabled": True},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "tools-metadata-patch",
        "PATCH",
        "/api/v1/tools/convert-audio",
        200,
        route_path="/api/v1/tools/{tool_id}",
        payload={"name": "Convert - Audio Generic", "description": "Patched via smoke."},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("inbound-list", "GET", "/api/v1/inbound", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "inbound-create",
        "POST",
        "/api/v1/inbound",
        201,
        payload={
            "name": "Smoke inbound create",
            "description": "Inbound create route smoke.",
            "path_slug": "smoke-inbound-create",
            "enabled": True,
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("outgoing-scheduled-list", "GET", "/api/v1/outgoing/scheduled", 200, response_assert=_assert_json_response),
    RouteSmokeCase("outgoing-continuous-list", "GET", "/api/v1/outgoing/continuous", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "outgoing-detail",
        "GET",
        lambda _context, state: f"/api/v1/outgoing/{state['api']['id']}",
        200,
        route_path="/api/v1/outgoing/{api_id}",
        setup=lambda context: {"api": create_outgoing_api(context, api_type="outgoing_scheduled")},
        params={"api_type": "outgoing_scheduled"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase("webhooks-list", "GET", "/api/v1/webhooks", 200, response_assert=_assert_json_response),
    RouteSmokeCase(
        "apis-create",
        "POST",
        "/api/v1/apis",
        201,
        payload={
            "type": "outgoing_scheduled",
            "name": "Smoke api create",
            "description": "API create route smoke.",
            "path_slug": "smoke-api-create",
            "enabled": True,
            "destination_url": "https://example.com/hooks/create",
            "http_method": "POST",
            "auth_type": "none",
            "payload_template": "{\"ok\":true}",
            "scheduled_time": "08:15",
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "apis-test-delivery",
        "POST",
        "/api/v1/apis/test-delivery",
        200,
        payload={
            "type": "outgoing_scheduled",
            "destination_url": "https://example.com/deliver",
            "http_method": "POST",
            "auth_type": "none",
            "payload_template": "{\"ping\":\"pong\"}",
        },
        response_assert=_assert_json_response,
        invoke=_invoke_with_urlopen_mock,
    ),
    RouteSmokeCase(
        "inbound-detail",
        "GET",
        lambda _context, state: f"/api/v1/inbound/{state['inbound']['id']}",
        200,
        route_path="/api/v1/inbound/{api_id}",
        setup=lambda context: {"inbound": create_inbound_api(context, slug="smoke-inbound-detail")},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "inbound-patch",
        "PATCH",
        lambda _context, state: f"/api/v1/inbound/{state['inbound']['id']}",
        200,
        route_path="/api/v1/inbound/{api_id}",
        setup=lambda context: {"inbound": create_inbound_api(context, slug="smoke-inbound-patch")},
        payload={"description": "Updated by smoke"},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "outgoing-patch",
        "PATCH",
        lambda _context, state: f"/api/v1/outgoing/{state['api']['id']}",
        200,
        route_path="/api/v1/outgoing/{api_id}",
        setup=lambda context: {"api": create_outgoing_api(context, api_type="outgoing_continuous")},
        payload={
            "type": "outgoing_continuous",
            "description": "Updated by smoke",
            "repeat_interval_minutes": 30,
        },
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "inbound-rotate-secret",
        "POST",
        lambda _context, state: f"/api/v1/inbound/{state['inbound']['id']}/rotate-secret",
        200,
        route_path="/api/v1/inbound/{api_id}/rotate-secret",
        setup=lambda context: {"inbound": create_inbound_api(context, slug="smoke-inbound-rotate")},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "inbound-disable",
        "POST",
        lambda _context, state: f"/api/v1/inbound/{state['inbound']['id']}/disable",
        200,
        route_path="/api/v1/inbound/{api_id}/disable",
        setup=lambda context: {"inbound": create_inbound_api(context, slug="smoke-inbound-disable")},
        response_assert=_assert_json_response,
    ),
    RouteSmokeCase(
        "inbound-receive",
        "POST",
        lambda _context, state: f"/api/v1/inbound/{state['inbound']['id']}",
        202,
        route_path="/api/v1/inbound/{api_id}",
        setup=lambda context: {"inbound": create_inbound_api(context, slug="smoke-inbound-receive")},
        headers=lambda _context, state: {
            "Authorization": f"Bearer {state['inbound']['secret']}",
            "Content-Type": "application/json",
        },
        payload={"smoke": True},
        response_assert=_assert_json_response,
    ),
)
