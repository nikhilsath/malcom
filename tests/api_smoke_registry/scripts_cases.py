from __future__ import annotations

from .builders import create_case, detail_case, list_case, patch_case
from .core import RouteSmokeCase, assert_json_response
from .resolvers import script_setup, state_path

SCRIPT_DETAIL_PATH = state_path("script", prefix="/api/v1/scripts/")

SCRIPTS_CASES: tuple[RouteSmokeCase, ...] = (
    create_case(
        "scripts-validate",
        "/api/v1/scripts/validate",
        {"language": "python", "code": "def run(payload):\n    return payload\n"},
        expected_status=200,
        response_assert=assert_json_response,
    ),
    list_case("scripts-list", "GET", "/api/v1/scripts", response_assert=assert_json_response),
    detail_case(
        "scripts-detail",
        SCRIPT_DETAIL_PATH,
        "/api/v1/scripts/{script_id}",
        script_setup,
        response_assert=assert_json_response,
    ),
    create_case(
        "scripts-create",
        "/api/v1/scripts",
        {
            "name": "Smoke Create",
            "description": "Create via route smoke.",
            "language": "python",
            "code": "def run(payload):\n    return payload\n",
        },
        response_assert=assert_json_response,
    ),
    patch_case(
        "scripts-update",
        SCRIPT_DETAIL_PATH,
        "/api/v1/scripts/{script_id}",
        script_setup,
        {"code": "def run(payload):\n    payload['updated'] = True\n    return payload\n"},
        response_assert=assert_json_response,
    ),
)
