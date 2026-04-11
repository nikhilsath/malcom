from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.schemas import *
from backend.services.coqui_tts_runtime import discover_coqui_tts_runtime, validate_coqui_tts_selection
from backend.services.support import *
from backend.services.tool_command_utils import verify_local_command_ready
from backend.services.tool_configs import (
    get_image_magic_tool_config as get_image_magic_tool_config_core,
    normalize_image_magic_tool_config as normalize_image_magic_tool_config_core,
    save_image_magic_tool_config as save_image_magic_tool_config_core,
)
from backend.services.tool_runtime import build_image_magic_tool_response as build_image_magic_tool_response_core

router = APIRouter()


@router.get("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def get_smtp_tool(request: Request) -> SmtpToolResponse:
    return build_smtp_tool_response(request.app, get_connection(request))


@router.get("/api/v1/tools/llm-deepl/local-llm", response_model=LocalLlmToolResponse)
def get_local_llm_tool(request: Request) -> LocalLlmToolResponse:
    return build_local_llm_tool_response(get_connection(request))


@router.get("/api/v1/tools/coqui-tts", response_model=CoquiTtsToolResponse)
def get_coqui_tts_tool(
    request: Request,
    command: str | None = None,
    model_name: str | None = None,
) -> CoquiTtsToolResponse:
    return build_coqui_tts_tool_response(
        get_connection(request),
        root_dir=get_root_dir(request),
        runtime_command=command,
        runtime_model_name=model_name,
    )


@router.get("/api/v1/tools/image-magic", response_model=ImageMagicToolResponse)
def get_image_magic_tool(request: Request) -> ImageMagicToolResponse:
    return build_image_magic_tool_response_core(get_connection(request))


@router.post("/api/v1/tools/llm-deepl/chat", response_model=LocalLlmChatResponse)
def create_local_llm_chat(payload: LocalLlmChatRequest, request: Request) -> LocalLlmChatResponse:
    messages = [message.model_dump() for message in payload.messages]
    return execute_local_llm_chat_request(
        get_connection(request),
        messages=messages,
        model_identifier_override=payload.model_identifier,
        previous_response_id=payload.previous_response_id,
    )


@router.post("/api/v1/tools/llm-deepl/chat/stream")
def stream_local_llm_chat(payload: LocalLlmChatRequest, request: Request) -> StreamingResponse:
    messages = [message.model_dump() for message in payload.messages]
    return StreamingResponse(
        build_local_llm_stream(
            get_connection(request),
            messages=messages,
            model_identifier_override=payload.model_identifier,
            previous_response_id=payload.previous_response_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/v1/tools", response_model=list[ToolDirectoryEntryResponse])
def list_tools(request: Request) -> list[ToolDirectoryEntryResponse]:
    # Data lineage: See README.md > Data Lineage Reference > Tools Manifest
    # Queries tools table. Default tools synced from code at startup; user tools persisted in database.
    return build_tool_directory_response(request)


@router.patch("/api/v1/tools/smtp", response_model=SmtpToolResponse)
def patch_smtp_tool(payload: SmtpToolUpdate, request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No SMTP tool changes provided.")

    next_config = get_smtp_tool_config(connection)
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "target_worker_id" in changes:
        next_config["target_worker_id"] = changes["target_worker_id"] or None
    if "bind_host" in changes:
        next_config["bind_host"] = str(changes["bind_host"]).strip()
    if "port" in changes:
        next_config["port"] = int(changes["port"])
    if "recipient_email" in changes:
        next_config["recipient_email"] = (str(changes["recipient_email"]).strip().lower() or None) if changes["recipient_email"] is not None else None

    save_smtp_tool_config(connection, next_config)
    sync_managed_tool_enabled_state(request, "smtp", next_config["enabled"])
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@router.patch("/api/v1/tools/llm-deepl/local-llm", response_model=LocalLlmToolResponse)
def patch_local_llm_tool(payload: LocalLlmToolUpdate, request: Request) -> LocalLlmToolResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No local LLM tool changes provided.")

    next_config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))

    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "provider" in changes:
        provider = str(changes["provider"]).strip()
        if provider not in LOCAL_LLM_ENDPOINT_PRESETS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported local LLM provider preset.")
        next_config["provider"] = provider
    if "server_base_url" in changes:
        next_config["server_base_url"] = str(changes["server_base_url"] or "").strip()
    if "model_identifier" in changes:
        next_config["model_identifier"] = str(changes["model_identifier"] or "").strip()
    if "endpoints" in changes and isinstance(changes["endpoints"], dict):
        for key, value in changes["endpoints"].items():
            if value is not None:
                next_config["endpoints"][key] = str(value).strip()

    normalized_config = normalize_local_llm_tool_config(next_config)
    save_local_llm_tool_config(connection, normalized_config)
    sync_managed_tool_enabled_state(request, "llm-deepl", normalized_config["enabled"])
    return build_local_llm_tool_response(connection)


@router.patch("/api/v1/tools/coqui-tts", response_model=CoquiTtsToolResponse)
def patch_coqui_tts_tool(payload: CoquiTtsToolUpdate, request: Request) -> CoquiTtsToolResponse:
    connection = get_connection(request)
    root_dir = get_root_dir(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Coqui TTS tool changes provided.")

    next_config = normalize_coqui_tts_tool_config(
        get_coqui_tts_tool_config(connection),
        root_dir=root_dir,
    )
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "command" in changes:
        next_config["command"] = str(changes["command"] or "").strip()
    if "model_name" in changes:
        next_config["model_name"] = str(changes["model_name"] or "").strip()
    if "speaker" in changes:
        next_config["speaker"] = str(changes["speaker"] or "").strip()
    if "language" in changes:
        next_config["language"] = str(changes["language"] or "").strip()

    normalized_config = normalize_coqui_tts_tool_config(next_config, root_dir=root_dir)
    if normalized_config["enabled"]:
        runtime = discover_coqui_tts_runtime(
            command=normalized_config["command"],
            selected_model_name=normalized_config["model_name"],
            root_dir=root_dir,
        )
        try:
            validate_coqui_tts_selection(
                runtime=runtime,
                model_name=normalized_config["model_name"],
                speaker=normalized_config["speaker"],
                language=normalized_config["language"],
            )
        except RuntimeError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    save_coqui_tts_tool_config(connection, normalized_config)
    sync_managed_tool_enabled_state(request, "coqui-tts", normalized_config["enabled"])
    return build_coqui_tts_tool_response(connection, root_dir=root_dir)


@router.patch("/api/v1/tools/image-magic", response_model=ImageMagicToolResponse | ToolMetadataResponse)
def patch_image_magic_tool(payload: ImageMagicToolUpdate, request: Request) -> ImageMagicToolResponse | ToolMetadataResponse:
    connection = get_connection(request)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No Image Magic tool changes provided.")

    metadata_only = (
        ("name" in changes or "description" in changes)
        and "enabled" not in changes
        and "target_worker_id" not in changes
        and "command" not in changes
    )

    if metadata_only:
        try:
            updated = update_tool_metadata(
                get_root_dir(request),
                connection,
                "image-magic",
                name=changes.get("name"),
                description=changes.get("description"),
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.") from error
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

        return ToolMetadataResponse(**updated)

    current_config = normalize_image_magic_tool_config_core(get_image_magic_tool_config_core(connection))
    next_config = dict(current_config)
    if "enabled" in changes:
        next_config["enabled"] = bool(changes["enabled"])
    if "target_worker_id" in changes:
        next_config["target_worker_id"] = changes["target_worker_id"] or None
    if "command" in changes:
        next_config["command"] = str(changes["command"] or "").strip()

    normalized_config = normalize_image_magic_tool_config_core(next_config)

    enabling_on_local_host = (
        normalized_config["enabled"]
        and (not current_config["enabled"] or "command" in changes)
        and (
            not normalized_config.get("target_worker_id")
            or normalized_config.get("target_worker_id") == get_local_worker_id()
        )
    )
    if enabling_on_local_host:
        try:
            verify_local_command_ready(
                normalized_config["command"],
                working_dir=get_root_dir(request),
                tool_name="Image Magic",
            )
        except RuntimeError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    save_image_magic_tool_config_core(connection, normalized_config)
    sync_managed_tool_enabled_state(request, "image-magic", normalized_config["enabled"])
    return build_image_magic_tool_response_core(connection)


@router.post("/api/v1/tools/image-magic/execute", response_model=ImageMagicExecuteResponse)
def execute_image_magic(payload: ImageMagicExecuteRequest, request: Request) -> ImageMagicExecuteResponse:
    connection = get_connection(request)
    config = normalize_image_magic_tool_config_core(get_image_magic_tool_config_core(connection))
    if not config["enabled"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Image Magic tool is disabled.")

    target_worker_id = config.get("target_worker_id")
    if target_worker_id and target_worker_id != get_local_worker_id():
        worker = get_runtime_worker_or_error(target_worker_id)
        response = call_worker_rpc(
            worker,
            method="POST",
            path="/api/v1/internal/workers/tools/image-magic/execute",
            json_body=payload.model_dump(),
            timeout=120.0,
        )
        return ImageMagicExecuteResponse(**response.json())

    try:
        result = execute_image_magic_conversion_request(
            payload,
            root_dir=get_root_dir(request),
            command=config["command"],
        )
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ImageMagicExecuteResponse(
        ok=True,
        output_file_path=result["output_file_path"],
        worker_id=get_local_worker_id(),
        worker_name=get_local_worker_name(),
    )


@router.post("/api/v1/tools/smtp/start", response_model=SmtpToolResponse)
def start_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = True
    save_smtp_tool_config(connection, config)
    sync_managed_tool_enabled_state(request, "smtp", True)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@router.post("/api/v1/tools/smtp/stop", response_model=SmtpToolResponse)
def stop_smtp_tool(request: Request) -> SmtpToolResponse:
    connection = get_connection(request)
    config = get_smtp_tool_config(connection)
    config["enabled"] = False
    save_smtp_tool_config(connection, config)
    sync_managed_tool_enabled_state(request, "smtp", False)
    sync_smtp_tool_runtime(request.app, connection)
    return build_smtp_tool_response(request.app, connection)


@router.post("/api/v1/tools/smtp/send-test", response_model=SmtpSendTestResponse)
def send_smtp_test_message(payload: SmtpSendTestRequest, request: Request) -> SmtpSendTestResponse:
    connection = get_connection(request)
    config = normalize_smtp_tool_config(get_smtp_tool_config(connection))
    machines = list_runtime_machine_assignments()
    selected_machine = get_selected_smtp_machine(config, machines)
    if selected_machine is not None and not selected_machine.is_local:
        worker = get_runtime_worker_or_error(selected_machine.worker_id)
        response = call_worker_rpc(
            worker,
            method="POST",
            path="/api/v1/internal/workers/tools/smtp/send-test",
            json_body=payload.model_dump(),
            timeout=20.0,
        )
        rpc_payload = response.json()
        return SmtpSendTestResponse(**rpc_payload)

    runtime = get_local_smtp_runtime_or_400(request.app)
    recipients = validate_smtp_send_inputs(mail_from=payload.mail_from, recipients=payload.recipients)

    if config.get("recipient_email") and any(recipient != config["recipient_email"] for recipient in recipients):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Test recipients must match the configured receive email.")

    message = build_smtp_email_message(
        mail_from=payload.mail_from.strip(),
        recipients=recipients,
        subject=payload.subject.strip(),
        body=payload.body,
    )

    try:
        with smtplib.SMTP(str(runtime["listening_host"]), int(runtime["listening_port"]), timeout=10) as client:
            client.send_message(message, from_addr=payload.mail_from.strip(), to_addrs=recipients)
    except smtplib.SMTPException as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP test send failed: {error}") from error
    except (OSError, TimeoutError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SMTP test connection failed: {error}") from error

    snapshot = request.app.state.smtp_manager.snapshot()
    latest_message = (snapshot.get("recent_messages") or [None])[0]
    return SmtpSendTestResponse(
        ok=True,
        message="Test email sent through the local SMTP listener.",
        message_id=(latest_message or {}).get("id") if isinstance(latest_message, dict) else None,
    )


@router.post("/api/v1/tools/smtp/send-relay", response_model=SmtpRelaySendResponse)
def send_smtp_relay(payload: SmtpRelaySendRequest, request: Request) -> SmtpRelaySendResponse:
    _ = request
    try:
        send_smtp_relay_message(payload)
    except HTTPException as error:
        detail = str(error.detail)
        if "authentication failed" in detail.lower():
            status_value = "auth_failed"
        elif "tls negotiation failed" in detail.lower():
            status_value = "tls_failed"
        elif "connection failed" in detail.lower():
            status_value = "connection_failed"
        elif error.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT:
            status_value = "invalid_input"
        else:
            status_value = "send_failed"
        return SmtpRelaySendResponse(ok=False, status=status_value, message=detail)

    return SmtpRelaySendResponse(ok=True, status="sent", message="Email sent through the external SMTP relay.")


@router.patch("/api/v1/tools/{tool_id}/directory", response_model=ToolDirectoryEntryResponse)
def patch_tool_directory(tool_id: str, payload: ToolDirectoryUpdate, request: Request) -> ToolDirectoryEntryResponse:
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tool changes provided.")

    connection = get_connection(request)

    try:
        if "name" in changes or "description" in changes:
            update_tool_metadata(
                get_root_dir(request),
                connection,
                tool_id,
                name=changes.get("name"),
                description=changes.get("description"),
            )

        if "enabled" in changes:
            desired_enabled = bool(changes["enabled"])
            if tool_id == "smtp":
                config = get_smtp_tool_config(connection)
                save_smtp_tool_config(connection, config)
                set_tool_enabled(
                    get_root_dir(request),
                    connection,
                    tool_id,
                    enabled=desired_enabled,
                )
                sync_smtp_tool_runtime(request.app, connection)
            else:
                if tool_id == "llm-deepl":
                    config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
                    save_local_llm_tool_config(connection, config)
                if tool_id == "coqui-tts":
                    config = normalize_coqui_tts_tool_config(
                        get_coqui_tts_tool_config(connection),
                        root_dir=get_root_dir(request),
                    )
                    if desired_enabled:
                        runtime = discover_coqui_tts_runtime(
                            command=config["command"],
                            selected_model_name=config["model_name"],
                            root_dir=get_root_dir(request),
                        )
                        try:
                            validate_coqui_tts_selection(
                                runtime=runtime,
                                model_name=config["model_name"],
                                speaker=config["speaker"],
                                language=config["language"],
                            )
                        except RuntimeError as error:
                            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
                    save_coqui_tts_tool_config(connection, config)
                if tool_id == "image-magic":
                    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
                    if desired_enabled and (
                        not config.get("target_worker_id")
                        or config.get("target_worker_id") == get_local_worker_id()
                    ):
                        try:
                            verify_local_command_ready(
                                config["command"],
                                working_dir=get_root_dir(request),
                                tool_name="Image Magic",
                            )
                        except RuntimeError as error:
                            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
                    save_image_magic_tool_config(connection, config)

                set_tool_enabled(
                    get_root_dir(request),
                    connection,
                    tool_id,
                    enabled=desired_enabled,
                )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    directory = build_tool_directory_response(request)
    entry = next((item for item in directory if item.id == tool_id), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    return entry


@router.patch("/api/v1/tools/{tool_id}", response_model=ToolMetadataResponse)
def patch_tool_metadata(tool_id: str, payload: ToolMetadataUpdate, request: Request) -> ToolMetadataResponse:
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tool changes provided.")

    try:
        updated = update_tool_metadata(
            get_root_dir(request),
            get_connection(request),
            tool_id,
            name=changes.get("name"),
            description=changes.get("description"),
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    return ToolMetadataResponse(**updated)
