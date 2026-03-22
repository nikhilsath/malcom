from __future__ import annotations

from .builders import action_case, list_case, patch_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response, resolve_value
from .resolvers import connector_setup, oauth_callback_params, oauth_start_setup, refresh_setup


def assert_redirect_to_connectors(response: object, _: SmokeContext, __: dict[str, object]) -> None:
    location = response.headers.get("location", "")
    assert location.startswith("/settings/connectors.html?"), "Expected redirect to connectors page"


def invoke_without_redirect(case: RouteSmokeCase, context: SmokeContext, state: dict[str, object]) -> object:
    path = resolve_value(case.path, context, state)
    params = resolve_value(case.params, context, state)
    return context.client.request(case.method.upper(), path, params=params, follow_redirects=False)


SETTINGS_CONNECTORS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("settings-get", "GET", "/api/v1/settings", response_assert=assert_json_response),
    patch_case(
        "settings-patch",
        "/api/v1/settings",
        "/api/v1/settings",
        None,
        {"general": {"environment": "live", "timezone": "utc"}},
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-test",
        "POST",
        "/api/v1/connectors/github-primary/test",
        200,
        route_path="/api/v1/connectors/{connector_id}/test",
        setup=connector_setup,
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-activity-catalog",
        "GET",
        "/api/v1/connectors/activity-catalog",
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-oauth-start",
        "POST",
        "/api/v1/connectors/google/oauth/start",
        200,
        route_path="/api/v1/connectors/{provider}/oauth/start",
        payload={
            "connector_id": "google-primary",
            "name": "Google",
            "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
            "owner": "Workspace",
            "client_id": "google-client-id",
            "client_secret_input": "google-client-secret",
        },
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-oauth-callback",
        "GET",
        "/api/v1/connectors/google/oauth/callback",
        route_path="/api/v1/connectors/{provider}/oauth/callback",
        setup=oauth_start_setup,
        params=oauth_callback_params,
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-oauth-callback-ui",
        "GET",
        "/api/v1/connectors/google/oauth/callback/ui",
        303,
        route_path="/api/v1/connectors/{provider}/oauth/callback/ui",
        setup=oauth_start_setup,
        params=oauth_callback_params,
        response_assert=assert_redirect_to_connectors,
        invoke=invoke_without_redirect,
    ),
    action_case(
        "connectors-refresh",
        "POST",
        "/api/v1/connectors/google-primary/refresh",
        200,
        route_path="/api/v1/connectors/{connector_id}/refresh",
        setup=refresh_setup,
        response_assert=assert_json_response,
    ),
)
