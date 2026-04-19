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

export const dashboardPlugin = {
  id: "dashboard",
  displayName: "Dashboard",
  description: "Runtime summary and operational overview.",
  capabilityKey: "dashboard",
  nav: [{ section: "Operations", label: "Dashboard", order: 10, routePath: "/dashboard" }],
  routes: [
    { path: "/dashboard", mountMode: "native", title: "Dashboard" },
    { path: "/dashboard/activity", mountMode: "native", title: "Recent Activity" }
  ],
  render(container, context) {
    const pluginSurfaces = buildSurfaceModels(context.plugin);
    const currentSurface = resolvePluginSurface(context.plugin, context.route.path) || pluginSurfaces[0];
    const visiblePlugins = context.availablePlugins || [];

    container.innerHTML = `
      <section class="plugin-panel">
        <div class="eyebrow">${escapeHtml(currentSurface.kindLabel)}</div>
        <h3>${escapeHtml(currentSurface.title)}</h3>
        <p>${escapeHtml(currentSurface.summary)}</p>
        <div class="cards">
          ${renderCardGrid([
            {
              title: "Current Surface",
              description: `${currentSurface.mountModeLabel} in the ${currentSurface.layout} layout with ${currentSurface.regions.join(", ")} regions.`
            },
            {
              title: "Operator Session",
              description: `${context.session.operator_name} is signed in to ${context.bootstrap.product.name} ${context.bootstrap.product.phase}.`
            },
            {
              title: "Hosted Coverage",
              description: `${pluginSurfaces.length} dashboard surfaces and ${visiblePlugins.length} visible first-party plugins are loaded from bootstrap.`
            }
          ])}
        </div>
        <div class="cards" style="margin-top: 20px;">
          ${renderCardGrid(pluginSurfaces.map((surface) => ({
            title: surface.title,
            description: `${surface.summary} ${surface.capabilityKey ? `Capability: ${surface.capabilityKey}.` : ""}`.trim(),
            actionPath: surface.path,
            actionLabel: surface.path === currentSurface.path ? "Current surface" : "Open surface"
          })))}
        </div>
        <div class="cards" style="margin-top: 20px;">
          ${renderCardGrid(visiblePlugins.map((plugin) => ({
            title: plugin.displayName,
            description: `${plugin.description} Capability: ${plugin.capabilityKey}.`,
            actionPath: plugin.routes[0]?.path || "/dashboard",
            actionLabel: "Open surface"
          })))}
        </div>
      </section>
    `;
  }
};
