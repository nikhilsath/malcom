"""Unit tests for backend.services.validation."""

from __future__ import annotations

import types

import pytest
from fastapi import HTTPException

from backend.schemas import (
    AutomationCreate,
    AutomationUpdate,
    ContinuousApiResourceUpdate,
    OutgoingAuthConfig,
    OutgoingWebhookSigningConfig,
    ScheduledApiResourceUpdate,
)
from backend.schemas.apis import (
    ContinuousApiResourceCreate,
    ScheduledApiResourceCreate,
    WebhookApiResourceCreate,
)
from backend.schemas.automation import AutomationStepConfig, AutomationStepDefinition, AutomationTriggerConfig
from backend.services.validation import (
    validate_automation_definition,
    validate_outgoing_resource_payload,
    validate_outgoing_update_payload,
    validate_webhook_resource_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_automation(trigger_type="manual", trigger_config=None, steps=None):
    return AutomationCreate(
        name="Test",
        trigger_type=trigger_type,
        trigger_config=trigger_config or AutomationTriggerConfig(),
        steps=steps or [],
    )


def _step(step_type, config_kwargs=None, *, step_id=None, on_true=None, on_false=None):
    return AutomationStepDefinition(
        id=step_id,
        type=step_type,
        name="test step",
        config=AutomationStepConfig(**(config_kwargs or {})),
        on_true_step_id=on_true,
        on_false_step_id=on_false,
    )


# ---------------------------------------------------------------------------
# validate_automation_definition — trigger validation
# ---------------------------------------------------------------------------

class TestValidateAutomationTrigger:
    def test_schedule_trigger_without_schedule_time_reports_issue(self):
        automation = _make_automation(trigger_type="schedule")
        issues = validate_automation_definition(automation)
        assert any("schedule_time" in i for i in issues)

    def test_schedule_trigger_with_schedule_time_passes(self):
        automation = _make_automation(
            trigger_type="schedule",
            trigger_config=AutomationTriggerConfig(schedule_time="09:30"),
        )
        issues = validate_automation_definition(automation)
        assert not any("schedule_time" in i for i in issues)

    def test_inbound_api_trigger_without_inbound_api_id_reports_issue(self):
        automation = _make_automation(trigger_type="inbound_api")
        issues = validate_automation_definition(automation)
        assert any("inbound_api_id" in i for i in issues)

    def test_inbound_api_trigger_with_inbound_api_id_passes(self):
        automation = _make_automation(
            trigger_type="inbound_api",
            trigger_config=AutomationTriggerConfig(inbound_api_id="api-123"),
        )
        issues = validate_automation_definition(automation)
        assert not any("inbound_api_id" in i for i in issues)

    def test_require_steps_flag_with_empty_steps_reports_issue(self):
        automation = _make_automation()
        issues = validate_automation_definition(automation, require_steps=True)
        assert any("at least one step" in i for i in issues)

    def test_require_steps_flag_with_steps_passes(self):
        automation = _make_automation(steps=[_step("log", {"message": "hi"})])
        issues = validate_automation_definition(automation, require_steps=True)
        assert not any("at least one step" in i for i in issues)

    def test_manual_trigger_produces_no_trigger_issues(self):
        automation = _make_automation(trigger_type="manual")
        issues = validate_automation_definition(automation)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_automation_definition — log step
# ---------------------------------------------------------------------------

class TestValidateLogStep:
    def test_log_step_without_message_or_table_id_reports_issue(self):
        automation = _make_automation(steps=[_step("log", {})])
        issues = validate_automation_definition(automation)
        assert any("config.message" in i or "log_table_id" in i for i in issues)

    def test_log_step_with_message_passes(self):
        automation = _make_automation(steps=[_step("log", {"message": "hello"})])
        issues = validate_automation_definition(automation)
        assert issues == []

    def test_log_step_with_table_but_no_mappings_reports_issue(self):
        automation = _make_automation(steps=[_step("log", {"log_table_id": "tbl-1"})])
        issues = validate_automation_definition(automation)
        assert any("log_column_mappings" in i for i in issues)

    def test_log_step_with_table_and_mappings_passes(self):
        step = _step("log", {"log_table_id": "tbl-1", "log_column_mappings": {"col": "val"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_automation_definition — outbound_request step
# ---------------------------------------------------------------------------

class TestValidateOutboundRequestStep:
    def test_manual_mode_without_destination_url_reports_issue(self):
        automation = _make_automation(steps=[_step("outbound_request", {"payload_template": "{}"})])
        issues = validate_automation_definition(automation)
        assert any("destination_url" in i for i in issues)

    def test_manual_mode_without_payload_template_reports_issue(self):
        automation = _make_automation(steps=[_step("outbound_request", {"destination_url": "https://example.com"})])
        issues = validate_automation_definition(automation)
        assert any("payload_template" in i for i in issues)

    def test_manual_mode_with_invalid_json_payload_reports_issue(self):
        step = _step("outbound_request", {"destination_url": "https://example.com", "payload_template": "{bad json"})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("invalid JSON" in i for i in issues)

    def test_manual_mode_valid_step_passes(self):
        step = _step("outbound_request", {"destination_url": "https://example.com", "payload_template": '{"key": "val"}'})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert issues == []

    def test_response_mapping_missing_key_reports_issue(self):
        step = _step("outbound_request", {
            "destination_url": "https://example.com",
            "payload_template": "{}",
            "response_mappings": [{"path": "$.result"}],
        })
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("requires a key" in i for i in issues)

    def test_response_mapping_missing_path_reports_issue(self):
        step = _step("outbound_request", {
            "destination_url": "https://example.com",
            "payload_template": "{}",
            "response_mappings": [{"key": "myvar"}],
        })
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("requires a JSON path" in i for i in issues)


# ---------------------------------------------------------------------------
# validate_automation_definition — connector_activity step
# ---------------------------------------------------------------------------

class TestValidateConnectorActivityStep:
    def test_missing_connector_id_reports_issue(self):
        automation = _make_automation(steps=[_step("connector_activity", {"activity_id": "act-1"})])
        issues = validate_automation_definition(automation)
        assert any("connector_id" in i for i in issues)

    def test_missing_activity_id_reports_issue(self):
        automation = _make_automation(steps=[_step("connector_activity", {"connector_id": "conn-1"})])
        issues = validate_automation_definition(automation)
        assert any("activity_id" in i for i in issues)

    def test_no_connection_skips_db_lookup(self):
        step = _step("connector_activity", {"connector_id": "conn-1", "activity_id": "act-1"})
        automation = _make_automation(steps=[step])
        # connection=None means DB lookup is skipped — should return no issues from this function
        issues = validate_automation_definition(automation, connection=None)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_automation_definition — script step
# ---------------------------------------------------------------------------

class TestValidateScriptStep:
    def test_script_step_without_script_id_reports_issue(self):
        automation = _make_automation(steps=[_step("script", {})])
        issues = validate_automation_definition(automation)
        assert any("script_id" in i for i in issues)

    def test_script_step_with_script_id_passes(self):
        automation = _make_automation(steps=[_step("script", {"script_id": "scr-1"})])
        issues = validate_automation_definition(automation)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_automation_definition — tool step
# ---------------------------------------------------------------------------

class TestValidateToolStep:
    def test_tool_step_without_tool_id_reports_issue(self):
        automation = _make_automation(steps=[_step("tool", {})])
        issues = validate_automation_definition(automation)
        assert any("tool_id" in i for i in issues)

    def test_coqui_tts_without_text_reports_issue(self):
        step = _step("tool", {"tool_id": "coqui-tts"})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("'text' input" in i for i in issues)

    def test_coqui_tts_with_text_input_passes(self):
        step = _step("tool", {"tool_id": "coqui-tts", "tool_inputs": {"text": "hello"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert not any("'text' input" in i for i in issues)

    def test_llm_deepl_without_user_prompt_reports_issue(self):
        step = _step("tool", {"tool_id": "llm-deepl"})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("'user_prompt'" in i for i in issues)

    def test_llm_deepl_with_user_prompt_passes(self):
        step = _step("tool", {"tool_id": "llm-deepl", "tool_inputs": {"user_prompt": "translate this"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert not any("'user_prompt'" in i for i in issues)

    def test_smtp_missing_all_required_fields_reports_issues(self):
        step = _step("tool", {"tool_id": "smtp"})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        required = ("relay_host", "relay_port", "from_address", "to", "subject", "body")
        for field in required:
            assert any(f"'{field}'" in i for i in issues), f"Expected issue for '{field}'"

    def test_smtp_with_non_integer_relay_port_reports_issue(self):
        step = _step("tool", {"tool_id": "smtp", "tool_inputs": {
            "relay_host": "mail.example.com",
            "relay_port": "not-a-number",
            "from_address": "from@example.com",
            "to": "to@example.com",
            "subject": "Hi",
            "body": "Body",
        }})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("relay_port" in i and "integer" in i for i in issues)

    def test_smtp_with_valid_integer_relay_port_passes(self):
        step = _step("tool", {"tool_id": "smtp", "tool_inputs": {
            "relay_host": "mail.example.com",
            "relay_port": "587",
            "from_address": "from@example.com",
            "to": "to@example.com",
            "subject": "Hi",
            "body": "Body",
        }})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert not any("relay_port" in i and "integer" in i for i in issues)

    def test_image_magic_without_input_file_reports_issue(self):
        step = _step("tool", {"tool_id": "image-magic", "tool_inputs": {"output_format": "png"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("input_file" in i for i in issues)

    def test_image_magic_without_output_format_reports_issue(self):
        step = _step("tool", {"tool_id": "image-magic", "tool_inputs": {"input_file": "img.jpg"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("output_format" in i for i in issues)

    def test_image_magic_with_both_fields_passes(self):
        step = _step("tool", {"tool_id": "image-magic", "tool_inputs": {"input_file": "img.jpg", "output_format": "png"}})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert not any("image-magic" in i for i in issues)


# ---------------------------------------------------------------------------
# validate_automation_definition — condition step
# ---------------------------------------------------------------------------

class TestValidateConditionStep:
    def test_condition_step_without_expression_reports_issue(self):
        automation = _make_automation(steps=[_step("condition", {})])
        issues = validate_automation_definition(automation)
        assert any("expression" in i for i in issues)

    def test_condition_step_with_expression_passes(self):
        automation = _make_automation(steps=[_step("condition", {"expression": "x > 0"})])
        issues = validate_automation_definition(automation)
        assert not any("expression" in i for i in issues)

    def test_condition_on_true_referencing_unknown_step_reports_issue(self):
        step = _step("condition", {"expression": "x > 0"}, step_id="s1", on_true="unknown-id")
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("on_true_step_id" in i for i in issues)

    def test_condition_on_false_referencing_unknown_step_reports_issue(self):
        step = _step("condition", {"expression": "x > 0"}, step_id="s1", on_false="unknown-id")
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert any("on_false_step_id" in i for i in issues)

    def test_condition_step_references_valid_steps_passes(self):
        s1 = _step("condition", {"expression": "x > 0"}, step_id="s1", on_true="s2", on_false="s3")
        s2 = _step("log", {"message": "true"}, step_id="s2")
        s3 = _step("log", {"message": "false"}, step_id="s3")
        automation = _make_automation(steps=[s1, s2, s3])
        issues = validate_automation_definition(automation)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_automation_definition — llm_chat step
# ---------------------------------------------------------------------------

class TestValidateLlmChatStep:
    def test_llm_chat_without_user_prompt_reports_issue(self):
        automation = _make_automation(steps=[_step("llm_chat", {})])
        issues = validate_automation_definition(automation)
        assert any("user_prompt" in i for i in issues)

    def test_llm_chat_with_user_prompt_passes(self):
        step = _step("llm_chat", {"user_prompt": "Summarize this."})
        automation = _make_automation(steps=[step])
        issues = validate_automation_definition(automation)
        assert issues == []


# ---------------------------------------------------------------------------
# validate_outgoing_resource_payload
# ---------------------------------------------------------------------------

def _make_scheduled_create(**overrides):
    defaults = dict(
        type="outgoing_scheduled",
        name="Scheduled API",
        path_slug="scheduled-api",
        destination_url="https://example.com/hook",
        http_method="POST",
        payload_template="{}",
        scheduled_time="09:00",
    )
    defaults.update(overrides)
    return ScheduledApiResourceCreate(**defaults)


def _make_continuous_create(**overrides):
    defaults = dict(
        type="outgoing_continuous",
        name="Continuous API",
        path_slug="continuous-api",
        destination_url="https://example.com/hook",
        http_method="POST",
        payload_template="{}",
    )
    defaults.update(overrides)
    return ContinuousApiResourceCreate(**defaults)


class TestValidateOutgoingResourcePayload:
    def test_non_outgoing_type_is_skipped(self):
        payload = WebhookApiResourceCreate(
            type="webhook",
            name="WH",
            path_slug="wh",
            callback_path="/cb",
            verification_token="tok",
            signing_secret="sec",
            signature_header="X-Sig",
        )
        # Should not raise for non-outgoing types
        validate_outgoing_resource_payload(payload)

    def test_missing_destination_url_and_connector_id_raises_422(self):
        # Use model_construct to bypass Pydantic's min_length requirement
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url=None,
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Destination URL is required" in exc_info.value.detail

    def test_invalid_url_scheme_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="ftp://example.com/path",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "valid http or https URL" in exc_info.value.detail

    def test_missing_http_method_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method=None,
            payload_template="{}",
            scheduled_time="09:00",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "HTTP method is required" in exc_info.value.detail

    def test_missing_payload_template_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template=None,
            scheduled_time="09:00",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Payload template is required" in exc_info.value.detail

    def test_invalid_json_payload_template_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{bad}",
            scheduled_time="09:00",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "valid JSON" in exc_info.value.detail

    def test_bearer_auth_without_token_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            auth_type="bearer",
            auth_config=OutgoingAuthConfig(token=None),
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Bearer authentication requires a token" in exc_info.value.detail

    def test_basic_auth_without_credentials_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            auth_type="basic",
            auth_config=OutgoingAuthConfig(username=None, password=None),
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Basic authentication requires a username and password" in exc_info.value.detail

    def test_header_auth_without_header_info_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            auth_type="header",
            auth_config=OutgoingAuthConfig(header_name=None, header_value=None),
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Header authentication requires a header name and value" in exc_info.value.detail

    def test_scheduled_without_scheduled_time_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "require a send time" in exc_info.value.detail

    def test_scheduled_with_repeat_interval_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            repeat_interval_minutes=60,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "do not use repeat intervals" in exc_info.value.detail

    def test_continuous_with_repeat_enabled_and_no_interval_raises_422(self):
        payload = ContinuousApiResourceCreate.model_construct(
            type="outgoing_continuous",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            repeat_enabled=True,
            repeat_interval_minutes=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "require an interval" in exc_info.value.detail

    def test_continuous_with_interval_but_no_repeat_enabled_raises_422(self):
        payload = ContinuousApiResourceCreate.model_construct(
            type="outgoing_continuous",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            repeat_enabled=False,
            repeat_interval_minutes=30,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Set repeating" in exc_info.value.detail

    def test_webhook_signing_unsupported_algorithm_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            webhook_signing=OutgoingWebhookSigningConfig(
                algorithm=None,  # type: ignore[arg-type]
                secret_source="inline",
                signing_secret="secret",
                signature_header="X-Sig",
            ),
        )
        # algorithm=None still triggers the 'any truthy field' check,
        # so the branch is entered and should raise for algorithm != "hmac_sha256"
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "hmac_sha256" in exc_info.value.detail

    def test_webhook_signing_missing_secret_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            webhook_signing=OutgoingWebhookSigningConfig(
                algorithm="hmac_sha256",
                secret_source="inline",
                signing_secret=None,
                signature_header="X-Sig",
            ),
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "signing secret" in exc_info.value.detail

    def test_webhook_signing_missing_header_raises_422(self):
        payload = ScheduledApiResourceCreate.model_construct(
            type="outgoing_scheduled",
            destination_url="https://example.com",
            connector_id=None,
            http_method="POST",
            payload_template="{}",
            scheduled_time="09:00",
            webhook_signing=OutgoingWebhookSigningConfig(
                algorithm="hmac_sha256",
                secret_source="inline",
                signing_secret="my-secret",
                signature_header=None,
            ),
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "signature header" in exc_info.value.detail

    def test_valid_scheduled_payload_passes(self):
        payload = _make_scheduled_create()
        validate_outgoing_resource_payload(payload)  # Should not raise

    def test_valid_continuous_payload_passes(self):
        payload = _make_continuous_create()
        validate_outgoing_resource_payload(payload)  # Should not raise


# ---------------------------------------------------------------------------
# validate_outgoing_update_payload
# ---------------------------------------------------------------------------

class TestValidateOutgoingUpdatePayload:
    def test_empty_destination_url_raises_422(self):
        payload = ScheduledApiResourceUpdate.model_construct(
            type="outgoing_scheduled",
            destination_url="",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_update_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Destination URL is required" in exc_info.value.detail

    def test_invalid_url_scheme_raises_422(self):
        payload = ScheduledApiResourceUpdate.model_construct(
            type="outgoing_scheduled",
            destination_url="ftp://example.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_update_payload(payload)
        assert exc_info.value.status_code == 422
        assert "valid http or https URL" in exc_info.value.detail

    def test_invalid_json_payload_template_raises_422(self):
        payload = ScheduledApiResourceUpdate.model_construct(
            type="outgoing_scheduled",
            payload_template="{not valid json",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_update_payload(payload)
        assert exc_info.value.status_code == 422
        assert "valid JSON" in exc_info.value.detail

    def test_bearer_auth_without_token_raises_422(self):
        payload = ScheduledApiResourceUpdate.model_construct(
            type="outgoing_scheduled",
            auth_type="bearer",
            auth_config=OutgoingAuthConfig(token=None),
            connector_id=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_update_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Bearer authentication requires a token" in exc_info.value.detail

    def test_continuous_interval_without_repeat_enabled_raises_422(self):
        payload = ContinuousApiResourceUpdate.model_construct(
            type="outgoing_continuous",
            repeat_enabled=False,
            repeat_interval_minutes=30,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_outgoing_update_payload(payload)
        assert exc_info.value.status_code == 422
        assert "Set repeating" in exc_info.value.detail

    def test_none_destination_url_is_skipped(self):
        # destination_url=None means "not being updated", should not raise
        payload = ScheduledApiResourceUpdate.model_construct(
            type="outgoing_scheduled",
            destination_url=None,
        )
        validate_outgoing_update_payload(payload)  # Should not raise

    def test_valid_scheduled_update_passes(self):
        payload = ScheduledApiResourceUpdate(
            type="outgoing_scheduled",
            destination_url="https://example.com",
        )
        validate_outgoing_update_payload(payload)  # Should not raise


# ---------------------------------------------------------------------------
# validate_webhook_resource_payload
# ---------------------------------------------------------------------------

class TestValidateWebhookResourcePayload:
    def test_non_webhook_type_is_skipped(self):
        payload = ScheduledApiResourceCreate.model_construct(type="outgoing_scheduled")
        validate_webhook_resource_payload(payload)  # Should not raise

    def test_missing_callback_path_raises_422(self):
        payload = WebhookApiResourceCreate.model_construct(
            type="webhook",
            callback_path=None,
            verification_token="tok",
            signing_secret="sec",
            signature_header="X-Sig",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_webhook_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "callback path is required" in exc_info.value.detail

    def test_callback_path_not_starting_with_slash_raises_422(self):
        payload = WebhookApiResourceCreate.model_construct(
            type="webhook",
            callback_path="no-slash",
            verification_token="tok",
            signing_secret="sec",
            signature_header="X-Sig",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_webhook_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "must start with '/'" in exc_info.value.detail

    def test_missing_verification_token_raises_422(self):
        payload = WebhookApiResourceCreate.model_construct(
            type="webhook",
            callback_path="/webhook/path",
            verification_token=None,
            signing_secret="sec",
            signature_header="X-Sig",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_webhook_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "verification token is required" in exc_info.value.detail

    def test_missing_signing_secret_raises_422(self):
        payload = WebhookApiResourceCreate.model_construct(
            type="webhook",
            callback_path="/webhook/path",
            verification_token="tok",
            signing_secret=None,
            signature_header="X-Sig",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_webhook_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "signing secret is required" in exc_info.value.detail

    def test_missing_signature_header_raises_422(self):
        payload = WebhookApiResourceCreate.model_construct(
            type="webhook",
            callback_path="/webhook/path",
            verification_token="tok",
            signing_secret="sec",
            signature_header=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_webhook_resource_payload(payload)
        assert exc_info.value.status_code == 422
        assert "signature header is required" in exc_info.value.detail

    def test_valid_webhook_payload_passes(self):
        payload = WebhookApiResourceCreate(
            type="webhook",
            name="My Webhook",
            path_slug="my-webhook",
            callback_path="/hooks/myservice",
            verification_token="verif-token",
            signing_secret="secret123",
            signature_header="X-Hub-Signature-256",
        )
        validate_webhook_resource_payload(payload)  # Should not raise
