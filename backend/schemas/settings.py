"""Settings domain schemas for workspace configuration, connectors, and app-level settings."""

from __future__ import annotations

from typing import Any, Literal

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


class DataSettings(BaseModel):
    payload_redaction: bool
    export_window_utc: str = Field(pattern=r"^(00:00|02:00|04:00)$")
    workflow_storage_path: str = "backend/data/workflows"


class AutomationSettings(BaseModel):
    default_tool_retries: int = Field(ge=0, le=10)


class SecuritySettings(BaseModel):
    session_timeout_minutes: Literal[30, 60, 120, 480]
    dual_approval_required: bool
    token_rotation_days: Literal[30, 60, 90]


class ProxySettings(BaseModel):
    domain: str = Field(default="", max_length=255)
    http_port: int = Field(ge=1, le=65535)
    https_port: int = Field(ge=1, le=65535)
    enabled: bool


class SettingsProxyTestRequest(BaseModel):
    domain: str = Field(default="", max_length=255)
    http_port: int = Field(ge=1, le=65535)
    https_port: int = Field(ge=1, le=65535)
    enabled: bool


class SettingsProxyTestCheck(BaseModel):
    scheme: str
    target: str
    reachable: bool
    status_code: int | None = None
    detail: str | None = None


class SettingsProxyTestResponse(BaseModel):
    ok: bool
    message: str
    checks: list[SettingsProxyTestCheck] = Field(default_factory=list)


class AppSettingsOptionsResponse(BaseModel):
    notification_channels: list[dict[str, str]] = Field(default_factory=list)
    notification_digests: list[dict[str, str]] = Field(default_factory=list)


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
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorAuthConfigUpdate(BaseModel):
    client_id: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=120)
    host: str | None = Field(default=None, max_length=255)
    port: str | None = Field(default=None, max_length=10)
    database: str | None = Field(default=None, max_length=255)
    sslmode: str | None = Field(default=None, max_length=50)
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


class ConnectorCreateRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(default="draft", pattern=r"^(draft|pending_oauth|connected|needs_attention|expired|revoked)$")
    auth_type: str = Field(default="bearer", pattern=r"^(oauth2|bearer|api_key|basic|header)$")
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


class ConnectorSettingsUpdate(BaseModel):
    records: list[ConnectorRecordUpdate] | None = None
    auth_policy: ConnectorAuthPolicy | None = None


class ConnectorAuthPolicyUpdateRequest(BaseModel):
    auth_policy: ConnectorAuthPolicy


class AppSettingsResponse(BaseModel):
    general: GeneralSettings
    logging: LoggingSettings
    notifications: NotificationSettings
    data: DataSettings
    automation: AutomationSettings
    security: SecuritySettings
    proxy: ProxySettings
    options: AppSettingsOptionsResponse


class AppSettingsUpdate(BaseModel):
    general: GeneralSettings | None = None
    logging: LoggingSettings | None = None
    notifications: NotificationSettings | None = None
    data: DataSettings | None = None
    automation: AutomationSettings | None = None
    security: SecuritySettings | None = None
    proxy: ProxySettings | None = None


class ConnectorActionResponse(BaseModel):
    ok: bool
    message: str
    connector: ConnectorRecordResponse


class ConnectorDeleteResponse(BaseModel):
    ok: bool
    message: str
    connector_id: str


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
    filename: str
    path: str
    created_at: str
    size_bytes: int


class SettingsCreateBackupResponse(BaseModel):
    ok: bool
    message: str
    backup: SettingsBackupMetadata | None = None


class SettingsListBackupsResponse(BaseModel):
    directory: str
    backups: list[SettingsBackupMetadata]


class SettingsBackupRestoreRequest(BaseModel):
    backup_id: str


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
    "ConnectorOAuthStartRequest",
    "ConnectorOAuthStartResponse",
    "ConnectorProviderPresetResponse",
    "ConnectorRecordResponse",
    "ConnectorRecordUpdate",
    "ConnectorUpdateRequest",
    "ConnectorSettingsResponse",
    "ConnectorSettingsUpdate",
    "DataSettings",
    "GeneralSettings",
    "LoggingSettings",
    "NotificationSettings",
    "ProxySettings",
    "SecuritySettings",
    "SettingsBackupMetadata",
    "SettingsBackupRestoreRequest",
    "SettingsBackupRestoreResponse",
    "SettingsCreateBackupResponse",
    "SettingsListBackupsResponse",
    "SettingsProxyTestCheck",
    "SettingsProxyTestRequest",
    "SettingsProxyTestResponse",
]