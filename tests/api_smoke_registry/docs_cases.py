from __future__ import annotations

from typing import Any

from .builders import action_case, create_case, detail_case, list_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response
from .resolvers import state_path


def doc_setup(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/docs",
        json={
            "slug": "smoke-article",
            "title": "Smoke Article",
            "summary": "Created for route smoke coverage.",
            "content": "# Smoke Article\n\nTest content.",
            "tags": ["smoke"],
            "is_ai_created": False,
        },
    )
    response.raise_for_status()
    return {"doc": response.json()}


DOC_DETAIL_PATH = state_path("doc", "slug", prefix="/api/v1/docs/")

DOCS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("docs-list", "GET", "/api/v1/docs", response_assert=assert_json_response),
    create_case(
        "docs-create",
        "/api/v1/docs",
        {
            "slug": "smoke-create",
            "title": "Smoke Create Article",
            "summary": "Smoke create.",
            "content": "# Smoke\n\nContent.",
            "tags": [],
            "is_ai_created": True,
        },
        response_assert=assert_json_response,
    ),
    detail_case(
        "docs-detail",
        DOC_DETAIL_PATH,
        "/api/v1/docs/{slug}",
        doc_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "docs-update",
        "PUT",
        DOC_DETAIL_PATH,
        expected_status=200,
        route_path="/api/v1/docs/{slug}",
        setup=doc_setup,
        payload={"content": "# Updated\n\nNew content.", "is_ai_created": False},
        response_assert=assert_json_response,
    ),
)
