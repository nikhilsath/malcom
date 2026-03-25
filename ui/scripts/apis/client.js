const normalizeResourceEntries = (response, fallbackType) => {
  const entries = Array.isArray(response)
    ? response
    : Array.isArray(response?.items)
      ? response.items
      : [];

  return entries.map((entry) => ({
    ...entry,
    type: entry?.type || fallbackType
  }));
};

export const createApiClient = () => ({
  async list() {
    const response = await window.Malcom?.requestJson?.("/api/v1/inbound");
    return normalizeResourceEntries(response, "incoming");
  },
  async create(payload) {
    return window.Malcom?.requestJson?.("/api/v1/apis", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  async testOutgoingDelivery(payload) {
    return window.Malcom?.requestJson?.("/api/v1/apis/test-delivery", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  async detail(apiId) {
    return window.Malcom?.requestJson?.(`/api/v1/inbound/${apiId}`);
  },
  async update(apiId, payload) {
    return window.Malcom?.requestJson?.(`/api/v1/inbound/${apiId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  async rotateSecret(apiId) {
    return window.Malcom?.requestJson?.(`/api/v1/inbound/${apiId}/rotate-secret`, {
      method: "POST"
    });
  },
  async listOutgoingScheduled() {
    const response = await window.Malcom?.requestJson?.("/api/v1/outgoing/scheduled");
    return normalizeResourceEntries(response, "outgoing_scheduled");
  },
  async listOutgoingContinuous() {
    const response = await window.Malcom?.requestJson?.("/api/v1/outgoing/continuous");
    return normalizeResourceEntries(response, "outgoing_continuous");
  },
  async detailOutgoing(apiId, apiType) {
    return window.Malcom?.requestJson?.(`/api/v1/outgoing/${apiId}?api_type=${encodeURIComponent(apiType)}`);
  },
  async updateOutgoing(apiId, payload) {
    return window.Malcom?.requestJson?.(`/api/v1/outgoing/${apiId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  async listWebhooks() {
    const response = await window.Malcom?.requestJson?.("/api/v1/webhooks");
    return normalizeResourceEntries(response, "webhook");
  },
  async detailWebhook(apiId) {
    return window.Malcom?.requestJson?.(`/api/v1/webhooks/${apiId}`);
  }
});

export const getAppSettings = () => window.MalcomLogStore?.getAppSettings?.() || { connectors: { records: [] } };

export const loadConnectorEntries = async () => {
  try {
    await window.MalcomLogStore?.ready?.();
  } catch {
    return getAppSettings().connectors?.records || [];
  }

  return getAppSettings().connectors?.records || [];
};

export const emitApiLog = ({
  level = "info",
  action,
  message,
  details = {},
  context = {}
}) => {
  window.MalcomLogStore?.log({
    source: "ui.apis",
    category: "api",
    level,
    action,
    message,
    details,
    context: {
      page: window.location.pathname,
      ...context
    }
  });
};
