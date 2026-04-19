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

export const apisPlugin = {
  id: "apis",
  displayName: "APIs",
  description: "Inbound, outbound, and webhook integration management.",
  capabilityKey: "apis",
  nav: [{ section: "Build", label: "APIs", order: 30, routePath: "/apis" }],
  routes: [
    { path: "/apis", mountMode: "native", title: "API Hub" },
    { path: "/apis/inbound", mountMode: "native", title: "Inbound APIs" },
    { path: "/apis/outbound", mountMode: "native", title: "Outbound APIs" },
    { path: "/apis/webhooks", mountMode: "native", title: "Webhooks" }
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
              title: "API Workspace",
              description: `${context.bootstrap.product.name} exposes ${surfaces.length} hosted API surfaces through the platform bootstrap contract.`
            },
            {
              title: "Navigation Mode",
              description: `${currentSurface.navigationMode} navigation with ${currentSurface.regions.join(", ")} shell regions.`
            },
            {
              title: "Current Path",
              description: `${currentSurface.path} is resolved directly from the hosted plugin registry.`
            }
          ])}
        </div>
      </section>
    `;
  }
};
