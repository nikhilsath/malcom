"""Automation domain schemas for automation definitions, step config, and run history."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .apis import OutgoingAuthConfig

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _validate_db_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(
            "Must start with a lowercase letter and contain only lowercase letters, "
            "digits, and underscores (max 63 characters)."
        )
    return value


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
    response_body_json: Any | None = None
    extracted_fields_json: dict[str, Any] | None = None


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
    wait_for_response: bool = True
    response_mappings: list[dict[str, str]] | None = None
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
    # Log / Write-to-DB fields (mutually exclusive with message for new steps)
    log_table_id: str | None = Field(default=None, max_length=120)
    log_column_mappings: dict[str, str] | None = None


class AutomationStepDefinition(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    type: Literal["log", "outbound_request", "script", "tool", "condition", "llm_chat"]
    name: str = Field(min_length=1, max_length=120)
    config: AutomationStepConfig = Field(default_factory=AutomationStepConfig)
    on_true_step_id: str | None = Field(default=None, max_length=120)
    on_false_step_id: str | None = Field(default=None, max_length=120)
    is_merge_target: bool = False


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


# ── Log / Write-to-DB table management models ────────────────────────────────

_ALLOWED_COLUMN_TYPES = {"text", "integer", "real", "boolean", "timestamp"}


class LogDbColumnDefinition(BaseModel):
    column_name: str = Field(min_length=1, max_length=63)
    data_type: Literal["text", "integer", "real", "boolean", "timestamp"] = "text"
    nullable: bool = True
    default_value: str | None = Field(default=None, max_length=255)

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        return _validate_db_identifier(v)


class LogDbTableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    description: str = Field(default="", max_length=500)
    columns: list[LogDbColumnDefinition] = Field(min_length=1, max_length=50)
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_db_identifier(v)

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Each imported row must be an object keyed by column name.")
        return rows


class LogDbColumnResponse(BaseModel):
    id: str
    table_id: str
    column_name: str
    data_type: str
    nullable: bool
    default_value: str | None
    position: int
    created_at: str


class LogDbTableSummary(BaseModel):
    id: str
    name: str
    description: str
    row_count: int
    created_at: str
    updated_at: str


class LogDbTableDetail(LogDbTableSummary):
    columns: list[LogDbColumnResponse]


class LogDbRowsResponse(BaseModel):
    table_id: str
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int


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
    "LogDbColumnDefinition",
    "LogDbColumnResponse",
    "LogDbRowsResponse",
    "LogDbTableCreate",
    "LogDbTableDetail",
    "LogDbTableSummary",
    "RuntimeStatusResponse",
]
