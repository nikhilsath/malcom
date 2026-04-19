from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import Request

from backend.schemas.platform import (
    FrontendSessionSummary,
    PlatformAuthMetadata,
    PlatformBootstrapResponse,
    PlatformEmbedDescriptor,
    PlatformEmbedLifecycleMetadata,
    PlatformFeatureSurface,
    PlatformFrontendMetadata,
    PlatformMountRequirements,
    PlatformNavContribution,
    PlatformPluginManifest,
    PlatformPluginCatalogResponse,
    PlatformProductMetadata,
    PlatformSessionLifecycleMetadata,
    PlatformRouteContribution,
)
from backend.services.platform_auth import get_frontend_access_ttl_minutes, get_frontend_bootstrap_token, get_frontend_refresh_ttl_days


def get_frontend_host_url() -> str | None:
    raw_value = os.getenv("MALCOM_FRONTEND_HOST_URL", "").strip().rstrip("/")
    return raw_value or None


def get_frontend_allowed_origins() -> list[str]:
    configured = [
        value.strip().rstrip("/")
        for value in os.getenv("MALCOM_FRONTEND_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]
    if configured:
        return configured
    host_url = get_frontend_host_url()
    if host_url:
        split = urlsplit(host_url)
        if split.scheme and split.netloc:
            return [f"{split.scheme}://{split.netloc}"]
    return ["*"]


def _build_mount_requirements(
    *,
    regions: list[str],
    default_region: str = "content",
    layout: str = "workspace",
    navigation_mode: str = "plugin",
    supports_embeds: bool = False,
) -> PlatformMountRequirements:
    return PlatformMountRequirements(
        regions=regions,
        default_region=default_region,
        layout=layout,
        navigation_mode=navigation_mode,
        session_required=True,
        supports_embeds=supports_embeds,
    )


def _build_feature_surface(
    *,
    surface_id: str,
    title: str,
    route_path: str,
    summary: str,
    kind: str,
    mount: PlatformMountRequirements,
    mount_mode: str = "native",
    capability_key: str | None = None,
    embed_id: str | None = None,
) -> PlatformFeatureSurface:
    return PlatformFeatureSurface(
        id=surface_id,
        title=title,
        route_path=route_path,
        summary=summary,
        kind=kind,
        mount_mode=mount_mode,
        capability_key=capability_key,
        embed_id=embed_id,
        mount=mount,
    )


def _build_route_contribution(surface: PlatformFeatureSurface) -> PlatformRouteContribution:
    return PlatformRouteContribution(
        path=surface.route_path,
        title=surface.title,
        mount_mode=surface.mount_mode,
        embed_id=surface.embed_id,
        capability_key=surface.capability_key,
        surface_id=surface.id,
    )


def _build_plugin_metadata(
    *,
    surface_group: str,
    primary_route_path: str,
    hosting_model: str,
    routes: list[PlatformRouteContribution],
    surfaces: list[PlatformFeatureSurface],
    mount: PlatformMountRequirements,
) -> dict[str, object]:
    native_route_count = sum(1 for route in routes if route.mount_mode == "native")
    iframe_route_count = sum(1 for route in routes if route.mount_mode == "iframe")
    return {
        "surface_group": surface_group,
        "primary_route_path": primary_route_path,
        "hosting_model": hosting_model,
        "route_mount_modes": sorted({route.mount_mode for route in routes}),
        "route_count": len(routes),
        "native_route_count": native_route_count,
        "iframe_route_count": iframe_route_count,
        "surface_ids": [surface.id for surface in surfaces],
        "surface_kinds": [surface.kind for surface in surfaces],
        "default_mount_regions": mount.regions,
        "navigation_mode": mount.navigation_mode,
        "supports_embeds": mount.supports_embeds,
    }


def _build_plugin_manifest(
    *,
    plugin_id: str,
    display_name: str,
    description: str,
    capability_key: str,
    surface_group: str,
    primary_route_path: str,
    hosting_model: str,
    mount: PlatformMountRequirements,
    nav_section: str,
    nav_icon: str,
    nav_order: int,
    surfaces: list[PlatformFeatureSurface],
) -> PlatformPluginManifest:
    routes = [_build_route_contribution(surface) for surface in surfaces]
    mount_modes = sorted({surface.mount_mode for surface in surfaces})
    nav_entries = [
        PlatformNavContribution(
            section=nav_section,
            label=display_name,
            route_path=primary_route_path,
            icon=nav_icon,
            order=nav_order,
        )
    ]
    # Expose dedicated builder routes in host navigation during migration.
    for surface in surfaces:
        if surface.kind != "builder" or surface.route_path == primary_route_path:
            continue
        nav_entries.append(
            PlatformNavContribution(
                section=nav_section,
                label=surface.title,
                route_path=surface.route_path,
                icon=nav_icon,
                order=nav_order + 1,
            )
        )
    return PlatformPluginManifest(
        id=plugin_id,
        display_name=display_name,
        version="0.1.0",
        description=description,
        owner="malcom",
        capability_key=capability_key,
        surface_group=surface_group,
        primary_route_path=primary_route_path,
        hosting_model=hosting_model,
        mount_modes=mount_modes,
        mount=mount,
        nav=nav_entries,
        routes=routes,
        surfaces=surfaces,
        metadata=_build_plugin_metadata(
            surface_group=surface_group,
            primary_route_path=primary_route_path,
            hosting_model=hosting_model,
            routes=routes,
            surfaces=surfaces,
            mount=mount,
        ),
    )


def list_platform_plugins() -> list[PlatformPluginManifest]:
    workspace_mount = _build_mount_requirements(regions=["topnav", "sidenav", "content"], navigation_mode="plugin")
    article_mount = _build_mount_requirements(regions=["topnav", "sidenav", "content"], layout="article", navigation_mode="plugin")
    builder_mount = _build_mount_requirements(
        regions=["topnav", "sidenav", "content"],
        layout="stack",
        navigation_mode="mixed",
        supports_embeds=True,
    )
    admin_mount = _build_mount_requirements(regions=["topnav", "sidenav", "content"], navigation_mode="plugin")

    return [
        _build_plugin_manifest(
            plugin_id="dashboard",
            display_name="Dashboard",
            description="Runtime summary, activity signals, and operational overview surfaces.",
            capability_key="dashboard",
            surface_group="workspace",
            primary_route_path="/dashboard",
            hosting_model="native",
            mount=workspace_mount,
            nav_section="Operations",
            nav_icon="grid",
            nav_order=10,
            surfaces=[
                _build_feature_surface(
                    surface_id="dashboard-overview",
                    title="Dashboard",
                    route_path="/dashboard",
                    summary="Workspace summary surface with runtime status, queues, and operator focus areas.",
                    kind="overview",
                    mount=workspace_mount,
                    capability_key="dashboard",
                ),
                _build_feature_surface(
                    surface_id="dashboard-activity",
                    title="Recent Activity",
                    route_path="/dashboard/activity",
                    summary="Operational activity feed for recent runtime, automation, and connector events.",
                    kind="operations",
                    mount=workspace_mount,
                    capability_key="dashboard_activity",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="automations",
            display_name="Automations",
            description="Automation landing, execution monitoring, library views, and builder launch surfaces.",
            capability_key="automations",
            surface_group="workspace",
            primary_route_path="/automations",
            hosting_model="mixed",
            mount=builder_mount,
            nav_section="Build",
            nav_icon="workflow",
            nav_order=20,
            surfaces=[
                _build_feature_surface(
                    surface_id="automations-home",
                    title="Automations",
                    route_path="/automations",
                    summary="Automation landing surface for workspace automation status and quick actions.",
                    kind="overview",
                    mount=workspace_mount,
                    capability_key="automations",
                ),
                _build_feature_surface(
                    surface_id="automations-runs",
                    title="Automation Runs",
                    route_path="/automations/runs",
                    summary="Execution history and operator review surface for automation runs.",
                    kind="operations",
                    mount=workspace_mount,
                    capability_key="automation_runs",
                ),
                _build_feature_surface(
                    surface_id="automations-library",
                    title="Automation Library",
                    route_path="/automations/library",
                    summary="Library surface for saved automations, templates, and reusable entry points.",
                    kind="library",
                    mount=workspace_mount,
                    capability_key="automation_library",
                ),
                _build_feature_surface(
                    surface_id="automations-builder",
                    title="Workflow Builder",
                    route_path="/automations/builder",
                    summary="Legacy builder mount retained behind the hosted frontend shell while native surfaces expand.",
                    kind="builder",
                    mount=builder_mount,
                    mount_mode="iframe",
                    capability_key="workflow_builder_embed",
                    embed_id="workflow-builder",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="apis",
            display_name="APIs",
            description="Inbound, outbound, and webhook management surfaces.",
            capability_key="apis",
            surface_group="workspace",
            primary_route_path="/apis",
            hosting_model="native",
            mount=workspace_mount,
            nav_section="Build",
            nav_icon="plug",
            nav_order=30,
            surfaces=[
                _build_feature_surface(
                    surface_id="apis-overview",
                    title="APIs",
                    route_path="/apis",
                    summary="API operations summary for inbound, outbound, and webhook workflows.",
                    kind="overview",
                    mount=workspace_mount,
                    capability_key="apis",
                ),
                _build_feature_surface(
                    surface_id="apis-inbound",
                    title="Inbound APIs",
                    route_path="/apis/inbound",
                    summary="Inbound API management surface for accepted payloads and event monitoring.",
                    kind="manager",
                    mount=workspace_mount,
                    capability_key="apis_inbound",
                ),
                _build_feature_surface(
                    surface_id="apis-outbound",
                    title="Outbound APIs",
                    route_path="/apis/outbound",
                    summary="Outbound delivery management surface for scheduled and continuous API calls.",
                    kind="manager",
                    mount=workspace_mount,
                    capability_key="apis_outbound",
                ),
                _build_feature_surface(
                    surface_id="apis-webhooks",
                    title="Webhooks",
                    route_path="/apis/webhooks",
                    summary="Webhook publisher surface for events, verification, and delivery history.",
                    kind="manager",
                    mount=workspace_mount,
                    capability_key="apis_webhooks",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="tools",
            display_name="Tools",
            description="Runtime tool catalog and machine capability management surfaces.",
            capability_key="tools",
            surface_group="workspace",
            primary_route_path="/tools",
            hosting_model="native",
            mount=workspace_mount,
            nav_section="Build",
            nav_icon="wrench",
            nav_order=40,
            surfaces=[
                _build_feature_surface(
                    surface_id="tools-catalog",
                    title="Tools",
                    route_path="/tools",
                    summary="Tool catalog surface for managed runtimes and registered capabilities.",
                    kind="catalog",
                    mount=workspace_mount,
                    capability_key="tools",
                ),
                _build_feature_surface(
                    surface_id="tools-runtimes",
                    title="Runtime Status",
                    route_path="/tools/runtimes",
                    summary="Runtime status surface for managed tool services and operational readiness.",
                    kind="operations",
                    mount=workspace_mount,
                    capability_key="tool_runtimes",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="scripts",
            display_name="Scripts",
            description="Script library and execution-oriented surfaces.",
            capability_key="scripts",
            surface_group="workspace",
            primary_route_path="/scripts",
            hosting_model="native",
            mount=workspace_mount,
            nav_section="Build",
            nav_icon="code",
            nav_order=50,
            surfaces=[
                _build_feature_surface(
                    surface_id="scripts-library",
                    title="Scripts",
                    route_path="/scripts",
                    summary="Script library surface for saved code assets and editing entry points.",
                    kind="library",
                    mount=workspace_mount,
                    capability_key="scripts",
                ),
                _build_feature_surface(
                    surface_id="scripts-executions",
                    title="Executions",
                    route_path="/scripts/executions",
                    summary="Execution history surface for script runs, outputs, and operator follow-up.",
                    kind="operations",
                    mount=workspace_mount,
                    capability_key="script_executions",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="settings",
            display_name="Settings",
            description="Workspace, connector, storage, and operator configuration surfaces.",
            capability_key="settings",
            surface_group="admin",
            primary_route_path="/settings",
            hosting_model="native",
            mount=admin_mount,
            nav_section="Admin",
            nav_icon="settings",
            nav_order=60,
            surfaces=[
                _build_feature_surface(
                    surface_id="settings-workspace",
                    title="Settings",
                    route_path="/settings",
                    summary="Workspace settings surface for environment-level configuration and access policies.",
                    kind="settings",
                    mount=admin_mount,
                    capability_key="settings",
                ),
                _build_feature_surface(
                    surface_id="settings-connectors",
                    title="Connectors",
                    route_path="/settings/connectors",
                    summary="Connector management surface for provider status, onboarding, and credential health.",
                    kind="manager",
                    mount=admin_mount,
                    capability_key="settings_connectors",
                ),
                _build_feature_surface(
                    surface_id="settings-storage",
                    title="Storage",
                    route_path="/settings/storage",
                    summary="Storage destination surface for local folders, repos, and external destinations.",
                    kind="manager",
                    mount=admin_mount,
                    capability_key="settings_storage",
                ),
            ],
        ),
        _build_plugin_manifest(
            plugin_id="docs",
            display_name="Docs",
            description="Documentation and operator guidance surfaces.",
            capability_key="docs",
            surface_group="reference",
            primary_route_path="/docs",
            hosting_model="native",
            mount=article_mount,
            nav_section="Admin",
            nav_icon="book",
            nav_order=70,
            surfaces=[
                _build_feature_surface(
                    surface_id="docs-home",
                    title="Docs",
                    route_path="/docs",
                    summary="Documentation landing surface for operator guidance and product reference.",
                    kind="reference",
                    mount=article_mount,
                    capability_key="docs",
                ),
                _build_feature_surface(
                    surface_id="docs-articles",
                    title="Articles",
                    route_path="/docs/articles",
                    summary="Structured article surface for browsable product and operator documentation.",
                    kind="reference",
                    mount=article_mount,
                    capability_key="docs_articles",
                ),
            ],
        ),
    ]


def build_platform_capabilities() -> dict[str, bool]:
    capabilities = {
        "plugin_sdk": True,
        "hosted_frontend": True,
        "legacy_ui_compatibility": True,
    }
    for plugin in list_platform_plugins():
        capabilities[plugin.capability_key] = True
        for route in plugin.routes:
            if route.capability_key:
                capabilities[route.capability_key] = True
        for surface in plugin.surfaces:
            if surface.capability_key:
                capabilities[surface.capability_key] = True
    return capabilities


def build_platform_bootstrap(request: Request, *, session: FrontendSessionSummary) -> PlatformBootstrapResponse:
    return PlatformBootstrapResponse(
        product=PlatformProductMetadata(
            name="Malcom",
            version="0.1.0",
            phase="hosted-frontend-first-party",
            legacy_ui_compatibility=True,
        ),
        session=session,
        frontend=PlatformFrontendMetadata(
            api_base_url=str(request.base_url).rstrip("/"),
            frontend_host_url=get_frontend_host_url(),
            allowed_origins=get_frontend_allowed_origins(),
            shell_regions=["topnav", "sidenav", "content"],
            theme_tokens={
                "brand_deep": "#341475",
                "brand_primary": "#441D81",
                "brand_main": "#5631BA",
                "accent_sky": "#4FA8F4",
            },
        ),
        auth=PlatformAuthMetadata(
            access_token_ttl_minutes=get_frontend_access_ttl_minutes(),
            refresh_token_ttl_days=get_frontend_refresh_ttl_days(),
            bootstrap_token_required=bool(get_frontend_bootstrap_token()),
            session_lifecycle=PlatformSessionLifecycleMetadata(
                access_token_ttl_minutes=get_frontend_access_ttl_minutes(),
                refresh_token_ttl_days=get_frontend_refresh_ttl_days(),
                bootstrap_token_required=bool(get_frontend_bootstrap_token()),
            ),
        ),
        plugins=list_platform_plugins(),
        capabilities=build_platform_capabilities(),
    )


def build_platform_plugin_catalog() -> PlatformPluginCatalogResponse:
    return PlatformPluginCatalogResponse(plugins=list_platform_plugins(), capabilities=build_platform_capabilities())


def build_platform_embed_descriptor(request: Request, *, embed_id: str) -> PlatformEmbedDescriptor:
    if embed_id != "workflow-builder":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown platform embed '{embed_id}'.")
    base_url = str(request.base_url).rstrip("/")
    return PlatformEmbedDescriptor(
        id="workflow-builder",
        title="Workflow Builder",
        src=f"{base_url}/automations/builder.html",
        builder_route="/automations/builder.html",
        handshake_channel="malcom.platform.embed.workflow-builder",
        capabilities=["workflow_builder_embed", "platform:embed:read"],
        lifecycle=PlatformEmbedLifecycleMetadata(),
        metadata={
            "compatibility_mode": "legacy-backend-ui",
            "builder_route": "/automations/builder.html",
            "session_binding": "platform-session",
            "lifecycle_events": ["mount", "ready", "resize", "teardown"],
            "notes": "The builder surface remains mounted from the legacy backend UI while hosted frontend routes expand around it.",
        },
    )


__all__ = [
    "build_platform_bootstrap",
    "build_platform_capabilities",
    "build_platform_embed_descriptor",
    "build_platform_plugin_catalog",
    "get_frontend_allowed_origins",
    "get_frontend_host_url",
    "list_platform_plugins",
]
