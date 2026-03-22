from __future__ import annotations

import json
import urllib.parse

from fastapi import HTTPException, status

from backend.schemas import (
    ApiResourceCreate,
    AutomationCreate,
    AutomationDetailResponse,
    AutomationUpdate,
    ContinuousApiResourceUpdate,
    OutgoingAuthConfig,
    ScheduledApiResourceUpdate,
)


def validate_automation_definition(
    payload: AutomationCreate | AutomationUpdate | AutomationDetailResponse,
    *,
    require_steps: bool = False,
) -> list[str]:
    issues: list[str] = []
    trigger_type = payload.trigger_type
    trigger_config = payload.trigger_config
    steps = payload.steps if hasattr(payload, "steps") else None
    step_ids = {s.id for s in (steps or []) if s.id}

    if trigger_type == "schedule" and not trigger_config.schedule_time:
        issues.append("Scheduled automations require trigger_config.schedule_time.")
    if trigger_type == "inbound_api" and not trigger_config.inbound_api_id:
        issues.append("Inbound API automations require trigger_config.inbound_api_id.")
    if trigger_type == "smtp_email" and not trigger_config.smtp_subject:
        issues.append("SMTP email automations require trigger_config.smtp_subject.")
    if require_steps and not steps:
        issues.append("Automations require at least one step.")

    for index, step in enumerate(steps or [], start=1):
        if step.type == "log":
            if step.config.log_table_id:
                if not step.config.log_column_mappings:
                    issues.append(
                        f"Step {index}: log steps targeting a table require log_column_mappings."
                    )
            else:
                if not step.config.message:
                    issues.append(f"Step {index} requires config.message or a log_table_id for log steps.")
        if step.type == "outbound_request":
            if not step.config.destination_url and not step.config.connector_id:
                issues.append(f"Step {index} requires config.destination_url.")
            if step.config.payload_template is None:
                issues.append(f"Step {index} requires config.payload_template.")
            else:
                try:
                    json.loads(step.config.payload_template)
                except json.JSONDecodeError as error:
                    issues.append(f"Step {index} has invalid JSON payload_template: {error.msg}.")
        if step.type == "script" and not step.config.script_id:
            issues.append(f"Step {index} requires config.script_id for script steps.")
        if step.type == "tool":
            if not step.config.tool_id:
                issues.append(f"Step {index} requires config.tool_id for tool steps.")
            if step.config.tool_id == "coqui-tts":
                text_val = (step.config.tool_inputs or {}).get("text") or step.config.tool_text
                if not text_val:
                    issues.append(f"Step {index} requires a 'text' input for coqui-tts steps.")
            if step.config.tool_id == "llm-deepl":
                if not (step.config.tool_inputs or {}).get("user_prompt"):
                    issues.append(f"Step {index} requires a 'user_prompt' input for llm-deepl steps.")
            if step.config.tool_id == "smtp":
                inputs = step.config.tool_inputs or {}
                for required_key in ("relay_host", "relay_port", "from_address", "to", "subject", "body"):
                    if not inputs.get(required_key):
                        issues.append(f"Step {index} requires input '{required_key}' for smtp steps.")
            if step.config.tool_id == "convert-audio":
                inputs = step.config.tool_inputs or {}
                if not inputs.get("input_file"):
                    issues.append(f"Step {index} requires input 'input_file' for convert-audio steps.")
                if not inputs.get("output_format"):
                    issues.append(f"Step {index} requires input 'output_format' for convert-audio steps.")
            if step.config.tool_id == "image-magic":
                inputs = step.config.tool_inputs or {}
                if not inputs.get("input_file"):
                    issues.append(f"Step {index} requires input 'input_file' for image-magic steps.")
                if not inputs.get("output_format"):
                    issues.append(f"Step {index} requires input 'output_format' for image-magic steps.")
        if step.type == "condition" and not step.config.expression:
            issues.append(f"Step {index} requires config.expression for condition steps.")
        if step.type == "condition":
            if step.on_true_step_id and step.on_true_step_id not in step_ids:
                issues.append(f"Step {index}: on_true_step_id '{step.on_true_step_id}' does not reference a known step in this automation.")
            if step.on_false_step_id and step.on_false_step_id not in step_ids:
                issues.append(f"Step {index}: on_false_step_id '{step.on_false_step_id}' does not reference a known step in this automation.")
        if step.type == "llm_chat" and not step.config.user_prompt:
            issues.append(f"Step {index} requires config.user_prompt for LLM chat steps.")

    return issues


def validate_outgoing_resource_payload(payload: ApiResourceCreate) -> None:
    if payload.type not in {"outgoing_scheduled", "outgoing_continuous"}:
        return

    if not payload.destination_url and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL is required.")

    parsed_url = urllib.parse.urlparse(payload.destination_url) if payload.destination_url else None
    if payload.destination_url and (parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    if not payload.http_method:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="HTTP method is required.")

    if payload.payload_template is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Payload template is required.")

    try:
        json.loads(payload.payload_template)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    auth_type = payload.auth_type or "none"
    auth_config = payload.auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and not auth_config.token and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Bearer authentication requires a token.")
    if auth_type == "basic" and (not auth_config.username or not auth_config.password) and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Basic authentication requires a username and password.")
    if auth_type == "header" and (not auth_config.header_name or not auth_config.header_value) and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Header authentication requires a header name and value.")

    if payload.type == "outgoing_scheduled" and not payload.scheduled_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs require a send time.")

    if payload.type == "outgoing_scheduled" and payload.repeat_interval_minutes is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs do not use repeat intervals.")

    if payload.type == "outgoing_continuous":
        if payload.repeat_enabled and payload.repeat_interval_minutes is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Continuous outgoing APIs require an interval when repeating is enabled.")
        if not payload.repeat_enabled and payload.repeat_interval_minutes is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Set repeating on continuous outgoing APIs before providing an interval.")


def validate_outgoing_update_payload(payload: ScheduledApiResourceUpdate | ContinuousApiResourceUpdate) -> None:
    if payload.destination_url is not None:
        if not payload.destination_url:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL is required.")

        parsed_url = urllib.parse.urlparse(payload.destination_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Destination URL must be a valid http or https URL.")

    if payload.payload_template is not None:
        try:
            json.loads(payload.payload_template)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Payload template must be valid JSON: {error.msg}.") from error

    auth_type = payload.auth_type or "none"
    auth_config = payload.auth_config or OutgoingAuthConfig()

    if auth_type == "bearer" and not auth_config.token and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Bearer authentication requires a token.")
    if auth_type == "basic" and (not auth_config.username or not auth_config.password) and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Basic authentication requires a username and password.")
    if auth_type == "header" and (not auth_config.header_name or not auth_config.header_value) and not payload.connector_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Header authentication requires a header name and value.")

    if payload.type == "outgoing_scheduled" and payload.scheduled_time is not None and not payload.scheduled_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Scheduled outgoing APIs require a send time.")

    if payload.type == "outgoing_continuous" and payload.repeat_enabled is False and payload.repeat_interval_minutes is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Set repeating on continuous outgoing APIs before providing an interval.")


def validate_webhook_resource_payload(payload: ApiResourceCreate) -> None:
    if payload.type != "webhook":
        return

    if not payload.callback_path or not payload.callback_path.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook callback path is required.")

    callback_path = payload.callback_path.strip()
    if not callback_path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook callback path must start with '/'.")

    if not payload.verification_token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook verification token is required.")

    if not payload.signing_secret:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook signing secret is required.")

    if not payload.signature_header or not payload.signature_header.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook signature header is required.")
