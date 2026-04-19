export const PLATFORM_ROUTE_MOUNT_MODES = new Set(["native", "iframe"]);

export const validatePluginManifest = (manifest) => {
  const errors = [];
  if (!manifest || typeof manifest !== "object") {
    return ["Plugin manifest must be an object."];
  }

  if (!manifest.id || typeof manifest.id !== "string") {
    errors.push("Plugin manifest must include an id.");
  }
  if (!manifest.displayName || typeof manifest.displayName !== "string") {
    errors.push(`Plugin ${manifest.id || "<unknown>"} must include a displayName.`);
  }
  if (!Array.isArray(manifest.routes) || manifest.routes.length === 0) {
    errors.push(`Plugin ${manifest.id || "<unknown>"} must declare at least one route.`);
  }
  for (const route of manifest.routes || []) {
    if (!route.path || typeof route.path !== "string") {
      errors.push(`Plugin ${manifest.id || "<unknown>"} has a route without a path.`);
      continue;
    }
    if (!PLATFORM_ROUTE_MOUNT_MODES.has(route.mountMode)) {
      errors.push(`Plugin ${manifest.id || "<unknown>"} route ${route.path} has unsupported mount mode ${route.mountMode}.`);
    }
    if (route.mountMode === "iframe" && !route.embedId) {
      errors.push(`Plugin ${manifest.id || "<unknown>"} route ${route.path} must declare embedId for iframe mode.`);
    }
  }

  return errors;
};

export const assertValidPluginManifest = (manifest) => {
  const errors = validatePluginManifest(manifest);
  if (errors.length > 0) {
    throw new Error(errors.join(" "));
  }
  return manifest;
};

export const normalizePluginManifest = (manifest) => {
  assertValidPluginManifest(manifest);
  return {
    ...manifest,
    nav: [...(manifest.nav || [])].sort((left, right) => (left.order || 0) - (right.order || 0)),
    routes: [...manifest.routes],
    mountModes: [...new Set(manifest.routes.map((route) => route.mountMode))]
  };
};

export const normalizePluginManifests = (manifests) => manifests.map((manifest) => normalizePluginManifest(manifest));
