"""Automation tool step execution helpers and local LLM request utilities.

Primary identifiers: ``execute_*_tool_step`` functions, local LLM chat/stream helpers,
SMTP relay helpers, and generated file sanitization utilities.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import smtplib
import socket
import ssl
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, status

from backend.runtime import RuntimeExecutionResult
from backend.schemas import (
    AutomationStepDefinition,
    ImageMagicExecuteRequest,
    LocalLlmChatResponse,
    SmtpRelaySendRequest,
)
from .tool_configs import (
    get_coqui_tts_tool_config,
    get_default_tool_retries,
    get_image_magic_tool_config,
    get_local_llm_tool_config,
    normalize_coqui_tts_tool_config,
    normalize_image_magic_tool_config,
    normalize_local_llm_tool_config,
)
from .tool_runtime import (
    build_smtp_email_message,
    call_worker_rpc,
    get_local_smtp_runtime_or_400,
    get_local_worker_id,
    get_local_worker_name,
    get_runtime_worker_or_error,
    normalize_smtp_recipient_list,
    send_smtp_relay_message,
    validate_smtp_send_inputs,
)

DatabaseConnection = Any


def render_template_string(template: str | None, context: dict[str, Any]) -> str:
    raw = template or ""

    def replace(match: re.Match[str]) -> str:
        current: Any = context
        for segment in match.group(1).strip().split("."):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return ""
        return str(current if current is not None else "")

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace, raw)


def sanitize_generated_audio_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return filename or f"coqui-output-{uuid4().hex[:8]}"


def _get_tool_input(step: AutomationStepDefinition, key: str, context: dict[str, Any], *, legacy_attr: str | None = None) -> str:
    inputs = step.config.tool_inputs or {}
    raw = inputs.get(key)
    if raw is None and legacy_attr:
        raw = getattr(step.config, legacy_attr, None)
    return render_template_string(raw, context).strip() if raw else ""


def verify_local_command_ready(command: str, *, working_dir: Path | None = None, tool_name: str = "Command") -> list[str]:
    command_parts = shlex.split(str(command or "").strip())
    if not command_parts:
        raise RuntimeError(f"{tool_name} command is invalid.")

    executable = command_parts[0]
    executable_path = Path(executable).expanduser()
    has_explicit_path = executable_path.is_absolute() or any(separator in executable for separator in ("/", "\\"))

    if has_explicit_path:
        if not executable_path.is_absolute() and working_dir is not None:
            executable_path = (working_dir / executable_path).resolve()
        if not executable_path.exists() or not os.access(executable_path, os.X_OK):
            raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")
        return command_parts

    if shutil.which(executable) is None:
        raise RuntimeError(f"{tool_name} command is not executable on this host: {command}")

    return command_parts


def execute_coqui_tts_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    *,
    root_dir: Path,
) -> RuntimeExecutionResult:
    config = normalize_coqui_tts_tool_config(get_coqui_tts_tool_config(connection), root_dir=root_dir)
    if not config["enabled"]:
        raise RuntimeError("Tool 'coqui-tts' is disabled.")
    if not config["command"]:
        raise RuntimeError("Coqui TTS command is not configured.")
    if not config["model_name"]:
        raise RuntimeError("Coqui TTS model name is not configured.")

    rendered_text = _get_tool_input(step, "text", context, legacy_attr="tool_text")
    if not rendered_text:
        raise RuntimeError("Coqui TTS steps require a 'text' input.")

    output_directory = Path(config["output_directory"])
    output_directory.mkdir(parents=True, exist_ok=True)
    requested_filename = _get_tool_input(step, "output_filename", context, legacy_attr="tool_output_filename")
    safe_filename = sanitize_generated_audio_filename(requested_filename) if requested_filename else f"coqui-output-{uuid4().hex[:8]}"
    if "." not in safe_filename:
        safe_filename = f"{safe_filename}.wav"
    output_path = output_directory / safe_filename

    command_parts = shlex.split(config["command"])
    if not command_parts:
        raise RuntimeError("Coqui TTS command is invalid.")
    command = [
        *command_parts,
        "--text",
        rendered_text,
        "--model_name",
        config["model_name"],
        "--out_path",
        str(output_path),
    ]
    speaker = _get_tool_input(step, "speaker", context, legacy_attr="tool_speaker") or config["speaker"]
    language = _get_tool_input(step, "language", context, legacy_attr="tool_language") or config["language"]
    if speaker:
        command.extend(["--speaker_idx", speaker])
    if language:
        command.extend(["--language_idx", language])

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root_dir),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Coqui TTS command was not found: {config['command']}") from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "Unknown Coqui TTS failure."
        raise RuntimeError(f"Coqui TTS generation failed: {detail}") from error

    outputs = {
        "audio_file_path": str(output_path),
    }
    detail = {
        "tool_id": "coqui-tts",
        "model_name": config["model_name"],
        "speaker": speaker or None,
        "language": language or None,
        "stdout": (completed.stdout or "").strip() or None,
        **outputs,
    }
    return RuntimeExecutionResult(
        status="completed",
        response_summary=f"Generated speech audio at {output_path.name}.",
        detail=detail,
        output=outputs,
    )


def execute_llm_deepl_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> RuntimeExecutionResult:
    messages: list[dict[str, str]] = []
    system_prompt = _get_tool_input(step, "system_prompt", context)
    user_prompt = _get_tool_input(step, "user_prompt", context)
    model_identifier = _get_tool_input(step, "model_identifier", context) or None

    if not user_prompt:
        raise RuntimeError("llm-deepl tool steps require a 'user_prompt' input.")

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    llm_response = execute_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier,
    )
    outputs = {
        "response_text": llm_response.response_text,
        "model_used": llm_response.model_identifier or "",
    }
    detail = llm_response.model_dump()
    detail["tool_id"] = "llm-deepl"
    detail.update(outputs)
    return RuntimeExecutionResult(
        status="completed",
        response_summary=llm_response.response_text[:500],
        detail=detail,
        output=outputs,
    )


def execute_smtp_tool_step(
    step: AutomationStepDefinition,
    context: dict[str, Any],
) -> RuntimeExecutionResult:
    relay_host = _get_tool_input(step, "relay_host", context)
    relay_port_raw = _get_tool_input(step, "relay_port", context)
    relay_security = _get_tool_input(step, "relay_security", context) or "none"
    relay_username = _get_tool_input(step, "relay_username", context) or None
    relay_password = _get_tool_input(step, "relay_password", context) or None
    from_address = _get_tool_input(step, "from_address", context)
    to_address = _get_tool_input(step, "to", context)
    subject = _get_tool_input(step, "subject", context)
    body = _get_tool_input(step, "body", context)

    if not relay_host:
        raise RuntimeError("SMTP tool steps require a 'relay_host' input.")
    if not relay_port_raw:
        raise RuntimeError("SMTP tool steps require a 'relay_port' input.")
    if not from_address:
        raise RuntimeError("SMTP tool steps require a 'from_address' input.")
    if not to_address:
        raise RuntimeError("SMTP tool steps require a 'to' input.")
    if not subject:
        raise RuntimeError("SMTP tool steps require a 'subject' input.")
    if not body:
        raise RuntimeError("SMTP tool steps require a 'body' input.")

    try:
        relay_port = int(relay_port_raw)
    except (ValueError, TypeError) as error:
        raise RuntimeError(f"SMTP relay_port must be a valid integer, got: {relay_port_raw!r}") from error

    if relay_security not in ("none", "starttls", "tls"):
        relay_security = "none"

    send_smtp_relay_message(
        SmtpRelaySendRequest(
            host=relay_host,
            port=relay_port,
            security=relay_security,
            auth_mode="password" if relay_username else "none",
            username=relay_username,
            password=relay_password,
            mail_from=from_address,
            recipients=[r.strip() for r in to_address.split(",") if r.strip()],
            subject=subject,
            body=body,
        )
    )
    outputs = {
        "status": "sent",
        "message": f"Email sent to {to_address} via {relay_host}:{relay_port}.",
    }
    return RuntimeExecutionResult(
        status="completed",
        response_summary=outputs["message"],
        detail={"tool_id": "smtp", **outputs},
        output=outputs,
    )


def _build_image_magic_output_path(
    *,
    input_file: str,
    output_format: str,
    output_filename: str | None,
    root_dir: Path,
) -> tuple[Path, Path]:
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = root_dir / input_file

    output_directory = input_path.parent
    requested_filename = output_filename.strip() if output_filename else ""
    safe_filename = sanitize_generated_audio_filename(requested_filename) if requested_filename else f"{input_path.stem}-converted"
    if "." not in safe_filename:
        safe_filename = f"{safe_filename}.{output_format}"

    return input_path, output_directory / safe_filename


def execute_image_magic_conversion_request(
    payload: ImageMagicExecuteRequest,
    *,
    root_dir: Path,
    command: str,
) -> dict[str, str]:
    output_format = str(payload.output_format or "").strip().lower()
    valid_formats = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif"}
    if output_format not in valid_formats:
        raise RuntimeError(f"Image Magic output_format must be one of: {', '.join(sorted(valid_formats))}.")

    input_path, output_path = _build_image_magic_output_path(
        input_file=payload.input_file,
        output_format=output_format,
        output_filename=payload.output_filename,
        root_dir=root_dir,
    )
    if not input_path.exists():
        raise RuntimeError(f"Image Magic input file was not found: {input_path}")

    command_parts = verify_local_command_ready(command, working_dir=root_dir, tool_name="Image Magic")
    image_command = [*command_parts, str(input_path)]
    resize_value = str(payload.resize or "").strip()
    if resize_value:
        image_command.extend(["-resize", resize_value])
    image_command.append(str(output_path))

    try:
        completed = subprocess.run(
            image_command,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(root_dir),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"Image Magic command was not found: {command}") from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "Unknown Image Magic failure."
        raise RuntimeError(f"Image conversion failed: {detail}") from error

    return {
        "output_file_path": str(output_path),
        "stdout": (completed.stdout or "").strip() or "",
    }


def _parse_tool_retry_count(raw_value: str, *, default_retries: int) -> int:
    if not raw_value:
        return default_retries
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default_retries
    return max(0, min(10, parsed))


def execute_image_magic_tool_step(
    connection: DatabaseConnection,
    step: AutomationStepDefinition,
    context: dict[str, Any],
    *,
    root_dir: Path,
) -> RuntimeExecutionResult:
    config = normalize_image_magic_tool_config(get_image_magic_tool_config(connection))
    if not config["enabled"]:
        raise RuntimeError("Tool 'image-magic' is disabled.")

    input_file = _get_tool_input(step, "input_file", context)
    output_format = _get_tool_input(step, "output_format", context)
    resize = _get_tool_input(step, "resize", context) or None
    output_filename = _get_tool_input(step, "output_filename", context) or None
    retries_override = _get_tool_input(step, "max_retries", context)

    if not input_file:
        raise RuntimeError("Image Magic steps require an 'input_file' input.")
    if not output_format:
        raise RuntimeError("Image Magic steps require an 'output_format' input.")

    default_retries = get_default_tool_retries(connection)
    max_retries = _parse_tool_retry_count(retries_override, default_retries=default_retries)
    attempts_total = max_retries + 1
    last_error: RuntimeError | None = None

    for attempt in range(1, attempts_total + 1):
        try:
            target_worker_id = config.get("target_worker_id")
            worker_id = get_local_worker_id()
            worker_name = get_local_worker_name()

            if target_worker_id and target_worker_id != worker_id:
                worker = get_runtime_worker_or_error(target_worker_id)
                response = call_worker_rpc(
                    worker,
                    method="POST",
                    path="/api/v1/internal/workers/tools/image-magic/execute",
                    json_body={
                        "input_file": input_file,
                        "output_format": output_format,
                        "output_filename": output_filename,
                        "resize": resize,
                    },
                    timeout=120.0,
                )
                payload = response.json()
                outputs = {
                    "output_file_path": str(payload.get("output_file_path") or ""),
                }
                detail = {
                    "tool_id": "image-magic",
                    "execution_mode": "remote",
                    "target_worker_id": worker.worker_id,
                    "target_worker_name": worker.name,
                    "resize": resize,
                    "attempt": attempt,
                    "attempts_total": attempts_total,
                    **outputs,
                }
                return RuntimeExecutionResult(
                    status="completed",
                    response_summary=f"Converted image on {worker.name}.",
                    detail=detail,
                    output=outputs,
                )

            execution = execute_image_magic_conversion_request(
                ImageMagicExecuteRequest(
                    input_file=input_file,
                    output_format=output_format,
                    output_filename=output_filename,
                    resize=resize,
                ),
                root_dir=root_dir,
                command=config["command"],
            )
            outputs = {
                "output_file_path": execution["output_file_path"],
            }
            detail = {
                "tool_id": "image-magic",
                "execution_mode": "local",
                "worker_id": worker_id,
                "worker_name": worker_name,
                "resize": resize,
                "attempt": attempt,
                "attempts_total": attempts_total,
                "stdout": execution.get("stdout") or None,
                **outputs,
            }
            return RuntimeExecutionResult(
                status="completed",
                response_summary=f"Converted image to {Path(outputs['output_file_path']).name}.",
                detail=detail,
                output=outputs,
            )
        except (RuntimeError, httpx.HTTPError, ValueError) as error:
            last_error = RuntimeError(str(error))
            if attempt >= attempts_total:
                break
            time.sleep(min(1.0, 0.25 * attempt))

    raise RuntimeError(f"Image Magic failed after {attempts_total} attempts: {last_error}")


def build_local_llm_endpoint_url(config: dict[str, Any], endpoint_key: str) -> str:
    base_url = str(config.get("server_base_url") or "").strip().rstrip("/")
    endpoint_path = str((config.get("endpoints") or {}).get(endpoint_key) or "").strip()

    if not base_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM server base URL is not configured.")
    if not endpoint_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Local LLM endpoint '{endpoint_key}' is not configured.")
    if endpoint_path.startswith("http://") or endpoint_path.startswith("https://"):
        return endpoint_path
    return f"{base_url}{endpoint_path if endpoint_path.startswith('/') else f'/{endpoint_path}'}"


def local_llm_uses_native_chat_api(config: dict[str, Any]) -> bool:
    chat_path = str((config.get("endpoints") or {}).get("chat") or "").strip().lower()
    return chat_path.endswith("/api/v1/chat")


def build_local_llm_openai_chat_url(config: dict[str, Any]) -> str:
    base_url = str(config.get("server_base_url") or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM server base URL is not configured.")
    return f"{base_url}/v1/chat/completions"


def should_retry_local_llm_with_openai_chat(config: dict[str, Any], error: httpx.HTTPError) -> bool:
    if not local_llm_uses_native_chat_api(config):
        return False
    if not isinstance(error, httpx.HTTPStatusError):
        return False
    return error.response.status_code == status.HTTP_404_NOT_FOUND


def extract_text_from_content_parts(parts: Any) -> str:
    if isinstance(parts, str):
        return parts
    if not isinstance(parts, list):
        return ""

    output: list[str] = []
    for item in parts:
        if isinstance(item, dict):
            if isinstance(item.get("text"), str):
                output.append(item["text"])
            elif isinstance(item.get("content"), str):
                output.append(item["content"])
    return "".join(output)


def extract_local_llm_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]

    if isinstance(payload.get("choices"), list) and payload["choices"]:
        choice = payload["choices"][0]
        if isinstance(choice, dict):
            message = choice.get("message") or {}
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            delta = choice.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]

    if isinstance(payload.get("output"), list):
        fragments: list[str] = []
        for item in payload["output"]:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            extracted = extract_text_from_content_parts(content)
            if extracted:
                fragments.append(extracted)
        if fragments:
            return "".join(fragments)

    if isinstance(payload.get("message"), dict) and isinstance(payload["message"].get("content"), str):
        return payload["message"]["content"]

    if isinstance(payload.get("content"), str):
        return payload["content"]

    return ""


def extract_local_llm_response_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "response_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def build_local_llm_native_chat_body(
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    previous_response_id: str | None = None,
    stream: bool,
) -> dict[str, Any]:
    latest_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    system_message = next((message["content"] for message in messages if message["role"] == "system"), None)

    if previous_response_id:
        native_input = latest_user_message
    else:
        transcript_lines: list[str] = []
        if system_message:
            transcript_lines.append(f"System instructions:\n{system_message}")
        conversation_messages = [message for message in messages if message["role"] != "system"]
        if conversation_messages:
            transcript_lines.append("Conversation:")
            transcript_lines.extend(
                f"{message['role'].capitalize()}: {message['content']}" for message in conversation_messages
            )
        native_input = "\n\n".join(line for line in transcript_lines if line.strip()) or latest_user_message

    body: dict[str, Any] = {
        "model": model_identifier,
        "input": native_input,
        "stream": stream,
        "store": False,
    }
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
    return body


def build_local_llm_openai_chat_body(
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    stream: bool,
) -> dict[str, Any]:
    return {
        "model": model_identifier,
        "messages": messages,
        "stream": stream,
    }


def prepare_local_llm_chat_request(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
    stream: bool,
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    config = normalize_local_llm_tool_config(get_local_llm_tool_config(connection))
    if not config["enabled"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM tool is disabled.")

    model_identifier = (model_identifier_override or config.get("model_identifier") or "").strip()
    if not model_identifier:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Local LLM model identifier is not configured.")

    chat_url = build_local_llm_endpoint_url(config, "chat")
    if local_llm_uses_native_chat_api(config):
        request_body = build_local_llm_native_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            previous_response_id=previous_response_id,
            stream=stream,
        )
    else:
        request_body = build_local_llm_openai_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            stream=stream,
        )
    return config, model_identifier, chat_url, request_body


def build_local_llm_fallback_chat_request(
    config: dict[str, Any],
    *,
    model_identifier: str,
    messages: list[dict[str, str]],
    stream: bool,
) -> tuple[str, dict[str, Any]]:
    return (
        build_local_llm_openai_chat_url(config),
        build_local_llm_openai_chat_body(
            model_identifier=model_identifier,
            messages=messages,
            stream=stream,
        ),
    )


def execute_local_llm_chat_request(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
) -> LocalLlmChatResponse:
    config, model_identifier, chat_url, request_body = prepare_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier_override,
        previous_response_id=previous_response_id,
        stream=False,
    )
    try:
        response = httpx.post(chat_url, json=request_body, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        if not should_retry_local_llm_with_openai_chat(config, error):
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Local LLM request failed: {error}") from error
        try:
            fallback_chat_url, fallback_body = build_local_llm_fallback_chat_request(
                config,
                model_identifier=model_identifier,
                messages=messages,
                stream=False,
            )
            response = httpx.post(fallback_chat_url, json=fallback_body, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPError as fallback_error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Local LLM request failed: {fallback_error}") from fallback_error

    payload = response.json()
    response_text = extract_local_llm_response_text(payload)
    return LocalLlmChatResponse(
        ok=True,
        model_identifier=model_identifier,
        response_text=response_text,
        response_id=extract_local_llm_response_id(payload),
    )


def encode_sse_event(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


def iter_local_llm_stream_events(response: httpx.Response, *, collected_fragments: list[str]):
    response_id: str | None = None
    event_name = "message"
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8", errors="replace")
        if line == "":
            if not data_lines:
                event_name = "message"
                continue
            data_payload = "\n".join(data_lines)
            if data_payload == "[DONE]":
                break
            try:
                parsed = json.loads(data_payload)
            except json.JSONDecodeError:
                parsed = {"raw": data_payload}

            fragment = ""
            if event_name == "message.delta":
                fragment = extract_text_from_content_parts(parsed.get("delta"))
            elif isinstance(parsed, dict):
                if isinstance(parsed.get("choices"), list) and parsed["choices"]:
                    choice = parsed["choices"][0]
                    if isinstance(choice, dict):
                        delta = choice.get("delta") or {}
                        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                            fragment = delta["content"]
                if not fragment:
                    fragment = extract_local_llm_response_text(parsed)
                if response_id is None:
                    response_id = extract_local_llm_response_id(parsed)

            if fragment:
                collected_fragments.append(fragment)
                yield encode_sse_event("delta", {"content": fragment})

            if event_name in {"chat.end", "response.completed"} and response_id is None and isinstance(parsed, dict):
                response_id = extract_local_llm_response_id(parsed)

            event_name = "message"
            data_lines = []
            continue

        if line.startswith("event:"):
            event_name = line[6:].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    return response_id


def build_local_llm_stream(
    connection: DatabaseConnection,
    *,
    messages: list[dict[str, str]],
    model_identifier_override: str | None = None,
    previous_response_id: str | None = None,
):
    config, model_identifier, chat_url, request_body = prepare_local_llm_chat_request(
        connection,
        messages=messages,
        model_identifier_override=model_identifier_override,
        previous_response_id=previous_response_id,
        stream=True,
    )

    def event_stream():
        response_id: str | None = None
        collected_fragments: list[str] = []
        try:
            try:
                with httpx.stream("POST", chat_url, json=request_body, timeout=60.0) as response:
                    response.raise_for_status()
                    response_id = yield from iter_local_llm_stream_events(response, collected_fragments=collected_fragments)
            except httpx.HTTPError as error:
                if not should_retry_local_llm_with_openai_chat(config, error):
                    raise
                fallback_chat_url, fallback_body = build_local_llm_fallback_chat_request(
                    config,
                    model_identifier=model_identifier,
                    messages=messages,
                    stream=True,
                )
                with httpx.stream("POST", fallback_chat_url, json=fallback_body, timeout=60.0) as response:
                    response.raise_for_status()
                    response_id = yield from iter_local_llm_stream_events(response, collected_fragments=collected_fragments)

            yield encode_sse_event(
                "done",
                {
                    "response_text": "".join(collected_fragments),
                    "response_id": response_id,
                    "model_identifier": model_identifier,
                },
            )
        except httpx.HTTPError as error:
            yield encode_sse_event("error", {"message": f"Local LLM streaming request failed: {error}"})

    return event_stream()


__all__ = [name for name in globals() if not name.startswith("_")]
