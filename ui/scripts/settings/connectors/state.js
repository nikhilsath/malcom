import { GOOGLE_RECOMMENDED_SCOPES } from "./dom.js";

export const connectorState = {
  settings: null,
  selectedConnectorId: null,
  pendingOauth: {},
  detailReturnFocusElement: null
};

export const getStore = () => window.MalcomLogStore;

export const cloneValue = (value) => JSON.parse(JSON.stringify(value));

export const slugifyConnectorId = (value) => (
  value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 100)
  || `connector_${Date.now()}`
);

export const titleCase = (value) => value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());

export const getSelectedConnector = () => (
  connectorState.settings?.connectors?.records?.find((record) => record.id === connectorState.selectedConnectorId) || null
);

export const isGoogleConnector = (record) => {
  const provider = (record?.provider || "").toString().trim().toLowerCase();
  return provider === "google" || provider.startsWith("google_");
};

export const canonicalizeProvider = (provider) => {
  const normalized = (provider || "").toString().trim().toLowerCase();
  return normalized.startsWith("google_") ? "google" : normalized;
};

export const getProviderPreset = (providerId) => (
  connectorState.settings?.connectors?.catalog?.find((item) => item.id === providerId) || null
);

export const getDefaultScopesForProvider = (providerId, preset = null) => {
  const presetScopes = preset?.default_scopes || [];
  if (presetScopes.length > 0) {
    return [...presetScopes];
  }
  if (providerId === "google") {
    return [...GOOGLE_RECOMMENDED_SCOPES];
  }
  return [];
};

export const getGoogleConnector = () => (
  connectorState.settings?.connectors?.records?.find((record) => isGoogleConnector(record)) || null
);
