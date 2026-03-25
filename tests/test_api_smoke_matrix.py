from __future__ import annotations

import pytest

from tests.api_smoke_registry import (
    ROUTE_SCENARIO_MAP,
    SMOKE_CASES,
    create_smoke_context,
    invoke_smoke_case,
    validate_route_scenario_mapping,
)


pytestmark = pytest.mark.smoke


@pytest.mark.parametrize("case", SMOKE_CASES, ids=[case.name for case in SMOKE_CASES])
def test_internal_api_route_smoke_matrix(case) -> None:
    context = create_smoke_context()
    try:
        invoke_smoke_case(case, context)
    finally:
        context.close()


def test_internal_api_routes_have_smoke_coverage() -> None:
    missing, extra = validate_route_scenario_mapping()

    assert all(ROUTE_SCENARIO_MAP.values())
    assert not missing, f"Missing route smoke coverage for: {missing}"
    assert not extra, f"Route smoke registry contains unknown routes: {extra}"
