import test from "node:test";
import assert from "node:assert/strict";

import { normalizePluginManifest, validatePluginManifest } from "./index.mjs";

const workspaceMount = { regions: ["topnav", "sidenav", "content"], navigationMode: "plugin", layout: "workspace" };

test("validatePluginManifest accepts a real first-party plugin contract", () => {
  const errors = validatePluginManifest({
    id: "settings",
    displayName: "Settings",
    capabilityKey: "settings",
    primaryRoutePath: "/settings",
    nav: [
      { label: "Connectors", order: 20, routePath: "/settings/connectors" },
      { label: "Settings", order: 10, routePath: "/settings" }
    ],
    mount: workspaceMount,
    routes: [
      { path: "/settings", mountMode: "native", title: "Settings Hub", surfaceId: "settings-overview" },
      { path: "/settings/connectors", mountMode: "native", title: "Connectors", surfaceId: "settings-connectors" }
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
        summary: "Connector onboarding and workspace connector management surface.",
        kind: "operations",
        capabilityKey: "settings_connectors",
        mount: workspaceMount
      }
    ]
  });
  assert.deepEqual(errors, []);
});

test("validatePluginManifest rejects iframe routes without an embed id", () => {
  const errors = validatePluginManifest({
    id: "automations",
    displayName: "Automations",
    routes: [{ path: "/automations/builder", mountMode: "iframe" }]
  });
  assert.equal(errors.length, 1);
  assert.match(errors[0], /embedId/);
});

test("normalizePluginManifest tracks mixed route mount modes", () => {
  const manifest = normalizePluginManifest({
    id: "automations",
    displayName: "Automations",
    primaryRoutePath: "/automations",
    nav: [
      { label: "Builder", order: 20, routePath: "/automations/builder" },
      { label: "Overview", order: 10, routePath: "/automations" }
    ],
    mount: { regions: ["topnav", "sidenav", "content"], navigationMode: "mixed", layout: "stack", supportsEmbeds: true },
    routes: [
      { path: "/automations", mountMode: "native", title: "Automations", surfaceId: "automations-home" },
      {
        path: "/automations/builder",
        mountMode: "iframe",
        title: "Workflow Builder",
        embedId: "workflow-builder",
        surfaceId: "automations-builder"
      }
    ],
    surfaces: [
      {
        id: "automations-home",
        title: "Automations",
        routePath: "/automations",
        summary: "Automation landing surface for hosted operators.",
        kind: "overview",
        capabilityKey: "automations",
        mount: workspaceMount
      },
      {
        id: "automations-builder",
        title: "Workflow Builder",
        routePath: "/automations/builder",
        summary: "Legacy builder route retained behind the hosted frontend shell.",
        kind: "builder",
        mountMode: "iframe",
        embedId: "workflow-builder",
        capabilityKey: "workflow_builder_embed",
        mount: { regions: ["topnav", "sidenav", "content"], navigationMode: "mixed", layout: "stack", supportsEmbeds: true }
      }
    ]
  });

  assert.equal(manifest.primaryRoutePath, "/automations");
  assert.deepEqual(manifest.mountModes, ["native", "iframe"]);
  assert.deepEqual(
    manifest.nav.map((entry) => [entry.label, entry.routePath]),
    [["Overview", "/automations"], ["Builder", "/automations/builder"]]
  );
  assert.deepEqual(
    manifest.routes.map((route) => [route.path, route.mountMode, route.surfaceId ?? null]),
    [["/automations", "native", "automations-home"], ["/automations/builder", "iframe", "automations-builder"]]
  );
  assert.deepEqual(
    manifest.surfaces.map((surface) => [surface.id, surface.routePath]),
    [["automations-home", "/automations"], ["automations-builder", "/automations/builder"]]
  );
});

test("normalizePluginManifest preserves surface mount metadata for native hosted plugins", () => {
  const manifest = normalizePluginManifest({
    id: "settings",
    displayName: "Settings",
    primaryRoutePath: "/settings",
    nav: [{ label: "Storage", order: 20, routePath: "/settings/storage" }, { label: "Settings", order: 10, routePath: "/settings" }],
    mount: workspaceMount,
    routes: [
      { path: "/settings", mountMode: "native", title: "Settings Hub", surfaceId: "settings-overview" },
      { path: "/settings/storage", mountMode: "native", title: "Storage", surfaceId: "settings-storage" }
    ],
    surfaces: [
      {
        id: "settings-overview",
        title: "Settings Hub",
        routePath: "/settings",
        summary: "Hosted settings overview surface.",
        kind: "overview",
        capabilityKey: "settings",
        mount: workspaceMount
      },
      {
        id: "settings-storage",
        title: "Storage",
        routePath: "/settings/storage",
        summary: "Hosted storage destination management surface.",
        kind: "operations",
        capabilityKey: "settings_storage",
        mount: workspaceMount
      }
    ]
  });

  assert.equal(manifest.primaryRoutePath, "/settings");
  assert.deepEqual(
    manifest.nav.map((entry) => [entry.label, entry.routePath]),
    [["Settings", "/settings"], ["Storage", "/settings/storage"]]
  );
  assert.equal(manifest.surfaces[1].mount.navigationMode, "plugin");
  assert.equal(manifest.surfaces[1].mount.layout, "workspace");
});
