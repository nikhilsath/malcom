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

export const docsPlugin = {
  id: "docs",
  displayName: "Docs",
  description: "Product and ecosystem documentation surface.",
  capabilityKey: "docs",
  nav: [{ section: "Admin", label: "Docs", order: 70, routePath: "/docs" }],
  routes: [
    { path: "/docs", mountMode: "native", title: "Docs Library" },
    { path: "/docs/articles", mountMode: "native", title: "Articles" }
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
              title: "Reference Layout",
              description: `${currentSurface.layout} layout keeps documentation surfaces aligned with the hosted article experience.`
            },
            {
              title: "Route Registry",
              description: `${surfaces.length} docs surfaces are exposed through the hosted plugin manifest.`
            },
            {
              title: "Audience",
              description: `${context.bootstrap.product.name} ${context.bootstrap.product.phase} uses docs as an operator and product reference surface.`
            }
          ])}
        </div>
      </section>
    `;
  }
};
