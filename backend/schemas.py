from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

class InboundApiCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    path_slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool = True


class InboundApiUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None


class OutgoingAuthConfig(BaseModel):
    token: str | None = Field(default=None, max_length=500)
    username: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, max_length=500)
    header_name: str | None = Field(default=None, max_length=120)
    header_value: str | None = Field(default=None, max_length=500)


class ApiResourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    path_slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool = True


class IncomingApiResourceCreate(ApiResourceBase):
    type: Literal["incoming"]


class OutgoingApiResourceBase(ApiResourceBase):
    repeat_enabled: bool = False
    repeat_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    destination_url: str = Field(min_length=1, max_length=2000)
    http_method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str = Field(default="{}", max_length=10000)
    connector_id: str | None = Field(default=None, max_length=120)


class ScheduledApiResourceCreate(OutgoingApiResourceBase):
    type: Literal["outgoing_scheduled"]
    scheduled_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    repeat_interval_minutes: None = None


class ContinuousApiResourceCreate(OutgoingApiResourceBase):
    type: Literal["outgoing_continuous"]


class WebhookApiResourceCreate(ApiResourceBase):
    type: Literal["webhook"]
    callback_path: str = Field(min_length=1, max_length=120)
    verification_token: str = Field(min_length=1, max_length=500)
    signing_secret: str = Field(min_length=1, max_length=500)
    signature_header: str = Field(min_length=1, max_length=120)
    event_filter: str = Field(default="", max_length=200)


ApiResourceCreate = Annotated[
    IncomingApiResourceCreate | ScheduledApiResourceCreate | ContinuousApiResourceCreate | WebhookApiResourceCreate,
    Field(discriminator="type"),
]


class OutgoingApiTestRequest(BaseModel):
    type: str = Field(pattern=r"^outgoing_(scheduled|continuous)$")
    destination_url: str = Field(min_length=1, max_length=2000)
    http_method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str = Field(default="none", pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str = Field(default="{}", max_length=10000)
    connector_id: str | None = Field(default=None, max_length=120)


class OutgoingApiTestResponse(BaseModel):
    ok: bool
    status_code: int
    response_body: str
    sent_headers: dict[str, str]
    destination_url: str


class ApiResourceResponse(BaseModel):
    id: str
    type: str
    name: str
    description: str
    path_slug: str
    enabled: bool
    created_at: str
    updated_at: str
    status: str | None = None
    endpoint_path: str | None = None
    endpoint_url: str | None = None
    secret: str | None = None
    destination_url: str | None = None
    http_method: str | None = None
    auth_type: str | None = None
    repeat_enabled: bool | None = None
    repeat_interval_minutes: int | None = None
    payload_template: str | None = None
    connector_id: str | None = None
    scheduled_time: str | None = None
    schedule_expression: str | None = None
    stream_mode: str | None = None
    callback_path: str | None = None
    signature_header: str | None = None
    event_filter: str | None = None
    has_verification_token: bool | None = None
    has_signing_secret: bool | None = None


class OutgoingApiDetailResponse(ApiResourceResponse):
    auth_config: OutgoingAuthConfig = Field(default_factory=OutgoingAuthConfig)


class ScheduledApiResourceUpdate(BaseModel):
    type: Literal["outgoing_scheduled"]
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None
    repeat_enabled: bool | None = None
    destination_url: str | None = Field(default=None, min_length=1, max_length=2000)
    http_method: str | None = Field(default=None, pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default=None, pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str | None = Field(default=None, max_length=10000)
    connector_id: str | None = Field(default=None, max_length=120)
    scheduled_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ContinuousApiResourceUpdate(BaseModel):
    type: Literal["outgoing_continuous"]
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    path_slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    enabled: bool | None = None
    repeat_enabled: bool | None = None
    repeat_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    destination_url: str | None = Field(default=None, min_length=1, max_length=2000)
    http_method: str | None = Field(default=None, pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    auth_type: str | None = Field(default=None, pattern=r"^(none|bearer|basic|header)$")
    auth_config: OutgoingAuthConfig | None = None
    payload_template: str | None = Field(default=None, max_length=10000)
    connector_id: str | None = Field(default=None, max_length=120)


OutgoingApiUpdate = Annotated[
    ScheduledApiResourceUpdate | ContinuousApiResourceUpdate,
    Field(discriminator="type"),
]


class InboundReceiveAccepted(BaseModel):
    status: str
    event_id: str
    trigger: dict[str, Any]


class InboundSecretResponse(BaseModel):
    id: str
    secret: str
    endpoint_url: str


class InboundApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    path_slug: str
    auth_type: str
    enabled: bool
    created_at: str
    updated_at: str
    endpoint_path: str
    last_received_at: str | None
    last_delivery_status: str | None
    events_count: int


class InboundApiCreated(InboundApiResponse):
    secret: str
    endpoint_url: str


class InboundApiDetail(InboundApiResponse):
    endpoint_url: str
    events: list[dict[str, Any]]


class DashboardDeviceResponse(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    location: str
    detail: str
    last_seen_at: str


class HostMachineSummary(BaseModel):
    id: str
    name: str
    status: str
    location: str
    detail: str
    last_seen_at: str
    hostname: str
    operating_system: str
    architecture: str
    memory_total_bytes: int
    memory_used_bytes: int
    memory_available_bytes: int
    memory_usage_percent: float
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    storage_usage_percent: float
    sampled_at: str


class DashboardDevicesApiResponse(BaseModel):
    host: HostMachineSummary | None
    devices: list[DashboardDeviceResponse]


class WorkerRegistrationRequest(BaseModel):
    worker_id: str | None = Field(default=None, min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=255)
    capabilities: list[str] = Field(default_factory=list)


class WorkerResponse(BaseModel):
    worker_id: str
    name: str
    hostname: str
    address: str
    capabilities: list[str]
    status: str
    created_at: str
    updated_at: str
    last_seen_at: str


class WorkerClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)


class WorkerClaimedJobResponse(BaseModel):
    job_id: str
    run_id: str
    step_id: str
    worker_id: str
    worker_name: str
    trigger: dict[str, Any]
    claimed_at: str


class WorkerClaimResponse(BaseModel):
    job: WorkerClaimedJobResponse | None


class WorkerCompletionRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    job_id: str = Field(min_length=1, max_length=120)
    status: Literal["completed", "failed"]
    response_summary: str | None = Field(default=None, max_length=500)
    error_summary: str | None = Field(default=None, max_length=500)
    detail: dict[str, Any] | None = None


class RuntimeMachineResponse(BaseModel):
    id: str
    name: str
    hostname: str
    address: str
    status: str
    is_local: bool
    capabilities: list[str]


class SmtpToolConfigResponse(BaseModel):
    enabled: bool
    target_worker_id: str | None = None
    bind_host: str
    port: int
    recipient_email: str | None = None


class SmtpRuntimeMessageResponse(BaseModel):
    id: str
    received_at: str
    mail_from: str
    recipients: list[str]
    peer: str
    size_bytes: int
    subject: str | None = None
    body_preview: str | None = None
    body: str | None = None
    raw_message: str | None = None


class SmtpInboundIdentityResponse(BaseModel):
    display_address: str
    configured_recipient_email: str | None = None
    accepts_any_recipient: bool
    listening_host: str | None = None
    listening_port: int | None = None
    connection_hint: str


class SmtpToolRuntimeResponse(BaseModel):
    status: Literal["stopped", "running", "assigned", "error"]
    message: str
    listening_host: str | None = None
    listening_port: int | None = None
    selected_machine_id: str | None = None
    selected_machine_name: str | None = None
    last_started_at: str | None = None
    last_stopped_at: str | None = None
    last_error: str | None = None
    session_count: int
    message_count: int
    last_message_at: str | None = None
    last_mail_from: str | None = None
    last_recipient: str | None = None
    recent_messages: list[SmtpRuntimeMessageResponse] = Field(default_factory=list)


class SmtpToolResponse(BaseModel):
    tool_id: Literal["smtp"]
    config: SmtpToolConfigResponse
    runtime: SmtpToolRuntimeResponse
    inbound_identity: SmtpInboundIdentityResponse
    machines: list[RuntimeMachineResponse]


class SmtpToolUpdate(BaseModel):
    enabled: bool | None = None
    target_worker_id: str | None = Field(default=None, max_length=120)
    bind_host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=0, le=65535)
    recipient_email: str | None = Field(default=None, max_length=320)


class LocalLlmEndpointsResponse(BaseModel):
    models: str
    chat: str
    model_load: str
    model_download: str
    model_download_status: str


class LocalLlmPresetResponse(BaseModel):
    id: str
    label: str
    server_base_url: str
    endpoints: LocalLlmEndpointsResponse


class LocalLlmToolConfigResponse(BaseModel):
    enabled: bool
    provider: str
    server_base_url: str
    model_identifier: str
    endpoints: LocalLlmEndpointsResponse


class LocalLlmToolResponse(BaseModel):
    tool_id: Literal["llm-deepl"]
    config: LocalLlmToolConfigResponse
    presets: list[LocalLlmPresetResponse]


class LocalLlmEndpointsUpdate(BaseModel):
    models: str | None = Field(default=None, max_length=255)
    chat: str | None = Field(default=None, max_length=255)
    model_load: str | None = Field(default=None, max_length=255)
    model_download: str | None = Field(default=None, max_length=255)
    model_download_status: str | None = Field(default=None, max_length=255)


class LocalLlmToolUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=60)
    server_base_url: str | None = Field(default=None, max_length=500)
    model_identifier: str | None = Field(default=None, max_length=255)
    endpoints: LocalLlmEndpointsUpdate | None = None


class CoquiTtsToolConfigResponse(BaseModel):
    enabled: bool
    command: str
    model_name: str
    speaker: str
    language: str
    output_directory: str


class CoquiTtsToolResponse(BaseModel):
    tool_id: Literal["coqui-tts"]
    config: CoquiTtsToolConfigResponse


class CoquiTtsToolUpdate(BaseModel):
    enabled: bool | None = None
    command: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    speaker: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=120)
    output_directory: str | None = Field(default=None, min_length=1, max_length=2000)


class LocalLlmChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class LocalLlmChatRequest(BaseModel):
    messages: list[LocalLlmChatMessage] = Field(default_factory=list, min_length=1, max_length=100)
    model_identifier: str | None = Field(default=None, max_length=255)
    previous_response_id: str | None = Field(default=None, max_length=255)
    stream: bool = False


class LocalLlmChatResponse(BaseModel):
    ok: bool
    model_identifier: str
    response_text: str
    response_id: str | None = None


class SmtpSendTestRequest(BaseModel):
    mail_from: str = Field(min_length=3, max_length=320)
    recipients: list[str] = Field(min_length=1)
    subject: str = Field(default="", max_length=998)
    body: str = Field(default="", max_length=20000)


class SmtpSendTestResponse(BaseModel):
    ok: bool
    message: str
    message_id: str | None = None


class SmtpRelaySendRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    security: Literal["none", "starttls", "tls"] = "none"
    auth_mode: Literal["none", "password"] = "none"
    username: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, max_length=2000)
    mail_from: str = Field(min_length=3, max_length=320)
    recipients: list[str] = Field(min_length=1)
    subject: str = Field(default="", max_length=998)
    body: str = Field(default="", max_length=20000)


class SmtpRelaySendResponse(BaseModel):
    ok: bool
    status: Literal["sent", "auth_failed", "tls_failed", "connection_failed", "invalid_input", "send_failed"]
    message: str




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


class ToolMetadataResponse(BaseModel):
    id: str
    name: str
    description: str


class ToolMetadataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class ToolDirectoryEntryResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    page_href: str


class ToolDirectoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    enabled: bool | None = None


class ScriptValidationIssue(BaseModel):
    message: str
    line: int | None = None
    column: int | None = None


class ScriptValidationResult(BaseModel):
    valid: bool
    issues: list[ScriptValidationIssue]


class ScriptSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    language: Literal["python", "javascript"]
    validation_status: Literal["valid", "invalid", "unknown"]
    validation_message: str | None = None
    last_validated_at: str | None = None
    created_at: str
    updated_at: str


class ScriptResponse(ScriptSummaryResponse):
    code: str


class ScriptValidationRequest(BaseModel):
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=200000)


class ScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    language: Literal["python", "javascript"]
    code: str = Field(min_length=1, max_length=200000)


class ScriptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    language: Literal["python", "javascript"] | None = None
    code: str | None = Field(default=None, min_length=1, max_length=200000)


class GeneralSettings(BaseModel):
    environment: Literal["live"]
    timezone: str = Field(pattern=r"^(utc|local|ops)$")


class LoggingSettings(BaseModel):
    max_stored_entries: int = Field(ge=50, le=5000)
    max_visible_entries: int = Field(ge=10, le=500)
    max_detail_characters: int = Field(ge=500, le=20000)
    max_file_size_mb: int = Field(ge=1, le=100)


class NotificationSettings(BaseModel):
    channel: str = Field(pattern=r"^(email|slack|pager)$")
    digest: str = Field(pattern=r"^(realtime|hourly|daily)$")
    escalate_oncall: bool


class SecuritySettings(BaseModel):
    session_timeout_minutes: int = Field(ge=15, le=60)
    dual_approval_required: bool
    token_rotation_days: Literal[30, 60, 90]


class DataSettings(BaseModel):
    payload_redaction: bool
    export_window_utc: str = Field(pattern=r"^(00:00|02:00|04:00)$")
    audit_retention_days: Literal[30, 90, 365]


class ConnectorProviderPresetResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    auth_types: list[str]
    default_scopes: list[str]
    docs_url: str
    base_url: str


class ConnectorAuthPolicy(BaseModel):
    rotation_interval_days: Literal[30, 60, 90]
    reconnect_requires_approval: bool
    credential_visibility: Literal["masked", "admin_only"]


class ConnectorAuthConfigResponse(BaseModel):
    client_id: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=120)
    header_name: str | None = Field(default=None, max_length=120)
    scope_preset: str | None = Field(default=None, max_length=120)
    redirect_uri: str | None = Field(default=None, max_length=2000)
    expires_at: str | None = None
    has_refresh_token: bool = False
    client_secret_masked: str | None = None
    access_token_masked: str | None = None
    refresh_token_masked: str | None = None
    api_key_masked: str | None = None
    password_masked: str | None = None
    header_value_masked: str | None = None


class ConnectorRecordResponse(BaseModel):
    id: str
    provider: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(pattern=r"^(draft|pending_oauth|connected|needs_attention|expired|revoked)$")
    auth_type: str = Field(pattern=r"^(oauth2|bearer|api_key|basic|header)$")
    scopes: list[str] = Field(default_factory=list)
    base_url: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    docs_url: str | None = Field(default=None, max_length=2000)
    credential_ref: str | None = Field(default=None, max_length=255)
    created_at: str
    updated_at: str
    last_tested_at: str | None = None
    auth_config: ConnectorAuthConfigResponse = Field(default_factory=ConnectorAuthConfigResponse)


class ConnectorSettingsResponse(BaseModel):
    catalog: list[ConnectorProviderPresetResponse]
    records: list[ConnectorRecordResponse] = Field(default_factory=list)
    auth_policy: ConnectorAuthPolicy


class ConnectorAuthConfigUpdate(BaseModel):
    client_id: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=120)
    header_name: str | None = Field(default=None, max_length=120)
    scope_preset: str | None = Field(default=None, max_length=120)
    redirect_uri: str | None = Field(default=None, max_length=2000)
    expires_at: str | None = None
    has_refresh_token: bool | None = None
    client_secret_input: str | None = Field(default=None, max_length=500)
    access_token_input: str | None = Field(default=None, max_length=500)
    refresh_token_input: str | None = Field(default=None, max_length=500)
    api_key_input: str | None = Field(default=None, max_length=500)
    password_input: str | None = Field(default=None, max_length=500)
    header_value_input: str | None = Field(default=None, max_length=500)
    clear_credentials: bool = False


class ConnectorRecordUpdate(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    provider: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(default="draft", pattern=r"^(draft|pending_oauth|connected|needs_attention|expired|revoked)$")
    auth_type: str = Field(pattern=r"^(oauth2|bearer|api_key|basic|header)$")
    scopes: list[str] = Field(default_factory=list)
    base_url: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    docs_url: str | None = Field(default=None, max_length=2000)
    credential_ref: str | None = Field(default=None, max_length=255)
    created_at: str | None = None
    updated_at: str | None = None
    last_tested_at: str | None = None
    auth_config: ConnectorAuthConfigUpdate = Field(default_factory=ConnectorAuthConfigUpdate)


class ConnectorSettingsUpdate(BaseModel):
    records: list[ConnectorRecordUpdate] | None = None
    auth_policy: ConnectorAuthPolicy | None = None


class AppSettingsResponse(BaseModel):
    general: GeneralSettings
    logging: LoggingSettings
    notifications: NotificationSettings
    security: SecuritySettings
    data: DataSettings
    connectors: ConnectorSettingsResponse


class AppSettingsUpdate(BaseModel):
    general: GeneralSettings | None = None
    logging: LoggingSettings | None = None
    notifications: NotificationSettings | None = None
    security: SecuritySettings | None = None
    data: DataSettings | None = None
    connectors: ConnectorSettingsUpdate | None = None


class ConnectorActionResponse(BaseModel):
    ok: bool
    message: str
    connector: ConnectorRecordResponse


class ConnectorOAuthStartRequest(BaseModel):
    connector_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    redirect_uri: str = Field(min_length=1, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    client_id: str | None = Field(default=None, max_length=255)
    client_secret_input: str | None = Field(default=None, max_length=500)


class ConnectorOAuthStartResponse(BaseModel):
    connector: ConnectorRecordResponse
    authorization_url: str
    state: str
    expires_at: str
    code_challenge_method: Literal["S256"]


class ConnectorOAuthCallbackResponse(BaseModel):
    ok: bool
    message: str
    connector: ConnectorRecordResponse

