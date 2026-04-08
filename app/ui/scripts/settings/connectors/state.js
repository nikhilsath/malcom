const createEmptyConnectorPayload = () => ({
  catalog: [],
  records: [],
  metadata: {
    statuses: [],
    active_storage_statuses: [],
    auth_policy: {
      rotation_intervals: [],
      credential_visibility_options: []
    }
  },
  auth_policy: {
    rotation_interval_days: 0,
    reconnect_requires_approval: false,
    credential_visibility: ""
  }
});

export const connectorState = {
  connectors: createEmptyConnectorPayload(),
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

const getConnectorPayload = () => {
  const storeConnectors = getStore().getConnectors?.();

  if (storeConnectors) {
    connectorState.connectors = storeConnectors;
    return storeConnectors;
  }

  return connectorState.connectors || createEmptyConnectorPayload();
};

export const getSelectedConnector = () => (
  getConnectorPayload()?.records?.find((record) => record.id === connectorState.selectedConnectorId) || null
);

export const isGoogleConnector = (record) => (record?.provider || "").toString().trim().toLowerCase() === "google";

export const canonicalizeProvider = (provider) => {
  return (provider || "").toString().trim().toLowerCase();
};

export const getProviderPreset = (providerId) => (
  getConnectorPayload()?.catalog?.find((item) => item.id === providerId) || null
);

export const getProviderMetadata = (providerId) => (
  getConnectorPayload()?.metadata?.providers?.find((item) => item.id === canonicalizeProvider(providerId)) || null
);

export const providerSupportsOauth = (providerId) => Boolean(getProviderMetadata(providerId)?.oauth_supported);

export const getProviderSetupMode = (providerId) => (
  getProviderMetadata(providerId)?.onboarding_mode || "credentials"
);

export const usesProviderSetupPanel = (recordOrProvider) => {
  const providerId = typeof recordOrProvider === "string"
    ? recordOrProvider
    : recordOrProvider?.provider;
  return ["google", "github", "notion", "trello"].includes(canonicalizeProvider(providerId));
};

export const getProviderActionLabel = (providerId, actionKey, fallback = "") => (
  getProviderMetadata(providerId)?.action_labels?.[actionKey] || fallback
);

export const getDefaultScopesForProvider = (providerId, preset = null) => {
  const presetScopes = preset?.recommended_scopes?.length ? preset.recommended_scopes : (preset?.default_scopes || []);
  if (presetScopes.length > 0) {
    return [...presetScopes];
  }
  return [];
};

export const getGoogleConnector = () => (
  getConnectorPayload()?.records?.find((record) => isGoogleConnector(record)) || null
);

export { createEmptyConnectorPayload };
