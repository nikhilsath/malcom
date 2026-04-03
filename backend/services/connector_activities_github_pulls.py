from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GITHUB_PULL_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_open_pull_requests",
        service="pulls",
        operation_type="read",
        label="List open pull requests",
        description="List open pull requests for a repository.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("limit", "Maximum pull requests", "integer", required=False, default=10),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("pull_requests", "Pull requests", "array"),
            _output("count", "Pull request count", "integer"),
        ),
        execution={"kind": "github_list_open_pull_requests"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="get_pull_request",
        service="pulls",
        operation_type="read",
        label="Get pull request",
        description="Fetch detailed metadata for a single pull request.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("pull_number", "Pull request number", "integer", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("pull_request", "Pull request", "object"),
        ),
        execution={"kind": "github_get_pull_request"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _normalize_pull_request(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item.get("number"),
        "title": item.get("title"),
        "state": item.get("state"),
        "html_url": item.get("html_url"),
        "author": (item.get("user") or {}).get("login"),
        "draft": bool(item.get("draft")),
        "head_branch": (item.get("head") or {}).get("ref"),
        "base_branch": (item.get("base") or {}).get("ref"),
        "mergeable": item.get("mergeable"),
    }


def _github_list_open_pull_requests(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    owner = str(resolved_inputs.get("owner") or "")
    repo = str(resolved_inputs.get("repo") or "")
    limit = _coerce_int(resolved_inputs.get("limit"), 10)
    query = urllib.parse.urlencode({"state": "open", "per_page": max(1, min(limit, 100))})
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/pulls?{query}", "GET", headers)
    _raise_for_status(status_code)
    pulls = [_normalize_pull_request(item) for item in (payload or [])]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "pull_requests": pulls,
        "count": len(pulls),
    }


def _github_get_pull_request(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    owner = str(resolved_inputs.get("owner") or "")
    repo = str(resolved_inputs.get("repo") or "")
    pull_number = _coerce_int(resolved_inputs.get("pull_number"), 0)
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/pulls/{pull_number}", "GET", headers)
    _raise_for_status(status_code)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "pull_request": _normalize_pull_request(payload or {}),
    }


GITHUB_PULL_HANDLER_REGISTRY = {
    "github_list_open_pull_requests": _github_list_open_pull_requests,
    "github_get_pull_request": _github_get_pull_request,
}
