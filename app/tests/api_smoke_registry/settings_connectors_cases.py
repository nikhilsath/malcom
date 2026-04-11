from __future__ import annotations

import os
from typing import Any

from .builders import action_case, list_case, patch_case
from .core import RouteSmokeCase, SmokeContext, assert_json_response, resolve_value
from .resolvers import oauth_callback_params, oauth_start_setup, refresh_setup, revoke_setup


def assert_redirect_to_connectors(response: object, _: SmokeContext, __: dict[str, object]) -> None:
    location = response.headers.get("location", "")
    assert location.startswith("/settings/connectors.html?"), "Expected redirect to connectors page"


def invoke_without_redirect(case: RouteSmokeCase, context: SmokeContext, state: dict[str, object]) -> object:
    path = resolve_value(case.path, context, state)
    headers = resolve_value(case.headers, context, state)
    params = resolve_value(case.params, context, state)
    return context.client.request(case.method.upper(), path, headers=headers, params=params, follow_redirects=False)


def connector_setup(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/connectors",
        json={
            "id": "github-primary",
            "provider": "github",
            "name": "GitHub",
            "status": "draft",
            "auth_type": "bearer",
            "scopes": ["repo"],
            "base_url": "https://api.github.com",
            "owner": "Workspace",
            "auth_config": {"access_token_input": "ghp_secret_token"},
        },
    )
    response.raise_for_status()
    return {"connector": response.json()}


def connector_path(_context: SmokeContext, state: dict[str, object]) -> str:
    connector = state.get("connector") if isinstance(state, dict) else None
    connector_id = "github-primary"
    if isinstance(connector, dict):
        connector_id = str(connector.get("id") or connector_id)
    return f"/api/v1/connectors/{connector_id}"


def configure_backup_dir(context: SmokeContext) -> None:
    previous_backup_dir = os.environ.get("MALCOM_BACKUP_DIR")
    setattr(context, "_previous_backup_dir", previous_backup_dir)
    backup_dir = context.root_dir / "test-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MALCOM_BACKUP_DIR"] = str(backup_dir)
    setattr(context, "_backup_dir", backup_dir)


def cleanup_backup_dir(context: SmokeContext) -> None:
    previous_backup_dir = getattr(context, "_previous_backup_dir", None)
    if previous_backup_dir:
        os.environ["MALCOM_BACKUP_DIR"] = previous_backup_dir
    else:
        os.environ.pop("MALCOM_BACKUP_DIR", None)


def backup_create_setup(context: SmokeContext) -> dict[str, Any]:
    configure_backup_dir(context)
    return {"backup_dir": getattr(context, "_backup_dir", None)}


def backup_list_setup(context: SmokeContext) -> dict[str, Any]:
    state = backup_create_setup(context)
    response = context.client.post("/api/v1/settings/data/backups")
    response.raise_for_status()
    backup = response.json().get("backup") or {}
    state["backup"] = backup
    return state


def backup_restore_setup(context: SmokeContext) -> dict[str, Any]:
    state = backup_list_setup(context)
    backup = state.get("backup") or {}
    filename = str(backup.get("filename") or "")
    if not filename:
        raise AssertionError("Expected backup create setup to return a filename for restore smoke coverage")
    state["backup_filename"] = filename
    return state


def restore_backup_payload(_context: SmokeContext, state: dict[str, object]) -> dict[str, object]:
    return {"backup_id": str(state.get("backup_filename") or "")}


def assert_backup_create_response(response: object, context: SmokeContext, _: dict[str, object]) -> None:
    assert_json_response(response, context, {})
    body = response.json()
    assert body.get("ok") is True, body
    backup = body.get("backup")
    assert isinstance(backup, dict), body
    assert backup.get("filename"), body
    assert backup.get("path"), body


def assert_backup_list_response(response: object, context: SmokeContext, _: dict[str, object]) -> None:
    assert_json_response(response, context, {})
    body = response.json()
    assert isinstance(body.get("backups"), list), body
    assert len(body["backups"]) >= 1, body
    assert body["backups"][0].get("filename"), body


def assert_backup_restore_response(response: object, context: SmokeContext, _: dict[str, object]) -> None:
    assert_json_response(response, context, {})
    body = response.json()
    assert body.get("ok") is True, body
    assert body.get("restored_at"), body


SETTINGS_CONNECTORS_CASES: tuple[RouteSmokeCase, ...] = (
    list_case("settings-get", "GET", "/api/v1/settings", response_assert=assert_json_response),
    patch_case(
        "settings-patch",
        "/api/v1/settings",
        "/api/v1/settings",
        None,
        {"general": {"environment": "live", "timezone": "utc"}},
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-list",
        "GET",
        "/api/v1/connectors",
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-create",
        "POST",
        "/api/v1/connectors",
        201,
        route_path="/api/v1/connectors",
        payload={
            "id": "smoke-github-primary",
            "provider": "github",
            "name": "Smoke GitHub",
            "status": "draft",
            "auth_type": "bearer",
            "scopes": ["repo"],
            "base_url": "https://api.github.com",
            "owner": "Workspace",
            "auth_config": {"access_token_input": "ghp_secret_token"},
        },
        response_assert=assert_json_response,
    ),
    patch_case(
        "connectors-patch",
        connector_path,
        "/api/v1/connectors/{connector_id}",
        connector_setup,
        {"name": "GitHub Updated", "status": "connected"},
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-delete",
        "DELETE",
        connector_path,
        200,
        route_path="/api/v1/connectors/{connector_id}",
        setup=connector_setup,
        response_assert=assert_json_response,
    ),
    patch_case(
        "connectors-auth-policy-patch",
        "/api/v1/connectors/auth-policy",
        "/api/v1/connectors/auth-policy",
        None,
        {
            "auth_policy": {
                "rotation_interval_days": 60,
                "reconnect_requires_approval": True,
                "credential_visibility": "admin_only",
            }
        },
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-test",
        "POST",
        "/api/v1/connectors/github-primary/test",
        200,
        route_path="/api/v1/connectors/{connector_id}/test",
        setup=connector_setup,
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-github-repositories",
        "GET",
        "/api/v1/connectors/github-primary/github/repositories",
        route_path="/api/v1/connectors/{connector_id}/github/repositories",
        setup=connector_setup,
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-activity-catalog",
        "GET",
        "/api/v1/connectors/activity-catalog",
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-http-presets",
        "GET",
        "/api/v1/connectors/http-presets",
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-oauth-start",
        "POST",
        "/api/v1/connectors/google/oauth/start",
        200,
        route_path="/api/v1/connectors/{provider}/oauth/start",
        payload={
            "connector_id": "google-primary",
            "name": "Google",
            "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
            "owner": "Workspace",
            "client_id": "google-client-id",
            "client_secret_input": "google-client-secret",
        },
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-oauth-callback",
        "GET",
        "/api/v1/connectors/google/oauth/callback",
        route_path="/api/v1/connectors/{provider}/oauth/callback",
        setup=oauth_start_setup,
        params=oauth_callback_params,
        response_assert=assert_json_response,
    ),
    list_case(
        "connectors-oauth-callback-html",
        "GET",
        "/api/v1/connectors/google/oauth/callback",
        303,
        route_path="/api/v1/connectors/{provider}/oauth/callback",
        setup=oauth_start_setup,
        headers={"Accept": "text/html"},
        params=oauth_callback_params,
        response_assert=assert_redirect_to_connectors,
        invoke=invoke_without_redirect,
    ),
    action_case(
        "connectors-refresh",
        "POST",
        "/api/v1/connectors/google-primary/refresh",
        200,
        route_path="/api/v1/connectors/{connector_id}/refresh",
        setup=refresh_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "connectors-revoke",
        "POST",
        "/api/v1/connectors/google-primary/revoke",
        200,
        route_path="/api/v1/connectors/{connector_id}/revoke",
        setup=revoke_setup,
        response_assert=assert_json_response,
    ),
    action_case(
        "settings-backup-create",
        "POST",
        "/api/v1/settings/data/backups",
        200,
        route_path="/api/v1/settings/data/backups",
        setup=backup_create_setup,
        teardown=cleanup_backup_dir,
        response_assert=assert_backup_create_response,
    ),
    list_case(
        "settings-backup-list",
        "GET",
        "/api/v1/settings/data/backups",
        setup=backup_list_setup,
        teardown=cleanup_backup_dir,
        response_assert=assert_backup_list_response,
    ),
    action_case(
        "settings-backup-restore",
        "POST",
        "/api/v1/settings/data/backups/restore",
        200,
        route_path="/api/v1/settings/data/backups/restore",
        setup=backup_restore_setup,
        teardown=cleanup_backup_dir,
        payload=restore_backup_payload,
        response_assert=assert_backup_restore_response,
    ),
    action_case(
        "settings-proxy-test",
        "POST",
        "/api/v1/settings/proxy/test",
        200,
        route_path="/api/v1/settings/proxy/test",
        payload={
            "domain": "tools.example.com",
            "http_port": 80,
            "https_port": 443,
            "enabled": True,
        },
        response_assert=assert_json_response,
    ),
)
