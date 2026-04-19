"""Hosted-frontend platform schemas for token auth, bootstrap contracts, and plugin manifests."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FrontendSessionSummary(BaseModel):
    id: str
    operator_name: str = Field(min_length=1, max_length=120)
    client_name: str = Field(min_length=1, max_length=120)
    status: Literal["active", "revoked", "expired"]
    session_type: Literal["hosted-frontend"] = "hosted-frontend"
    requested_origin: str | None = None
    requested_scopes: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    issued_at: str
    access_expires_at: str
    refresh_expires_at: str
    last_used_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrontendAuthTokenCreateRequest(BaseModel):
    bootstrap_token: str = Field(min_length=1, max_length=500)
    operator_name: str = Field(min_length=1, max_length=120)
    client_name: str = Field(default="hosted-frontend", min_length=1, max_length=120)
    requested_origin: str | None = Field(default=None, max_length=2000)
    requested_scopes: list[str] = Field(default_factory=list)


class FrontendAuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=500)
    client_name: str | None = Field(default=None, max_length=120)


class FrontendAuthRevokeRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=500)


class FrontendAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"
    access_expires_at: str
    refresh_expires_at: str
    session: FrontendSessionSummary


class PlatformRouteContribution(BaseModel):
    path: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=120)
    mount_mode: Literal["native", "iframe"] = "native"
    embed_id: str | None = Field(default=None, max_length=120)
    capability_key: str | None = Field(default=None, max_length=120)
    surface_id: str | None = Field(default=None, max_length=120)


class PlatformMountRequirements(BaseModel):
    regions: list[Literal["topnav", "sidenav", "content", "modal"]] = Field(default_factory=list)
    default_region: Literal["content", "modal"] = "content"
    layout: Literal["workspace", "split-pane", "stack", "article"] = "workspace"
    navigation_mode: Literal["host", "plugin", "mixed"] = "host"
    session_required: bool = True
    supports_embeds: bool = False


class PlatformFeatureSurface(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    route_path: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=500)
    kind: Literal["overview", "operations", "catalog", "manager", "library", "settings", "reference", "builder"]
    mount_mode: Literal["native", "iframe"] = "native"
    embed_id: str | None = Field(default=None, max_length=120)
    capability_key: str | None = Field(default=None, max_length=120)
    mount: PlatformMountRequirements


class PlatformNavContribution(BaseModel):
    section: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    route_path: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=40)
    order: int = 0


class PlatformSessionLifecycleMetadata(BaseModel):
    session_mode: Literal["refreshable"] = "refreshable"
    rotation_strategy: Literal["rolling"] = "rolling"
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    bootstrap_token_required: bool


class PlatformPluginManifest(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=120)
    capability_key: str = Field(min_length=1, max_length=120)
    surface_group: Literal["workspace", "admin", "reference"]
    primary_route_path: str = Field(min_length=1, max_length=255)
    hosting_model: Literal["native", "mixed"] = "native"
    mount_modes: list[Literal["native", "iframe"]] = Field(default_factory=list)
    mount: PlatformMountRequirements
    nav: list[PlatformNavContribution] = Field(default_factory=list)
    routes: list[PlatformRouteContribution] = Field(default_factory=list)
    surfaces: list[PlatformFeatureSurface] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformEmbedLifecycleMetadata(BaseModel):
    session_binding: Literal["platform-session"] = "platform-session"
    compatibility_mode: Literal["legacy-backend-ui"] = "legacy-backend-ui"
    refreshes_session: bool = True
    lifecycle_events: list[Literal["mount", "ready", "resize", "teardown"]] = Field(default_factory=lambda: ["mount", "ready", "resize", "teardown"])


class PlatformEmbedDescriptor(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    src: str = Field(min_length=1, max_length=4000)
    builder_route: str = Field(min_length=1, max_length=255)
    mount_mode: Literal["iframe"] = "iframe"
    origin_policy: Literal["same-origin", "cross-origin-token"] = "cross-origin-token"
    handshake_channel: str = Field(min_length=1, max_length=120)
    capabilities: list[str] = Field(default_factory=list)
    lifecycle: PlatformEmbedLifecycleMetadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformProductMetadata(BaseModel):
    name: str
    version: str
    phase: str
    legacy_ui_compatibility: bool


class PlatformFrontendMetadata(BaseModel):
    api_base_url: str
    frontend_host_url: str | None = None
    allowed_origins: list[str] = Field(default_factory=list)
    shell_regions: list[str] = Field(default_factory=list)
    theme_tokens: dict[str, str] = Field(default_factory=dict)


class PlatformAuthMetadata(BaseModel):
    token_type: Literal["Bearer"] = "Bearer"
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    bootstrap_token_required: bool
    session_lifecycle: PlatformSessionLifecycleMetadata


class PlatformBootstrapResponse(BaseModel):
    product: PlatformProductMetadata
    session: FrontendSessionSummary
    frontend: PlatformFrontendMetadata
    auth: PlatformAuthMetadata
    plugins: list[PlatformPluginManifest] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)


class PlatformPluginCatalogResponse(BaseModel):
    plugins: list[PlatformPluginManifest] = Field(default_factory=list)
    capabilities: dict[str, bool] = Field(default_factory=dict)


__all__ = [
    "FrontendAuthRefreshRequest",
    "FrontendAuthRevokeRequest",
    "FrontendAuthTokenCreateRequest",
    "FrontendAuthTokenResponse",
    "FrontendSessionSummary",
    "PlatformAuthMetadata",
    "PlatformBootstrapResponse",
    "PlatformEmbedDescriptor",
    "PlatformEmbedLifecycleMetadata",
    "PlatformFeatureSurface",
    "PlatformFrontendMetadata",
    "PlatformMountRequirements",
    "PlatformNavContribution",
    "PlatformPluginCatalogResponse",
    "PlatformPluginManifest",
    "PlatformProductMetadata",
    "PlatformSessionLifecycleMetadata",
    "PlatformRouteContribution",
]
