import { normalizePluginManifests } from "../../sdk/src/index.mjs";

export const describeRouteMountMode = (mountMode) => (mountMode === "iframe" ? "Iframe embed" : "Native route");

export const describeSurfaceKind = (kind) => {
  const labels = {
    overview: "Overview",
    operations: "Operations",
    catalog: "Catalog",
    manager: "Manager",
    library: "Library",
    settings: "Settings",
    reference: "Reference",
    builder: "Builder"
  };
  return labels[kind] || "Surface";
};

export const buildRouteCardModels = (plugin) =>
  plugin.routes.map((route, index) => ({
    ...route,
    title: route.title || route.path,
    mountModeLabel: describeRouteMountMode(route.mountMode),
    isPrimary: index === 0
  }));

export const buildSurfaceModels = (plugin) => {
  const routes = Array.isArray(plugin.routes) ? plugin.routes : [];
  const routeEntries = new Map(routes.map((route, index) => [route.path, { ...route, routeIndex: index }]));
  const sourceSurfaces = Array.isArray(plugin.surfaces) && plugin.surfaces.length > 0
    ? plugin.surfaces
    : routes.map((route, index) => ({
        id: route.surfaceId || `${plugin.id}-route-${index}`,
        title: route.title || route.path,
        routePath: route.path,
        summary: plugin.description,
        kind: index === 0 ? "overview" : "manager",
        mountMode: route.mountMode,
        embedId: route.embedId || null,
        capabilityKey: route.capabilityKey || null,
        mount: plugin.mount || {}
      }));

  return sourceSurfaces
    .map((surface, index) => {
      const path = surface.routePath || surface.route_path;
      const matchedRoute = routeEntries.get(path) || routes[index] || null;
      const mount = surface.mount || plugin.mount || {};
      const mountMode = matchedRoute?.mountMode || surface.mountMode || surface.mount_mode || "native";
      const capabilityKey = surface.capabilityKey || surface.capability_key || matchedRoute?.capabilityKey || null;

      return {
        id: surface.id || matchedRoute?.surfaceId || `${plugin.id}-surface-${index}`,
        title: surface.title || matchedRoute?.title || path || plugin.displayName,
        path: path || matchedRoute?.path || plugin.primaryRoutePath || routes[0]?.path || "/",
        summary: surface.summary || plugin.description,
        kind: surface.kind || "overview",
        kindLabel: describeSurfaceKind(surface.kind || "overview"),
        mountMode,
        mountModeLabel: describeRouteMountMode(mountMode),
        embedId: matchedRoute?.embedId || surface.embedId || surface.embed_id || null,
        capabilityKey,
        navigationMode: mount.navigationMode || mount.navigation_mode || plugin.mount?.navigationMode || plugin.mount?.navigation_mode || "plugin",
        layout: mount.layout || plugin.mount?.layout || "workspace",
        regions: mount.regions || plugin.mount?.regions || [],
        supportsEmbeds: mount.supportsEmbeds || mount.supports_embeds || plugin.mount?.supportsEmbeds || plugin.mount?.supports_embeds || false,
        isPrimary: (path || matchedRoute?.path) === plugin.primaryRoutePath || index === 0
      };
    })
    .sort((left, right) => {
      const leftIndex = routeEntries.get(left.path)?.routeIndex ?? Number.MAX_SAFE_INTEGER;
      const rightIndex = routeEntries.get(right.path)?.routeIndex ?? Number.MAX_SAFE_INTEGER;
      return leftIndex - rightIndex;
    });
};

export const resolvePluginSurface = (plugin, pathname) => buildSurfaceModels(plugin).find((surface) => surface.path === pathname) || null;

export const createPluginRegistry = ({ plugins, capabilities = {}, implementations = {} }) => {
  const normalizedPlugins = normalizePluginManifests(plugins);
  const visiblePlugins = normalizedPlugins.filter((plugin) => capabilities[plugin.capabilityKey] !== false);
  const routeEntries = new Map();

  for (const plugin of visiblePlugins) {
    for (const route of plugin.routes) {
      if (routeEntries.has(route.path)) {
        throw new Error(`Duplicate plugin route registered for ${route.path}.`);
      }
      routeEntries.set(route.path, {
        ...route,
        pluginId: plugin.id,
        displayName: plugin.displayName,
        implementation: implementations[plugin.id] || null
      });
    }
  }

  return {
    plugins: visiblePlugins,
    capabilities,
    implementations,
    getNavItems() {
      return visiblePlugins.flatMap((plugin) =>
        (plugin.nav || []).map((entry) => ({
          pluginId: plugin.id,
          capabilityKey: plugin.capabilityKey,
          path: entry.path || entry.routePath || plugin.routes[0]?.path || "/",
          ...entry
        }))
      );
    },
    resolveRoute(pathname) {
      return routeEntries.get(pathname) || null;
    }
  };
};

export const buildPluginCardModel = (plugin, capabilities) => ({
  id: plugin.id,
  displayName: plugin.displayName,
  description: plugin.description,
  capabilityKey: plugin.capabilityKey,
  enabled: capabilities[plugin.capabilityKey] !== false,
  routes: plugin.routes
});
