from __future__ import annotations

from .builders import action_case, create_case, detail_case, list_case, patch_case
from .core import RouteSmokeCase, assert_json_response
from .external_mocks import invoke_with_urlopen_mock
from .resources import create_inbound_api, create_outgoing_api
from .resolvers import inbound_auth_headers, state_path

INBOUND_DETAIL_PATH = state_path("inbound", prefix="/api/v1/inbound/")
OUTGOING_DETAIL_PATH = state_path("api", prefix="/api/v1/outgoing/")
def inbound_detail_setup(context):
    return {"inbound": create_inbound_api(context, slug="smoke-inbound-detail")}


def inbound_patch_setup(context):
    return {"inbound": create_inbound_api(context, slug="smoke-inbound-patch")}


def inbound_rotate_setup(context):
    return {"inbound": create_inbound_api(context, slug="smoke-inbound-rotate")}


def inbound_disable_setup(context):
    return {"inbound": create_inbound_api(context, slug="smoke-inbound-disable")}


def inbound_receive_setup(context):
    return {"inbound": create_inbound_api(context, slug="smoke-inbound-receive")}


def outgoing_scheduled_setup(context):
    return {"api": create_outgoing_api(context, api_type="outgoing_scheduled")}


def outgoing_continuous_setup(context):
    return {"api": create_outgoing_api(context, api_type="outgoing_continuous")}


def inbound_rotate_path(_context, state):
    return f"/api/v1/inbound/{state['inbound']['id']}/rotate-secret"


def inbound_disable_path(_context, state):
    return f"/api/v1/inbound/{state['inbound']['id']}/disable"


INBOUND_OUTGOING_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("inbound-list", "GET", "/api/v1/inbound", response_assert=assert_json_response),
    create_case(
        "inbound-create",
        "/api/v1/inbound",
        {
            "name": "Smoke inbound create",
            "description": "Inbound create route smoke.",
            "path_slug": "smoke-inbound-create",
            "enabled": True,
        },
        response_assert=assert_json_response,
    ),
    list_case("outgoing-scheduled-list", "GET", "/api/v1/outgoing/scheduled", response_assert=assert_json_response),
    list_case("outgoing-continuous-list", "GET", "/api/v1/outgoing/continuous", response_assert=assert_json_response),
    detail_case(
        "outgoing-detail",
        OUTGOING_DETAIL_PATH,
        "/api/v1/outgoing/{api_id}",
        outgoing_scheduled_setup,
        params={"api_type": "outgoing_scheduled"},
        response_assert=assert_json_response,
    ),
    list_case("webhooks-list", "GET", "/api/v1/webhooks", response_assert=assert_json_response),
    create_case(
        "apis-create",
        "/api/v1/apis",
        {
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
        response_assert=assert_json_response,
    ),
    action_case(
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
        response_assert=assert_json_response,
        invoke=invoke_with_urlopen_mock,
    ),
    detail_case(
        "inbound-detail",
        INBOUND_DETAIL_PATH,
        "/api/v1/inbound/{api_id}",
        inbound_detail_setup,
        response_assert=assert_json_response,
    ),
    patch_case(
        "inbound-patch",
        INBOUND_DETAIL_PATH,
        "/api/v1/inbound/{api_id}",
        inbound_patch_setup,
        {"description": "Updated by smoke"},
        response_assert=assert_json_response,
    ),
    patch_case(
        "outgoing-patch",
        OUTGOING_DETAIL_PATH,
        "/api/v1/outgoing/{api_id}",
        outgoing_continuous_setup,
        {"type": "outgoing_continuous", "description": "Updated by smoke", "repeat_interval_minutes": 30},
        response_assert=assert_json_response,
    ),
    action_case(
        "inbound-rotate-secret",
        "POST",
        inbound_rotate_path,
        200,
        route_path="/api/v1/inbound/{api_id}/rotate-secret",
        setup=inbound_rotate_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "inbound-disable",
        "POST",
        inbound_disable_path,
        200,
        route_path="/api/v1/inbound/{api_id}/disable",
        setup=inbound_disable_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "inbound-receive",
        "POST",
        INBOUND_DETAIL_PATH,
        202,
        route_path="/api/v1/inbound/{api_id}",
        setup=inbound_receive_setup,
        headers=inbound_auth_headers,
        payload={"smoke": True},
        response_assert=assert_json_response,
    ),
)
