from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
import re
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
    ConnectorActivityDefinition(
        provider_id="github",
        activity_id="download_repo_archive",
        service="repos",
        operation_type="read",
        label="Download repository archive",
        description="Download a repository archive (zipball/tarball) and save it to workflow storage.",
        required_scopes=("repo",),
        input_schema=(
            _field("owner", "Repository owner", "string", required=True),
            _field("repo", "Repository name", "string", required=True),
            _field(
                "download_location",
                "Download location",
                "select",
                required=True,
                default="",
                options=("", "workflow_storage", "workspace_media", "app_logs"),
                help_text="Choose where this archive should be stored.",
            ),
            _field("ref", "Branch, tag, or commit (optional)", "string", required=False, default=""),
            _field("archive_format", "Archive format", "string", required=False, default="zipball"),
            _field("output_prefix", "Output file prefix", "string", required=False, default=""),
        ),
        output_schema=(
            _output("provider", "Provider", "string"),
            _output("activity", "Activity", "string"),
            _output("repository", "Repository", "string"),
            _output("download_location", "Download location", "string"),
            _output("ref", "Resolved ref", "string"),
            _output("archive_format", "Archive format", "string"),
            _output("content_type", "Content type", "string"),
            _output("bytes_written", "Bytes written", "integer"),
            _output("archive_path", "Archive file path", "string"),
            _output("archive_file", "Archive file name", "string"),
        ),
        execution={"kind": "github_download_repo_archive"},
    ),
)


_SAFE_FILE_SEGMENT_RE = re.compile(r"[^a-z0-9._-]+")


def _safe_segment(value: str) -> str:
    normalized = _SAFE_FILE_SEGMENT_RE.sub("-", value.lower()).strip("-._")
    return normalized or "value"


def _download_location_dir(context: dict[str, Any] | None, download_location: str) -> Path:
    root_dir = Path(str((context or {}).get("_root_dir") or Path.cwd()))
    if download_location == "workflow_storage":
        path = root_dir / "backend" / "data" / "workflows"
    elif download_location == "workspace_media":
        path = root_dir / "media"
    elif download_location == "app_logs":
        path = root_dir / "backend" / "data" / "logs"
    else:
        raise RuntimeError("Download location is required for repository archive downloads.")
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def _github_download_repo_archive(
    provider_id: str,
    activity_id: str,
    resolved_inputs: dict[str, Any],
    base_url: str,
    headers: dict[str, str],
    context: dict[str, Any] | None,
    executor: RequestExecutor,
) -> dict[str, Any]:
    owner = str(resolved_inputs.get("owner") or "")
    repo = str(resolved_inputs.get("repo") or "")
    download_location = str(resolved_inputs.get("download_location") or "").strip()
    ref = str(resolved_inputs.get("ref") or "").strip()
    requested_format = str(resolved_inputs.get("archive_format") or "zipball").strip().lower()
    archive_format = "tarball" if requested_format == "tarball" else "zipball"
    suffix = ".tar.gz" if archive_format == "tarball" else ".zip"
    ref_segment = urllib.parse.quote(ref, safe="") if ref else ""
    endpoint = f"{base_url}/repos/{owner}/{repo}/{archive_format}"
    if ref_segment:
        endpoint = f"{endpoint}/{ref_segment}"

    status_code, payload = _execute_request(executor, endpoint, "GET", headers)
    _raise_for_status(status_code)

    raw_bytes_b64 = payload.get("_raw_bytes_b64") if isinstance(payload, dict) else None
    if not isinstance(raw_bytes_b64, str) or not raw_bytes_b64:
        raise RuntimeError("Repository archive download did not return binary payload data.")

    archive_bytes = base64.b64decode(raw_bytes_b64.encode("ascii"))
    output_prefix_raw = str(resolved_inputs.get("output_prefix") or "").strip()
    output_prefix = _safe_segment(output_prefix_raw) if output_prefix_raw else f"{_safe_segment(owner)}-{_safe_segment(repo)}"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    file_name = f"{output_prefix}-{archive_format}-{timestamp}{suffix}"
    archive_path = _download_location_dir(context, download_location) / file_name
    archive_path.write_bytes(archive_bytes)

    return {
        "provider": provider_id,
        "activity": activity_id,
        "repository": f"{owner}/{repo}",
        "download_location": download_location,
        "ref": ref,
        "archive_format": archive_format,
        "content_type": (payload.get("_raw_content_type") if isinstance(payload, dict) else "") or "application/octet-stream",
        "bytes_written": len(archive_bytes),
        "archive_path": str(archive_path),
        "archive_file": file_name,
    }


GITHUB_REPO_HANDLER_REGISTRY = {
    "github_repo_details": _github_repo_details,
    "github_list_repository_branches": _github_list_repository_branches,
    "github_download_repo_archive": _github_download_repo_archive,
}
