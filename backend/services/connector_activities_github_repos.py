from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GITHUB_REPO_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="repo_details",
        service="repos",
        operation_type="read",
        label="Repository details",
        description="Fetch normalized metadata for a GitHub repository.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("default_branch", "Default branch", "string"),
            _output("visibility", "Visibility", "string"),
            _output("open_issues_count", "Open issues count", "integer"),
            _output("stars", "Stars", "integer"),
        ),
        execution={"kind": "github_repo_details"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_repository_branches",
        service="repos",
        operation_type="read",
        label="List repository branches",
        description="List repository branches with protection and commit metadata.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("limit", "Maximum branches", "integer", required=False, default=20),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("branches", "Branches", "array"),
            _output("count", "Branch count", "integer"),
        ),
        execution={"kind": "github_list_repository_branches"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _github_repo_details(
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
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}", "GET", headers)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": payload.get("full_name") or f"{owner}/{repo}",
        "default_branch": payload.get("default_branch"),
        "visibility": payload.get("visibility") or ("private" if payload.get("private") else "public"),
        "open_issues_count": int(payload.get("open_issues_count") or 0),
        "stars": int(payload.get("stargazers_count") or 0),
    }


def _github_list_repository_branches(
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
    limit = _coerce_int(resolved_inputs.get("limit"), 20)
    query = urllib.parse.urlencode({"per_page": max(1, min(limit, 100))})
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/branches?{query}", "GET", headers)
    _raise_for_status(status_code)
    branches = [
        {
            "name": item.get("name"),
            "protected": bool(item.get("protected")),
            "commit_sha": (item.get("commit") or {}).get("sha"),
            "html_url": (item.get("_links") or {}).get("html"),
        }
        for item in (payload or [])
    ]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "branches": branches,
        "count": len(branches),
    }


GITHUB_REPO_HANDLER_REGISTRY = {
    "github_repo_details": _github_repo_details,
    "github_list_repository_branches": _github_list_repository_branches,
}
