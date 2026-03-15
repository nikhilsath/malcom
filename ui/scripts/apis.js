import createApiModalMarkup from "../modals/create-api-modal.html?raw";
import createApiTypeModalMarkup from "../modals/create-api-type-modal.html?raw";
import outgoingApiEditModalMarkup from "../modals/outgoing-api-edit-modal.html?raw";

const apiElements = {
  createModal: document.getElementById("apis-create-modal"),
  createModalContent: document.getElementById("apis-create-modal-content"),
  detailModal: document.getElementById("api-detail-modal"),
  automationPlaceholderModal: document.getElementById("apis-automation-placeholder-modal"),
  automationAlert: document.getElementById("api-automation-alert"),
  alert: document.getElementById("api-system-alert"),
  tableBody: document.getElementById("api-directory-body"),
  tableShell: document.getElementById("api-table-shell"),
  directoryEmpty: document.getElementById("api-directory-empty"),
  detailEmpty: document.getElementById("api-detail-empty"),
  detailContent: document.getElementById("api-detail-content"),
  detailTitle: document.getElementById("api-detail-title"),
  detailDescription: document.getElementById("api-detail-description"),
  detailMetadata: document.getElementById("api-detail-metadata"),
  rotateSecretButton: document.getElementById("api-detail-rotate-secret-button"),
  toggleStatusButton: document.getElementById("api-detail-toggle-status-button"),
  secretPanel: document.getElementById("api-secret-panel"),
  secretValue: document.getElementById("api-secret-value"),
  secretCurl: document.getElementById("api-secret-curl"),
  logsSummaryTotalValue: document.getElementById("api-logs-summary-total-value"),
  logsSummaryAcceptedValue: document.getElementById("api-logs-summary-accepted-value"),
  logsSummaryErrorsValue: document.getElementById("api-logs-summary-errors-value"),
  logsSearchInput: document.getElementById("api-logs-search-input"),
  logsStatusFilter: document.getElementById("api-logs-status-filter"),
  logsSourceFilter: document.getElementById("api-logs-source-filter"),
  logsSortInput: document.getElementById("api-logs-sort-input"),
  logsResetButton: document.getElementById("api-logs-reset-button"),
  logsEmpty: document.getElementById("api-logs-empty"),
  logList: document.getElementById("api-log-list"),
  outgoingList: document.getElementById("apis-outgoing-list"),
  outgoingListEmpty: document.getElementById("apis-outgoing-list-empty"),
  outgoingEditModal: document.getElementById("outgoing-api-edit-modal"),
  outgoingEditModalContent: document.getElementById("outgoing-api-edit-modal-content"),
  webhooksList: document.getElementById("apis-webhooks-list"),
  webhooksListEmpty: document.getElementById("apis-webhooks-list-empty"),
  overviewAlert: document.getElementById("api-system-alert"),
  overviewTotalCount: document.getElementById("apis-overview-total-count"),
  overviewHelper: document.getElementById("apis-overview-helper"),
  overviewScheduledActiveCount: document.getElementById("apis-overview-summary-scheduled-active-value"),
  overviewCallsPerHour: document.getElementById("apis-overview-summary-calls-hour-value"),
  overviewCallsPerDay: document.getElementById("apis-overview-summary-calls-day-value"),
  overviewMonitoredWebhooksCount: document.getElementById("apis-overview-summary-monitored-webhooks-value"),
  overviewIncomingList: document.getElementById("apis-overview-incoming-list"),
  overviewIncomingEmpty: document.getElementById("apis-overview-incoming-empty"),
  overviewOutgoingList: document.getElementById("apis-overview-outgoing-list"),
  overviewOutgoingEmpty: document.getElementById("apis-overview-outgoing-empty"),
  overviewWebhooksList: document.getElementById("apis-overview-webhooks-list"),
  overviewWebhooksEmpty: document.getElementById("apis-overview-webhooks-empty")
};

const hasCreateModalElements = () => Boolean(
  apiElements.createModal && apiElements.createModalContent
);

const getCreateOpenButton = () => document.getElementById("apis-create-button");

const getCreateTypeModal = () => document.getElementById("apis-create-type-modal");

const hasAutomationPlaceholderElements = () => Boolean(
  apiElements.automationPlaceholderModal
);

const isAutomationPage = () => Boolean(apiElements.automationAlert);

const hasOverviewElements = () => Boolean(
  apiElements.alert
  && apiElements.tableBody
  && apiElements.tableShell
  && apiElements.directoryEmpty
  && apiElements.detailEmpty
  && apiElements.detailContent
  && apiElements.detailTitle
  && apiElements.detailDescription
  && apiElements.detailMetadata
  && apiElements.rotateSecretButton
  && apiElements.toggleStatusButton
  && apiElements.secretPanel
  && apiElements.secretValue
  && apiElements.secretCurl
  && apiElements.logsSummaryTotalValue
  && apiElements.logsSummaryAcceptedValue
  && apiElements.logsSummaryErrorsValue
  && apiElements.logsSearchInput
  && apiElements.logsStatusFilter
  && apiElements.logsSourceFilter
  && apiElements.logsSortInput
  && apiElements.logsResetButton
  && apiElements.logsEmpty
  && apiElements.logList
);

const hasOutgoingRegistryElements = () => Boolean(
  apiElements.outgoingList && apiElements.outgoingListEmpty
);

const hasOutgoingEditModalElements = () => Boolean(
  apiElements.outgoingEditModal && apiElements.outgoingEditModalContent
);

const hasWebhookRegistryElements = () => Boolean(
  apiElements.webhooksList && apiElements.webhooksListEmpty
);

const hasOverviewLandingElements = () => Boolean(
  apiElements.overviewTotalCount
  && apiElements.overviewHelper
  && apiElements.overviewScheduledActiveCount
  && apiElements.overviewCallsPerHour
  && apiElements.overviewCallsPerDay
  && apiElements.overviewMonitoredWebhooksCount
);

const modalFallbackMarkup = `
  <div class="modal__panel" id="create-api-modal-panel">
    <div class="modal__header" id="create-api-modal-header">
      <div class="modal__header-copy" id="create-api-modal-header-copy">
        <p class="modal__eyebrow" id="create-api-modal-eyebrow">Create</p>
        <div class="api-panel-title-row" id="create-api-modal-title-row">
          <h3 class="modal__title" id="apis-create-modal-title">Create API</h3>
          <button type="button" id="create-api-modal-description-tooltip-toggle" class="api-tooltip-toggle api-tooltip-toggle--compact" aria-label="Explain this API type" aria-expanded="false" aria-controls="create-api-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="button button--secondary modal__close-button" id="create-api-modal-close" aria-label="Close create API modal" data-modal-close="apis-create-modal">Close</button>
    </div>
    <div id="create-api-modal-description" class="api-tooltip-content api-tooltip-content--section" role="tooltip" hidden>The shared create form could not be loaded.</div>
    <div class="modal__body" id="create-api-modal-body">
      <p id="create-api-modal-fallback-copy" class="modal__description">Refresh the page and try again. If the problem persists, check the UI asset path for the shared modal template.</p>
    </div>
  </div>
`;

const createTypeModalFallbackMarkup = `
  <div
    id="apis-create-type-modal"
    class="modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="apis-create-type-modal-title"
    aria-describedby="apis-create-type-modal-description"
    aria-hidden="true"
  >
    <div class="modal__backdrop" id="apis-create-type-modal-backdrop" data-modal-close="apis-create-type-modal"></div>
    <div class="modal__dialog" id="apis-create-type-modal-dialog">
      <div class="modal__content" id="apis-create-type-modal-content">
        <div class="modal__panel api-create-type-modal-panel" id="apis-create-type-modal-panel">
          <div class="modal__header" id="apis-create-type-modal-header">
            <div class="modal__header-copy" id="apis-create-type-modal-header-copy">
              <p class="modal__eyebrow" id="apis-create-type-modal-eyebrow">Create</p>
              <h3 class="modal__title" id="apis-create-type-modal-title">Choose an API surface</h3>
              <p class="modal__description" id="apis-create-type-modal-description">Select the workflow you want to create and the full form will open with the relevant fields.</p>
            </div>
            <button type="button" class="button button--secondary modal__close-button" id="apis-create-type-modal-close" aria-label="Close create API type modal" data-modal-close="apis-create-type-modal">Close</button>
          </div>
          <div class="modal__body modal__body--form api-create-type-modal-body" id="apis-create-type-modal-body">
            <div id="apis-create-type-modal-options" class="api-create-type-modal-options">
              <button type="button" id="apis-create-type-option-incoming" class="api-create-type-modal-option" data-api-type="incoming">
                <span id="apis-create-type-option-incoming-title" class="api-create-type-modal-option__title">Incoming</span>
                <span id="apis-create-type-option-incoming-description" class="api-create-type-modal-option__description">Provision an authenticated inbound endpoint for JSON callbacks.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-scheduled" class="api-create-type-modal-option" data-api-type="outgoing_scheduled">
                <span id="apis-create-type-option-outgoing-scheduled-title" class="api-create-type-modal-option__title">Outgoing scheduled</span>
                <span id="apis-create-type-option-outgoing-scheduled-description" class="api-create-type-modal-option__description">Send a payload on a defined daily schedule.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-continuous" class="api-create-type-modal-option" data-api-type="outgoing_continuous">
                <span id="apis-create-type-option-outgoing-continuous-title" class="api-create-type-modal-option__title">Outgoing continuous</span>
                <span id="apis-create-type-option-outgoing-continuous-description" class="api-create-type-modal-option__description">Keep an outbound delivery ready on a repeating interval.</span>
              </button>
              <button type="button" id="apis-create-type-option-webhook" class="api-create-type-modal-option" data-api-type="webhook">
                <span id="apis-create-type-option-webhook-title" class="api-create-type-modal-option__title">Webhook</span>
                <span id="apis-create-type-option-webhook-description" class="api-create-type-modal-option__description">Store publisher verification and signing details.</span>
              </button>
              <button type="button" id="apis-create-type-option-automation" class="api-create-type-modal-option" data-api-type="automation">
                <span id="apis-create-type-option-automation-title" class="api-create-type-modal-option__title">Automation</span>
                <span id="apis-create-type-option-automation-description" class="api-create-type-modal-option__description">Open the automation workflow placeholder and start a new draft.</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`;

const outgoingEditModalFallbackMarkup = `
  <div class="modal__panel" id="outgoing-api-edit-modal-panel">
    <div class="modal__header" id="outgoing-api-edit-modal-header">
      <div class="modal__header-copy" id="outgoing-api-edit-modal-header-copy">
        <p class="modal__eyebrow" id="outgoing-api-edit-modal-eyebrow">Outgoing</p>
        <div class="api-panel-title-row" id="outgoing-api-edit-modal-title-row">
          <h3 class="modal__title" id="outgoing-api-edit-modal-title">Edit outgoing API</h3>
          <button type="button" id="outgoing-api-edit-modal-tooltip-toggle" class="api-tooltip-toggle api-tooltip-toggle--compact" aria-label="Explain outgoing API editing" aria-expanded="false" aria-controls="outgoing-api-edit-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="button button--secondary modal__close-button" id="outgoing-api-edit-modal-close" aria-label="Close outgoing API modal" data-modal-close="outgoing-api-edit-modal">Close</button>
    </div>
    <div id="outgoing-api-edit-modal-description" class="api-tooltip-content api-tooltip-content--section" role="tooltip" hidden>The outgoing edit form could not be loaded.</div>
    <div class="modal__body" id="outgoing-api-edit-modal-body">
      <p id="outgoing-api-edit-modal-fallback-copy" class="modal__description">Refresh the page and try again. If the problem persists, check the UI asset path for the outgoing edit modal template.</p>
    </div>
  </div>
`;

const apiState = {
  entries: [],
  selectedApiId: null,
  detailReturnFocusElement: null,
  lastSecretByApiId: {},
  outgoingEntries: [],
  webhookEntries: [],
  createModalType: "incoming",
  createTypeReturnFocusElement: null,
  outgoingEditReturnFocusElement: null,
  selectedOutgoingApiId: null,
  detailEvents: [],
  detailLogFilters: {
    search: "",
    status: "all",
    source: "all",
    sort: "newest"
  }
};

const developerModeEnabled = () => window.Malcom?.developerModeEnabled?.() ?? false;

const emitApiLog = ({
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

const apiResourceTypes = {
  incoming: {
    title: "New Incoming API",
    description: "Provision a webhook endpoint with a bearer token for authenticated JSON requests.",
    authLabel: "Bearer secret",
    enabledCopy: "Accept requests immediately",
    submitLabel: "Create incoming API",
    successMessage: "Incoming API created.",
    alertMessage: "Incoming API created. Store the generated bearer token now; it will not be shown again.",
    redirectPath: "/ui/apis/incoming.html"
  },
  outgoing_scheduled: {
    title: "New Outgoing Scheduled API",
    description: "Configure the destination URL, daily send time, credentials, and payload Malcom should deliver once by default or repeat daily when enabled.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Enable this scheduled delivery on create",
    submitLabel: "Create scheduled API",
    successMessage: "Scheduled outgoing API created.",
    alertMessage: "Scheduled outgoing API created.",
    redirectPath: "/ui/apis/outgoing.html"
  },
  outgoing_continuous: {
    title: "New Outgoing Continuous API",
    description: "Configure the destination URL, credentials, payload, and optional repeat interval for continuous outbound delivery.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Enable this outbound delivery on create",
    submitLabel: "Create continuous API",
    successMessage: "Continuous outgoing API created.",
    alertMessage: "Continuous outgoing API created.",
    redirectPath: "/ui/apis/outgoing.html"
  },
  webhook: {
    title: "New Webhook",
    description: "Register a webhook record for external publisher callbacks and verification settings.",
    authLabel: "Defined per webhook publisher",
    enabledCopy: "Enable the webhook immediately",
    submitLabel: "Create webhook",
    successMessage: "Webhook created.",
    alertMessage: "Webhook created.",
    redirectPath: "/ui/apis/webhooks.html"
  }
};

const sanitizeSlug = (value) => value
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9-]+/g, "-")
  .replace(/-{2,}/g, "-")
  .replace(/^-|-$/g, "");

const isOutgoingType = (type) => type === "outgoing_scheduled" || type === "outgoing_continuous";

const extractPayloadVariables = (value) => {
  const matches = value.matchAll(/{{\s*([^{}]+?)\s*}}/g);
  const variables = [];
  const seen = new Set();

  for (const match of matches) {
    const variableName = match[1]?.trim();

    if (!variableName || seen.has(variableName)) {
      continue;
    }

    seen.add(variableName);
    variables.push(variableName);
  }

  return variables;
};

const titleCase = (value) => value
  .split("_")
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(" ");

const getScheduledStatus = (entry) => entry.status || (entry.enabled ? "active" : "paused");

const getEntryStatusLabel = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return titleCase(getScheduledStatus(entry));
  }

  return entry.enabled ? "Enabled" : "Disabled";
};

const getEntryStatusTone = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return getScheduledStatus(entry) === "active" ? "status-badge--success" : "status-badge--muted";
  }

  return entry.enabled ? "status-badge--success" : "status-badge--muted";
};

const getOutgoingRegistryStatusLabel = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return getScheduledStatus(entry) === "active" ? "Active" : "Inactive";
  }

  return entry.enabled ? "Active" : "Inactive";
};

const getOutgoingRegistryStatusTone = (entry) => (getOutgoingRegistryStatusLabel(entry) === "Active"
  ? "status-badge--success"
  : "status-badge--warning");

const formatRate = (value) => value.toFixed(1);

const formatIntervalMinutes = (value) => {
  if (!value) {
    return "Not set";
  }

  if (value % 60 === 0) {
    const hours = value / 60;
    return `${hours} ${hours === 1 ? "hour" : "hours"}`;
  }

  return `${value} ${value === 1 ? "minute" : "minutes"}`;
};

const formatDateTime = (value) => {
  if (!value) {
    return "Never";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

const formatOutgoingSendTime = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return entry.scheduled_time || "Not set";
  }

  if (!entry.repeat_enabled) {
    return "Manual";
  }

  return entry.repeat_interval_minutes
    ? `Every ${formatIntervalMinutes(entry.repeat_interval_minutes)}`
    : "Repeating";
};

const formatRelativeActivity = (value) => {
  if (!value) {
    return "No recent activity";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recent activity unknown";
  }

  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.max(1, Math.round(diffMs / 60000));

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);

  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
};

const getEntryPrimaryLocation = (entry) => {
  if (entry.type === "incoming") {
    return entry.endpoint_path || `/api/v1/inbound/${entry.id}`;
  }

  if (entry.type?.startsWith("outgoing")) {
    return entry.destination_url || "Not configured";
  }

  if (entry.type === "webhook") {
    return entry.callback_path || "Not configured";
  }

  return entry.path_slug || "Not configured";
};

const getEntryLastActivity = (entry) => entry.last_received_at || entry.updated_at || entry.created_at || "";

const getLogSettings = () => window.MalcomLogStore?.getSettings?.() || window.MalcomLogStore?.defaults || {
  maxDetailCharacters: 4000
};

const formatBytes = (value) => {
  if (!Number.isFinite(value) || value < 0) {
    return "0 B";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

const sortEventsByStatus = (left, right) => {
  const statusWeight = {
    accepted: 0,
    queued: 1,
    unauthorized: 2,
    invalid_json: 3,
    unsupported_media_type: 4,
    disabled: 5
  };

  const leftWeight = statusWeight[left.status] ?? 99;
  const rightWeight = statusWeight[right.status] ?? 99;

  if (leftWeight !== rightWeight) {
    return leftWeight - rightWeight;
  }

  return new Date(right.received_at || 0) - new Date(left.received_at || 0);
};

const classifyEventSource = (eventItem) => {
  const sourceIp = eventItem.source_ip || "";

  if (!sourceIp) {
    return "unknown";
  }

  if (sourceIp === "127.0.0.1" || sourceIp === "::1" || sourceIp.startsWith("192.168.") || sourceIp.startsWith("10.")) {
    return "internal";
  }

  return "external";
};

const deriveEventLabel = (eventItem) => {
  const payload = eventItem.payload_json;

  if (payload && typeof payload === "object") {
    if (typeof payload.event === "string" && payload.event.trim()) {
      return payload.event.trim();
    }

    if (typeof payload.type === "string" && payload.type.trim()) {
      return payload.type.trim();
    }
  }

  return "Request event";
};

const stringifyPreviewValue = (value) => {
  if (value === null || value === undefined) {
    return "null";
  }

  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const truncatePreview = (value) => {
  const preview = stringifyPreviewValue(value);
  const maxDetailCharacters = Math.max(500, Number(getLogSettings().maxDetailCharacters) || 4000);

  if (preview.length <= maxDetailCharacters) {
    return {
      preview,
      truncated: false
    };
  }

  return {
    preview: `${preview.slice(0, maxDetailCharacters)}\n… truncated`,
    truncated: true
  };
};

const buildEventSearchValue = (eventItem) => [
  eventItem.event_id,
  eventItem.status,
  eventItem.source_ip,
  eventItem.error_message,
  stringifyPreviewValue(eventItem.payload_json),
  stringifyPreviewValue(eventItem.request_headers_subset)
].join(" ").toLowerCase();

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const setAlert = (message, tone = "info") => {
  if (!apiElements.alert) {
    return;
  }

  if (!message) {
    apiElements.alert.hidden = true;
    apiElements.alert.textContent = "";
    apiElements.alert.className = "api-system-alert";
    return;
  }

  apiElements.alert.hidden = false;
  apiElements.alert.textContent = message;
  apiElements.alert.className = `api-system-alert api-system-alert--${tone}`;
};

const setAutomationAlert = (message, tone = "info") => {
  if (!apiElements.automationAlert) {
    return;
  }

  if (!message) {
    apiElements.automationAlert.hidden = true;
    apiElements.automationAlert.textContent = "";
    apiElements.automationAlert.className = "api-system-alert";
    return;
  }

  apiElements.automationAlert.hidden = false;
  apiElements.automationAlert.textContent = message;
  apiElements.automationAlert.className = `api-system-alert api-system-alert--${tone}`;
};

const normalizeError = (error) => {
  if (error instanceof Error) {
    return { message: error.message, stack: error.stack };
  }

  return { message: String(error), stack: undefined };
};

const resolvePageHref = (absolutePath) => {
  const relativePath = absolutePath.startsWith("/ui/") ? absolutePath.slice(3) : absolutePath;
  return new URL(`..${relativePath}`, window.location.href).href;
};

const buildEndpointUrl = (apiId) => `${window.Malcom?.getBaseUrl?.() ?? ""}/api/v1/inbound/${apiId}`;

const buildSampleCurl = (apiId, secret) => {
  const endpoint = buildEndpointUrl(apiId);
  const jsonPayload = JSON.stringify({ hello: "world" }, null, 2);

  return `curl -X POST "${endpoint}" \\
  -H "Authorization: Bearer ${secret}" \\
  -H "Content-Type: application/json" \\
  -d '${jsonPayload}'`;
};

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

const backendApi = {
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
  }
};

const closeApiTooltips = () => {
  document.querySelectorAll(".api-tooltip-toggle[aria-controls]").forEach((toggle) => {
    const tooltipId = toggle.getAttribute("aria-controls");
    if (!tooltipId) {
      return;
    }

    const tooltip = document.getElementById(tooltipId);
    toggle.setAttribute("aria-expanded", "false");
    if (tooltip) {
      tooltip.hidden = true;
    }
  });
};

const bindApiTooltips = () => {
  const toggles = document.querySelectorAll(".api-tooltip-toggle[aria-controls]");

  if (toggles.length === 0) {
    return;
  }

  toggles.forEach((toggle) => {
    if (toggle.dataset.tooltipBound === "true") {
      return;
    }

    toggle.dataset.tooltipBound = "true";
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const tooltipId = toggle.getAttribute("aria-controls");

      if (!tooltipId) {
        return;
      }

      const tooltip = document.getElementById(tooltipId);

      if (!tooltip) {
        return;
      }

      const shouldOpen = toggle.getAttribute("aria-expanded") !== "true";
      closeApiTooltips();
      toggle.setAttribute("aria-expanded", String(shouldOpen));
      tooltip.hidden = !shouldOpen;
    });
  });

  if (document.body.dataset.apiTooltipListenerBound === "true") {
    return;
  }

  document.body.dataset.apiTooltipListenerBound = "true";

  document.addEventListener("click", (event) => {
    const target = event.target;

    if (!(target instanceof Element)) {
      closeApiTooltips();
      return;
    }

    if (!target.closest(".api-tooltip-toggle") && !target.closest(".api-tooltip-content")) {
      closeApiTooltips();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeApiTooltips();
    }
  });
};

const renderTable = () => {
  if (!hasOverviewElements()) {
    return;
  }

  apiElements.tableBody.textContent = "";
  const hasEntries = apiState.entries.length > 0;

  apiElements.directoryEmpty.hidden = hasEntries;
  apiElements.tableShell.hidden = !hasEntries;

  if (!hasEntries) {
    return;
  }

  const fragment = document.createDocumentFragment();

  apiState.entries.forEach((entry) => {
    const row = document.createElement("tr");
    row.id = `api-directory-row-${entry.id}`;
    row.className = "api-directory-row";
    row.tabIndex = 0;
    row.dataset.apiId = entry.id;
    row.setAttribute("role", "button");
    row.setAttribute("aria-pressed", String(apiState.selectedApiId === entry.id));

    if (apiState.selectedApiId === entry.id) {
      row.classList.add("api-directory-row--selected");
    }

    row.innerHTML = `
      <td id="api-directory-name-${entry.id}" class="api-directory-cell api-directory-cell--name">
        <span id="api-directory-name-value-${entry.id}" class="api-directory-name">${escapeHtml(entry.name)}</span>
        <span id="api-directory-description-value-${entry.id}" class="api-directory-description">${escapeHtml(entry.description || "No description provided.")}</span>
      </td>
      <td id="api-directory-status-${entry.id}" class="api-directory-cell">
        <span id="api-directory-status-badge-${entry.id}" class="status-badge ${entry.enabled ? "status-badge--success" : "status-badge--muted"}">${entry.enabled ? "Enabled" : "Disabled"}</span>
      </td>
      <td id="api-directory-path-${entry.id}" class="api-directory-cell api-directory-cell--path">${escapeHtml(entry.endpoint_path || `/api/v1/inbound/${entry.id}`)}</td>
      <td id="api-directory-received-${entry.id}" class="api-directory-cell">${escapeHtml(formatDateTime(entry.last_received_at))}</td>
      <td id="api-directory-result-${entry.id}" class="api-directory-cell">${escapeHtml(entry.last_delivery_status || "No deliveries")}</td>
    `;

    row.addEventListener("click", () => {
      apiState.detailReturnFocusElement = row;
      loadApiDetail(entry.id);
    });

    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        apiState.detailReturnFocusElement = row;
        loadApiDetail(entry.id);
      }
    });

    fragment.appendChild(row);
  });

  apiElements.tableBody.appendChild(fragment);
};

const renderMetadata = (entry) => {
  if (!hasOverviewElements()) {
    return;
  }

  const metadataRows = [
    { label: "Endpoint URL", value: entry.endpoint_url || buildEndpointUrl(entry.id) },
    { label: "Endpoint path", value: entry.endpoint_path || `/api/v1/inbound/${entry.id}` },
    { label: "Authentication", value: "Bearer secret" },
    { label: "Status", value: entry.enabled ? "Enabled" : "Disabled" },
    { label: "Created", value: formatDateTime(entry.created_at) },
    { label: "Updated", value: formatDateTime(entry.updated_at) },
    { label: "Last received", value: formatDateTime(entry.last_received_at) }
  ];

  apiElements.detailMetadata.innerHTML = metadataRows.map((item, index) => `
    <div id="api-detail-metadata-row-${index}" class="api-detail-metadata-row">
      <dt id="api-detail-metadata-label-${index}" class="api-detail-metadata-label">${escapeHtml(item.label)}</dt>
      <dd id="api-detail-metadata-value-${index}" class="api-detail-metadata-value">${escapeHtml(item.value)}</dd>
    </div>
  `).join("");
};

const renderSecretPanel = (entry) => {
  if (!hasOverviewElements()) {
    return;
  }

  const latestSecret = apiState.lastSecretByApiId[entry.id];

  if (!latestSecret) {
    apiElements.secretPanel.hidden = true;
    apiElements.secretValue.textContent = "";
    apiElements.secretCurl.textContent = "";
    return;
  }

  apiElements.secretPanel.hidden = false;
  apiElements.secretValue.textContent = latestSecret;
  apiElements.secretCurl.textContent = buildSampleCurl(entry.id, latestSecret);
};

const renderLogSummary = (events) => {
  if (!hasOverviewElements()) {
    return;
  }

  const acceptedCount = events.filter((eventItem) => eventItem.status === "accepted").length;
  const needsAttentionCount = events.filter((eventItem) => eventItem.status !== "accepted").length;

  apiElements.logsSummaryTotalValue.textContent = String(events.length);
  apiElements.logsSummaryAcceptedValue.textContent = String(acceptedCount);
  apiElements.logsSummaryErrorsValue.textContent = String(needsAttentionCount);
};

const getFilteredEvents = (events) => {
  const filters = apiState.detailLogFilters;
  const searchTerm = filters.search.trim().toLowerCase();

  const filteredEvents = events.filter((eventItem) => {
    if (filters.status !== "all" && eventItem.status !== filters.status) {
      return false;
    }

    if (filters.source !== "all" && classifyEventSource(eventItem) !== filters.source) {
      return false;
    }

    if (searchTerm && !buildEventSearchValue(eventItem).includes(searchTerm)) {
      return false;
    }

    return true;
  });

  if (filters.sort === "oldest") {
    return filteredEvents.sort((left, right) => new Date(left.received_at || 0) - new Date(right.received_at || 0));
  }

  if (filters.sort === "status") {
    return filteredEvents.sort(sortEventsByStatus);
  }

  return filteredEvents.sort((left, right) => new Date(right.received_at || 0) - new Date(left.received_at || 0));
};

const renderLogs = (events) => {
  if (!hasOverviewElements()) {
    return;
  }

  apiElements.logList.textContent = "";
  const filteredEvents = getFilteredEvents(events);
  renderLogSummary(filteredEvents);
  apiElements.logsEmpty.hidden = filteredEvents.length > 0;

  const logsEmptyTitle = document.getElementById("api-logs-empty-title");
  const logsEmptyDescription = document.getElementById("api-logs-empty-description");

  if (logsEmptyTitle && logsEmptyDescription) {
    if (events.length > 0 && filteredEvents.length === 0) {
      logsEmptyTitle.textContent = "No logs match the current filters";
      logsEmptyDescription.textContent = "Clear the current search or filters to see the full event history for this endpoint.";
    } else {
      logsEmptyTitle.textContent = "No requests received yet";
      logsEmptyDescription.textContent = "Send a JSON payload to this endpoint to populate the delivery log.";
    }
  }

  if (filteredEvents.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  filteredEvents.forEach((eventItem) => {
    const card = document.createElement("article");
    card.id = `api-log-card-${eventItem.event_id}`;
    card.className = "api-log-card";
    const payloadPreview = truncatePreview(eventItem.payload_json);
    const headersPreview = truncatePreview(eventItem.request_headers_subset);
    const headerCount = Object.keys(eventItem.request_headers_subset || {}).length;
    const payloadBytes = stringifyPreviewValue(eventItem.payload_json).length;
    const sourceClass = classifyEventSource(eventItem);
    const eventLabel = deriveEventLabel(eventItem);
    const statusTone = eventItem.status === "accepted" ? "status-badge--success" : "status-badge--warning";

    card.innerHTML = `
      <div id="api-log-header-${eventItem.event_id}" class="api-log-card__header">
        <div id="api-log-header-copy-${eventItem.event_id}" class="api-log-card__header-copy">
          <h5 id="api-log-title-${eventItem.event_id}" class="api-log-card__title">${escapeHtml(eventLabel)}</h5>
          <p id="api-log-meta-${eventItem.event_id}" class="api-log-card__meta">${escapeHtml(formatDateTime(eventItem.received_at))} • ${escapeHtml(eventItem.source_ip || "Unknown source")}</p>
          <div id="api-log-summary-${eventItem.event_id}" class="api-log-card__summary">
            <span id="api-log-summary-id-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(eventItem.event_id)}</span>
            <span id="api-log-summary-source-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(titleCase(sourceClass))} source</span>
            <span id="api-log-summary-headers-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(`${headerCount} headers`)}</span>
            <span id="api-log-summary-bytes-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(formatBytes(payloadBytes))}</span>
          </div>
        </div>
        <div id="api-log-actions-${eventItem.event_id}" class="api-log-card__actions">
          <span id="api-log-status-${eventItem.event_id}" class="status-badge ${statusTone}">${escapeHtml(eventItem.status)}</span>
          <button type="button" id="api-log-copy-payload-${eventItem.event_id}" class="button button--secondary secondary-action-button" data-copy-log="payload" data-event-id="${escapeHtml(eventItem.event_id)}">Copy payload</button>
          <button type="button" id="api-log-copy-headers-${eventItem.event_id}" class="button button--secondary secondary-action-button" data-copy-log="headers" data-event-id="${escapeHtml(eventItem.event_id)}">Copy headers</button>
        </div>
      </div>
      <div id="api-log-grid-${eventItem.event_id}" class="api-log-card__grid">
        <div id="api-log-headers-panel-${eventItem.event_id}" class="api-log-card__panel">
          <p id="api-log-headers-label-${eventItem.event_id}" class="api-log-card__label">Headers</p>
          <pre id="api-log-headers-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(headersPreview.preview)}</pre>
          <p id="api-log-headers-helper-${eventItem.event_id}" class="api-log-card__helper" ${headersPreview.truncated ? "" : "hidden"}>Header preview trimmed to match current logging detail settings.</p>
        </div>
        <div id="api-log-payload-panel-${eventItem.event_id}" class="api-log-card__panel">
          <p id="api-log-payload-label-${eventItem.event_id}" class="api-log-card__label">Payload</p>
          <pre id="api-log-payload-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(payloadPreview.preview)}</pre>
          <p id="api-log-payload-helper-${eventItem.event_id}" class="api-log-card__helper" ${payloadPreview.truncated ? "" : "hidden"}>Payload preview trimmed to match current logging detail settings.</p>
        </div>
      </div>
      <p id="api-log-error-${eventItem.event_id}" class="api-log-card__error" ${eventItem.error_message ? "" : "hidden"}>${escapeHtml(eventItem.error_message || "")}</p>
    `;

    fragment.appendChild(card);
  });

  apiElements.logList.appendChild(fragment);
};

const setDetailState = (isVisible) => {
  if (!hasOverviewElements()) {
    return;
  }

  apiElements.detailEmpty.hidden = isVisible;
  apiElements.detailContent.hidden = !isVisible;
};

const renderDetail = (entry) => {
  if (!hasOverviewElements()) {
    return;
  }

  const statusCopy = document.getElementById("api-directory-status-copy");

  if (!entry) {
    apiState.detailEvents = [];
    renderLogSummary([]);
    setDetailState(false);
    if (statusCopy) {
      statusCopy.textContent = "Choose a row to open the detail workspace. The selected endpoint stays highlighted in the directory.";
    }
    return;
  }

  setDetailState(true);
  apiState.detailEvents = Array.isArray(entry.events) ? entry.events : [];
  apiElements.detailTitle.textContent = entry.name;
  apiElements.detailDescription.textContent = entry.description || "No description provided.";
  apiElements.toggleStatusButton.textContent = entry.enabled ? "Disable endpoint" : "Enable endpoint";
  if (statusCopy) {
    statusCopy.textContent = `Inspecting ${entry.name}. The directory highlight tracks the active endpoint while you review logs and metadata.`;
  }
  renderMetadata(entry);
  renderSecretPanel(entry);
  renderLogs(apiState.detailEvents);
};

const loadApiDirectory = async () => {
  if (!hasOverviewElements()) {
    return;
  }

  apiState.entries = await backendApi.list();
  if (apiState.selectedApiId && !apiState.entries.some((entry) => entry.id === apiState.selectedApiId)) {
    apiState.selectedApiId = null;
  }

  renderTable();

  if (apiState.selectedApiId) {
    await loadApiDetail(apiState.selectedApiId, {
      syncTableSelection: false,
      openDetailModal: false
    });
  } else {
    renderDetail(null);
  }
};

async function loadApiDetail(apiId, options = {}) {
  if (!hasOverviewElements()) {
    return;
  }

  const {
    syncTableSelection = true,
    openDetailModal = true
  } = options;

  apiState.selectedApiId = apiId;
  apiElements.detailTitle.textContent = "Loading inbound API";
  apiElements.detailDescription.textContent = "Fetching endpoint metadata and recent events.";
  setDetailState(true);

  if (syncTableSelection) {
    renderTable();
  }

  const detail = await backendApi.detail(apiId);
  renderDetail(detail);
  emitApiLog({
    action: "inbound_api_detail_viewed",
    message: `Viewed inbound API "${detail.name}".`,
    details: {
      apiId: detail.id,
      eventCount: Array.isArray(detail.events) ? detail.events.length : 0
    }
  });

  if (openDetailModal) {
    openDetailModalView();
  }

  if (syncTableSelection) {
    renderTable();
  }
}

const syncModalBodyState = () => {
  document.body.classList.toggle(
    "modal-open",
    Boolean(document.querySelector(".modal.modal--open"))
  );
};

const syncCreateTypeTriggerState = (isExpanded) => {
  const createOpenButton = getCreateOpenButton();

  if (createOpenButton) {
    createOpenButton.setAttribute("aria-expanded", String(isExpanded));
  }
};

const ensureCreateTypeModal = () => {
  const createOpenButton = getCreateOpenButton();

  if (!createOpenButton) {
    return null;
  }

  let modal = getCreateTypeModal();

  if (modal) {
    return modal;
  }

  const modalHost = document.createElement("div");
  modalHost.id = "apis-create-type-modal-host";
  modalHost.innerHTML = createApiTypeModalMarkup.trim() || createTypeModalFallbackMarkup.trim();
  document.body.appendChild(modalHost);
  modal = getCreateTypeModal();

  if (!modal) {
    modalHost.innerHTML = createTypeModalFallbackMarkup.trim();
    modal = getCreateTypeModal();
  }

  return modal;
};

const openCreateTypeModal = () => {
  const modal = ensureCreateTypeModal();

  if (!modal) {
    openCreateModal("incoming");
    return;
  }

  apiState.createTypeReturnFocusElement = getCreateOpenButton();
  modal.classList.add("modal--open");
  modal.setAttribute("aria-hidden", "false");
  syncCreateTypeTriggerState(true);
  syncModalBodyState();
  const firstOption = modal.querySelector(".api-create-type-modal-option");

  if (firstOption instanceof HTMLElement) {
    firstOption.focus();
  }
};

const closeCreateTypeModal = ({ restoreFocus = true } = {}) => {
  const modal = getCreateTypeModal();

  if (!modal) {
    return;
  }

  modal.classList.remove("modal--open");
  modal.setAttribute("aria-hidden", "true");
  syncCreateTypeTriggerState(false);
  syncModalBodyState();

  if (restoreFocus && apiState.createTypeReturnFocusElement instanceof HTMLElement) {
    apiState.createTypeReturnFocusElement.focus();
  }
};

const setCreateModalType = (selectedType) => {
  const nextType = apiResourceTypes[selectedType] ? selectedType : "incoming";
  const typeInput = document.getElementById("create-api-type-input");

  apiState.createModalType = nextType;

  if (typeInput) {
    typeInput.value = nextType;
  }

  syncCreateModalType(nextType);
};

const openCreateModal = (selectedType = apiState.createModalType) => {
  if (!apiElements.createModal) {
    return;
  }

  closeApiTooltips();
  setCreateModalType(selectedType);
  apiElements.createModal.classList.add("modal--open");
  apiElements.createModal.setAttribute("aria-hidden", "false");
  syncModalBodyState();
};

const closeCreateModal = () => {
  if (!apiElements.createModal) {
    return;
  }

  closeApiTooltips();
  apiElements.createModal.classList.remove("modal--open");
  apiElements.createModal.setAttribute("aria-hidden", "true");
  syncModalBodyState();

  const createOpenButton = apiState.createTypeReturnFocusElement || getCreateOpenButton();

  if (createOpenButton) {
    createOpenButton.focus();
  }
};

const openOutgoingEditModal = () => {
  if (!apiElements.outgoingEditModal) {
    return;
  }

  closeApiTooltips();
  apiElements.outgoingEditModal.classList.add("modal--open");
  apiElements.outgoingEditModal.setAttribute("aria-hidden", "false");
  syncModalBodyState();
};

const closeOutgoingEditModal = () => {
  if (!apiElements.outgoingEditModal) {
    return;
  }

  closeApiTooltips();
  apiElements.outgoingEditModal.classList.remove("modal--open");
  apiElements.outgoingEditModal.setAttribute("aria-hidden", "true");
  syncModalBodyState();

  if (apiState.outgoingEditReturnFocusElement instanceof HTMLElement) {
    apiState.outgoingEditReturnFocusElement.focus();
  }
};

const syncOutgoingEditRowSelection = () => {
  document.querySelectorAll(".apis-outgoing-list__row[data-outgoing-id]").forEach((row) => {
    const isSelected = row.getAttribute("data-outgoing-id") === apiState.selectedOutgoingApiId;
    row.setAttribute("aria-pressed", String(isSelected));
    row.classList.toggle("apis-outgoing-list__row--selected", isSelected);
  });
};

const loadOutgoingEditDetail = async (entryId, entryType, triggerElement = null) => {
  const feedback = document.getElementById("outgoing-api-edit-form-feedback");

  apiState.selectedOutgoingApiId = entryId;
  apiState.outgoingEditReturnFocusElement = triggerElement instanceof HTMLElement ? triggerElement : null;
  syncOutgoingEditRowSelection();

  if (feedback) {
    setFormMessage(feedback, "Loading outgoing API...", "info");
  }

  const detail = await backendApi.detailOutgoing(entryId, entryType);
  const form = document.getElementById("outgoing-api-edit-form");
  const title = document.getElementById("outgoing-api-edit-modal-title");
  const typeInput = document.getElementById("outgoing-api-edit-type-input");
  const idInput = document.getElementById("outgoing-api-edit-id-input");
  const nameInput = document.getElementById("outgoing-api-edit-name-input");
  const slugInput = document.getElementById("outgoing-api-edit-slug-input");
  const descriptionInput = document.getElementById("outgoing-api-edit-description-input");
  const enabledInput = document.getElementById("outgoing-api-edit-enabled-input");
  const destinationInput = document.getElementById("outgoing-api-edit-destination-input");
  const methodInput = document.getElementById("outgoing-api-edit-method-input");
  const scheduledTimeInput = document.getElementById("outgoing-api-edit-scheduled-time-input");
  const scheduledRepeatInput = document.getElementById("outgoing-api-edit-scheduled-repeat-input");
  const continuousRepeatInput = document.getElementById("outgoing-api-edit-continuous-repeat-input");
  const continuousIntervalValueInput = document.getElementById("outgoing-api-edit-continuous-interval-value-input");
  const continuousIntervalUnitInput = document.getElementById("outgoing-api-edit-continuous-interval-unit-input");
  const authTypeInput = document.getElementById("outgoing-api-edit-auth-type-input");
  const authTokenInput = document.getElementById("outgoing-api-edit-auth-token-input");
  const authUsernameInput = document.getElementById("outgoing-api-edit-auth-username-input");
  const authPasswordInput = document.getElementById("outgoing-api-edit-auth-password-input");
  const authHeaderNameInput = document.getElementById("outgoing-api-edit-auth-header-name-input");
  const authHeaderValueInput = document.getElementById("outgoing-api-edit-auth-header-value-input");
  const payloadInput = document.getElementById("outgoing-api-edit-payload-input");

  if (!form || !typeInput || !idInput || !nameInput || !slugInput || !descriptionInput || !enabledInput || !destinationInput || !methodInput || !authTypeInput || !payloadInput) {
    return;
  }

  if (title) {
    title.textContent = detail.type === "outgoing_scheduled" ? "Edit scheduled API" : "Edit continuous API";
  }

  typeInput.value = detail.type;
  idInput.value = detail.id;
  nameInput.value = detail.name || "";
  slugInput.value = detail.path_slug || "";
  descriptionInput.value = detail.description || "";
  enabledInput.checked = Boolean(detail.enabled);
  destinationInput.value = detail.destination_url || "";
  methodInput.value = detail.http_method || "POST";
  if (scheduledTimeInput) {
    scheduledTimeInput.value = detail.scheduled_time || "09:00";
  }
  if (scheduledRepeatInput) {
    scheduledRepeatInput.checked = Boolean(detail.repeat_enabled);
  }
  if (continuousRepeatInput) {
    continuousRepeatInput.checked = Boolean(detail.repeat_enabled);
  }
  if (continuousIntervalValueInput && continuousIntervalUnitInput) {
    const repeatInterval = Number(detail.repeat_interval_minutes || 5);
    if (repeatInterval % 60 === 0) {
      continuousIntervalUnitInput.value = "hours";
      continuousIntervalValueInput.value = String(Math.max(1, repeatInterval / 60));
    } else {
      continuousIntervalUnitInput.value = "minutes";
      continuousIntervalValueInput.value = String(Math.max(1, repeatInterval));
    }
  }
  authTypeInput.value = detail.auth_type || "none";
  authTokenInput.value = detail.auth_config?.token || "";
  authUsernameInput.value = detail.auth_config?.username || "";
  authPasswordInput.value = detail.auth_config?.password || "";
  authHeaderNameInput.value = detail.auth_config?.header_name || "";
  authHeaderValueInput.value = detail.auth_config?.header_value || "";
  payloadInput.value = detail.payload_template || "{}";

  form.dataset.outgoingType = detail.type;
  form.dataset.outgoingId = detail.id;
  form.dispatchEvent(new CustomEvent("outgoing-edit-sync"));
  setFormMessage(feedback, "", "info");
  openOutgoingEditModal();
};

const openAutomationPlaceholderModal = () => {
  if (!apiElements.automationPlaceholderModal) {
    return;
  }

  if (isAutomationPage() && window.location.hash !== "#create-automation-placeholder") {
    window.history.replaceState(null, "", `${window.location.pathname}#create-automation-placeholder`);
  }

  apiElements.automationPlaceholderModal.classList.add("modal--open");
  apiElements.automationPlaceholderModal.setAttribute("aria-hidden", "false");
  syncModalBodyState();
};

const closeAutomationPlaceholderModal = () => {
  if (!apiElements.automationPlaceholderModal) {
    return;
  }

  apiElements.automationPlaceholderModal.classList.remove("modal--open");
  apiElements.automationPlaceholderModal.setAttribute("aria-hidden", "true");
  syncModalBodyState();

  if (isAutomationPage() && window.location.hash === "#create-automation-placeholder") {
    window.history.replaceState(null, "", window.location.pathname);
  }

  const createOpenButton = apiState.createTypeReturnFocusElement || getCreateOpenButton();

  if (createOpenButton) {
    createOpenButton.focus();
  }
};

const openDetailModalView = () => {
  if (!apiElements.detailModal) {
    return;
  }

  apiElements.detailModal.classList.add("modal--open");
  apiElements.detailModal.setAttribute("aria-hidden", "false");
  syncModalBodyState();
};

const closeDetailModalView = () => {
  if (!apiElements.detailModal) {
    return;
  }

  apiElements.detailModal.classList.remove("modal--open");
  apiElements.detailModal.setAttribute("aria-hidden", "true");
  syncModalBodyState();

  if (apiState.detailReturnFocusElement instanceof HTMLElement) {
    apiState.detailReturnFocusElement.focus();
  }
};

const navigateToAutomationPlaceholder = () => {
  const targetHref = resolvePageHref("/ui/apis/automation.html#create-automation-placeholder");

  if (window.location.href !== targetHref) {
    window.location.assign(targetHref);
    return;
  }

  openAutomationPlaceholderModal();
};

const bindModalEvents = () => {
  if (hasCreateModalElements()) {
    document.addEventListener("click", (event) => {
      const openTarget = event.target.closest("#apis-create-button");

      if (openTarget) {
        event.preventDefault();

        if (getCreateTypeModal()?.classList.contains("modal--open")) {
          closeCreateTypeModal();
          return;
        }

        openCreateTypeModal();
        return;
      }

      const directCreateTarget = event.target.closest("[data-create-api-type]");

      if (directCreateTarget instanceof HTMLElement) {
        const selectedType = directCreateTarget.dataset.createApiType || "incoming";
        apiState.createTypeReturnFocusElement = directCreateTarget;
        closeCreateTypeModal({ restoreFocus: false });
        openCreateModal(selectedType);
        return;
      }

      const typeTarget = event.target.closest(".api-create-type-modal-option");

      if (typeTarget instanceof HTMLElement) {
        const selectedType = typeTarget.dataset.apiType || "incoming";
        apiState.createTypeReturnFocusElement = getCreateOpenButton();
        closeCreateTypeModal({ restoreFocus: false });

        if (selectedType === "automation") {
          if (isAutomationPage() && hasAutomationPlaceholderElements()) {
            openAutomationPlaceholderModal();
          } else {
            navigateToAutomationPlaceholder();
          }
          return;
        }

        openCreateModal(selectedType);
        return;
      }
    });

    const createTypeModal = ensureCreateTypeModal();

    createTypeModal?.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeCreateTypeModal();
      }
    });

    apiElements.createModal.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeCreateModal();
      }
    });

    apiElements.outgoingEditModal?.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeOutgoingEditModal();
      }
    });
  }

  if (apiElements.detailModal) {
    apiElements.detailModal.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeDetailModalView();
      }
    });
  }

  if (apiElements.automationPlaceholderModal) {
    apiElements.automationPlaceholderModal.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeAutomationPlaceholderModal();
      }
    });
  }

  if (!hasCreateModalElements() && !apiElements.detailModal && !apiElements.outgoingEditModal) {
    return;
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }

    if (apiElements.detailModal?.classList.contains("modal--open")) {
      closeDetailModalView();
      return;
    }

    if (apiElements.automationPlaceholderModal?.classList.contains("modal--open")) {
      closeAutomationPlaceholderModal();
      return;
    }

    if (apiElements.createModal?.classList.contains("modal--open")) {
      closeCreateModal();
      return;
    }

    if (apiElements.outgoingEditModal?.classList.contains("modal--open")) {
      closeOutgoingEditModal();
      return;
    }

    if (getCreateTypeModal()?.classList.contains("modal--open")) {
      closeCreateTypeModal();
    }
  });
};

const syncCreateModalType = (selectedType) => {
  const config = apiResourceTypes[selectedType] || apiResourceTypes.incoming;
  const title = document.getElementById("apis-create-modal-title");
  const description = document.getElementById("create-api-modal-description");
  const authInput = document.getElementById("create-api-auth-input");
  const enabledCopy = document.getElementById("create-api-enabled-copy");
  const submitButton = document.getElementById("create-api-submit-button");
  const outgoingPanel = document.getElementById("create-api-outgoing-panel");
  const webhookPanel = document.getElementById("create-api-webhook-panel");
  const scheduledTimeField = document.getElementById("create-api-scheduled-time-field");
  const scheduledRepeatField = document.getElementById("create-api-scheduled-repeat-field");
  const continuousRepeatField = document.getElementById("create-api-continuous-repeat-field");
  const continuousIntervalValueField = document.getElementById("create-api-continuous-interval-value-field");
  const continuousIntervalUnitField = document.getElementById("create-api-continuous-interval-unit-field");
  const continuousRepeatInput = document.getElementById("create-api-continuous-repeat-input");
  const showContinuousIntervalFields = selectedType === "outgoing_continuous" && Boolean(continuousRepeatInput?.checked);

  if (title) {
    title.textContent = config.title;
  }

  if (description) {
    description.textContent = config.description;
    description.hidden = true;
  }

  if (authInput) {
    authInput.value = config.authLabel;
  }

  if (enabledCopy) {
    enabledCopy.textContent = config.enabledCopy;
  }

  if (submitButton) {
    submitButton.textContent = config.submitLabel;
  }

  if (outgoingPanel) {
    outgoingPanel.hidden = !isOutgoingType(selectedType);
  }

  if (webhookPanel) {
    webhookPanel.hidden = selectedType !== "webhook";
  }

  if (scheduledTimeField) {
    scheduledTimeField.hidden = selectedType !== "outgoing_scheduled";
  }

  if (scheduledRepeatField) {
    scheduledRepeatField.hidden = selectedType !== "outgoing_scheduled";
  }

  if (continuousRepeatField) {
    continuousRepeatField.hidden = selectedType !== "outgoing_continuous";
  }

  if (continuousIntervalValueField) {
    continuousIntervalValueField.hidden = !showContinuousIntervalFields;
  }

  if (continuousIntervalUnitField) {
    continuousIntervalUnitField.hidden = !showContinuousIntervalFields;
  }

  const payloadInput = document.getElementById("create-api-payload-input");

  if (payloadInput instanceof HTMLTextAreaElement) {
    payloadInput.dispatchEvent(new Event("input"));
  }
};

const navigateToResourcePage = (type) => {
  const targetHref = resolvePageHref(apiResourceTypes[type].redirectPath);

  if (window.location.href !== targetHref) {
    window.location.assign(targetHref);
  }
};

const bindCreateForm = () => {
  const form = document.getElementById("create-api-form");
  const typeInput = document.getElementById("create-api-type-input");
  const nameInput = document.getElementById("create-api-name-input");
  const slugInput = document.getElementById("create-api-slug-input");
  const descriptionInput = document.getElementById("create-api-description-input");
  const enabledInput = document.getElementById("create-api-enabled-input");
  const feedback = document.getElementById("create-api-form-feedback");
  const destinationInput = document.getElementById("create-api-destination-input");
  const methodInput = document.getElementById("create-api-method-input");
  const scheduledTimeInput = document.getElementById("create-api-scheduled-time-input");
  const scheduledRepeatInput = document.getElementById("create-api-scheduled-repeat-input");
  const continuousRepeatInput = document.getElementById("create-api-continuous-repeat-input");
  const continuousIntervalValueInput = document.getElementById("create-api-continuous-interval-value-input");
  const continuousIntervalUnitInput = document.getElementById("create-api-continuous-interval-unit-input");
  const outgoingAuthTypeInput = document.getElementById("create-api-outgoing-auth-type-input");
  const authTokenInput = document.getElementById("create-api-auth-token-input");
  const authUsernameInput = document.getElementById("create-api-auth-username-input");
  const authPasswordInput = document.getElementById("create-api-auth-password-input");
  const authHeaderNameInput = document.getElementById("create-api-auth-header-name-input");
  const authHeaderValueInput = document.getElementById("create-api-auth-header-value-input");
  const payloadTemplateInput = document.getElementById("create-api-payload-input");
  const payloadLayout = document.getElementById("create-api-payload-layout");
  const payloadVariablesPanel = document.getElementById("create-api-payload-variables-panel");
  const payloadVariablesList = document.getElementById("create-api-payload-variables-list");
  const createModalDialog = document.getElementById("apis-create-modal-dialog");
  const webhookCallbackPathInput = document.getElementById("create-api-webhook-callback-input");
  const webhookVerificationTokenInput = document.getElementById("create-api-webhook-verification-input");
  const webhookSigningSecretInput = document.getElementById("create-api-webhook-signing-input");
  const webhookSignatureHeaderInput = document.getElementById("create-api-webhook-header-input");
  const webhookEventFilterInput = document.getElementById("create-api-webhook-event-input");
  const testButton = document.getElementById("create-api-test-button");
  const testFeedback = document.getElementById("create-api-test-feedback");

  if (!form || !typeInput || !nameInput || !slugInput || !descriptionInput || !enabledInput || !feedback) {
    return;
  }

  const getSelectedType = () => typeInput.value || apiState.createModalType || "incoming";
  const outgoingAuthFields = {
    bearer: [document.getElementById("create-api-auth-token-field")],
    basic: [
      document.getElementById("create-api-auth-username-field"),
      document.getElementById("create-api-auth-password-field")
    ],
    header: [
      document.getElementById("create-api-auth-header-name-field"),
      document.getElementById("create-api-auth-header-value-field")
    ]
  };

  const setFormMessage = (element, message, tone) => {
    if (!element) {
      return;
    }

    element.textContent = message;
    element.className = message
      ? `api-form-feedback api-form-feedback--${tone}`
      : "api-form-feedback";
  };

  const convertIntervalToMinutes = () => {
    const intervalValue = Number.parseInt(continuousIntervalValueInput?.value || "", 10);
    const intervalUnit = continuousIntervalUnitInput?.value || "minutes";

    if (!Number.isFinite(intervalValue) || intervalValue <= 0) {
      return null;
    }

    return intervalUnit === "hours" ? intervalValue * 60 : intervalValue;
  };

  const syncContinuousIntervalConstraints = () => {
    if (!continuousIntervalValueInput) {
      return;
    }

    const intervalUnit = continuousIntervalUnitInput?.value || "minutes";
    continuousIntervalValueInput.min = "1";
    continuousIntervalValueInput.max = intervalUnit === "hours" ? "168" : "10080";
  };

  const syncOutgoingAuthFields = () => {
    const authType = outgoingAuthTypeInput?.value || "none";

    Object.values(outgoingAuthFields).flat().forEach((field) => {
      if (field) {
        field.hidden = true;
      }
    });

    (outgoingAuthFields[authType] || []).forEach((field) => {
      if (field) {
        field.hidden = false;
      }
    });
  };

  const syncOutgoingRepeatFields = () => {
    const selectedType = getSelectedType();
    const continuousIntervalValueField = document.getElementById("create-api-continuous-interval-value-field");
    const continuousIntervalUnitField = document.getElementById("create-api-continuous-interval-unit-field");
    const continuousRepeating = Boolean(continuousRepeatInput?.checked);

    if (continuousIntervalValueField) {
      continuousIntervalValueField.hidden = selectedType !== "outgoing_continuous" || !continuousRepeating;
    }

    if (continuousIntervalUnitField) {
      continuousIntervalUnitField.hidden = selectedType !== "outgoing_continuous" || !continuousRepeating;
    }
  };

  const syncPayloadVariablePreview = () => {
    if (!payloadLayout || !payloadVariablesPanel || !payloadVariablesList || !createModalDialog) {
      return;
    }

    const selectedType = getSelectedType();
    const variables = isOutgoingType(selectedType)
      ? extractPayloadVariables(payloadTemplateInput?.value || "")
      : [];
    const hasVariables = variables.length > 0;

    payloadVariablesList.textContent = "";

    variables.forEach((variableName, index) => {
      const chip = document.createElement("span");
      chip.id = `create-api-payload-variable-${variableName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "value"}-${index + 1}`;
      chip.className = "api-payload-variable-chip";
      chip.textContent = `{{${variableName}}}`;
      payloadVariablesList.appendChild(chip);
    });

    payloadVariablesPanel.hidden = !hasVariables;
    payloadLayout.classList.toggle("api-payload-layout--expanded", hasVariables);
    createModalDialog.classList.toggle("modal__dialog--payload-expanded", hasVariables);
  };

  const buildOutgoingDraft = () => {
    const selectedType = getSelectedType();

    if (!isOutgoingType(selectedType)) {
      return null;
    }

    const authType = outgoingAuthTypeInput?.value || "none";
    const repeatEnabled = selectedType === "outgoing_scheduled"
      ? Boolean(scheduledRepeatInput?.checked)
      : Boolean(continuousRepeatInput?.checked);

    return {
      type: selectedType,
      repeat_enabled: repeatEnabled,
      repeat_interval_minutes: selectedType === "outgoing_continuous" && repeatEnabled ? convertIntervalToMinutes() : null,
      destination_url: destinationInput?.value.trim() || "",
      http_method: methodInput?.value || "POST",
      auth_type: authType,
      auth_config: {
        token: authTokenInput?.value || "",
        username: authUsernameInput?.value || "",
        password: authPasswordInput?.value || "",
        header_name: authHeaderNameInput?.value || "",
        header_value: authHeaderValueInput?.value || ""
      },
      payload_template: payloadTemplateInput?.value.trim() || "",
      scheduled_time: scheduledTimeInput?.value || ""
    };
  };

  const buildWebhookDraft = () => ({
    callback_path: webhookCallbackPathInput?.value.trim() || "",
    verification_token: webhookVerificationTokenInput?.value || "",
    signing_secret: webhookSigningSecretInput?.value || "",
    signature_header: webhookSignatureHeaderInput?.value.trim() || "",
    event_filter: webhookEventFilterInput?.value.trim() || ""
  });

  const validateDraft = (draft, { requireName = true } = {}) => {
    if (requireName && (!draft.name || !draft.path_slug)) {
      return "Name and path slug are required.";
    }

    if (draft.type === "webhook") {
      if (!draft.callback_path) {
        return "Callback path is required for webhooks.";
      }

      if (!draft.callback_path.startsWith("/")) {
        return "Callback path must start with '/'.";
      }

      if (!draft.verification_token) {
        return "Verification token is required for webhooks.";
      }

      if (!draft.signing_secret) {
        return "Signing secret is required for webhooks.";
      }

      if (!draft.signature_header) {
        return "Signature header is required for webhooks.";
      }

      return "";
    }

    if (!isOutgoingType(draft.type)) {
      return "";
    }

    if (!draft.destination_url) {
      return "Destination URL is required for outgoing APIs.";
    }

    if (!/^https?:\/\//i.test(draft.destination_url)) {
      return "Destination URL must start with http:// or https://.";
    }

    if (!draft.payload_template) {
      return "A JSON payload template is required for outgoing APIs.";
    }

    try {
      JSON.parse(draft.payload_template);
    } catch {
      return "Payload template must be valid JSON.";
    }

    if (draft.type === "outgoing_scheduled" && !draft.scheduled_time) {
      return "Choose a send time for the scheduled outgoing API.";
    }

    if (draft.type === "outgoing_continuous" && draft.repeat_enabled) {
      if (!draft.repeat_interval_minutes) {
        return "Choose a repeat interval for the continuous outgoing API.";
      }

      if (draft.repeat_interval_minutes < 1) {
        return "Continuous repeat intervals must be at least 1 minute.";
      }

      if (draft.repeat_interval_minutes > 10080) {
        return "Continuous repeat intervals cannot exceed 168 hours.";
      }
    }

    if (draft.auth_type === "bearer" && !draft.auth_config.token) {
      return "Enter a bearer token or switch destination auth to None.";
    }

    if (draft.auth_type === "basic" && (!draft.auth_config.username || !draft.auth_config.password)) {
      return "Basic auth requires both a username and password.";
    }

    if (draft.auth_type === "header" && (!draft.auth_config.header_name || !draft.auth_config.header_value)) {
      return "Custom header auth requires both a header name and value.";
    }

    return "";
  };

  const resetOutgoingFields = () => {
    if (destinationInput) {
      destinationInput.value = "";
    }
    if (methodInput) {
      methodInput.value = "POST";
    }
    if (scheduledTimeInput) {
      scheduledTimeInput.value = "09:00";
    }
    if (scheduledRepeatInput) {
      scheduledRepeatInput.checked = false;
    }
    if (continuousRepeatInput) {
      continuousRepeatInput.checked = false;
    }
    if (continuousIntervalValueInput) {
      continuousIntervalValueInput.value = "5";
    }
    if (continuousIntervalUnitInput) {
      continuousIntervalUnitInput.value = "minutes";
    }
    syncContinuousIntervalConstraints();
    if (outgoingAuthTypeInput) {
      outgoingAuthTypeInput.value = "none";
    }
    if (authTokenInput) {
      authTokenInput.value = "";
    }
    if (authUsernameInput) {
      authUsernameInput.value = "";
    }
    if (authPasswordInput) {
      authPasswordInput.value = "";
    }
    if (authHeaderNameInput) {
      authHeaderNameInput.value = "";
    }
    if (authHeaderValueInput) {
      authHeaderValueInput.value = "";
    }
    if (payloadTemplateInput) {
      payloadTemplateInput.value = '{ "event": "scheduled.delivery", "sent_at": "{{timestamp}}" }';
    }
    syncOutgoingAuthFields();
    syncOutgoingRepeatFields();
    syncPayloadVariablePreview();
    setFormMessage(testFeedback, "", "info");
  };

  const resetWebhookFields = () => {
    if (webhookCallbackPathInput) {
      webhookCallbackPathInput.value = "";
    }
    if (webhookVerificationTokenInput) {
      webhookVerificationTokenInput.value = "";
    }
    if (webhookSigningSecretInput) {
      webhookSigningSecretInput.value = "";
    }
    if (webhookSignatureHeaderInput) {
      webhookSignatureHeaderInput.value = "";
    }
    if (webhookEventFilterInput) {
      webhookEventFilterInput.value = "";
    }
  };

  nameInput.addEventListener("input", () => {
    if (!slugInput.dataset.userEdited) {
      slugInput.value = sanitizeSlug(nameInput.value);
    }
  });

  slugInput.addEventListener("input", () => {
    slugInput.dataset.userEdited = "true";
    slugInput.value = sanitizeSlug(slugInput.value);
  });

  outgoingAuthTypeInput?.addEventListener("change", syncOutgoingAuthFields);
  scheduledRepeatInput?.addEventListener("change", syncOutgoingRepeatFields);
  continuousRepeatInput?.addEventListener("change", syncOutgoingRepeatFields);
  continuousIntervalUnitInput?.addEventListener("change", syncContinuousIntervalConstraints);
  payloadTemplateInput?.addEventListener("input", syncPayloadVariablePreview);

  testButton?.addEventListener("click", async () => {
    const selectedType = getSelectedType();
    if (!isOutgoingType(selectedType)) {
      return;
    }

    const validationMessage = validateDraft(buildOutgoingDraft(), { requireName: false });

    if (validationMessage) {
      setFormMessage(testFeedback, validationMessage, "error");
      return;
    }

    testButton.disabled = true;
    setFormMessage(testFeedback, "Sending test payload...", "info");

    try {
      const result = await backendApi.testOutgoingDelivery(buildOutgoingDraft());
      const responsePreview = result.response_body ? ` Response: ${result.response_body}` : "";
      setFormMessage(testFeedback, `Test delivery returned ${result.status_code}.${responsePreview}`.trim(), result.ok ? "success" : "error");
      emitApiLog({
        level: result.ok ? "info" : "warning",
        action: "outgoing_api_test_delivery_completed",
        message: `Test delivery returned ${result.status_code}.`,
        details: {
          type: selectedType,
          destinationUrl: buildOutgoingDraft()?.destination_url || "",
          statusCode: result.status_code,
          ok: result.ok
        }
      });
    } catch (error) {
      const draft = buildOutgoingDraft();
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      setFormMessage(testFeedback, errorMessage, "error");
      emitApiLog({
        level: "error",
        action: "outgoing_api_test_delivery_failed",
        message: "Test delivery failed before a response was returned.",
        details: {
          type: selectedType,
          destinationUrl: draft?.destination_url || "",
          error: errorMessage,
          stack: errorStack
        }
      });
    } finally {
      testButton.disabled = false;
    }
  });

  syncOutgoingAuthFields();
  syncCreateModalType(getSelectedType());
  syncContinuousIntervalConstraints();
  syncOutgoingRepeatFields();
  syncPayloadVariablePreview();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormMessage(feedback, "", "info");
    const selectedType = getSelectedType();

    const payload = {
      type: selectedType,
      name: nameInput.value.trim(),
      path_slug: sanitizeSlug(slugInput.value),
      description: descriptionInput.value.trim(),
      enabled: enabledInput.checked
    };

    if (isOutgoingType(selectedType)) {
      Object.assign(payload, buildOutgoingDraft());
    }

    if (selectedType === "webhook") {
      Object.assign(payload, buildWebhookDraft());
    }

    const validationMessage = validateDraft(payload);

    if (validationMessage) {
      setFormMessage(feedback, validationMessage, "error");
      return;
    }

    try {
      const created = await backendApi.create(payload);
      if (created.secret) {
        apiState.lastSecretByApiId[created.id] = created.secret;
      }

      if (selectedType === "incoming" && hasOverviewElements()) {
        apiState.selectedApiId = created.id;
        await loadApiDirectory();
        await loadApiDetail(created.id);
      }

      if (selectedType !== "incoming") {
        if (hasOutgoingRegistryElements()) {
          await loadOutgoingRegistries();
        }

        if (hasWebhookRegistryElements()) {
          await loadWebhookRegistry();
        }
      }

      form.reset();
      enabledInput.checked = true;
      delete slugInput.dataset.userEdited;
      resetOutgoingFields();
      resetWebhookFields();
      setCreateModalType("incoming");
      setFormMessage(feedback, apiResourceTypes[selectedType].successMessage, "success");
      closeCreateModal();
      setAlert(apiResourceTypes[selectedType].alertMessage, "success");
      emitApiLog({
        action: `${selectedType}_created`,
        message: `Created ${selectedType} "${created.name}".`,
        details: {
          type: selectedType,
          apiId: created.id,
          pathSlug: created.path_slug,
          enabled: created.enabled
        }
      });

      if (selectedType !== "incoming" || !hasOverviewElements()) {
        navigateToResourcePage(selectedType);
      }
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error(`Failed to create ${selectedType}`, error);
      setFormMessage(feedback, errorMessage, "error");
      emitApiLog({
        level: "error",
        action: `${selectedType}_create_failed`,
        message: `Failed to create ${selectedType}.`,
        details: {
          error: errorMessage,
          stack: errorStack,
          type: selectedType,
          attemptedName: payload.name,
          attemptedSlug: payload.path_slug
        }
      });
    }
  });
};

const bindOutgoingEditForm = () => {
  const form = document.getElementById("outgoing-api-edit-form");

  if (!(form instanceof HTMLFormElement) || form.dataset.bound === "true") {
    return;
  }

  form.dataset.bound = "true";

  const idInput = document.getElementById("outgoing-api-edit-id-input");
  const typeInput = document.getElementById("outgoing-api-edit-type-input");
  const nameInput = document.getElementById("outgoing-api-edit-name-input");
  const slugInput = document.getElementById("outgoing-api-edit-slug-input");
  const descriptionInput = document.getElementById("outgoing-api-edit-description-input");
  const enabledInput = document.getElementById("outgoing-api-edit-enabled-input");
  const destinationInput = document.getElementById("outgoing-api-edit-destination-input");
  const methodInput = document.getElementById("outgoing-api-edit-method-input");
  const scheduledTimeInput = document.getElementById("outgoing-api-edit-scheduled-time-input");
  const scheduledTimeField = document.getElementById("outgoing-api-edit-scheduled-time-field");
  const scheduledRepeatInput = document.getElementById("outgoing-api-edit-scheduled-repeat-input");
  const scheduledRepeatField = document.getElementById("outgoing-api-edit-scheduled-repeat-field");
  const continuousRepeatInput = document.getElementById("outgoing-api-edit-continuous-repeat-input");
  const continuousRepeatField = document.getElementById("outgoing-api-edit-continuous-repeat-field");
  const continuousIntervalValueInput = document.getElementById("outgoing-api-edit-continuous-interval-value-input");
  const continuousIntervalValueField = document.getElementById("outgoing-api-edit-continuous-interval-value-field");
  const continuousIntervalUnitInput = document.getElementById("outgoing-api-edit-continuous-interval-unit-input");
  const continuousIntervalUnitField = document.getElementById("outgoing-api-edit-continuous-interval-unit-field");
  const authTypeInput = document.getElementById("outgoing-api-edit-auth-type-input");
  const authTokenInput = document.getElementById("outgoing-api-edit-auth-token-input");
  const authTokenField = document.getElementById("outgoing-api-edit-auth-token-field");
  const authUsernameInput = document.getElementById("outgoing-api-edit-auth-username-input");
  const authUsernameField = document.getElementById("outgoing-api-edit-auth-username-field");
  const authPasswordInput = document.getElementById("outgoing-api-edit-auth-password-input");
  const authPasswordField = document.getElementById("outgoing-api-edit-auth-password-field");
  const authHeaderNameInput = document.getElementById("outgoing-api-edit-auth-header-name-input");
  const authHeaderNameField = document.getElementById("outgoing-api-edit-auth-header-name-field");
  const authHeaderValueInput = document.getElementById("outgoing-api-edit-auth-header-value-input");
  const authHeaderValueField = document.getElementById("outgoing-api-edit-auth-header-value-field");
  const payloadInput = document.getElementById("outgoing-api-edit-payload-input");
  const testButton = document.getElementById("outgoing-api-edit-test-button");
  const testFeedback = document.getElementById("outgoing-api-edit-test-feedback");
  const feedback = document.getElementById("outgoing-api-edit-form-feedback");

  const getSelectedType = () => typeInput?.value || form.dataset.outgoingType || "outgoing_scheduled";

  const syncAuthFields = () => {
    const authType = authTypeInput?.value || "none";
    [authTokenField, authUsernameField, authPasswordField, authHeaderNameField, authHeaderValueField].forEach((field) => {
      if (field) {
        field.hidden = true;
      }
    });

    if (authType === "bearer" && authTokenField) {
      authTokenField.hidden = false;
    }

    if (authType === "basic") {
      if (authUsernameField) {
        authUsernameField.hidden = false;
      }
      if (authPasswordField) {
        authPasswordField.hidden = false;
      }
    }

    if (authType === "header") {
      if (authHeaderNameField) {
        authHeaderNameField.hidden = false;
      }
      if (authHeaderValueField) {
        authHeaderValueField.hidden = false;
      }
    }
  };

  const syncTypeFields = () => {
    const selectedType = getSelectedType();
    const isScheduled = selectedType === "outgoing_scheduled";
    const isContinuous = selectedType === "outgoing_continuous";
    const continuousRepeating = Boolean(continuousRepeatInput?.checked);

    if (scheduledTimeField) {
      scheduledTimeField.hidden = !isScheduled;
    }
    if (scheduledRepeatField) {
      scheduledRepeatField.hidden = !isScheduled;
    }
    if (continuousRepeatField) {
      continuousRepeatField.hidden = !isContinuous;
    }
    if (continuousIntervalValueField) {
      continuousIntervalValueField.hidden = !isContinuous || !continuousRepeating;
    }
    if (continuousIntervalUnitField) {
      continuousIntervalUnitField.hidden = !isContinuous || !continuousRepeating;
    }
  };

  const buildRepeatIntervalMinutes = () => {
    const rawValue = Number(continuousIntervalValueInput?.value || "0");
    const unit = continuousIntervalUnitInput?.value || "minutes";
    return unit === "hours" ? rawValue * 60 : rawValue;
  };

  const buildPayload = () => ({
    type: getSelectedType(),
    name: nameInput?.value.trim() || "",
    path_slug: sanitizeSlug(slugInput?.value || ""),
    description: descriptionInput?.value.trim() || "",
    enabled: Boolean(enabledInput?.checked),
    repeat_enabled: getSelectedType() === "outgoing_scheduled"
      ? Boolean(scheduledRepeatInput?.checked)
      : Boolean(continuousRepeatInput?.checked),
    repeat_interval_minutes: getSelectedType() === "outgoing_continuous" && continuousRepeatInput?.checked
      ? buildRepeatIntervalMinutes()
      : null,
    destination_url: destinationInput?.value.trim() || "",
    http_method: methodInput?.value || "POST",
    auth_type: authTypeInput?.value || "none",
    auth_config: {
      token: authTokenInput?.value || "",
      username: authUsernameInput?.value || "",
      password: authPasswordInput?.value || "",
      header_name: authHeaderNameInput?.value || "",
      header_value: authHeaderValueInput?.value || ""
    },
    payload_template: payloadInput?.value.trim() || "",
    scheduled_time: getSelectedType() === "outgoing_scheduled" ? (scheduledTimeInput?.value || "") : undefined
  });

  const validatePayload = (payload) => {
    if (!payload.name || !payload.path_slug) {
      return "Name and path slug are required.";
    }
    if (!payload.destination_url) {
      return "Destination URL is required.";
    }
    if (!/^https?:\/\//i.test(payload.destination_url)) {
      return "Destination URL must start with http:// or https://.";
    }
    if (!payload.payload_template) {
      return "A JSON payload template is required.";
    }
    try {
      JSON.parse(payload.payload_template);
    } catch {
      return "Payload template must be valid JSON.";
    }
    if (payload.type === "outgoing_scheduled" && !payload.scheduled_time) {
      return "Choose a send time for the scheduled outgoing API.";
    }
    if (payload.type === "outgoing_continuous" && payload.repeat_enabled) {
      if (!payload.repeat_interval_minutes) {
        return "Choose a repeat interval for the continuous outgoing API.";
      }
      if (payload.repeat_interval_minutes < 1 || payload.repeat_interval_minutes > 10080) {
        return "Continuous repeat intervals must be between 1 minute and 168 hours.";
      }
    }
    if (payload.auth_type === "bearer" && !payload.auth_config.token) {
      return "Enter a bearer token or change destination auth.";
    }
    if (payload.auth_type === "basic" && (!payload.auth_config.username || !payload.auth_config.password)) {
      return "Basic auth requires both a username and password.";
    }
    if (payload.auth_type === "header" && (!payload.auth_config.header_name || !payload.auth_config.header_value)) {
      return "Custom header auth requires both a header name and value.";
    }
    return "";
  };

  authTypeInput?.addEventListener("change", syncAuthFields);
  scheduledRepeatInput?.addEventListener("change", syncTypeFields);
  continuousRepeatInput?.addEventListener("change", syncTypeFields);
  form.addEventListener("outgoing-edit-sync", () => {
    syncAuthFields();
    syncTypeFields();
  });

  testButton?.addEventListener("click", async () => {
    const payload = buildPayload();
    const validationMessage = validatePayload(payload);

    if (validationMessage) {
      setFormMessage(testFeedback, validationMessage, "error");
      return;
    }

    testButton.disabled = true;
    setFormMessage(testFeedback, "Sending test payload...", "info");

    try {
      const result = await backendApi.testOutgoingDelivery(payload);
      const responsePreview = result.response_body ? ` Response: ${result.response_body}` : "";
      setFormMessage(testFeedback, `Test delivery returned ${result.status_code}.${responsePreview}`.trim(), result.ok ? "success" : "error");
    } catch (error) {
      const { message: errorMessage } = normalizeError(error);
      setFormMessage(testFeedback, errorMessage, "error");
    } finally {
      testButton.disabled = false;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const entryId = idInput?.value || form.dataset.outgoingId || "";
    const payload = buildPayload();
    const validationMessage = validatePayload(payload);

    if (!entryId) {
      setFormMessage(feedback, "Outgoing API id is missing.", "error");
      return;
    }

    if (validationMessage) {
      setFormMessage(feedback, validationMessage, "error");
      return;
    }

    setFormMessage(feedback, "Saving outgoing API...", "info");

    try {
      await backendApi.updateOutgoing(entryId, payload);
      await loadOutgoingRegistries();
      setFormMessage(feedback, "Outgoing API saved.", "success");
      setAlert("Outgoing API updated.", "success");
      closeOutgoingEditModal();
      emitApiLog({
        action: "outgoing_api_updated",
        message: `Updated outgoing API "${payload.name}".`,
        details: {
          apiId: entryId,
          type: payload.type,
          enabled: payload.enabled
        }
      });
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      setFormMessage(feedback, errorMessage, "error");
      emitApiLog({
        level: "error",
        action: "outgoing_api_update_failed",
        message: "Failed to update outgoing API.",
        details: {
          apiId: entryId,
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  });

  syncAuthFields();
  syncTypeFields();
};

const renderResourceList = (container, emptyState, entries, sectionIdPrefix) => {
  if (!container || !emptyState) {
    return;
  }

  container.textContent = "";
  emptyState.hidden = entries.length > 0;

  if (entries.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  entries.forEach((entry) => {
    const metadataItems = [];
    const signalItems = [
      getEntryStatusLabel(entry),
      getEntryPrimaryLocation(entry),
      formatRelativeActivity(getEntryLastActivity(entry))
    ];
    const quickActions = [];

    if (entry.type.startsWith("outgoing")) {
      metadataItems.push(
        { label: "Destination", value: entry.destination_url || "Not configured" },
        { label: "Method", value: entry.http_method || "POST" },
        { label: "Auth", value: titleCase(entry.auth_type || "none") }
      );

      if (entry.type === "outgoing_scheduled") {
        metadataItems.push({ label: "Send time", value: entry.scheduled_time || "Not set" });
        metadataItems.push({ label: "Delivery policy", value: entry.repeat_enabled ? "Repeats daily" : "One-time send, auto-disable after delivery" });
      }

      if (entry.type === "outgoing_continuous") {
        metadataItems.push({
          label: "Delivery policy",
          value: entry.repeat_enabled
            ? `Repeats every ${formatIntervalMinutes(entry.repeat_interval_minutes)}`
            : "One-time send, auto-disable after delivery"
        });
      }

      quickActions.push(
        {
          id: `${sectionIdPrefix}-copy-destination-${entry.id}`,
          label: "Copy destination",
          action: "copy-entry-value",
          value: entry.destination_url || "",
          valueLabel: "Destination URL"
        },
        {
          id: `${sectionIdPrefix}-open-outgoing-${entry.id}`,
          label: "Open outgoing",
          href: resolvePageHref("/ui/apis/outgoing.html")
        }
      );
    } else if (entry.type === "webhook") {
      metadataItems.push(
        { label: "Callback path", value: entry.callback_path || "Not configured" },
        { label: "Signature header", value: entry.signature_header || "Not configured" },
        { label: "Event filter", value: entry.event_filter || "All events" }
      );

      quickActions.push(
        {
          id: `${sectionIdPrefix}-copy-callback-${entry.id}`,
          label: "Copy callback",
          action: "copy-entry-value",
          value: entry.callback_path || "",
          valueLabel: "Callback path"
        },
        {
          id: `${sectionIdPrefix}-open-webhooks-${entry.id}`,
          label: "Open webhooks",
          href: resolvePageHref("/ui/apis/webhooks.html")
        }
      );
    } else {
      metadataItems.push(
        { label: "Endpoint", value: entry.endpoint_path || `/api/v1/inbound/${entry.id}` },
        { label: "Last received", value: formatDateTime(entry.last_received_at) },
        { label: "Recent result", value: entry.last_delivery_status || "No deliveries" }
      );

      quickActions.push(
        {
          id: `${sectionIdPrefix}-copy-endpoint-${entry.id}`,
          label: "Copy endpoint",
          action: "copy-entry-value",
          value: entry.endpoint_url || buildEndpointUrl(entry.id),
          valueLabel: "Endpoint URL"
        },
        {
          id: `${sectionIdPrefix}-open-incoming-${entry.id}`,
          label: "Open incoming",
          href: resolvePageHref("/ui/apis/incoming.html")
        }
      );
    }

    const card = document.createElement("article");
    card.id = `${sectionIdPrefix}-card-${entry.id}`;
    card.className = "resource-card";
    card.innerHTML = `
      <div id="${sectionIdPrefix}-header-${entry.id}" class="resource-card__header">
        <div id="${sectionIdPrefix}-copy-${entry.id}">
          <h4 id="${sectionIdPrefix}-title-${entry.id}" class="resource-card__title">${escapeHtml(entry.name)}</h4>
          <p id="${sectionIdPrefix}-description-${entry.id}" class="resource-card__description">${escapeHtml(entry.description || "No description provided.")}</p>
        </div>
        <span id="${sectionIdPrefix}-status-${entry.id}" class="status-badge ${getEntryStatusTone(entry)}">${escapeHtml(getEntryStatusLabel(entry))}</span>
      </div>
      <div id="${sectionIdPrefix}-signals-${entry.id}" class="resource-card__signal-row">
        ${signalItems.map((item, signalIndex) => `
          <span id="${sectionIdPrefix}-signal-${signalIndex}-${entry.id}" class="resource-card__signal">${escapeHtml(item)}</span>
        `).join("")}
      </div>
      <div id="${sectionIdPrefix}-meta-${entry.id}" class="resource-card__meta">
        ${metadataItems.map((item, metaIndex) => `
          <div id="${sectionIdPrefix}-meta-${metaIndex}-${entry.id}" class="resource-card__meta-item">
            <span id="${sectionIdPrefix}-meta-label-${metaIndex}-${entry.id}" class="resource-card__meta-label">${escapeHtml(item.label)}</span>
            <span id="${sectionIdPrefix}-meta-value-${metaIndex}-${entry.id}" class="resource-card__meta-value">${escapeHtml(item.value)}</span>
          </div>
        `).join("")}
      </div>
      <div id="${sectionIdPrefix}-actions-${entry.id}" class="resource-card__actions">
        ${quickActions.map((action, actionIndex) => action.href
          ? `<a id="${action.id}" class="button button--secondary secondary-action-button resource-card__action resource-card__action-link" href="${escapeHtml(action.href)}">${escapeHtml(action.label)}</a>`
          : `<button type="button" id="${action.id}" class="button button--secondary secondary-action-button resource-card__action" data-resource-action="${escapeHtml(action.action)}" data-resource-value="${escapeHtml(action.value)}" data-resource-label="${escapeHtml(action.valueLabel)}" data-resource-entry-id="${escapeHtml(entry.id)}">${escapeHtml(action.label)}</button>`
        ).join("")}
      </div>
    `;
    fragment.appendChild(card);
  });

  container.appendChild(fragment);
};

const renderOutgoingRegistryList = (container, emptyState, entries, sectionIdPrefix) => {
  if (!container || !emptyState) {
    return;
  }

  container.textContent = "";
  emptyState.hidden = entries.length > 0;

  if (entries.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  entries.forEach((entry) => {
    const row = document.createElement("article");
    row.id = `${sectionIdPrefix}-row-${entry.id}`;
    row.className = "apis-outgoing-list__row";
    row.tabIndex = 0;
    row.dataset.outgoingId = entry.id;
    row.dataset.outgoingType = entry.type;
    row.setAttribute("role", "button");
    row.setAttribute("aria-pressed", String(apiState.selectedOutgoingApiId === entry.id));
    if (apiState.selectedOutgoingApiId === entry.id) {
      row.classList.add("apis-outgoing-list__row--selected");
    }
    row.innerHTML = `
      <div id="${sectionIdPrefix}-name-cell-${entry.id}" class="apis-outgoing-list__cell apis-outgoing-list__cell--name">
        <div id="${sectionIdPrefix}-name-stack-${entry.id}" class="apis-outgoing-list__name-stack">
          <span id="${sectionIdPrefix}-name-${entry.id}" class="apis-outgoing-list__name">${escapeHtml(entry.name)}</span>
          <span id="${sectionIdPrefix}-type-${entry.id}" class="apis-outgoing-list__type">${escapeHtml(entry.type === "outgoing_scheduled" ? "Scheduled" : "Continuous")}</span>
        </div>
        <span id="${sectionIdPrefix}-status-${entry.id}" class="status-badge ${getOutgoingRegistryStatusTone(entry)}">${escapeHtml(getOutgoingRegistryStatusLabel(entry))}</span>
      </div>
      <div id="${sectionIdPrefix}-last-fired-cell-${entry.id}" class="apis-outgoing-list__cell">
        <span id="${sectionIdPrefix}-last-fired-label-${entry.id}" class="apis-outgoing-list__label">Last fired</span>
        <span id="${sectionIdPrefix}-last-fired-value-${entry.id}" class="apis-outgoing-list__value">${escapeHtml(formatDateTime(getEntryLastActivity(entry)))}</span>
      </div>
      <div id="${sectionIdPrefix}-send-time-cell-${entry.id}" class="apis-outgoing-list__cell">
        <span id="${sectionIdPrefix}-send-time-label-${entry.id}" class="apis-outgoing-list__label">Send time</span>
        <span id="${sectionIdPrefix}-send-time-value-${entry.id}" class="apis-outgoing-list__value">${escapeHtml(formatOutgoingSendTime(entry))}</span>
      </div>
      <div id="${sectionIdPrefix}-url-cell-${entry.id}" class="apis-outgoing-list__cell apis-outgoing-list__cell--url">
        <span id="${sectionIdPrefix}-url-label-${entry.id}" class="apis-outgoing-list__label">URL</span>
        <span id="${sectionIdPrefix}-url-value-${entry.id}" class="apis-outgoing-list__value apis-outgoing-list__value--url">${escapeHtml(entry.destination_url || "Not configured")}</span>
      </div>
    `;

    row.addEventListener("click", () => {
      loadOutgoingEditDetail(entry.id, entry.type, row).catch((error) => {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        setAlert(errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "outgoing_api_detail_load_failed",
          message: "Failed to load outgoing API detail.",
          details: {
            apiId: entry.id,
            type: entry.type,
            error: errorMessage,
            stack: errorStack
          }
        });
      });
    });

    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        row.click();
      }
    });

    fragment.appendChild(row);
  });

  container.appendChild(fragment);
};

const syncOverviewLandingSummary = ({
  incomingEntries,
  scheduledEntries,
  continuousEntries,
  webhookEntries
}) => {
  if (!hasOverviewLandingElements()) {
    return;
  }

  const totalCount = incomingEntries.length + scheduledEntries.length + continuousEntries.length + webhookEntries.length;
  const activeScheduledCalls = scheduledEntries.filter((entry) => getScheduledStatus(entry) === "active").length;
  const scheduledRepeatsPerHour = scheduledEntries
    .filter((entry) => getScheduledStatus(entry) === "active" && entry.repeat_enabled)
    .length / 24;
  const continuousRepeatsPerHour = continuousEntries
    .filter((entry) => entry.enabled && entry.repeat_enabled && entry.repeat_interval_minutes)
    .reduce((sum, entry) => sum + (60 / entry.repeat_interval_minutes), 0);
  const monitoredWebhooks = webhookEntries.filter((entry) => entry.enabled).length;
  const callsPerHour = scheduledRepeatsPerHour + continuousRepeatsPerHour;
  const callsPerDay = callsPerHour * 24;

  apiElements.overviewTotalCount.textContent = `${totalCount} configured APIs`;
  apiElements.overviewHelper.textContent = totalCount > 0
    ? "Across all configured API registries."
    : "Create an API to add it to the registry.";
  apiElements.overviewScheduledActiveCount.textContent = String(activeScheduledCalls);
  apiElements.overviewCallsPerHour.textContent = formatRate(callsPerHour);
  apiElements.overviewCallsPerDay.textContent = formatRate(callsPerDay);
  apiElements.overviewMonitoredWebhooksCount.textContent = String(monitoredWebhooks);
};

const loadOverviewLanding = async () => {
  if (!hasOverviewLandingElements()) {
    return;
  }

  const [incomingEntries, scheduledEntries, continuousEntries, webhookEntries] = await Promise.all([
    backendApi.list(),
    backendApi.listOutgoingScheduled(),
    backendApi.listOutgoingContinuous(),
    backendApi.listWebhooks()
  ]);

  const sortedScheduledEntries = [...scheduledEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedContinuousEntries = [...continuousEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedWebhookEntries = [...webhookEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));

  syncOverviewLandingSummary({
    incomingEntries,
    scheduledEntries: sortedScheduledEntries,
    continuousEntries: sortedContinuousEntries,
    webhookEntries: sortedWebhookEntries
  });
  renderResourceList(
    apiElements.overviewIncomingList,
    apiElements.overviewIncomingEmpty,
    incomingEntries,
    "apis-overview-incoming-list"
  );
  renderResourceList(
    apiElements.overviewOutgoingList,
    apiElements.overviewOutgoingEmpty,
    [...sortedScheduledEntries, ...sortedContinuousEntries],
    "apis-overview-outgoing-list"
  );
  renderResourceList(
    apiElements.overviewWebhooksList,
    apiElements.overviewWebhooksEmpty,
    sortedWebhookEntries,
    "apis-overview-webhooks-list"
  );
  setAlert("", "info");
};

const loadOutgoingRegistries = async () => {
  if (!hasOutgoingRegistryElements()) {
    return;
  }

  const [scheduledEntries, continuousEntries] = await Promise.all([
    backendApi.listOutgoingScheduled(),
    backendApi.listOutgoingContinuous()
  ]);
  apiState.outgoingEntries = [...scheduledEntries, ...continuousEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  if (apiState.selectedOutgoingApiId && !apiState.outgoingEntries.some((entry) => entry.id === apiState.selectedOutgoingApiId)) {
    apiState.selectedOutgoingApiId = null;
  }
  renderOutgoingRegistryList(apiElements.outgoingList, apiElements.outgoingListEmpty, apiState.outgoingEntries, "apis-outgoing-list");
};

const loadWebhookRegistry = async () => {
  if (!hasWebhookRegistryElements()) {
    return;
  }

  apiState.webhookEntries = await backendApi.listWebhooks();
  renderResourceList(apiElements.webhooksList, apiElements.webhooksListEmpty, apiState.webhookEntries, "apis-webhooks-list");
};

const bindLogControls = () => {
  if (!hasOverviewElements()) {
    return;
  }

  const rerenderLogs = () => renderLogs(apiState.detailEvents);

  apiElements.logsSearchInput.addEventListener("input", () => {
    apiState.detailLogFilters.search = apiElements.logsSearchInput.value || "";
    rerenderLogs();
  });

  apiElements.logsStatusFilter.addEventListener("change", () => {
    apiState.detailLogFilters.status = apiElements.logsStatusFilter.value || "all";
    rerenderLogs();
  });

  apiElements.logsSourceFilter.addEventListener("change", () => {
    apiState.detailLogFilters.source = apiElements.logsSourceFilter.value || "all";
    rerenderLogs();
  });

  apiElements.logsSortInput.addEventListener("change", () => {
    apiState.detailLogFilters.sort = apiElements.logsSortInput.value || "newest";
    rerenderLogs();
  });

  apiElements.logsResetButton.addEventListener("click", () => {
    apiState.detailLogFilters = {
      search: "",
      status: "all",
      source: "all",
      sort: "newest"
    };
    apiElements.logsSearchInput.value = "";
    apiElements.logsStatusFilter.value = "all";
    apiElements.logsSourceFilter.value = "all";
    apiElements.logsSortInput.value = "newest";
    rerenderLogs();
  });

  apiElements.logList.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-copy-log]");

    if (!(trigger instanceof HTMLElement)) {
      return;
    }

    const copyTarget = trigger.dataset.copyLog;
    const eventId = trigger.dataset.eventId;
    const eventItem = apiState.detailEvents.find((entry) => entry.event_id === eventId);

    if (!eventItem) {
      return;
    }

    const textToCopy = copyTarget === "headers"
      ? stringifyPreviewValue(eventItem.request_headers_subset)
      : stringifyPreviewValue(eventItem.payload_json);

    try {
      await navigator.clipboard.writeText(textToCopy);
      setAlert(`${copyTarget === "headers" ? "Headers" : "Payload"} copied for ${eventId}.`, "success");
      emitApiLog({
        action: "inbound_log_payload_copied",
        message: `Copied ${copyTarget} from inbound API log ${eventId}.`,
        details: {
          apiId: apiState.selectedApiId,
          eventId,
          target: copyTarget
        }
      });
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      setAlert(`Unable to copy ${copyTarget}.`, "error");
      emitApiLog({
        level: "error",
        action: "inbound_log_copy_failed",
        message: `Failed to copy ${copyTarget} from an inbound API log.`,
        details: {
          apiId: apiState.selectedApiId,
          eventId,
          target: copyTarget,
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  });
};

const bindResourceCardActions = () => {
  document.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-resource-action]");

    if (!(trigger instanceof HTMLElement)) {
      return;
    }

    const action = trigger.dataset.resourceAction || "";

    if (action !== "copy-entry-value") {
      return;
    }

    const value = trigger.dataset.resourceValue || "";
    const label = trigger.dataset.resourceLabel || "Value";
    const entryId = trigger.dataset.resourceEntryId || "";

    if (!value) {
      setAlert(`${label} is not available for this record.`, "error");
      return;
    }

    try {
      await navigator.clipboard.writeText(value);
      setAlert(`${label} copied for ${entryId}.`, "success");
      emitApiLog({
        action: "resource_value_copied",
        message: `Copied ${label.toLowerCase()} for API resource ${entryId}.`,
        details: {
          entryId,
          label,
          page: window.location.pathname
        }
      });
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      setAlert(`Unable to copy ${label}.`, "error");
      emitApiLog({
        level: "error",
        action: "resource_value_copy_failed",
        message: `Failed to copy ${label.toLowerCase()} for API resource ${entryId}.`,
        details: {
          entryId,
          label,
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  });
};

const bindDetailActions = () => {
  if (!hasOverviewElements()) {
    return;
  }

  apiElements.rotateSecretButton.addEventListener("click", async () => {
    if (!apiState.selectedApiId) {
      return;
    }

    try {
      const rotated = await backendApi.rotateSecret(apiState.selectedApiId);
      apiState.lastSecretByApiId[apiState.selectedApiId] = rotated.secret;
      await loadApiDirectory();
      await loadApiDetail(apiState.selectedApiId);
      setAlert("Bearer secret rotated. Update external callers to use the new token.", "success");
      emitApiLog({
        action: "inbound_api_secret_rotated",
        message: "Rotated inbound API bearer secret.",
        details: {
          apiId: apiState.selectedApiId
        }
      });
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Failed to rotate inbound API bearer secret", error);
      setAlert(errorMessage, "error");
      emitApiLog({
        level: "error",
        action: "inbound_api_secret_rotate_failed",
        message: "Failed to rotate inbound API bearer secret.",
        details: {
          apiId: apiState.selectedApiId,
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  });

  apiElements.toggleStatusButton.addEventListener("click", async () => {
    const entry = apiState.entries.find((item) => item.id === apiState.selectedApiId);

    if (!entry) {
      return;
    }

    try {
      await backendApi.update(entry.id, { enabled: !entry.enabled });
      await loadApiDirectory();
      await loadApiDetail(entry.id);
      setAlert(entry.enabled ? "Inbound API disabled." : "Inbound API enabled.", "success");
      emitApiLog({
        action: entry.enabled ? "inbound_api_disabled" : "inbound_api_enabled",
        message: `${entry.enabled ? "Disabled" : "Enabled"} inbound API "${entry.name}".`,
        details: {
          apiId: entry.id,
          enabled: !entry.enabled
        }
      });
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Failed to update inbound API status", error);
      setAlert(errorMessage, "error");
      emitApiLog({
        level: "error",
        action: "inbound_api_toggle_failed",
        message: "Failed to update inbound API status.",
        details: {
          apiId: entry.id,
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  });
};

const initModalMarkup = async () => {
  if (!hasCreateModalElements()) {
    return;
  }

  try {
    if (!createApiModalMarkup.trim()) {
      throw new Error("Create API modal template is empty.");
    }

    apiElements.createModalContent.innerHTML = createApiModalMarkup;
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Failed to load create API modal template", error);
    emitApiLog({
      level: "error",
      action: "modal_template_load_failed",
      message: "Unable to load create API modal template.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
    apiElements.createModalContent.innerHTML = modalFallbackMarkup;
  }

  bindCreateForm();
};

const initOutgoingEditModalMarkup = async () => {
  if (!hasOutgoingEditModalElements()) {
    return;
  }

  try {
    if (!outgoingApiEditModalMarkup.trim()) {
      throw new Error("Outgoing API edit modal template is empty.");
    }

    apiElements.outgoingEditModalContent.innerHTML = outgoingApiEditModalMarkup;
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Failed to load outgoing API edit modal template", error);
    emitApiLog({
      level: "error",
      action: "outgoing_edit_modal_template_load_failed",
      message: "Unable to load outgoing API edit modal template.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
    apiElements.outgoingEditModalContent.innerHTML = outgoingEditModalFallbackMarkup;
  }

  bindOutgoingEditForm();
};

const initCreateModal = async () => {
  bindModalEvents();

  if (!hasCreateModalElements()) {
    return;
  }

  ensureCreateTypeModal();
  await initModalMarkup();
  setCreateModalType(apiState.createModalType);
};

const initOutgoingEditModal = async () => {
  if (!hasOutgoingEditModalElements()) {
    return;
  }

  await initOutgoingEditModalMarkup();
};

const initApiOverview = async () => {
  if (!hasOverviewElements()) {
    return;
  }

  bindLogControls();
  bindDetailActions();

  try {
    await loadApiDirectory();
    setAlert(
      developerModeEnabled() ? "Developer mode is enabled. Database-backed sample endpoints are included." : "",
      "info"
    );
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Unable to load inbound APIs", error);
    setAlert("Unable to load inbound APIs. Start the FastAPI service and refresh the page.", "error");
    renderDetail(null);
    emitApiLog({
      level: "error",
      action: "inbound_api_load_failed",
      message: "Unable to load inbound APIs from the backend.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
  }
};

const initOutgoingRegistry = async () => {
  if (!hasOutgoingRegistryElements()) {
    return;
  }

  try {
    await loadOutgoingRegistries();
    setAlert("", "info");
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Unable to load outgoing APIs", error);
    emitApiLog({
      level: "error",
      action: "outgoing_api_load_failed",
      message: "Unable to load outgoing APIs from the backend.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
    setAlert("Unable to load outgoing APIs. Start the FastAPI service and refresh the page.", "error");
  }
};

const initWebhookRegistry = async () => {
  if (!hasWebhookRegistryElements()) {
    return;
  }

  try {
    await loadWebhookRegistry();
    setAlert("", "info");
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Unable to load webhooks", error);
    emitApiLog({
      level: "error",
      action: "webhook_load_failed",
      message: "Unable to load webhooks from the backend.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
    setAlert("Unable to load webhooks. Start the FastAPI service and refresh the page.", "error");
  }
};

const initAutomationPage = async () => {
  if (!isAutomationPage()) {
    return;
  }

  try {
    if (!hasCreateModalElements() || !hasAutomationPlaceholderElements()) {
      throw new Error("Automation page modal hosts are missing.");
    }

    setAutomationAlert("", "info");

    if (window.location.hash === "#create-automation-placeholder") {
      apiState.createTypeReturnFocusElement = getCreateOpenButton();
      openAutomationPlaceholderModal();
    }
  } catch (error) {
    const { message: errorMessage, stack: errorStack } = normalizeError(error);
    console.error("Unable to initialize automation page", error);
    setAutomationAlert(errorMessage, "error");
    emitApiLog({
      level: "error",
      action: "automation_page_init_failed",
      message: "Unable to initialize automation page.",
      details: {
        error: errorMessage,
        stack: errorStack
      }
    });
  }
};

const initApiPage = async () => {
  bindResourceCardActions();
  await initCreateModal();
  await initOutgoingEditModal();
  bindApiTooltips();
  if (hasOverviewLandingElements()) {
    try {
      await loadOverviewLanding();
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Unable to load API overview", error);
      setAlert("Unable to load API overview. Start the FastAPI service and refresh the page.", "error");
      emitApiLog({
        level: "error",
        action: "api_overview_load_failed",
        message: "Unable to load API overview registries from the backend.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  }
  await initApiOverview();
  await initOutgoingRegistry();
  await initWebhookRegistry();
  await initAutomationPage();
};

initApiPage();
