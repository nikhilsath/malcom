"""Settings domain schemas for workspace configuration, connectors, and app-level settings."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    environment: Literal["live"]
    timezone: str = Field(pattern=r"^(utc|local|ops)$")


class LoggingSettings(BaseModel):
    max_stored_entries: int = Field(ge=50, le=5000)
    max_visible_entries: int = Field(ge=10, le=500)
    max_detail_characters: int = Field(ge=500, le=20000)
    max_file_size_mb: int = Field(ge=1, le=100)


class NotificationSettings(BaseModel):
    channel: str = Field(pattern=r"^(email|pager)$")
    digest: str = Field(pattern=r"^(realtime|hourly|daily)$")


class SecuritySettings(BaseModel):
    session_timeout_minutes: Literal[15, 30, 60, 120]
    dual_approval_required: bool
    token_rotation_days: Literal[30, 60, 90]


class DataSettings(BaseModel):
    payload_redaction: bool
    export_window_utc: str = Field(pattern=r"^(00:00|02:00|04:00)$")
    workflow_storage_path: str = Field(default="backend/data/workflows")


class AutomationSettings(BaseModel):
    default_tool_retries: int = Field(ge=0, le=10)


class ConnectorProviderPresetResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    auth_types: list[str]
    default_scopes: list[str]
    recommended_scopes: list[str] = Field(default_factory=list)
    docs_url: str
    base_url: str


class ConnectorProviderSetupFieldResponse(BaseModel):
    key: str
    label: str
    input_type: Literal["text", "password", "url"]
    required: bool = False
    secret: bool = False
    readonly: bool = False


class ConnectorProviderUiCopyResponse(BaseModel):
    eyebrow: str
    title: str
    description: str
    last_checked_empty: str


class ConnectorProviderActionLabelsResponse(BaseModel):
    save: str
    test: str
    connect: str
    reconnect: str
    refresh: str
    revoke: str


class ConnectorProviderMetadataResponse(BaseModel):
    id: str
    name: str
    onboarding_mode: Literal["oauth", "credentials"]
    oauth_supported: bool
    callback_supported: bool
    refresh_supported: bool
    revoke_supported: bool
    redirect_uri_required: bool
    redirect_uri_readonly: bool
    scopes_locked: bool
    default_redirect_path: str | None = None
    required_fields: list[str] = Field(default_factory=list)
    setup_fields: list[ConnectorProviderSetupFieldResponse] = Field(default_factory=list)
    ui_copy: ConnectorProviderUiCopyResponse
    action_labels: ConnectorProviderActionLabelsResponse
    status_messages: dict[str, str] = Field(default_factory=dict)


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
    request_auth_type: str = Field(pattern=r"^(none|bearer|basic|header)$")
    scopes: list[str] = Field(default_factory=list)
    base_url: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    docs_url: str | None = Field(default=None, max_length=2000)
    credential_ref: str | None = Field(default=None, max_length=255)
    created_at: str
    updated_at: str
    last_tested_at: str | None = None
    auth_config: ConnectorAuthConfigResponse = Field(default_factory=ConnectorAuthConfigResponse)


class SettingsOptionValueResponse(BaseModel):
    value: str
    label: str
    description: str | None = None


class ConnectorAuthPolicyMetadataResponse(BaseModel):
    rotation_intervals: list[SettingsOptionValueResponse]
    credential_visibility_options: list[SettingsOptionValueResponse]


class ConnectorMetadataResponse(BaseModel):
    statuses: list[SettingsOptionValueResponse]
    active_storage_statuses: list[str]
    auth_policy: ConnectorAuthPolicyMetadataResponse
    providers: list[ConnectorProviderMetadataResponse]


class ConnectorSettingsResponse(BaseModel):
    catalog: list[ConnectorProviderPresetResponse]
    records: list[ConnectorRecordResponse] = Field(default_factory=list)
    auth_policy: ConnectorAuthPolicy
    metadata: ConnectorMetadataResponse


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


class ConnectorCreateRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(default="draft", pattern=r"^(draft|pending_oauth|connected|needs_attention|expired|revoked)$")
    auth_type: str = Field(pattern=r"^(oauth2|bearer|api_key|basic|header)$")
    scopes: list[str] = Field(default_factory=list)
    base_url: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    docs_url: str | None = Field(default=None, max_length=2000)
    credential_ref: str | None = Field(default=None, max_length=255)
    auth_config: ConnectorAuthConfigUpdate = Field(default_factory=ConnectorAuthConfigUpdate)


class ConnectorUpdateRequest(BaseModel):
    provider: str | None = Field(default=None, pattern=r"^[a-z0-9_]+$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, pattern=r"^(draft|pending_oauth|connected|needs_attention|expired|revoked)$")
    auth_type: str | None = Field(default=None, pattern=r"^(oauth2|bearer|api_key|basic|header)$")
    scopes: list[str] | None = None
    base_url: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, max_length=120)
    docs_url: str | None = Field(default=None, max_length=2000)
    credential_ref: str | None = Field(default=None, max_length=255)
    last_tested_at: str | None = None
    auth_config: ConnectorAuthConfigUpdate | None = None


class ConnectorAuthPolicyUpdateRequest(BaseModel):
    auth_policy: ConnectorAuthPolicy


class ConnectorDeleteResponse(BaseModel):
    ok: bool
    message: str
    connector_id: str


class AppSettingsResponse(BaseModel):
    general: GeneralSettings
    logging: LoggingSettings
    notifications: NotificationSettings
    security: SecuritySettings
    data: DataSettings
    automation: AutomationSettings
    options: "AppSettingsOptionsResponse"


class AppSettingsOptionsResponse(BaseModel):
    notification_channels: list[SettingsOptionValueResponse]
    notification_digests: list[SettingsOptionValueResponse]
    data_export_windows: list[SettingsOptionValueResponse]


class AppSettingsUpdate(BaseModel):
    general: GeneralSettings | None = None
    logging: LoggingSettings | None = None
    notifications: NotificationSettings | None = None
    security: SecuritySettings | None = None
    data: DataSettings | None = None
    automation: AutomationSettings | None = None


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


class SettingsBackupMetadata(BaseModel):
    id: str
    filename: str
    created_at: str
    size_bytes: int | None = None
    path: str | None = None


class SettingsCreateBackupResponse(BaseModel):
    ok: bool
    message: str
    backup: SettingsBackupMetadata | None = None


class SettingsListBackupsResponse(BaseModel):
    directory: str | None = None
    backups: list[SettingsBackupMetadata] = Field(default_factory=list)


class SettingsBackupRestoreRequest(BaseModel):
    backup_id: str = Field(min_length=1)


class SettingsBackupRestoreResponse(BaseModel):
    ok: bool
    message: str
    restored_at: str | None = None


__all__ = [
    "AutomationSettings",
    "AppSettingsOptionsResponse",
    "AppSettingsResponse",
    "AppSettingsUpdate",
    "ConnectorActionResponse",
    "ConnectorAuthConfigResponse",
    "ConnectorAuthConfigUpdate",
    "ConnectorAuthPolicy",
    "ConnectorAuthPolicyUpdateRequest",
    "ConnectorCreateRequest",
    "ConnectorDeleteResponse",
    "ConnectorOAuthCallbackResponse",
    # Settings backup/restore schemas
    "SettingsBackupMetadata",
    "SettingsCreateBackupResponse",
    "SettingsListBackupsResponse",
    "SettingsBackupRestoreRequest",
    "SettingsBackupRestoreResponse",
    "ConnectorOAuthStartRequest",
    "ConnectorOAuthStartResponse",
    "ConnectorMetadataResponse",
    "ConnectorAuthPolicyMetadataResponse",
    "ConnectorProviderPresetResponse",
    "ConnectorProviderSetupFieldResponse",
    "ConnectorProviderUiCopyResponse",
    "ConnectorProviderActionLabelsResponse",
    "ConnectorProviderMetadataResponse",
    "ConnectorRecordResponse",
    "ConnectorSettingsResponse",
    "ConnectorUpdateRequest",
    "DataSettings",
    "GeneralSettings",
    "LoggingSettings",
    "NotificationSettings",
    "SecuritySettings",
    "SettingsOptionValueResponse",
]
