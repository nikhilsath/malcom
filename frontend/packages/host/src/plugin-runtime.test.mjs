import test from "node:test";
import assert from "node:assert/strict";

import { buildRouteCardModels, buildSurfaceModels, createPluginRegistry, resolvePluginSurface } from "./plugin-runtime.mjs";

const workspaceMount = { regions: ["topnav", "sidenav", "content"], navigationMode: "plugin", layout: "workspace" };
const mixedMount = {
  regions: ["topnav", "sidenav", "content"],
  navigationMode: "mixed",
  layout: "stack",
  supportsEmbeds: true
};

const pluginDefinitions = [
  {
    id: "dashboard",
    displayName: "Dashboard",
    capabilityKey: "dashboard",
    primaryRoutePath: "/dashboard",
    nav: [{ label: "Dashboard", order: 10, routePath: "/dashboard" }],
    mount: workspaceMount,
    routes: [
      { path: "/dashboard", mountMode: "native", title: "Dashboard", surfaceId: "dashboard-overview" },
      { path: "/dashboard/activity", mountMode: "native", title: "Recent Activity", surfaceId: "dashboard-activity" }
    ],
    surfaces: [
      {
        id: "dashboard-overview",
        title: "Dashboard",
        routePath: "/dashboard",
        summary: "Workspace summary surface with runtime status, queues, and operator focus areas.",
        kind: "overview",
        capabilityKey: "dashboard",
        mount: workspaceMount
      },
      {
        id: "dashboard-activity",
        title: "Recent Activity",
        routePath: "/dashboard/activity",
        summary: "Operational activity feed for recent runtime, automation, and connector events.",
        kind: "operations",
        capabilityKey: "dashboard_activity",
        mount: workspaceMount
      }
    ]
  },
  {
    id: "automations",
    displayName: "Automations",
    capabilityKey: "automations",
    primaryRoutePath: "/automations",
    nav: [{ label: "Automations", order: 20, routePath: "/automations" }],
    mount: mixedMount,
    routes: [
      { path: "/automations", mountMode: "native", title: "Automations", surfaceId: "automations-home" },
      { path: "/automations/runs", mountMode: "native", title: "Automation Runs", surfaceId: "automations-runs" },
      {
        path: "/automations/builder",
        mountMode: "iframe",
        title: "Workflow Builder",
        embedId: "workflow-builder",
        sessionBinding: "hosted-frontend",
        sessionTransition: "refresh_required",
        refreshesSession: true,
        capabilityKey: "workflow_builder_embed",
        surfaceId: "automations-builder"
      }
    ],
    surfaces: [
      {
        id: "automations-home",
        title: "Automations",
        routePath: "/automations",
        summary: "Automation landing surface for workspace automation status and quick actions.",
        kind: "overview",
        capabilityKey: "automations",
        mount: workspaceMount
      },
      {
        id: "automations-runs",
        title: "Automation Runs",
        routePath: "/automations/runs",
        summary: "Execution history and operator review surface for automation runs.",
        kind: "operations",
        capabilityKey: "automation_runs",
        mount: workspaceMount
      },
      {
        id: "automations-builder",
        title: "Workflow Builder",
        routePath: "/automations/builder",
        summary: "Legacy builder mount retained behind the hosted frontend shell while native surfaces expand.",
        kind: "builder",
        mountMode: "iframe",
        embedId: "workflow-builder",
        sessionBinding: "hosted-frontend",
        sessionTransition: "refresh_required",
        refreshesSession: true,
        capabilityKey: "workflow_builder_embed",
        mount: mixedMount
      }
    ]
  },
  {
    id: "apis",
    displayName: "APIs",
    capabilityKey: "apis",
    primaryRoutePath: "/apis",
    nav: [{ label: "APIs", order: 30, routePath: "/apis" }],
    mount: workspaceMount,
    routes: [
      { path: "/apis", mountMode: "native", title: "API Hub", surfaceId: "apis-overview" },
      { path: "/apis/inbound", mountMode: "native", title: "Inbound APIs", surfaceId: "apis-inbound" },
      { path: "/apis/outbound", mountMode: "native", title: "Outbound APIs", surfaceId: "apis-outbound" },
      { path: "/apis/webhooks", mountMode: "native", title: "Webhooks", surfaceId: "apis-webhooks" }
    ],
    surfaces: [
      {
        id: "apis-overview",
        title: "APIs",
        routePath: "/apis",
        summary: "API command center for the inbound, outbound, and webhook surfaces.",
        kind: "overview",
        capabilityKey: "apis",
        mount: workspaceMount
      },
      {
        id: "apis-inbound",
        title: "Inbound APIs",
        routePath: "/apis/inbound",
        summary: "Inbound API definitions and delivery visibility for hosted operators.",
        kind: "operations",
        capabilityKey: "inbound_apis",
        mount: workspaceMount
      },
      {
        id: "apis-outbound",
        title: "Outbound APIs",
        routePath: "/apis/outbound",
        summary: "Scheduled and continuous outbound API delivery surfaces.",
        kind: "operations",
        capabilityKey: "outbound_apis",
        mount: workspaceMount
      },
      {
        id: "apis-webhooks",
        title: "Webhooks",
        routePath: "/apis/webhooks",
        summary: "Webhook publisher surface for endpoints and recent deliveries.",
        kind: "operations",
        capabilityKey: "webhook_apis",
        mount: workspaceMount
      }
    ]
  },
  {
    id: "tools",
    displayName: "Tools",
    capabilityKey: "tools",
    primaryRoutePath: "/tools",
    nav: [{ label: "Tools", order: 40, routePath: "/tools" }],
    mount: workspaceMount,
    routes: [
      { path: "/tools", mountMode: "native", title: "Tool Hub", surfaceId: "tools-overview" },
      { path: "/tools/runtimes", mountMode: "native", title: "Runtime Status", surfaceId: "tools-runtimes" }
    ],
    surfaces: [
      {
        id: "tools-overview",
        title: "Tool Hub",
        routePath: "/tools",
        summary: "Hosted tool catalog surface for runtime-backed capabilities.",
        kind: "overview",
        capabilityKey: "tools",
        mount: workspaceMount
      },
      {
        id: "tools-runtimes",
        title: "Runtime Status",
        routePath: "/tools/runtimes",
        summary: "Runtime readiness and execution surface for local tools.",
        kind: "operations",
        capabilityKey: "tool_runtimes",
        mount: workspaceMount
      }
    ]
  },
  {
    id: "scripts",
    displayName: "Scripts",
    capabilityKey: "scripts",
    primaryRoutePath: "/scripts",
    nav: [{ label: "Scripts", order: 50, routePath: "/scripts" }],
    mount: workspaceMount,
    routes: [
      { path: "/scripts", mountMode: "native", title: "Script Library", surfaceId: "scripts-overview" },
      { path: "/scripts/executions", mountMode: "native", title: "Executions", surfaceId: "scripts-executions" }
    ],
    surfaces: [
      {
        id: "scripts-overview",
        title: "Script Library",
        routePath: "/scripts",
        summary: "Hosted script library surface for authored scripts and quick actions.",
        kind: "overview",
        capabilityKey: "scripts",
        mount: workspaceMount
      },
      {
        id: "scripts-executions",
        title: "Executions",
        routePath: "/scripts/executions",
        summary: "Execution history and status surface for hosted script runs.",
        kind: "operations",
        capabilityKey: "script_executions",
        mount: workspaceMount
      }
    ]
  },
  {
    id: "settings",
    displayName: "Settings",
    capabilityKey: "settings",
    primaryRoutePath: "/settings",
    nav: [{ label: "Settings", order: 60, routePath: "/settings" }],
    mount: workspaceMount,
    routes: [
      { path: "/settings", mountMode: "native", title: "Settings Hub", surfaceId: "settings-overview" },
      { path: "/settings/connectors", mountMode: "native", title: "Connectors", surfaceId: "settings-connectors" },
      { path: "/settings/storage", mountMode: "native", title: "Storage", surfaceId: "settings-storage" }
    ],
    surfaces: [
      {
        id: "settings-overview",
        title: "Settings Hub",
        routePath: "/settings",
        summary: "Workspace settings landing surface for hosted administration.",
        kind: "overview",
        capabilityKey: "settings",
        mount: workspaceMount
      },
      {
        id: "settings-connectors",
        title: "Connectors",
        routePath: "/settings/connectors",
        summary: "Connector onboarding and health surface for hosted administration.",
        kind: "operations",
        capabilityKey: "settings_connectors",
        mount: workspaceMount
      },
      {
        id: "settings-storage",
        title: "Storage",
        routePath: "/settings/storage",
        summary: "Storage destination surface for runtime-backed file locations.",
        kind: "operations",
        capabilityKey: "settings_storage",
        mount: workspaceMount
      }
    ]
  },
  {
    id: "docs",
    displayName: "Docs",
    capabilityKey: "docs",
    primaryRoutePath: "/docs",
    nav: [{ label: "Docs", order: 70, routePath: "/docs" }],
    mount: workspaceMount,
    routes: [
      { path: "/docs", mountMode: "native", title: "Docs Library", surfaceId: "docs-overview" },
      { path: "/docs/articles", mountMode: "native", title: "Articles", surfaceId: "docs-articles" }
    ],
    surfaces: [
      {
        id: "docs-overview",
        title: "Docs Library",
        routePath: "/docs",
        summary: "Documentation landing surface for hosted operators and contributors.",
        kind: "overview",
        capabilityKey: "docs",
        mount: workspaceMount
      },
      {
        id: "docs-articles",
        title: "Articles",
        routePath: "/docs/articles",
        summary: "Article browsing surface for indexed operational documentation.",
        kind: "operations",
        capabilityKey: "docs_articles",
        mount: workspaceMount
      }
    ]
  }
];

test("createPluginRegistry filters disabled capabilities", () => {
  const registry = createPluginRegistry({
    plugins: pluginDefinitions,
    capabilities: { dashboard: true, workflow_builder_embed: false }
  });

  assert.equal(registry.plugins.length, 7);
  assert.equal(registry.resolveRoute("/automations/builder").surfaceId, "automations-builder");
  assert.equal(registry.resolveRoute("/dashboard").pluginId, "dashboard");
  assert.equal(registry.resolveRoute("/automations").pluginId, "automations");
});

test("createPluginRegistry keeps iframe routes when capability is enabled", () => {
  const registry = createPluginRegistry({
    plugins: pluginDefinitions,
    capabilities: { dashboard: true, workflow_builder_embed: true }
  });

  const route = registry.resolveRoute("/automations/builder");
  assert.equal(route.mountMode, "iframe");
  assert.equal(route.embedId, "workflow-builder");
  assert.equal(route.sessionBinding, "hosted-frontend");
  assert.equal(route.sessionTransition, "refresh_required");
  assert.equal(route.refreshesSession, true);
  assert.equal(route.pluginId, "automations");
  assert.equal(route.surfaceId, "automations-builder");
});

test("createPluginRegistry exposes explicit nav route paths", () => {
  const registry = createPluginRegistry({
    plugins: pluginDefinitions,
    capabilities: { dashboard: true, workflow_builder_embed: true }
  });

  assert.deepEqual(
    registry.getNavItems().map((entry) => entry.path),
    ["/dashboard", "/automations", "/apis", "/tools", "/scripts", "/settings", "/docs"]
  );
});

test("createPluginRegistry resolves concrete hosted routes across the first-party feature surfaces", () => {
  const registry = createPluginRegistry({
    plugins: pluginDefinitions,
    capabilities: { dashboard: true, workflow_builder_embed: true }
  });

  assert.deepEqual(
    [
      "/dashboard/activity",
      "/automations/runs",
      "/apis/inbound",
      "/tools/runtimes",
      "/scripts/executions",
      "/settings/connectors",
      "/docs/articles"
    ].map((path) => {
      const route = registry.resolveRoute(path);
      return [path, route?.pluginId, route?.surfaceId];
    }),
    [
      ["/dashboard/activity", "dashboard", "dashboard-activity"],
      ["/automations/runs", "automations", "automations-runs"],
      ["/apis/inbound", "apis", "apis-inbound"],
      ["/tools/runtimes", "tools", "tools-runtimes"],
      ["/scripts/executions", "scripts", "scripts-executions"],
      ["/settings/connectors", "settings", "settings-connectors"],
      ["/docs/articles", "docs", "docs-articles"]
    ]
  );
});

test("buildRouteCardModels marks the first route as primary and preserves hosted builder metadata", () => {
  const routeCards = buildRouteCardModels(pluginDefinitions[1]);
  assert.equal(routeCards[0].isPrimary, true);
  assert.equal(routeCards[2].embedId, "workflow-builder");
  assert.equal(routeCards[2].sessionTransition, "refresh_required");
  assert.equal(routeCards[2].refreshesSession, true);
  assert.equal(routeCards[2].mountModeLabel, "Iframe embed");
  assert.equal(routeCards[2].surfaceId, "automations-builder");
});

test("buildSurfaceModels preserves concrete first-party surface metadata", () => {
  const surfaces = buildSurfaceModels(pluginDefinitions[5]);

  assert.deepEqual(
    surfaces.map((surface) => surface.path),
    ["/settings", "/settings/connectors", "/settings/storage"]
  );
  assert.equal(surfaces[1].kindLabel, "Operations");
  assert.equal(surfaces[1].mountMode, "native");
  assert.equal(surfaces[1].navigationMode, "plugin");
  assert.equal(surfaces[2].layout, "workspace");
});

test("resolvePluginSurface resolves hosted routes to the matching feature surface", () => {
  const surface = resolvePluginSurface(pluginDefinitions[6], "/docs/articles");

  assert.equal(surface.id, "docs-articles");
  assert.equal(surface.kind, "operations");
  assert.equal(surface.title, "Articles");
});
