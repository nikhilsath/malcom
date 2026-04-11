"""Tool runtime response builders, sync helpers, and worker RPC utilities.

This module owns the canonical implementations for all tool runtime concerns:
worker identity helpers, RPC calls, runtime response builders, and tool sync.
"""

from __future__ import annotations

import hmac
import json
import os
import smtplib
import socket
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, status

from backend.database import connect, fetch_all, initialize
from backend.runtime import runtime_event_bus
from backend.schemas import (
    AutomationTriggerConfig,
    CoquiTtsToolConfigResponse,
    CoquiTtsToolResponse,
    ImageMagicToolConfigResponse,
    ImageMagicToolResponse,
    LocalLlmEndpointsResponse,
    LocalLlmPresetResponse,
    LocalLlmToolConfigResponse,
    LocalLlmToolResponse,
    RuntimeMachineResponse,
    SmtpInboundIdentityResponse,
    SmtpRelaySendRequest,
    SmtpToolConfigResponse,
    SmtpToolResponse,
    SmtpToolRuntimeResponse,
    ToolDirectoryEntryResponse,
)
from backend.smtp_runtime import SmtpMachineAssignment, SmtpRuntimeManager
from backend.tool_registry import load_tool_directory, set_tool_enabled
from backend.services.runtime_workers import (
    get_local_worker_address,
    get_local_worker_id,
    get_local_worker_name,
    get_runtime_hostname,
    slugify_identifier,
)
from .coqui_tts_runtime import discover_coqui_tts_runtime
from .tool_configs import (
    get_coqui_tts_tool_config,
    get_default_tool_retries,
    get_image_magic_tool_config,
    get_local_llm_endpoint_presets,
    get_local_llm_tool_config,
    get_smtp_tool_config,
    normalize_coqui_tts_tool_config,
    normalize_image_magic_tool_config,
    normalize_local_llm_tool_config,
    normalize_smtp_tool_config,
)

# Re-export identity helpers so callers can import them from tool_runtime
__all__ = [name for name in globals() if not name.startswith("__")]

# ---------------------------------------------------------------------------
# Cluster secret / RPC auth
# ---------------------------------------------------------------------------


def get_cluster_shared_secret() -> str:
    configured = os.environ.get("MALCOM_CLUSTER_SECRET", "").strip()
    return configured or "malcom-lan-shared-secret"


def build_worker_rpc_headers() -> dict[str, str]:
    return {"X-Malcom-Cluster-Secret": get_cluster_shared_secret()}


def assert_worker_rpc_authorized(request: Request) -> None:
    provided_secret = str(request.headers.get("x-malcom-cluster-secret") or "").strip()
    if not provided_secret or not hmac.compare_digest(provided_secret, get_cluster_shared_secret()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cluster secret.")


# ---------------------------------------------------------------------------
# Worker RPC helpers
# ---------------------------------------------------------------------------


def _resolve_worker_base_url(address: str) -> str:
    value = str(address or "").strip()
    if not value:
        raise RuntimeError("Target worker address is missing.")
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/")
    if ":" in value:
        return f"http://{value}".rstrip("/")
    return f"http://{value}:8000"


def call_worker_rpc(
    worker: Any,
    *,
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    base_url = _resolve_worker_base_url(worker.address)
    response = httpx.request(
        method,
        f"{base_url}{path}",
        json=json_body,
        headers=build_worker_rpc_headers(),
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def get_runtime_worker_or_error(worker_id: str) -> Any:
    worker = next((item for item in runtime_event_bus.list_workers() if item.worker_id == worker_id), None)
    if worker is None:
        raise RuntimeError(f"Target worker '{worker_id}' is not connected.")
    return worker


# ---------------------------------------------------------------------------
# Machine assignment helpers
# ---------------------------------------------------------------------------


def list_runtime_machine_assignments() -> list[SmtpMachineAssignment]:
    local_worker_id = get_local_worker_id()
    local_machine = SmtpMachineAssignment(
        worker_id=local_worker_id,
        name=get_local_worker_name(),
        hostname=get_runtime_hostname(),
        address=get_local_worker_address(),
        status="healthy",
        is_local=True,
        capabilities=("runtime-trigger-execution", "smtp-server", "image-magic-execution"),
    )
    machines: dict[str, SmtpMachineAssignment] = {local_worker_id: local_machine}

    for worker in runtime_event_bus.list_workers():
        capabilities = tuple(dict.fromkeys(worker.capabilities))
        if worker.worker_id == local_worker_id:
            machines[worker.worker_id] = SmtpMachineAssignment(
                worker_id=worker.worker_id,
                name=worker.name,
                hostname=worker.hostname,
                address=worker.address,
                status=worker.status,
                is_local=True,
                capabilities=tuple(dict.fromkeys((*capabilities, "smtp-server", "image-magic-execution"))),
            )
            continue

        machines[worker.worker_id] = SmtpMachineAssignment(
            worker_id=worker.worker_id,
            name=worker.name,
            hostname=worker.hostname,
            address=worker.address,
            status=worker.status,
            is_local=False,
            capabilities=capabilities,
        )

    return sorted(machines.values(), key=lambda item: (not item.is_local, item.name.lower()))


def machine_assignment_to_response(machine: SmtpMachineAssignment) -> RuntimeMachineResponse:
    return RuntimeMachineResponse(
        id=machine.worker_id,
        name=machine.name,
        hostname=machine.hostname,
        address=machine.address,
        status=machine.status,
        is_local=machine.is_local,
        capabilities=list(machine.capabilities),
    )


def get_selected_smtp_machine(config: dict[str, Any], machines: list[SmtpMachineAssignment]) -> SmtpMachineAssignment | None:
    target_worker_id = config.get("target_worker_id") or get_local_worker_id()
    return next((machine for machine in machines if machine.worker_id == target_worker_id), None)


# ---------------------------------------------------------------------------
# SMTP relay helpers
# ---------------------------------------------------------------------------


def normalize_smtp_recipient_list(recipients: list[str]) -> list[str]:
    normalized: list[str] = []
    for recipient in recipients:
        value = str(recipient or "").strip().lower()
        if value:
            normalized.append(value)
    return normalized


def build_smtp_inbound_identity(config: dict[str, Any], runtime: dict[str, Any]) -> SmtpInboundIdentityResponse:
    configured_recipient_email = config.get("recipient_email")
    listening_host = runtime.get("listening_host")
    listening_port = runtime.get("listening_port")
    accepts_any_recipient = configured_recipient_email is None
    display_address = configured_recipient_email or "Catch-all recipient"
    endpoint = f"{listening_host}:{listening_port}" if listening_host and listening_port is not None else "listener offline"
    connection_hint = (
        f"Send SMTP mail to {display_address} via {endpoint}."
        if configured_recipient_email
        else f"Send SMTP mail to any recipient via {endpoint}."
    )
    return SmtpInboundIdentityResponse(
        display_address=display_address,
        configured_recipient_email=configured_recipient_email,
        accepts_any_recipient=accepts_any_recipient,
        listening_host=listening_host,
        listening_port=listening_port,
        connection_hint=connection_hint,
    )


def build_smtp_email_message(*, mail_from: str, recipients: list[str], subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body or "")
    return message


def get_local_smtp_runtime_or_400(app: FastAPI) -> dict[str, Any]:
    runtime = app.state.smtp_manager.snapshot()
    if runtime.get("status") != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SMTP listener is not running.")
    if runtime.get("listening_host") is None or runtime.get("listening_port") is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SMTP listener endpoint is unavailable.")
    return runtime


def validate_smtp_send_inputs(*, mail_from: str, recipients: list[str]) -> list[str]:
    normalized_sender = str(mail_from or "").strip().lower()
    normalized_recipients = normalize_smtp_recipient_list(recipients)
    if not normalized_sender or "@" not in normalized_sender:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A valid sender email is required.")
    if not normalized_recipients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="At least one recipient email is required.")
    if any("@" not in recipient for recipient in normalized_recipients):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Recipient email addresses must be valid.")
    return normalized_recipients


def send_smtp_relay_message(payload: SmtpRelaySendRequest) -> None:
    recipients = validate_smtp_send_inputs(mail_from=payload.mail_from, recipients=payload.recipients)
    message = build_smtp_email_message(
        mail_from=payload.mail_from.strip(),
        recipients=recipients,
        subject=payload.subject.strip(),
        body=payload.body,
    )
    timeout_seconds = 10

    if payload.auth_mode == "password":
        if not payload.username or not payload.password:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Username and password are required for SMTP authentication.")

    try:
        if payload.security == "tls":
            with smtplib.SMTP_SSL(payload.host, payload.port, timeout=timeout_seconds) as client:
                if payload.auth_mode == "password":
                    client.login(payload.username or "", payload.password or "")
                client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
            return

        with smtplib.SMTP(payload.host, payload.port, timeout=timeout_seconds) as client:
            if payload.security == "starttls":
                client.starttls(context=ssl.create_default_context())
            if payload.auth_mode == "password":
                client.login(payload.username or "", payload.password or "")
            client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
    except smtplib.SMTPAuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP authentication failed: {error.smtp_error.decode(errors='ignore') if isinstance(error.smtp_error, bytes) else error.smtp_error or 'authentication failed'}") from error
    except (ssl.SSLError, smtplib.SMTPNotSupportedError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP TLS negotiation failed: {error}") from error
    except (socket.gaierror, TimeoutError, OSError, smtplib.SMTPConnectError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP connection failed: {error}") from error
    except smtplib.SMTPRecipientsRefused as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP recipients refused: {', '.join(error.recipients.keys())}") from error
    except smtplib.SMTPException as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP send failed: {error}") from error


# ---------------------------------------------------------------------------
# SMTP tool sync and response builder
# ---------------------------------------------------------------------------


def fetch_remote_smtp_tool_state(connection: Any, worker_id: str) -> dict[str, Any]:
    worker = get_runtime_worker_or_error(worker_id)
    response = call_worker_rpc(
        worker,
        method="GET",
        path="/api/v1/internal/workers/tools/smtp/status",
        timeout=2.0,
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Remote SMTP status response was invalid.")
    return payload


def sync_smtp_tool_runtime(app: FastAPI, connection: Any) -> None:
    smtp_manager: SmtpRuntimeManager = app.state.smtp_manager
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    machine = get_selected_smtp_machine(config, machines)
    if machine is None:
        smtp_manager.sync(
            enabled=False,
            bind_host=config["bind_host"],
            port=config["port"],
            recipient_email=config.get("recipient_email"),
            machine=None,
        )
        return

    if not machine.is_local:
        smtp_manager.stop()
        try:
            worker = get_runtime_worker_or_error(machine.worker_id)
            call_worker_rpc(
                worker,
                method="POST",
                path="/api/v1/internal/workers/tools/smtp/sync",
                json_body={
                    "enabled": config["enabled"],
                    "bind_host": config["bind_host"],
                    "port": config["port"],
                    "recipient_email": config.get("recipient_email"),
                },
                timeout=2.0,
            )
        except Exception:
            return
        return

    smtp_manager.sync(
        enabled=config["enabled"],
        bind_host=config["bind_host"],
        port=config["port"],
        recipient_email=config.get("recipient_email"),
        machine=machine,
    )


def build_smtp_tool_response(app: FastAPI, connection: Any) -> SmtpToolResponse:
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    runtime = app.state.smtp_manager.snapshot()
    inbound_identity = build_smtp_inbound_identity(config, runtime)

    selected_machine = get_selected_smtp_machine(config, machines)
    if selected_machine is not None and not selected_machine.is_local:
        try:
            remote_state = fetch_remote_smtp_tool_state(connection, selected_machine.worker_id)
            runtime = remote_state.get("runtime") or runtime
            inbound_identity_payload = remote_state.get("inbound_identity") or {}
            inbound_identity = SmtpInboundIdentityResponse(**{
                "display_address": inbound_identity_payload.get("display_address") or inbound_identity.display_address,
                "configured_recipient_email": inbound_identity_payload.get("configured_recipient_email"),
                "accepts_any_recipient": bool(inbound_identity_payload.get("accepts_any_recipient")),
                "listening_host": inbound_identity_payload.get("listening_host"),
                "listening_port": inbound_identity_payload.get("listening_port"),
                "connection_hint": inbound_identity_payload.get("connection_hint") or inbound_identity.connection_hint,
            })
        except Exception as error:
            runtime = {
                **runtime,
                "status": "assigned",
                "message": f"Remote SMTP worker sync failed: {error}",
                "selected_machine_id": selected_machine.worker_id,
                "selected_machine_name": selected_machine.name,
                "last_error": str(error),
            }

    return SmtpToolResponse(
        tool_id="smtp",
        config=SmtpToolConfigResponse(
            enabled=config["enabled"],
            target_worker_id=config.get("target_worker_id"),
            bind_host=config["bind_host"],
            port=config["port"],
            recipient_email=config.get("recipient_email"),
        ),
        runtime=SmtpToolRuntimeResponse(**runtime),
        inbound_identity=inbound_identity,
        machines=[machine_assignment_to_response(machine) for machine in machines],
    )


# ---------------------------------------------------------------------------
# LLM / Coqui TTS / Image Magic response builders
# ---------------------------------------------------------------------------


def build_local_llm_tool_response(connection: Any) -> LocalLlmToolResponse:
    config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
    presets = [
        LocalLlmPresetResponse(
            id=preset_id,
            label=str(preset["label"]),
            server_base_url=str(preset["server_base_url"]),
            endpoints=LocalLlmEndpointsResponse(**preset["endpoints"]),
        )
        for preset_id, preset in get_local_llm_endpoint_presets().items()
    ]
    return LocalLlmToolResponse(
        tool_id="llm-deepl",
        config=LocalLlmToolConfigResponse(
            enabled=config["enabled"],
            provider=config["provider"],
            server_base_url=config["server_base_url"],
            model_identifier=config["model_identifier"],
            endpoints=LocalLlmEndpointsResponse(**config["endpoints"]),
        ),
        presets=presets,
    )


def build_coqui_tts_tool_response(
    connection: Any,
    *,
    root_dir: Path,
    runtime_command: str | None = None,
    runtime_model_name: str | None = None,
) -> CoquiTtsToolResponse:
    config = normalize_coqui_tts_tool_config(get_coqui_tts_tool_config(connection), root_dir=root_dir)
    runtime = discover_coqui_tts_runtime(
        command=str(runtime_command or config["command"]).strip(),
        selected_model_name=str(runtime_model_name or config["model_name"]).strip(),
        root_dir=root_dir,
    )
    return CoquiTtsToolResponse(
        tool_id="coqui-tts",
        config=CoquiTtsToolConfigResponse(
            enabled=config["enabled"],
            command=config["command"],
            model_name=config["model_name"],
            speaker=config["speaker"],
            language=config["language"],
        ),
        runtime=runtime,
    )


def build_image_magic_tool_response(connection: Any) -> ImageMagicToolResponse:
    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
    machines = list_runtime_machine_assignments()
    return ImageMagicToolResponse(
        tool_id="image-magic",
        config=ImageMagicToolConfigResponse(
            enabled=config["enabled"],
            target_worker_id=config.get("target_worker_id"),
            command=config["command"],
            default_retries=get_default_tool_retries(connection),
        ),
        machines=[machine_assignment_to_response(machine) for machine in machines],
    )


# ---------------------------------------------------------------------------
# SMTP automation trigger handler
# ---------------------------------------------------------------------------


def handle_smtp_message_automation_triggers(app: FastAPI, message: dict[str, Any]) -> None:
    # Lazy import to avoid circular dependency (automation_execution imports from tool_runtime)
    from backend.services.automation_execution import execute_automation_definition  # noqa: PLC0415

    connection = connect(database_url=app.state.database_url)
    try:
        initialize(connection)
        matching_automations = fetch_all(
            connection,
            """
            SELECT id, trigger_config_json
            FROM automations
            WHERE enabled = 1
              AND trigger_type = 'smtp_email'
            ORDER BY created_at ASC
            """,
        )
        message_subject = str(message.get("subject") or "").strip().lower()
        message_recipients = [str(item or "").strip().lower() for item in message.get("recipients", []) if str(item or "").strip()]

        for automation_row in matching_automations:
            trigger_config = AutomationTriggerConfig(**json.loads(automation_row["trigger_config_json"]))
            expected_subject = str(trigger_config.smtp_subject or "").strip().lower()
            expected_recipient = str(trigger_config.smtp_recipient_email or "").strip().lower()

            if expected_subject and message_subject != expected_subject:
                continue
            if expected_recipient and expected_recipient not in message_recipients:
                continue

            execute_automation_definition(
                connection,
                app.state.logger,
                automation_id=automation_row["id"],
                trigger_type="smtp_email",
                payload={
                    "smtp": message,
                    "subject": message.get("subject"),
                    "body": message.get("body"),
                    "mail_from": message.get("mail_from"),
                    "recipients": message.get("recipients"),
                    "received_at": message.get("received_at"),
                },
                root_dir=Path(app.state.root_dir),
                database_url=app.state.database_url,
            )
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Tool directory helpers
# ---------------------------------------------------------------------------


def sync_managed_tool_enabled_state(request: Request, tool_id: str, enabled: bool) -> ToolDirectoryEntryResponse:
    connection = request.app.state.connection
    root_dir = Path(request.app.state.root_dir)
    entry = set_tool_enabled(
        root_dir,
        connection,
        tool_id,
        enabled=enabled,
    )
    return ToolDirectoryEntryResponse(**entry)


def build_tool_directory_response(request: Request) -> list[ToolDirectoryEntryResponse]:
    """Build tool manifest for automation builder from the tools table.

    Data lineage: See README.md > Data Lineage Reference > Tools Manifest
    Source: tools table in database. Default tools synced at startup via sync_tools_to_database().
    """
    connection = request.app.state.connection
    root_dir = Path(request.app.state.root_dir)
    entries = load_tool_directory(root_dir, connection)
    return [ToolDirectoryEntryResponse(**entry) for entry in entries]


__all__ = [name for name in globals() if not name.startswith("_")]
