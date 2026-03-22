from __future__ import annotations

from typing import Any

from .core import SmokeContext


def create_inbound_api(context: SmokeContext, *, slug: str = "smoke-inbound") -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/inbound",
        json={
            "name": f"{slug} inbound",
            "description": "Smoke inbound endpoint.",
            "path_slug": slug,
            "enabled": True,
        },
    )
    response.raise_for_status()
    return response.json()


def create_script(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/scripts",
        json={
            "name": "Smoke Script",
            "description": "Script detail smoke test.",
            "language": "python",
            "code": "def run(payload):\n    return payload\n",
        },
    )
    response.raise_for_status()
    return response.json()


def create_automation(context: SmokeContext, *, name: str = "Smoke automation") -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/automations",
        json={
            "name": name,
            "description": "Route smoke automation.",
            "enabled": True,
            "trigger_type": "manual",
            "trigger_config": {},
            "steps": [{"type": "log", "name": "Log payload", "config": {"message": "Smoke"}}],
        },
    )
    response.raise_for_status()
    return response.json()


def create_outgoing_api(context: SmokeContext, *, api_type: str) -> dict[str, Any]:
    payload = {
        "type": api_type,
        "name": f"{api_type} api",
        "description": "Created for route smoke coverage.",
        "path_slug": api_type.replace("_", "-"),
        "enabled": True,
        "destination_url": "https://example.com/hooks/smoke",
        "http_method": "POST",
        "auth_type": "none",
        "payload_template": "{\"smoke\":true}",
    }
    if api_type == "outgoing_scheduled":
        payload["scheduled_time"] = "09:30"
    if api_type == "outgoing_continuous":
        payload["repeat_enabled"] = True
        payload["repeat_interval_minutes"] = 15
    response = context.client.post("/api/v1/apis", json=payload)
    response.raise_for_status()
    return response.json()


def create_connector_record(context: SmokeContext, *, auth_type: str = "bearer") -> dict[str, Any]:
    payload = {
        "connectors": {
            "records": [
                {
                    "id": "github-primary",
                    "provider": "github",
                    "name": "GitHub",
                    "status": "draft",
                    "auth_type": auth_type,
                    "scopes": ["repo"],
                    "base_url": "https://api.github.com",
                    "owner": "Workspace",
                    "auth_config": {
                        "access_token_input": "ghp_secret_token",
                        "refresh_token_input": "ghr_secret_refresh" if auth_type == "oauth2" else None,
                    },
                }
            ]
        }
    }
    response = context.client.patch("/api/v1/settings", json=payload)
    response.raise_for_status()
    return response.json()["connectors"]["records"][0]


def start_google_oauth(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/connectors/google/oauth/start",
        json={
            "connector_id": "google-primary",
            "name": "Google",
            "redirect_uri": "http://localhost:8000/api/v1/connectors/google/oauth/callback",
            "owner": "Workspace",
            "client_id": "google-client-id",
            "client_secret_input": "google-client-secret",
        },
    )
    response.raise_for_status()
    return response.json()


def create_worker_job(context: SmokeContext) -> dict[str, Any]:
    inbound = create_inbound_api(context, slug="smoke-worker-source")
    context.client.post(
        f"/api/v1/inbound/{inbound['id']}",
        headers={"Authorization": f"Bearer {inbound['secret']}", "Content-Type": "application/json"},
        json={"id": 999},
    ).raise_for_status()
    context.client.post(
        "/api/v1/workers/register",
        json={
            "worker_id": "worker_smoke_01",
            "name": "Smoke Worker",
            "hostname": "smoke-worker.local",
            "address": "127.0.0.1",
            "capabilities": ["runtime-trigger-execution"],
        },
    ).raise_for_status()
    claim = context.client.post("/api/v1/workers/claim-trigger", json={"worker_id": "worker_smoke_01"})
    claim.raise_for_status()
    return {"job": claim.json()["job"]}


def create_inbound_event(context: SmokeContext) -> dict[str, Any]:
    inbound = create_inbound_api(context, slug="smoke-trigger-source")
    response = context.client.post(
        f"/api/v1/inbound/{inbound['id']}",
        headers={"Authorization": f"Bearer {inbound['secret']}", "Content-Type": "application/json"},
        json={"id": 42},
    )
    response.raise_for_status()
    return {"inbound": inbound}


def configure_local_llm(context: SmokeContext) -> dict[str, Any]:
    response = context.client.patch(
        "/api/v1/tools/llm-deepl/local-llm",
        json={
            "enabled": True,
            "provider": "lm_studio_api_v1",
            "server_base_url": "http://127.0.0.1:1234",
            "model_identifier": "qwen/qwen3.5-9b",
            "endpoints": {
                "models": "/api/v1/models",
                "chat": "/api/v1/chat",
                "model_load": "/api/v1/models/load",
                "model_download": "/api/v1/models/download",
                "model_download_status": "/api/v1/models/download/status/:job_id",
            },
        },
    )
    response.raise_for_status()
    return response.json()


def configure_smtp_tool(context: SmokeContext) -> dict[str, Any]:
    response = context.client.patch(
        "/api/v1/tools/smtp",
        json={"enabled": True, "bind_host": "127.0.0.1", "port": 2525, "recipient_email": "recipient@example.com"},
    )
    response.raise_for_status()
    return response.json()


def configure_image_magic_tool(context: SmokeContext) -> dict[str, Any]:
    response = context.client.patch(
        "/api/v1/tools/image-magic",
        json={"enabled": True, "command": "magick"},
    )
    response.raise_for_status()
    return response.json()


def create_log_table(context: SmokeContext) -> dict[str, Any]:
    response = context.client.post(
        "/api/v1/log-tables",
        json={
            "name": "smoke_log_tbl",
            "description": "Smoke log table.",
            "columns": [{"column_name": "entry", "data_type": "text", "nullable": True}],
        },
    )
    response.raise_for_status()
    return response.json()
