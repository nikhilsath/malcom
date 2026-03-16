"""Automation domain schemas for automation definitions, step config, and run history."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .apis import OutgoingAuthConfig


class AutomationRunStepResponse(BaseModel):
    step_id: str
    run_id: str
    step_name: str
    status: str
    request_summary: str | None
    response_summary: str | None
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    detail_json: dict[str, Any] | None


class AutomationRunResponse(BaseModel):
    run_id: str
    automation_id: str
    trigger_type: str
    status: str
    worker_id: str | None
    worker_name: str | None
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    error_summary: str | None


class AutomationRunDetailResponse(AutomationRunResponse):
    steps: list[AutomationRunStepResponse]


class AutomationTriggerConfig(BaseModel):
    schedule_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    inbound_api_id: str | None = Field(default=None, max_length=120)
    smtp_subject: str | None = Field(default=None, max_length=500)
    smtp_recipient_email: str | None = Field(default=None, max_length=320)


class AutomationStepConfig(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    destination_url: str | None = Field(default=None, max_length=2000)
    http_method: str | None = Field(default="POST", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    connector_id: str | None = Field(default=None, max_length=120)
    payload_template: str | None = Field(default=None, max_length=10000)
    script_id: str | None = Field(default=None, max_length=120)
    tool_id: str | None = Field(default=None, max_length=120)
    tool_inputs: dict[str, str] | None = None
    tool_text: str | None = Field(default=None, max_length=20000)
    tool_output_filename: str | None = Field(default=None, max_length=255)
    tool_speaker: str | None = Field(default=None, max_length=120)
    tool_language: str | None = Field(default=None, max_length=120)
    expression: str | None = Field(default=None, max_length=500)
    stop_on_false: bool = False
    system_prompt: str | None = Field(default=None, max_length=5000)
    user_prompt: str | None = Field(default=None, max_length=20000)
    model_identifier: str | None = Field(default=None, max_length=255)


class AutomationStepDefinition(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    type: Literal["log", "outbound_request", "script", "tool", "condition", "llm_chat"]
    name: str = Field(min_length=1, max_length=120)
    config: AutomationStepConfig = Field(default_factory=AutomationStepConfig)


class AutomationSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    trigger_type: Literal["manual", "schedule", "inbound_api", "smtp_email"]
    trigger_config: AutomationTriggerConfig
    step_count: int
    created_at: str
    updated_at: str
    last_run_at: str | None = None
    next_run_at: str | None = None


class AutomationDetailResponse(AutomationSummaryResponse):
    steps: list[AutomationStepDefinition]


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    enabled: bool = True
    trigger_type: Literal["manual", "schedule", "inbound_api", "smtp_email"]
    trigger_config: AutomationTriggerConfig = Field(default_factory=AutomationTriggerConfig)
    steps: list[AutomationStepDefinition] = Field(default_factory=list, max_length=50)


class AutomationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None
    trigger_type: Literal["manual", "schedule", "inbound_api", "smtp_email"] | None = None
    trigger_config: AutomationTriggerConfig | None = None
    steps: list[AutomationStepDefinition] | None = Field(default=None, max_length=50)


class AutomationValidationResponse(BaseModel):
    valid: bool
    issues: list[str]


class RuntimeStatusResponse(BaseModel):
    active: bool
    last_tick_started_at: str | None = None
    last_tick_finished_at: str | None = None
    last_error: str | None = None
    job_count: int


__all__ = [
    "AutomationCreate",
    "AutomationDetailResponse",
    "AutomationRunDetailResponse",
    "AutomationRunResponse",
    "AutomationRunStepResponse",
    "AutomationStepConfig",
    "AutomationStepDefinition",
    "AutomationSummaryResponse",
    "AutomationTriggerConfig",
    "AutomationUpdate",
    "AutomationValidationResponse",
    "RuntimeStatusResponse",
]