import {
  buildPluginCardModel,
  buildRouteCardModels,
  buildSurfaceModels,
  createPluginRegistry,
  resolvePluginSurface
} from "../../packages/host/src/plugin-runtime.mjs";
import { getFirstPartyPluginImplementation } from "../../plugins/index.mjs";

const STORAGE_KEY = "malcom.frontend.host.session";
const appRoot = document.getElementById("app");
let activeShellContext = null;
let cleanupActiveEmbedBridge = null;

const readStoredSession = () => {
  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY);
    return rawValue ? JSON.parse(rawValue) : null;
  } catch {
    return null;
  }
};

const writeStoredSession = (payload) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
};

const clearStoredSession = () => {
  window.localStorage.removeItem(STORAGE_KEY);
};

const resolvePath = () => {
  const pathname = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : window.location.pathname;
  return pathname && pathname !== "/" ? pathname : "/dashboard";
};

const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const requestJson = async (baseUrl, path, options = {}, accessToken) => {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.message || `Request failed with ${response.status}`);
  }
  return body;
};

const bindRouteTriggers = (root) => {
  root.querySelectorAll("[data-route-path]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.hash = button.dataset.routePath;
    });
  });
};

const resetActiveEmbedBridge = () => {
  if (typeof cleanupActiveEmbedBridge === "function") {
    cleanupActiveEmbedBridge();
  }
  cleanupActiveEmbedBridge = null;
};

const buildEmbedUrl = (embed, bootstrap) => {
  const url = new URL(embed.src, window.location.href);
  url.searchParams.set("platform_embed_id", embed.id);
  url.searchParams.set("platform_handshake_channel", embed.handshake_channel || "");
  url.searchParams.set("platform_session_id", bootstrap.session.id || "");
  url.searchParams.set("platform_client_name", bootstrap.session.client_name || "");
  url.searchParams.set("platform_session_type", bootstrap.session.session_type || "hosted-frontend");
  url.searchParams.set("platform_embed_mode", embed.metadata?.compatibility_mode || "legacy-backend-ui");
  return url.toString();
};

const getRouteEyebrow = (route, currentSurface) => {
  if (route.mountMode === "iframe") {
    return "Builder Launch Path";
  }
  return currentSurface?.kindLabel || "Native Hosted Route";
};

const getRouteDescription = (route, plugin, currentSurface) => {
  if (route.mountMode === "iframe") {
    return (
      currentSurface?.summary ||
      `Plugin-registry launch path for ${route.title || plugin.displayName}; the host resolves this route before mounting the builder embed contract.`
    );
  }
  return currentSurface?.summary || plugin.description;
};

const getSurfaceActionLabel = (surface, currentPath) => {
  if (surface.path === currentPath) {
    return "Current route";
  }
  return surface.mountMode === "iframe" ? "Launch builder" : "Open route";
};

const renderLogin = (statusMessage = "") => {
  activeShellContext = null;
  appRoot.innerHTML = `
    <main class="content">
      <section class="auth-card">
        <div class="eyebrow">Hosted Frontend Platform</div>
        <h1>Connect The Shell</h1>
        <p>This standalone host authenticates against the new platform contract and renders plugin-owned routes independently from the backend UI runtime.</p>
        <form id="auth-form" class="field-grid">
          <label>
            Backend URL
            <input id="backend-url" name="backendUrl" type="url" value="http://127.0.0.1:8000" required>
          </label>
          <label>
            Bootstrap Token
            <input id="bootstrap-token" name="bootstrapToken" type="password" autocomplete="off" required>
          </label>
          <label>
            Operator Name
            <input id="operator-name" name="operatorName" type="text" value="Operator" required>
          </label>
          <button class="primary" type="submit">Sign In</button>
        </form>
        <div id="auth-status" class="status">${escapeHtml(statusMessage)}</div>
      </section>
    </main>
  `;

  document.getElementById("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const backendUrl = document.getElementById("backend-url").value.trim();
    const bootstrapToken = document.getElementById("bootstrap-token").value.trim();
    const operatorName = document.getElementById("operator-name").value.trim();
    const status = document.getElementById("auth-status");
    status.textContent = "Signing in...";

    try {
      const tokenPayload = await requestJson(
        backendUrl,
        "/api/v1/platform/auth/tokens",
        {
          method: "POST",
          body: JSON.stringify({
            bootstrap_token: bootstrapToken,
            operator_name: operatorName,
            client_name: "hosted-frontend",
            requested_origin: window.location.origin === "null" ? null : window.location.origin
          })
        }
      );
      writeStoredSession({ backendUrl, ...tokenPayload });
      await renderShell();
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : String(error);
    }
  });
};

const renderRouteFallback = (container, plugin, route, registry, bootstrap) => {
  const routeCards = buildSurfaceModels(plugin)
    .map(
      (routeCard) => `
        <article class="card">
          <strong>${escapeHtml(routeCard.title)}</strong>
          <p>${escapeHtml(routeCard.summary)}</p>
          <p>${escapeHtml(routeCard.kindLabel)}</p>
          <p>${escapeHtml(routeCard.mountModeLabel)}</p>
          <p>${routeCard.embedId ? `Embed: ${escapeHtml(routeCard.embedId)}` : "Native hosted surface."}</p>
          <button class="primary" type="button" data-route-path="${escapeHtml(routeCard.path)}">Open route</button>
        </article>
      `
    )
    .join("");

  const pluginCards = registry.plugins
    .map((entry) => {
      const card = buildPluginCardModel(entry, bootstrap.capabilities);
      return `
        <article class="card">
          <strong>${escapeHtml(card.displayName)}</strong>
          <p>${escapeHtml(card.description)}</p>
          <p>Capability: ${escapeHtml(card.capabilityKey)}</p>
          <p>${card.enabled ? "Enabled in the hosted shell." : "Hidden by capability gating."}</p>
        </article>
      `;
    })
    .join("");

  container.innerHTML = `
    <section class="plugin-panel">
      <div class="eyebrow">Hosted Surface</div>
      <h2>${escapeHtml(route.title || plugin.displayName)}</h2>
      <p>${escapeHtml(plugin.description)}</p>
      <div class="cards">
        ${routeCards}
      </div>
      <div class="cards" style="margin-top: 20px;">
        ${pluginCards}
      </div>
    </section>
  `;
};

const renderShell = async () => {
  const sessionState = readStoredSession();
  if (!sessionState?.access_token || !sessionState?.backendUrl) {
    renderLogin();
    return;
  }

  let bootstrap;
  try {
    bootstrap = await requestJson(sessionState.backendUrl, "/api/v1/platform/bootstrap", {}, sessionState.access_token);
  } catch (error) {
    clearStoredSession();
    renderLogin(error instanceof Error ? error.message : String(error));
    return;
  }

  const pluginImplementations = Object.fromEntries(
    bootstrap.plugins.map((plugin) => [plugin.id, getFirstPartyPluginImplementation(plugin.id)])
  );
  const registry = createPluginRegistry({
    plugins: bootstrap.plugins.map((plugin) => ({
      id: plugin.id,
      displayName: plugin.display_name,
      description: plugin.description,
      capabilityKey: plugin.capability_key,
      surfaceGroup: plugin.surface_group,
      primaryRoutePath: plugin.primary_route_path,
      hostingModel: plugin.hosting_model,
      mountModes: plugin.mount_modes,
      mount: plugin.mount
        ? {
            regions: plugin.mount.regions,
            defaultRegion: plugin.mount.default_region,
            layout: plugin.mount.layout,
            navigationMode: plugin.mount.navigation_mode,
            sessionRequired: plugin.mount.session_required,
            supportsEmbeds: plugin.mount.supports_embeds
          }
        : null,
      metadata: plugin.metadata || {},
      nav: plugin.nav.map((entry) => ({
        section: entry.section,
        label: entry.label,
        order: entry.order,
        path: entry.path || entry.route_path || plugin.primary_route_path || null,
        routePath: entry.route_path || null
      })),
      routes: plugin.routes.map((route) => ({
        path: route.path,
        title: route.title,
        mountMode: route.mount_mode,
        embedId: route.embed_id || null,
        capabilityKey: route.capability_key || null,
        surfaceId: route.surface_id || null
      })),
      surfaces: (plugin.surfaces || []).map((surface) => ({
        id: surface.id,
        title: surface.title,
        routePath: surface.route_path,
        summary: surface.summary,
        kind: surface.kind,
        mountMode: surface.mount_mode,
        embedId: surface.embed_id || null,
        capabilityKey: surface.capability_key || null,
        mount: surface.mount
          ? {
              regions: surface.mount.regions,
              defaultRegion: surface.mount.default_region,
              layout: surface.mount.layout,
              navigationMode: surface.mount.navigation_mode,
              sessionRequired: surface.mount.session_required,
              supportsEmbeds: surface.mount.supports_embeds
            }
          : null
      }))
    })),
    capabilities: bootstrap.capabilities,
    implementations: pluginImplementations
  });

  activeShellContext = { registry, bootstrap, sessionState };

  appRoot.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand__eyebrow">Phase 1 Platform</div>
          <h1>Malcom Host</h1>
          <p>Plugins: ${registry.plugins.length}. Operator: ${escapeHtml(bootstrap.session.operator_name)}.</p>
        </div>
        <nav id="plugin-nav"></nav>
        <button id="sign-out" class="primary" type="button" style="margin-top: 20px;">Sign Out</button>
      </aside>
      <main class="content">
        <section class="panel hero">
          <div class="eyebrow">Hosted Frontend</div>
          <h2 id="route-title">Platform Home</h2>
          <p id="route-description">Separate shell, token auth, plugin routing, and iframe embeds are all active in this phase-1 runtime.</p>
        </section>
        <section id="route-root"></section>
      </main>
    </div>
  `;

  document.getElementById("sign-out").addEventListener("click", () => {
    clearStoredSession();
    renderLogin("Session cleared.");
  });

  const navRoot = document.getElementById("plugin-nav");
  const navGroups = new Map();
  for (const entry of registry.getNavItems()) {
    const groupKey = entry.section || "Other";
    if (!navGroups.has(groupKey)) {
      const wrapper = document.createElement("section");
      wrapper.className = "nav-group";
      wrapper.innerHTML = `<h2>${escapeHtml(groupKey)}</h2>`;
      navRoot.appendChild(wrapper);
      navGroups.set(groupKey, wrapper);
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nav-button";
    button.dataset.routePath = entry.path || "/";
    button.textContent = entry.label;
    button.addEventListener("click", () => {
      window.location.hash = button.dataset.routePath;
      void renderRoute();
    });
    navGroups.get(groupKey).appendChild(button);
  }

  await renderRoute();
};

const renderRoute = async () => {
  if (!activeShellContext) {
    return;
  }

  const { registry, bootstrap, sessionState } = activeShellContext;
  const routeRoot = document.getElementById("route-root");
  const routeTitle = document.getElementById("route-title");
  const routeDescription = document.getElementById("route-description");
  const resolvedPath = resolvePath();
  const route = registry.resolveRoute(resolvedPath) || registry.resolveRoute("/dashboard") || registry.plugins[0]?.routes?.[0];

  if (!route) {
    routeRoot.innerHTML = `
      <section class="plugin-panel">
        <div class="eyebrow">Hosted Frontend</div>
        <h2>Route Missing</h2>
        <p>No hosted route could be resolved from the current shell registry.</p>
      </section>
    `;
    return;
  }

  const plugin =
    registry.plugins.find((entry) => entry.id === route.pluginId) || {
      displayName: route.title || "Hosted Route",
      description: "A hosted frontend route.",
      routes: [route]
    };
  const pluginSurfaces = buildSurfaceModels(plugin);
  const currentSurface = resolvePluginSurface(plugin, route.path);
  const implementation = route.implementation;

  document.querySelectorAll(".nav-button").forEach((button) => {
    button.setAttribute("aria-current", button.dataset.routePath === route.path ? "page" : "false");
  });

  routeTitle.textContent = route.title || plugin.displayName;
  routeDescription.textContent = getRouteDescription(route, plugin, currentSurface);

  routeRoot.innerHTML = `
    <section id="host-route-panel" class="plugin-panel">
      <div id="host-route-eyebrow" class="eyebrow">${getRouteEyebrow(route, currentSurface)}</div>
      <h2>${escapeHtml(route.title || plugin.displayName)}</h2>
      <p>${escapeHtml(getRouteDescription(route, plugin, currentSurface))}</p>
      <div id="host-route-surfaces" class="cards">
        ${pluginSurfaces
          .map(
            (surface) => `
              <article class="card">
                <strong>${escapeHtml(surface.title)}</strong>
                <p>${escapeHtml(surface.summary)}</p>
                <p>${escapeHtml(`${surface.kindLabel} · ${surface.mountModeLabel}`)}</p>
                <button class="primary" type="button" data-route-path="${escapeHtml(surface.path)}">${getSurfaceActionLabel(surface, route.path)}</button>
              </article>
            `
          )
          .join("")}
      </div>
      <div id="route-surface"></div>
    </section>
  `;

  const surface = document.getElementById("route-surface");

  if (implementation?.render) {
    implementation.render(surface, {
      bootstrap,
      session: bootstrap.session,
      route,
      plugin,
      currentSurface,
      pluginSurfaces,
      availablePlugins: registry.plugins,
      buildPluginCardModel,
      buildRouteCardModels
    });
  } else {
    renderRouteFallback(surface, plugin, route, registry, bootstrap);
  }

  if (route.mountMode === "iframe") {
    resetActiveEmbedBridge();
    const embed = await requestJson(
      sessionState.backendUrl,
      `/api/v1/platform/embeds/${route.embedId}`,
      {},
      sessionState.access_token
    );
    const embedStatus = document.createElement("p");
    embedStatus.id = "platform-embed-status";
    embedStatus.textContent = "Waiting for builder embed handshake...";

    const embedPanel = document.createElement("section");
    embedPanel.className = "card";
    embedPanel.innerHTML = `
      <strong>${escapeHtml(embed.title || route.title || plugin.displayName)}</strong>
      <p>${escapeHtml(embed.metadata?.compatibility_mode ? `Compatibility mode: ${embed.metadata.compatibility_mode}` : "Compatibility mode is managed by the embed contract.")}</p>
      <p>${escapeHtml(embed.handshake_channel ? `Handshake channel: ${embed.handshake_channel}` : "Handshake metadata is provided by the platform contract.")}</p>
    `;
    embedPanel.appendChild(embedStatus);
    surface.appendChild(embedPanel);

    const frame = document.createElement("iframe");
    frame.src = buildEmbedUrl(embed, bootstrap);
    frame.title = embed.title || route.title || plugin.displayName;
    frame.setAttribute("loading", "lazy");
    surface.appendChild(frame);

    const handshakePayload = {
      embedId: embed.id,
      builderRoute: embed.builder_route || embed.metadata?.builder_route || null,
      session: {
        id: bootstrap.session.id,
        client_name: bootstrap.session.client_name,
        session_type: bootstrap.session.session_type
      },
      lifecycle: embed.lifecycle || {},
      compatibilityMode: embed.metadata?.compatibility_mode || "legacy-backend-ui"
    };

    const messageListener = (event) => {
      const data = event.data;
      if (!data || typeof data !== "object" || data.channel !== embed.handshake_channel) {
        return;
      }
      if (data.type === "ready") {
        embedStatus.textContent = "Builder embed is ready and acknowledged the hosted shell handshake.";
        return;
      }
      if (data.type === "resize" && data.detail?.height) {
        frame.style.minHeight = `${Math.max(Number(data.detail.height) || 0, 600)}px`;
        embedStatus.textContent = `Builder embed requested height ${Number(data.detail.height)}px.`;
        return;
      }
      if (data.type === "teardown") {
        embedStatus.textContent = "Builder embed reported teardown.";
      }
    };

    window.addEventListener("message", messageListener);
    frame.addEventListener("load", () => {
      embedStatus.textContent = "Builder iframe loaded. Sending hosted shell mount payload...";
      frame.contentWindow?.postMessage(
        {
          channel: embed.handshake_channel,
          type: "mount",
          payload: handshakePayload
        },
        "*"
      );
    });
    cleanupActiveEmbedBridge = () => window.removeEventListener("message", messageListener);
  } else {
    resetActiveEmbedBridge();
  }

  bindRouteTriggers(routeRoot);
};

window.addEventListener("hashchange", () => {
  void renderRoute();
});

void renderShell();
