from __future__ import annotations

import urllib.parse
from typing import Any

from .connector_activities_defs import ConnectorActivityDefinition, JSON_SOURCE_HINT, _field, _output
from .connector_activities_runtime import RequestExecutor, _coerce_int, _execute_request


GITHUB_ACTION_ACTIVITY_DEFINITIONS: tuple[ConnectorActivityDefinition, ...] = (
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_repository_workflows",
        service="actions",
        operation_type="read",
        label="List workflows",
        description="List Actions workflows available in a repository.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("limit", "Maximum workflows", "integer", required=False, default=20),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("workflows", "Workflows", "array"),
            _output("count", "Workflow count", "integer"),
        ),
        execution={"kind": "github_list_repository_workflows"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="list_workflow_runs",
        service="actions",
        operation_type="read",
        label="List workflow runs",
        description="List workflow runs with optional branch, status, and event filters.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("workflow_id", "Workflow ID or file name", "string", required=False, placeholder="ci.yml or 123456"),
            _field("branch", "Branch", "string", required=False),
            _field("event", "Event", "string", required=False, placeholder="push"),
            _field("status", "Status", "string", required=False, placeholder="completed"),
            _field("limit", "Maximum runs", "integer", required=False, default=20),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("workflow_runs", "Workflow runs", "array"),
            _output("count", "Workflow run count", "integer"),
        ),
        execution={"kind": "github_list_workflow_runs"},
    ),
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="trigger_workflow_dispatch",
        service="actions",
        operation_type="write",
        label="Trigger workflow dispatch",
        description="Trigger a workflow_dispatch run for a GitHub Actions workflow.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field("workflow_id", "Workflow ID or file name", "string", required=True, placeholder="ci.yml or 123456"),
            _field("ref", "Git ref", "string", required=True, placeholder="main"),
            _field("inputs_payload", "Inputs JSON", "json", required=False, value_hint=JSON_SOURCE_HINT),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("workflow_id", "Workflow ID", "string"),
            _output("ref", "Git ref", "string"),
            _output("dispatched", "Dispatched", "boolean"),
        ),
        execution={"kind": "github_trigger_workflow_dispatch"},
    ),
)


def _raise_for_status(status_code: int) -> None:
    if status_code >= 400:
        raise RuntimeError(f"Connector activity request failed with status {status_code}.")


def _normalize_workflow(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "path": item.get("path"),
        "state": item.get("state"),
        "html_url": item.get("html_url"),
    }


def _normalize_workflow_run(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "display_title": item.get("display_title"),
        "status": item.get("status"),
        "conclusion": item.get("conclusion"),
        "event": item.get("event"),
        "branch": item.get("head_branch"),
        "html_url": item.get("html_url"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def _github_list_repository_workflows(
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
    query = urllib.parse.urlencode({"per_page": max(1, min(_coerce_int(resolved_inputs.get("limit"), 20), 100))})
    status_code, payload = _execute_request(executor, f"{base_url}/repos/{owner}/{repo}/actions/workflows?{query}", "GET", headers)
    _raise_for_status(status_code)
    workflows = [_normalize_workflow(item) for item in ((payload or {}).get("workflows") or [])]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "workflows": workflows,
        "count": len(workflows),
    }


def _github_list_workflow_runs(
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
    workflow_id = str(resolved_inputs.get("workflow_id") or "").strip()
    endpoint = f"{base_url}/repos/{owner}/{repo}/actions/runs"
    if workflow_id:
        endpoint = f"{base_url}/repos/{owner}/{repo}/actions/workflows/{urllib.parse.quote(workflow_id, safe='')}/runs"
    params: dict[str, Any] = {"per_page": max(1, min(_coerce_int(resolved_inputs.get("limit"), 20), 100))}
    for field in ("branch", "event", "status"):
        value = str(resolved_inputs.get(field) or "").strip()
        if value:
            params[field] = value
    status_code, payload = _execute_request(executor, f"{endpoint}?{urllib.parse.urlencode(params)}", "GET", headers)
    _raise_for_status(status_code)
    runs = [_normalize_workflow_run(item) for item in ((payload or {}).get("workflow_runs") or [])]
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "workflow_runs": runs,
        "count": len(runs),
    }


def _github_trigger_workflow_dispatch(
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
    workflow_id = str(resolved_inputs.get("workflow_id") or "")
    ref = str(resolved_inputs.get("ref") or "")
    body = {"ref": ref}
    inputs_payload = resolved_inputs.get("inputs_payload")
    if isinstance(inputs_payload, dict) and inputs_payload:
        body["inputs"] = inputs_payload
    status_code, _payload = _execute_request(
        executor,
        f"{base_url}/repos/{owner}/{repo}/actions/workflows/{urllib.parse.quote(workflow_id, safe='')}/dispatches",
        "POST",
        headers,
        body,
    )
    _raise_for_status(status_code)
    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "workflow_id": workflow_id,
        "ref": ref,
        "dispatched": True,
    }


GITHUB_ACTION_HANDLER_REGISTRY = {
    "github_list_repository_workflows": _github_list_repository_workflows,
    "github_list_workflow_runs": _github_list_workflow_runs,
    "github_trigger_workflow_dispatch": _github_trigger_workflow_dispatch,
}
