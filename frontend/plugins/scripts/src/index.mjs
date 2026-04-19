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

export const scriptsPlugin = {
  id: "scripts",
  displayName: "Scripts",
  description: "Reusable script library and validation workflows.",
  capabilityKey: "scripts",
  nav: [{ section: "Build", label: "Scripts", order: 50, routePath: "/scripts" }],
  routes: [
    { path: "/scripts", mountMode: "native", title: "Script Library" },
    { path: "/scripts/executions", mountMode: "native", title: "Executions" }
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
              title: "Operator",
              description: `${context.session.operator_name} is using the hosted script workspace with ${currentSurface.navigationMode} navigation.`
            },
            {
              title: "Route Scope",
              description: `${surfaces.length} script-focused surfaces are registered through the plugin manifest.`
            },
            {
              title: "Execution Model",
              description: `${currentSurface.mountModeLabel} with ${currentSurface.layout} layout expectations for script authoring and review.`
            }
          ])}
        </div>
      </section>
    `;
  }
};
