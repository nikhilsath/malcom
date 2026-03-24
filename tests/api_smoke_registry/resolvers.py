from __future__ import annotations

from typing import Any

from .core import SmokeContext
from .resources import create_automation, create_script, start_google_oauth


def state_path(key: str, field: str = "id", *, prefix: str) -> Any:
    def _resolver(_context: SmokeContext, state: dict[str, Any]) -> str:
        return f"{prefix}{state[key][field]}"

    return _resolver


def nested_state_path(key: str, field: str, *, prefix: str, suffix: str) -> Any:
    def _resolver(_context: SmokeContext, state: dict[str, Any]) -> str:
        return f"{prefix}{state[key][field]}{suffix}"

    return _resolver


def worker_complete_payload(_context: SmokeContext, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "worker_id": "worker_smoke_01",
        "job_id": state["job"]["job_id"],
        "status": "completed",
        "response_summary": "Route smoke completed trigger.",
    }


def inbound_auth_headers(_context: SmokeContext, state: dict[str, Any]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {state['inbound']['secret']}",
        "Content-Type": "application/json",
    }


def script_setup(context: SmokeContext) -> dict[str, Any]:
    return {"script": create_script(context)}


def automation_setup(context: SmokeContext) -> dict[str, Any]:
    return {"automation": create_automation(context)}


def run_setup(context: SmokeContext) -> dict[str, Any]:
    automation = create_automation(context)
    run_id = context.client.post(f"/api/v1/automations/{automation['id']}/execute").json()["run_id"]
    return {"run_id": run_id}


def run_detail_path(_context: SmokeContext, state: dict[str, Any]) -> str:
    return f"/api/v1/runs/{state['run_id']}"


def oauth_start_setup(context: SmokeContext) -> dict[str, Any]:
    return {"oauth": start_google_oauth(context)}


def connector_setup(context: SmokeContext) -> dict[str, Any]:
    from .resources import create_connector_record

    return {"connector": create_connector_record(context)}


def oauth_callback_params(_context: SmokeContext, state: dict[str, Any]) -> dict[str, str]:
    return {"state": state["oauth"]["state"], "code": "demo"}


def refresh_setup(context: SmokeContext) -> dict[str, Any]:
    state = start_google_oauth(context)
    callback = context.client.get(
        "/api/v1/connectors/google/oauth/callback",
        params={"state": state["state"], "code": "demo"},
    ).json()
    return {"callback": callback}


def revoke_setup(context: SmokeContext) -> dict[str, Any]:
    state = start_google_oauth(context)
    callback = context.client.get(
        "/api/v1/connectors/google/oauth/callback",
        params={"state": state["state"], "code": "demo"},
    ).json()
    return {"callback": callback}
