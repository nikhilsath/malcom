import { buildSurfaceModels, resolvePluginSurface } from "../../../packages/host/src/plugin-runtime.mjs";

const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const renderCardGrid = (items) =>
  items
    .map(
      (item) => `
        <article class="card">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.description)}</p>
          ${item.actionPath ? `<button class="primary" type="button" data-route-path="${escapeHtml(item.actionPath)}">${escapeHtml(item.actionLabel || "Open")}</button>` : ""}
        </article>
      `
    )
    .join("");

export const settingsPlugin = {
  id: "settings",
  displayName: "Settings",
  description: "Workspace, connector, and access controls.",
  capabilityKey: "settings",
  nav: [{ section: "Admin", label: "Settings", order: 60, routePath: "/settings" }],
  routes: [
    { path: "/settings", mountMode: "native", title: "Settings Hub" },
    { path: "/settings/connectors", mountMode: "native", title: "Connectors" },
    { path: "/settings/storage", mountMode: "native", title: "Storage" }
  ],
  render(container, context) {
    const surfaces = buildSurfaceModels(context.plugin);
    const currentSurface = resolvePluginSurface(context.plugin, context.route.path) || surfaces[0];

    container.innerHTML = `
      <section class="plugin-panel">
        <div class="eyebrow">${escapeHtml(currentSurface.kindLabel)}</div>
        <h3>${escapeHtml(currentSurface.title)}</h3>
        <p>${escapeHtml(currentSurface.summary)}</p>
        <div class="cards">
          ${renderCardGrid(surfaces.map((surface) => ({
            title: surface.title,
            description: `${surface.summary} ${surface.capabilityKey ? `Capability: ${surface.capabilityKey}.` : ""}`.trim(),
            actionPath: surface.path,
            actionLabel: surface.path === currentSurface.path ? "Current surface" : "Open surface"
          })))}
        </div>
        <div class="cards" style="margin-top: 20px;">
          ${renderCardGrid([
            {
              title: "Admin Scope",
              description: `${context.plugin.surfaceGroup} surfaces run with ${currentSurface.layout} layout requirements and ${currentSurface.navigationMode} navigation.`
            },
            {
              title: "Capability Gate",
              description: `${currentSurface.capabilityKey || context.plugin.capabilityKey} controls visibility for the current settings route.`
            },
            {
              title: "Session Binding",
              description: `${context.session.client_name} session ${context.session.id} is active for hosted admin workflows.`
            }
          ])}
        </div>
      </section>
    `;
  }
};
