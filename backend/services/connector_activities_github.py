from __future__ import annotations

from typing import Any

from .connector_activities_catalog import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GITHUB_CONNECTOR_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_open_pull_requests",
        service="github",
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
        activity_id="list_assigned_issues",
        service="github",
        operation_type="read",
        label="List assigned issues",
        description="List issues assigned to the authenticated GitHub user.",
        required_scopes=("repo",),
        input_schema=(
            _field("state", "Issue state", "select", required=False, default="open", options=["open", "closed", "all"]),
            _field("limit", "Maximum issues", "integer", required=False, default=10),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("issues", "Issues", "array"),
            _output("count", "Issue count", "integer"),
        ),
        execution={"kind": "github_list_assigned_issues"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="repo_details",
        service="github",
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
)


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
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/pulls?state=open&per_page={limit}", "GET", headers)
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")
    pulls = [
        {
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "html_url": item.get("html_url"),
            "author": (item.get("user") or {}).get("login"),
        }
        for item in (payload or [])
    ]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "pull_requests": pulls,
        "count": len(pulls),
    }


def _github_list_assigned_issues(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    _context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    state = str(resolved_inputs.get("state") or "open")
    limit = _coerce_int(resolved_inputs.get("limit"), 10)
    status_code, payload = _execute_request(executor, f"{base_url}/issues?filter=assigned&state={state}&per_page={limit}", "GET", headers)
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")
    issues = [
        {
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "repository": (item.get("repository") or {}).get("full_name"),
            "html_url": item.get("html_url"),
        }
        for item in (payload or [])
        if "pull_request" not in item
    ]
    return {"provider": provider_id, "activity": activity_id, "issues": issues, "count": len(issues)}


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
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")
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


GITHUB_HANDLER_REGISTRY = {
    "github_list_open_pull_requests": _github_list_open_pull_requests,
    "github_list_assigned_issues": _github_list_assigned_issues,
    "github_repo_details": _github_repo_details,
}
