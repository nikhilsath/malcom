from __future__ import annotations

import pytest

from tests.api_smoke_registry import (
    SMOKE_CASES,
    create_smoke_context,
    get_internal_api_route_signatures,
    invoke_smoke_case,
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
    route_signatures = get_internal_api_route_signatures()
    case_signatures = {
        (case.method.upper(), case.route_path or (case.path if isinstance(case.path, str) else ""))
        for case in SMOKE_CASES
    }

    missing = sorted(route_signatures - case_signatures)
    extra = sorted(case_signatures - route_signatures)

    assert not missing, f"Missing route smoke coverage for: {missing}"
    assert not extra, f"Route smoke registry contains unknown routes: {extra}"
