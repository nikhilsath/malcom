from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GITHUB_ISSUE_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_assigned_issues",
        service="issues",
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
        activity_id="list_repository_issues",
        service="issues",
        operation_type="read",
        label="List repository issues",
        description="List repository issues with state and label filters.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("state", "Issue state", "select", required=False, default="open", options=["open", "closed", "all"]),
            _field("labels", "Labels", "string", required=False, placeholder="bug,triage"),
            _field("limit", "Maximum issues", "integer", required=False, default=20),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("issues", "Issues", "array"),
            _output("count", "Issue count", "integer"),
        ),
        execution={"kind": "github_list_repository_issues"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="create_issue",
        service="issues",
        operation_type="write",
        label="Create issue",
        description="Create a new GitHub issue with optional labels and assignees.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("title", "Issue title", "string", required=True),
            _field("body", "Issue body", "textarea", required=False),
            _field("labels", "Labels", "string", required=False, placeholder="bug,triage"),
            _field("assignees", "Assignees", "string", required=False, placeholder="octocat,teammate"),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("issue", "Issue", "object"),
        ),
        execution={"kind": "github_create_issue"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="add_issue_comment",
        service="issues",
        operation_type="write",
        label="Add issue comment",
        description="Add a comment to a GitHub issue.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("issue_number", "Issue number", "integer", required=True),
            _field("body", "Comment body", "textarea", required=True),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("issue_number", "Issue number", "integer"),
            _output("comment", "Comment", "object"),
        ),
        execution={"kind": "github_add_issue_comment"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _csv_to_list(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item.get("number"),
        "title": item.get("title"),
        "state": item.get("state"),
        "labels": [label.get("name") for label in (item.get("labels") or []) if isinstance(label, dict)],
        "assignees": [user.get("login") for user in (item.get("assignees") or []) if isinstance(user, dict)],
        "html_url": item.get("html_url"),
        "author": (item.get("user") or {}).get("login"),
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
    query = urllib.parse.urlencode({"filter": "assigned", "state": state, "per_page": max(1, min(limit, 100))})
    status_code, payload = _execute_request(executor, f"{base_url}/issues?{query}", "GET", headers)
    _raise_for_status(status_code)
    issues = [_normalize_issue(item) for item in (payload or []) if "pull_request" not in item]
    return {"provider": provider_id, "activity": activity_id, "issues": issues, "count": len(issues)}


def _github_list_repository_issues(
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
    params: dict[str, Any] = {
        "state": str(resolved_inputs.get("state") or "open"),
        "per_page": max(1, min(_coerce_int(resolved_inputs.get("limit"), 20), 100)),
    }
    labels = str(resolved_inputs.get("labels") or "").strip()
    if labels:
        params["labels"] = labels
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/repos/{owner}/{repo}/issues?{urllib.parse.urlencode(params)}",
        "GET",
        headers,
    )
    _raise_for_status(status_code)
    issues = [_normalize_issue(item) for item in (payload or []) if "pull_request" not in item]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "issues": issues,
        "count": len(issues),
    }


def _github_create_issue(
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
    body = {
        "title": str(resolved_inputs.get("title") or ""),
        "body": str(resolved_inputs.get("body") or ""),
    }
    labels = _csv_to_list(resolved_inputs.get("labels"))
    assignees = _csv_to_list(resolved_inputs.get("assignees"))
    if labels:
        body["labels"] = labels
    if assignees:
        body["assignees"] = assignees
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/issues", "POST", headers, body)
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "issue": _normalize_issue(payload),
    }


def _github_add_issue_comment(
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
    issue_number = _coerce_int(resolved_inputs.get("issue_number"), 0)
    status_code, payload = _execute_request(
        executor,
        f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
        "POST",
        headers,
        {"body": str(resolved_inputs.get("body") or "")},
    )
    _raise_for_status(status_code)
    payload = payload or {}
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "issue_number": issue_number,
        "comment": {
            "id": payload.get("id"),
            "body": payload.get("body"),
            "html_url": payload.get("html_url"),
            "author": (payload.get("user") or {}).get("login"),
        },
    }


GITHUB_ISSUE_HANDLER_REGISTRY = {
    "github_list_assigned_issues": _github_list_assigned_issues,
    "github_list_repository_issues": _github_list_repository_issues,
    "github_create_issue": _github_create_issue,
    "github_add_issue_comment": _github_add_issue_comment,
}
