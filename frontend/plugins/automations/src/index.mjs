import { buildRouteCardModels } from "../../../packages/host/src/plugin-runtime.mjs";

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

const formatRouteDetails = (entry) =>
  `${entry.path} · ${entry.mountModeLabel}${entry.embedId ? ` · ${entry.embedId}` : " · native host"}`;

const buildRouteCards = (routeCards, currentPath) =>
  routeCards.map((entry) => ({
    title: entry.title,
    description: formatRouteDetails(entry),
    actionPath: entry.path,
    actionLabel:
      entry.path === currentPath
        ? "Current route"
        : entry.mountMode === "iframe"
          ? "Launch builder"
          : "Open route"
  }));

export const automationsPlugin = {
  id: "automations",
  displayName: "Automations",
  description: "Automation overview and workflow-builder launch surface.",
  capabilityKey: "automations",
  nav: [
    { section: "Build", label: "Automations", order: 20, routePath: "/automations" },
    { section: "Build", label: "Builder", order: 21, routePath: "/automations/builder" }
  ],
  routes: [
    { path: "/automations", mountMode: "native", title: "Automation Overview" },
    { path: "/automations/builder", mountMode: "iframe", title: "Workflow Builder", embedId: "workflow-builder" }
  ],
  render(container, context) {
    const route = context.route || this.routes[0];
    const routeCards = buildRouteCardModels(this);
    const nativeRoutes = routeCards.filter((entry) => entry.mountMode !== "iframe");
    const builderRoute = routeCards.find((entry) => entry.mountMode === "iframe");
    const automationsEnabled = context.bootstrap?.capabilities?.automations !== false;

    if (route.mountMode === "iframe") {
      container.innerHTML = `
        <section id="automations-builder-panel" class="plugin-panel">
          <div id="automations-builder-eyebrow" class="eyebrow">Iframe-backed Builder Path</div>
          <h3 id="automations-builder-title">Workflow Builder Launch</h3>
          <p id="automations-builder-summary">This route is the distinct builder launch path for automations. The host resolves it through the plugin registry, then mounts the platform embed contract for the existing workflow canvas.</p>
          <div id="automations-builder-highlights" class="cards">
            ${renderCardGrid([
              {
                title: "Return To Landing",
                description: "Go back to the native automations landing route for summaries, route ownership, and hosted navigation.",
                actionPath: "/automations",
                actionLabel: "Open landing"
              },
              {
                title: "Builder Route",
                description: builderRoute
                  ? formatRouteDetails(builderRoute)
                  : "The builder launch path is supplied by the automations plugin manifest."
              },
              {
                title: "Embed Lifecycle",
                description: "The host keeps builder access behind the iframe route while native automations pages expand independently of the legacy canvas."
              }
            ])}
          </div>
          <div id="automations-builder-routes" class="cards" style="margin-top: 20px;">
            ${renderCardGrid(buildRouteCards(routeCards, route.path))}
          </div>
        </section>
      `;
      return;
    }

    container.innerHTML = `
      <section id="automations-native-panel" class="plugin-panel">
        <div id="automations-native-eyebrow" class="eyebrow">Native Hosted Route</div>
        <h3 id="automations-native-title">Automation Landing</h3>
        <p id="automations-native-summary">This hosted route is the automation landing flow. It keeps native automation navigation in the shell while handing the existing canvas off to a separate builder launch path.</p>
        <div id="automations-native-highlights" class="cards">
          ${renderCardGrid([
            {
              title: "Launch Builder",
              description: builderRoute
                ? `Open ${builderRoute.title} when you need the legacy workflow canvas and embed-backed editor.`
                : "The builder route remains available through the plugin manifest when iframe compatibility is required.",
              actionPath: "/automations/builder",
              actionLabel: "Launch builder"
            },
            {
              title: "Native Routes",
              description: `${nativeRoutes.length} hosted route${nativeRoutes.length === 1 ? "" : "s"} currently stay native in the shell so automation navigation is distinct from the builder handoff.`
            },
            {
              title: "Capability State",
              description: automationsEnabled
                ? "Automations are enabled for this hosted session, so both the landing route and builder launch path are available."
                : "Automations are currently capability-gated for this session."
            }
          ])}
        </div>
        <div id="automations-native-flow" class="cards" style="margin-top: 20px;">
          ${renderCardGrid([
            {
              title: "Automation Entry",
              description: "Use this landing route to review hosted automation ownership before jumping into the embedded builder."
            },
            {
              title: "Builder Handoff",
              description: builderRoute
                ? `The plugin registry keeps ${builderRoute.path} as a dedicated iframe-backed launch path instead of folding it into the native landing screen.`
                : "The plugin manifest separates the iframe-backed builder from native hosted routes."
            }
          ])}
        </div>
        <div id="automations-native-routes" class="cards" style="margin-top: 20px;">
          ${renderCardGrid(buildRouteCards(routeCards, route.path))}
        </div>
      </section>
    `;
  }
};
