from __future__ import annotations

import os
from typing import Any

from .builders import action_case, list_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response


def configure_platform_auth_env(context: SmokeContext) -> dict[str, Any]:
    previous_bootstrap_token = os.environ.get("MALCOM_FRONTEND_BOOTSTRAP_TOKEN")
    os.environ["MALCOM_FRONTEND_BOOTSTRAP_TOKEN"] = "smoke-platform-bootstrap"
    setattr(context, "_previous_frontend_bootstrap_token", previous_bootstrap_token)
    return {}


def platform_auth_setup(context: SmokeContext) -> dict[str, Any]:
    configure_platform_auth_env(context)
    token_response = context.client.post(
        "/api/v1/platform/auth/tokens",
        json={
            "bootstrap_token": "smoke-platform-bootstrap",
            "operator_name": "Smoke Platform Operator",
            "client_name": "hosted-frontend",
            "requested_origin": "https://frontend.example.test",
        },
    )
    token_response.raise_for_status()
    return token_response.json()


def platform_auth_teardown(context: SmokeContext) -> None:
    previous_bootstrap_token = getattr(context, "_previous_frontend_bootstrap_token", None)
    if previous_bootstrap_token:
        os.environ["MALCOM_FRONTEND_BOOTSTRAP_TOKEN"] = previous_bootstrap_token
    else:
        os.environ.pop("MALCOM_FRONTEND_BOOTSTRAP_TOKEN", None)


def platform_headers(_context: SmokeContext, state: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {state['access_token']}"}


def platform_refresh_payload(_context: SmokeContext, state: dict[str, Any]) -> dict[str, Any]:
    return {"refresh_token": state["refresh_token"], "client_name": "hosted-frontend"}


def assert_embed_descriptor(response: object, context: SmokeContext, _: dict[str, Any]) -> None:
    assert_json_response(response, context, {})
    body = response.json()
    assert body["id"] == "workflow-builder"
    assert body["mount_mode"] == "iframe"


PLATFORM_CASES: tuple[RouteSmokeCase, ...] = (
    action_case(
        "platform-auth-issue",
        "POST",
        "/api/v1/platform/auth/tokens",
        200,
        route_path="/api/v1/platform/auth/tokens",
        setup=configure_platform_auth_env,
        payload={
            "bootstrap_token": "smoke-platform-bootstrap",
            "operator_name": "Smoke Platform Operator",
            "client_name": "hosted-frontend",
        },
        response_assert=assert_json_response,
        teardown=platform_auth_teardown,
    ),
    action_case(
        "platform-auth-refresh",
        "POST",
        "/api/v1/platform/auth/refresh",
        200,
        route_path="/api/v1/platform/auth/refresh",
        setup=platform_auth_setup,
        payload=platform_refresh_payload,
        response_assert=assert_json_response,
        teardown=platform_auth_teardown,
    ),
    action_case(
        "platform-auth-revoke",
        "POST",
        "/api/v1/platform/auth/revoke",
        200,
        route_path="/api/v1/platform/auth/revoke",
        setup=platform_auth_setup,
        payload=lambda _context, state: {"refresh_token": state["refresh_token"]},
        response_assert=assert_json_response,
        teardown=platform_auth_teardown,
    ),
    list_case(
        "platform-bootstrap",
        "GET",
        "/api/v1/platform/bootstrap",
        route_path="/api/v1/platform/bootstrap",
        setup=platform_auth_setup,
        headers=platform_headers,
        response_assert=assert_json_response,
        teardown=platform_auth_teardown,
    ),
    list_case(
        "platform-plugins",
        "GET",
        "/api/v1/platform/plugins",
        route_path="/api/v1/platform/plugins",
        setup=platform_auth_setup,
        headers=platform_headers,
        response_assert=assert_json_response,
        teardown=platform_auth_teardown,
    ),
    list_case(
        "platform-embed-workflow-builder",
        "GET",
        "/api/v1/platform/embeds/workflow-builder",
        route_path="/api/v1/platform/embeds/{embed_id}",
        setup=platform_auth_setup,
        headers=platform_headers,
        response_assert=assert_embed_descriptor,
        teardown=platform_auth_teardown,
    ),
)
