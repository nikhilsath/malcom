from __future__ import annotations

from .builders import action_case, create_case, detail_case, list_case, patch_case
from .core import RouteSmokeCase, assert_json_response
from .resources import create_log_table
from .resolvers import automation_setup, nested_state_path, run_detail_path, run_setup

AUTOMATION_DETAIL_PATH = nested_state_path("automation", "id", prefix="/api/v1/automations/", suffix="")
AUTOMATION_VALIDATE_PATH = nested_state_path("automation", "id", prefix="/api/v1/automations/", suffix="/validate")
AUTOMATION_EXECUTE_PATH = nested_state_path("automation", "id", prefix="/api/v1/automations/", suffix="/execute")
AUTOMATION_RUNS_PATH = nested_state_path("automation", "id", prefix="/api/v1/automations/", suffix="/runs")
LOG_TABLE_DETAIL_PATH = nested_state_path("log_table", "id", prefix="/api/v1/log-tables/", suffix="")
LOG_TABLE_ROWS_PATH = nested_state_path("log_table", "id", prefix="/api/v1/log-tables/", suffix="/rows")
LOG_TABLE_CLEAR_PATH = nested_state_path("log_table", "id", prefix="/api/v1/log-tables/", suffix="/rows/clear")


def log_table_setup(context):
    return {"log_table": create_log_table(context)}


AUTOMATION_LOG_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("automations-list", "GET", "/api/v1/automations", response_assert=assert_json_response),
    list_case("automations-workflow-connectors", "GET", "/api/v1/automations/workflow-connectors", response_assert=assert_json_response),
    create_case(
        "automations-create",
        "/api/v1/automations",
        {
            "name": "Smoke automation create",
            "description": "Created through route smoke.",
            "enabled": True,
            "trigger_type": "manual",
            "trigger_config": {},
            "steps": [{"type": "log", "name": "Route smoke", "config": {"message": "Smoke"}}],
        },
        response_assert=assert_json_response,
    ),
    detail_case("automations-detail", AUTOMATION_DETAIL_PATH, "/api/v1/automations/{automation_id}", automation_setup, response_assert=assert_json_response),
    patch_case(
        "automations-patch",
        AUTOMATION_DETAIL_PATH,
        "/api/v1/automations/{automation_id}",
        automation_setup,
        {"name": "Updated smoke automation"},
        response_assert=assert_json_response,
    ),
    action_case(
        "automations-delete",
        "DELETE",
        AUTOMATION_DETAIL_PATH,
        204,
        route_path="/api/v1/automations/{automation_id}",
        setup=automation_setup,
    ),
    action_case(
        "automations-validate",
        "POST",
        AUTOMATION_VALIDATE_PATH,
        200,
        route_path="/api/v1/automations/{automation_id}/validate",
        setup=automation_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "automations-execute",
        "POST",
        AUTOMATION_EXECUTE_PATH,
        200,
        route_path="/api/v1/automations/{automation_id}/execute",
        setup=automation_setup,
        response_assert=assert_json_response,
    ),
    detail_case(
        "automations-runs",
        AUTOMATION_RUNS_PATH,
        "/api/v1/automations/{automation_id}/runs",
        automation_setup,
        response_assert=assert_json_response,
    ),
    list_case("runs-list", "GET", "/api/v1/runs", response_assert=assert_json_response),
    detail_case("runs-detail", run_detail_path, "/api/v1/runs/{run_id}", run_setup, response_assert=assert_json_response),
    list_case("log-tables-list", "GET", "/api/v1/log-tables", response_assert=assert_json_response),
    create_case(
        "log-tables-create",
        "/api/v1/log-tables",
        {
            "name": "smoke_events",
            "description": "Smoke test log table.",
            "columns": [{"column_name": "payload", "data_type": "text", "nullable": True}],
        },
        response_assert=assert_json_response,
    ),
    detail_case("log-tables-detail", LOG_TABLE_DETAIL_PATH, "/api/v1/log-tables/{table_id}", log_table_setup, response_assert=assert_json_response),
    detail_case("log-tables-rows", LOG_TABLE_ROWS_PATH, "/api/v1/log-tables/{table_id}/rows", log_table_setup, response_assert=assert_json_response),
    action_case(
        "log-tables-rows-clear",
        "POST",
        LOG_TABLE_CLEAR_PATH,
        200,
        route_path="/api/v1/log-tables/{table_id}/rows/clear",
        setup=log_table_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "log-tables-delete",
        "DELETE",
        LOG_TABLE_DETAIL_PATH,
        204,
        route_path="/api/v1/log-tables/{table_id}",
        setup=log_table_setup,
    ),
)
