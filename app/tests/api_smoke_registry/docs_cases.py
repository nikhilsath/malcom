from __future__ import annotations

from typing import Any
from uuid import uuid4

from .builders import action_case, detail_case, list_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response
from .resolvers import state_path


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _docs_create_payload(_context: SmokeContext, _state: dict[str, Any]) -> dict[str, Any]:
    slug = _unique_slug("smoke-create")
    return {
        "slug": slug,
        "title": "Smoke Create Article",
        "summary": "Smoke create.",
        "content": "# Smoke\n\nContent.",
        "tags": [],
        "is_ai_created": True,
    }


def doc_setup(context: SmokeContext) -> dict[str, Any]:
    slug = _unique_slug("smoke-article")
    response = context.client.post(
        "/api/v1/docs",
        json={
            "slug": slug,
            "title": "Smoke Article",
            "summary": "Created for route smoke coverage.",
            "content": "# Smoke Article\n\nTest content.",
            "tags": ["smoke"],
            "is_ai_created": False,
        },
    )
    response.raise_for_status()
    return {"doc": response.json()}


def _assert_doc_detail_has_content(response: Any, _: SmokeContext, __: dict[str, Any]) -> None:
    """Validate that docs detail response includes non-empty content from markdown file."""
    assert_json_response(response, _, __)
    data = response.json()
    assert "content" in data, "Response missing 'content' field"
    assert isinstance(data["content"], str), "Content must be a string"
    assert len(data["content"]) > 0, "Content must not be empty (markdown file not loaded)"
    assert "#" in data["content"], "Content should contain markdown heading"


DOC_DETAIL_PATH = state_path("doc", "slug", prefix="/api/v1/docs/")

DOCS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("docs-list", "GET", "/api/v1/docs", response_assert=assert_json_response),
    action_case(
        "docs-create",
        "POST",
        "/api/v1/docs",
        expected_status=201,
        payload=_docs_create_payload,
        response_assert=assert_json_response,
    ),
    detail_case(
        "docs-detail",
        DOC_DETAIL_PATH,
        "/api/v1/docs/{slug}",
        doc_setup,
        response_assert=_assert_doc_detail_has_content,
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
