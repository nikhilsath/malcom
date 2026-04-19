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

export const toolsPlugin = {
  id: "tools",
  displayName: "Tools",
  description: "Managed runtime tool configuration.",
  capabilityKey: "tools",
  nav: [{ section: "Build", label: "Tools", order: 40, routePath: "/tools" }],
  routes: [
    { path: "/tools", mountMode: "native", title: "Tool Hub" },
    { path: "/tools/runtimes", mountMode: "native", title: "Runtime Status" }
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
              title: "Hosting Model",
              description: `${context.plugin.hostingModel} hosted tool surfaces with ${context.plugin.mount?.layout || currentSurface.layout} layout requirements.`
            },
            {
              title: "Runtime Regions",
              description: `${currentSurface.regions.join(", ")} regions are requested by the runtime contract for this surface.`
            },
            {
              title: "Catalog Scope",
              description: `${context.plugin.metadata?.surface_group || context.plugin.surfaceGroup || "workspace"} scope with ${context.plugin.metadata?.route_count || surfaces.length} registered hosted routes.`
            }
          ])}
        </div>
      </section>
    `;
  }
};
