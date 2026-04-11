"""Tool domain schemas for tool metadata, runtime configuration, and tool-specific APIs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .workers import RuntimeMachineResponse


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


class CoquiTtsOptionResponse(BaseModel):
    value: str
    label: str


class CoquiTtsToolRuntimeResponse(BaseModel):
    ready: bool
    command_available: bool
    message: str
    command_options: list[CoquiTtsOptionResponse] = Field(default_factory=list)
    model_options: list[CoquiTtsOptionResponse] = Field(default_factory=list)
    speaker_options: list[CoquiTtsOptionResponse] = Field(default_factory=list)
    language_options: list[CoquiTtsOptionResponse] = Field(default_factory=list)


class CoquiTtsToolResponse(BaseModel):
    tool_id: Literal["coqui-tts"]
    config: CoquiTtsToolConfigResponse
    runtime: CoquiTtsToolRuntimeResponse


class CoquiTtsToolUpdate(BaseModel):
    enabled: bool | None = None
    command: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    speaker: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=120)


class ImageMagicToolConfigResponse(BaseModel):
    enabled: bool
    target_worker_id: str | None = None
    command: str
    default_retries: int


class ImageMagicToolResponse(BaseModel):
    tool_id: Literal["image-magic"]
    config: ImageMagicToolConfigResponse
    machines: list[RuntimeMachineResponse]


class ImageMagicToolUpdate(BaseModel):
    enabled: bool | None = None
    target_worker_id: str | None = Field(default=None, max_length=120)
    command: str | None = Field(default=None, min_length=1, max_length=500)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class ImageMagicExecuteRequest(BaseModel):
    input_file: str = Field(min_length=1, max_length=2000)
    output_format: str = Field(min_length=1, max_length=20)
    resize: str | None = Field(default=None, max_length=255)
    output_filename: str | None = Field(default=None, max_length=255)


class ImageMagicExecuteResponse(BaseModel):
    ok: bool
    output_file_path: str
    worker_id: str
    worker_name: str


class WorkerRpcSmtpSyncRequest(BaseModel):
    enabled: bool
    bind_host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=0, le=65535)
    recipient_email: str | None = Field(default=None, max_length=320)


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


class ToolMetadataResponse(BaseModel):
    id: str
    name: str
    description: str


class ToolMetadataUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class ToolSchemaFieldResponse(BaseModel):
    key: str
    label: str
    type: str
    required: bool | None = None
    options: list[str] | None = None


class ToolDirectoryEntryResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    page_href: str
    inputs: list[ToolSchemaFieldResponse] = Field(default_factory=list)
    outputs: list[ToolSchemaFieldResponse] = Field(default_factory=list)


class ToolDirectoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    enabled: bool | None = None


__all__ = [
    "CoquiTtsToolConfigResponse",
    "CoquiTtsOptionResponse",
    "CoquiTtsToolResponse",
    "CoquiTtsToolRuntimeResponse",
    "CoquiTtsToolUpdate",
    "ImageMagicExecuteRequest",
    "ImageMagicExecuteResponse",
    "ImageMagicToolConfigResponse",
    "ImageMagicToolResponse",
    "ImageMagicToolUpdate",
    "LocalLlmChatMessage",
    "LocalLlmChatRequest",
    "LocalLlmChatResponse",
    "LocalLlmEndpointsResponse",
    "LocalLlmEndpointsUpdate",
    "LocalLlmPresetResponse",
    "LocalLlmToolConfigResponse",
    "LocalLlmToolResponse",
    "LocalLlmToolUpdate",
    "SmtpInboundIdentityResponse",
    "SmtpRelaySendRequest",
    "SmtpRelaySendResponse",
    "SmtpRuntimeMessageResponse",
    "SmtpSendTestRequest",
    "SmtpSendTestResponse",
    "SmtpToolConfigResponse",
    "SmtpToolResponse",
    "SmtpToolRuntimeResponse",
    "SmtpToolUpdate",
    "ToolDirectoryEntryResponse",
    "ToolDirectoryUpdate",
    "ToolSchemaFieldResponse",
    "ToolMetadataResponse",
    "ToolMetadataUpdate",
    "WorkerRpcSmtpSyncRequest",
]
