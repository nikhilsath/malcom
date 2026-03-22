from __future__ import annotations

from typing import Any

from .core import Resolver, RouteSmokeCase, SetupFn


def list_case(name: str, method: str, path: str, expected_status: int = 200, **kwargs: Any) -> RouteSmokeCase:
    return RouteSmokeCase(name, method, path, expected_status, **kwargs)


def create_case(name: str, path: str, payload: dict[str, Any], expected_status: int = 201, **kwargs: Any) -> RouteSmokeCase:
    return RouteSmokeCase(name, "POST", path, expected_status, payload=payload, **kwargs)


def detail_case(
    name: str,
    path: str | Resolver,
    route_path: str,
    setup: SetupFn,
    expected_status: int = 200,
    **kwargs: Any,
) -> RouteSmokeCase:
    return RouteSmokeCase(name, "GET", path, expected_status, route_path=route_path, setup=setup, **kwargs)


def patch_case(
    name: str,
    path: str | Resolver,
    route_path: str,
    setup: SetupFn | None,
    payload: dict[str, Any] | Resolver,
    expected_status: int = 200,
    **kwargs: Any,
) -> RouteSmokeCase:
    return RouteSmokeCase(name, "PATCH", path, expected_status, route_path=route_path, setup=setup, payload=payload, **kwargs)


def action_case(
    name: str,
    method: str,
    path: str | Resolver,
    expected_status: int,
    *,
    route_path: str | None = None,
    setup: SetupFn | None = None,
    payload: dict[str, Any] | Resolver | None = None,
    **kwargs: Any,
) -> RouteSmokeCase:
    return RouteSmokeCase(name, method, path, expected_status, route_path=route_path, setup=setup, payload=payload, **kwargs)
