from __future__ import annotations

from .builders import action_case, list_case
from .core import RouteSmokeCase, assert_json_response
from .resources import create_inbound_event, create_worker_job
from .resolvers import worker_complete_payload

RUNTIME_WORKERS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("healthcheck", "GET", "/health", response_assert=assert_json_response),
    list_case("runtime-status", "GET", "/api/v1/runtime/status", response_assert=assert_json_response),
    list_case("scheduler-jobs", "GET", "/api/v1/scheduler/jobs", response_assert=assert_json_response),
    list_case("dashboard-devices", "GET", "/api/v1/dashboard/devices", response_assert=assert_json_response),
    list_case("dashboard-queue", "GET", "/api/v1/dashboard/queue", response_assert=assert_json_response),
    action_case("dashboard-queue-pause", "POST", "/api/v1/dashboard/queue/pause", 200, response_assert=assert_json_response),
    action_case("dashboard-queue-unpause", "POST", "/api/v1/dashboard/queue/unpause", 200, response_assert=assert_json_response),
    list_case("runtime-triggers", "GET", "/api/v1/runtime/triggers", setup=create_inbound_event, response_assert=assert_json_response),
    list_case("workers-list", "GET", "/api/v1/workers", response_assert=assert_json_response),
    action_case(
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
        response_assert=assert_json_response,
    ),
    action_case(
        "workers-claim-trigger",
        "POST",
        "/api/v1/workers/claim-trigger",
        200,
        setup=create_worker_job,
        payload={"worker_id": "worker_smoke_01"},
        response_assert=assert_json_response,
    ),
    action_case(
        "workers-complete-trigger",
        "POST",
        "/api/v1/workers/complete-trigger",
        200,
        setup=create_worker_job,
        payload=worker_complete_payload,
        response_assert=assert_json_response,
    ),
)
