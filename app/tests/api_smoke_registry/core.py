from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.main import app
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


def resolve_value(value: Any, context: SmokeContext, state: dict[str, Any]) -> Any:
    return value(context, state) if callable(value) else value


def route_signature(method: str, path: str) -> str:
    return f"{method.upper()} {path}"


def case_signature(case: RouteSmokeCase) -> str:
    if case.route_path:
        return route_signature(case.method, case.route_path)
    if isinstance(case.path, str):
        return route_signature(case.method, case.path)
    raise ValueError(f"Case {case.name} requires route_path for callable paths")


def all_discovered_route_signatures() -> set[str]:
    return {route_signature(method, path) for method, path in get_internal_api_route_signatures()}


def assert_json_response(response: Any, _: SmokeContext, __: dict[str, Any]) -> None:
    assert response.headers["content-type"].startswith("application/json")


def default_invoke(case: RouteSmokeCase, context: SmokeContext, state: dict[str, Any]) -> Any:
    path = resolve_value(case.path, context, state)
    payload = resolve_value(case.payload, context, state)
    headers = resolve_value(case.headers, context, state)
    params = resolve_value(case.params, context, state)
    request_kwargs: dict[str, Any] = {"headers": headers, "params": params}
    if payload is not None and case.method.upper() not in {"GET", "DELETE"}:
        request_kwargs["json"] = payload
    return context.client.request(case.method.upper(), path, **request_kwargs)


def invoke_smoke_case(case: RouteSmokeCase, context: SmokeContext) -> Any:
    state = case.setup(context) if case.setup else {}
    response = None
    try:
        response = (case.invoke or default_invoke)(case, context, state)
        assert response.status_code == case.expected_status, f"{case.name}: expected {case.expected_status}, got {response.status_code}"
        if case.response_assert:
            case.response_assert(response, context, state)
        return response
    finally:
        if case.teardown:
            case.teardown(context)
