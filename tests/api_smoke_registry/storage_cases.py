from __future__ import annotations

from typing import Any

from .builders import action_case, create_case, list_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response
from .resolvers import state_path

_LOCATION_ID_PATH = state_path("location", prefix="/api/v1/storage/locations/")
_CHECKOUT_ID_PATH = state_path("checkout", prefix="/api/v1/storage/repos/")

_LOCAL_LOCATION_PAYLOAD = {
    "name": "Smoke local location",
    "location_type": "local",
    "path": "/tmp/smoke-storage",
    "is_default_logs": False,
}

_REPO_LOCATION_PAYLOAD = {
    "name": "Smoke repo location",
    "location_type": "repo",
    "path": "/tmp/smoke-repo-root",
    "is_default_logs": False,
}


def _location_setup(context: SmokeContext) -> dict[str, Any]:
    res = context.client.post("/api/v1/storage/locations", json=_LOCAL_LOCATION_PAYLOAD)
    res.raise_for_status()
    return {"location": res.json()}


def _checkout_setup(context: SmokeContext) -> dict[str, Any]:
    loc_res = context.client.post("/api/v1/storage/locations", json=_REPO_LOCATION_PAYLOAD)
    loc_res.raise_for_status()
    location = loc_res.json()
    co_res = context.client.post(
        "/api/v1/storage/repos",
        json={
            "storage_location_id": location["id"],
            "repo_url": "https://github.com/example/smoke-repo.git",
            "local_path": "/tmp/smoke-checkout",
            "branch": "main",
        },
    )
    co_res.raise_for_status()
    return {"location": location, "checkout": co_res.json()}


def _repo_create_payload(_ctx: SmokeContext, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "storage_location_id": state["location"]["id"],
        "repo_url": "https://github.com/example/smoke-repo.git",
        "local_path": "/tmp/smoke-checkout-create",
        "branch": "main",
    }


STORAGE_CASES: tuple[RouteSmokeCase, ...] = (
    # Storage locations
    list_case("storage-locations-list", "GET", "/api/v1/storage/locations", response_assert=assert_json_response),
    create_case(
        "storage-locations-create",
        "/api/v1/storage/locations",
        _LOCAL_LOCATION_PAYLOAD,
        expected_status=201,
        response_assert=assert_json_response,
    ),
    action_case(
        "storage-locations-update",
        "PUT",
        _LOCATION_ID_PATH,
        200,
        route_path="/api/v1/storage/locations/{location_id}",
        setup=_location_setup,
        payload={"name": "Updated smoke location"},
        response_assert=assert_json_response,
    ),
    action_case(
        "storage-locations-usage",
        "GET",
        lambda _ctx, state: f"/api/v1/storage/locations/{state['location']['id']}/usage",
        200,
        route_path="/api/v1/storage/locations/{location_id}/usage",
        setup=_location_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "storage-locations-delete",
        "DELETE",
        _LOCATION_ID_PATH,
        200,
        route_path="/api/v1/storage/locations/{location_id}",
        setup=_location_setup,
        response_assert=assert_json_response,
    ),
    # Repo checkouts
    list_case("storage-repos-list", "GET", "/api/v1/storage/repos", response_assert=assert_json_response),
    action_case(
        "storage-repos-create",
        "POST",
        "/api/v1/storage/repos",
        201,
        route_path="/api/v1/storage/repos",
        setup=lambda ctx: {
            "location": ctx.client.post("/api/v1/storage/locations", json=_REPO_LOCATION_PAYLOAD).json()
        },
        payload=_repo_create_payload,
        response_assert=assert_json_response,
    ),
    action_case(
        "storage-repos-delete",
        "DELETE",
        _CHECKOUT_ID_PATH,
        200,
        route_path="/api/v1/storage/repos/{checkout_id}",
        setup=_checkout_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "storage-repos-sync",
        "POST",
        lambda _ctx, state: f"/api/v1/storage/repos/{state['checkout']['id']}/sync",
        500,  # git clone fails in the test environment — exercises the route handler
        route_path="/api/v1/storage/repos/{checkout_id}/sync",
        setup=_checkout_setup,
    ),
)

