"""API domain schemas for inbound, outgoing, and webhook resource contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

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


ApiResourceCreate: TypeAlias = Annotated[
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


OutgoingApiUpdate: TypeAlias = Annotated[
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


__all__ = [
    "ApiResourceBase",
    "ApiResourceCreate",
    "ApiResourceResponse",
    "ContinuousApiResourceCreate",
    "ContinuousApiResourceUpdate",
    "InboundApiCreate",
    "InboundApiCreated",
    "InboundApiDetail",
    "InboundApiResponse",
    "InboundApiUpdate",
    "InboundReceiveAccepted",
    "InboundSecretResponse",
    "IncomingApiResourceCreate",
    "OutgoingApiDetailResponse",
    "OutgoingApiResourceBase",
    "OutgoingApiTestRequest",
    "OutgoingApiTestResponse",
    "OutgoingApiUpdate",
    "OutgoingAuthConfig",
    "ScheduledApiResourceCreate",
    "ScheduledApiResourceUpdate",
    "WebhookApiResourceCreate",
]