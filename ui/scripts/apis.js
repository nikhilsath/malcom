const apiElements = {
  createModal: document.getElementById("apis-create-modal"),
  createModalContent: document.getElementById("apis-create-modal-content"),
  detailModal: document.getElementById("api-detail-modal"),
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
  logsEmpty: document.getElementById("api-logs-empty"),
  logList: document.getElementById("api-log-list"),
  outgoingList: document.getElementById("apis-outgoing-list"),
  outgoingListEmpty: document.getElementById("apis-outgoing-list-empty"),
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

const getCreateTypePopover = () => document.getElementById("apis-create-type-popover");

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
  && apiElements.logsEmpty
  && apiElements.logList
);

const hasOutgoingRegistryElements = () => Boolean(
  apiElements.outgoingList && apiElements.outgoingListEmpty
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
  && apiElements.overviewIncomingList
  && apiElements.overviewIncomingEmpty
  && apiElements.overviewOutgoingList
  && apiElements.overviewOutgoingEmpty
  && apiElements.overviewWebhooksList
  && apiElements.overviewWebhooksEmpty
);

const modalFallbackMarkup = `
  <div class="modal__panel" id="create-api-modal-panel">
    <div class="modal__header" id="create-api-modal-header">
      <div class="modal__header-copy" id="create-api-modal-header-copy">
        <p class="modal__eyebrow" id="create-api-modal-eyebrow">Create</p>
        <h3 class="modal__title" id="apis-create-modal-title">Create API</h3>
        <p class="modal__description" id="create-api-modal-description">Choose the type of API resource you want to create and Malcom will store it in the corresponding backend table.</p>
      </div>
      <button type="button" class="button button--secondary modal__close-button" id="create-api-modal-close" aria-label="Close create API modal" data-modal-close="apis-create-modal">Close</button>
  </div>
  <div class="modal__body modal__body--form" id="create-api-modal-body">
    <form id="create-api-form" class="api-form">
      <input id="create-api-type-input" name="resourceType" type="hidden" value="incoming">
      <div id="create-api-form-grid" class="api-form-grid">
          <label id="create-api-name-field" class="api-form-field">
            <span id="create-api-name-label" class="api-form-label">Name</span>
            <input id="create-api-name-input" class="api-form-input" name="name" type="text" maxlength="80" required>
          </label>
          <label id="create-api-slug-field" class="api-form-field">
            <span id="create-api-slug-label" class="api-form-label">Path slug</span>
            <input id="create-api-slug-input" class="api-form-input" name="pathSlug" type="text" maxlength="80" required>
          </label>
          <label id="create-api-description-field" class="api-form-field api-form-field--full">
            <span id="create-api-description-label" class="api-form-label">Description</span>
            <textarea id="create-api-description-input" class="api-form-textarea" name="description" rows="3"></textarea>
          </label>
          <label id="create-api-auth-field" class="api-form-field">
            <span id="create-api-auth-label" class="api-form-label">Authentication</span>
            <input id="create-api-auth-input" class="api-form-input" name="authTypeSummary" type="text" value="Bearer secret" readonly>
          </label>
          <label id="create-api-enabled-field" class="api-form-field api-form-field--toggle">
            <span id="create-api-enabled-label" class="api-form-label">Enabled on create</span>
            <span id="create-api-enabled-control" class="api-inline-toggle">
              <input id="create-api-enabled-input" name="enabled" type="checkbox" checked>
              <span id="create-api-enabled-copy" class="api-inline-toggle__label">Accept requests immediately</span>
            </span>
          </label>
          <section id="create-api-outgoing-panel" class="api-form-field api-form-field--full" hidden>
            <div id="create-api-outgoing-panel-copy" class="api-form-section-copy">
              <p id="create-api-outgoing-panel-eyebrow" class="api-form-label">Outgoing delivery</p>
              <p id="create-api-outgoing-panel-description" class="api-form-section-description">Configure the request Malcom should send on schedule or as a continuous outbound stream.</p>
            </div>
            <div id="create-api-outgoing-grid" class="api-form-grid">
              <label id="create-api-destination-field" class="api-form-field api-form-field--full">
                <span id="create-api-destination-label" class="api-form-label">Destination URL</span>
                <input id="create-api-destination-input" class="api-form-input" name="destinationUrl" type="url" inputmode="url" placeholder="https://example.com/webhooks/orders">
              </label>
              <label id="create-api-method-field" class="api-form-field">
                <span id="create-api-method-label" class="api-form-label">HTTP method</span>
                <select id="create-api-method-input" class="api-form-input" name="httpMethod">
                  <option value="POST" selected>POST</option>
                  <option value="PUT">PUT</option>
                  <option value="PATCH">PATCH</option>
                  <option value="DELETE">DELETE</option>
                  <option value="GET">GET</option>
                </select>
              </label>
              <label id="create-api-scheduled-time-field" class="api-form-field" hidden>
                <span id="create-api-scheduled-time-label" class="api-form-label">Send time</span>
                <input id="create-api-scheduled-time-input" class="api-form-input" name="scheduledTime" type="time" value="09:00">
              </label>
              <label id="create-api-scheduled-repeat-field" class="api-form-field api-form-field--toggle" hidden>
                <span id="create-api-scheduled-repeat-label" class="api-form-label">Repeat daily</span>
                <span id="create-api-scheduled-repeat-control" class="api-inline-toggle">
                  <input id="create-api-scheduled-repeat-input" name="repeatEnabledScheduled" type="checkbox">
                  <span id="create-api-scheduled-repeat-copy" class="api-inline-toggle__label">Send once, then disable automatically after delivery</span>
                </span>
              </label>
              <label id="create-api-continuous-repeat-field" class="api-form-field api-form-field--toggle" hidden>
                <span id="create-api-continuous-repeat-label" class="api-form-label">Repeat continuously</span>
                <span id="create-api-continuous-repeat-control" class="api-inline-toggle">
                  <input id="create-api-continuous-repeat-input" name="repeatEnabledContinuous" type="checkbox">
                  <span id="create-api-continuous-repeat-copy" class="api-inline-toggle__label">Send once, then disable automatically after delivery</span>
                </span>
              </label>
              <label id="create-api-continuous-interval-value-field" class="api-form-field" hidden>
                <span id="create-api-continuous-interval-value-label" class="api-form-label">Repeat every</span>
                <input id="create-api-continuous-interval-value-input" class="api-form-input" name="repeatIntervalValue" type="number" min="1" max="168" step="1" value="5">
              </label>
              <label id="create-api-continuous-interval-unit-field" class="api-form-field" hidden>
                <span id="create-api-continuous-interval-unit-label" class="api-form-label">Interval unit</span>
                <select id="create-api-continuous-interval-unit-input" class="api-form-input" name="repeatIntervalUnit">
                  <option value="minutes" selected>Minutes</option>
                  <option value="hours">Hours</option>
                </select>
              </label>
              <label id="create-api-outgoing-auth-type-field" class="api-form-field">
                <span id="create-api-outgoing-auth-type-label" class="api-form-label">Destination auth</span>
                <select id="create-api-outgoing-auth-type-input" class="api-form-input" name="outgoingAuthType">
                  <option value="none" selected>None</option>
                  <option value="bearer">Bearer token</option>
                  <option value="basic">Basic auth</option>
                  <option value="header">Custom header</option>
                </select>
              </label>
              <label id="create-api-auth-token-field" class="api-form-field api-form-field--full" hidden>
                <span id="create-api-auth-token-label" class="api-form-label">Bearer token</span>
                <input id="create-api-auth-token-input" class="api-form-input" name="authToken" type="password" autocomplete="off">
              </label>
              <label id="create-api-auth-username-field" class="api-form-field" hidden>
                <span id="create-api-auth-username-label" class="api-form-label">Username</span>
                <input id="create-api-auth-username-input" class="api-form-input" name="authUsername" type="text" autocomplete="off">
              </label>
              <label id="create-api-auth-password-field" class="api-form-field" hidden>
                <span id="create-api-auth-password-label" class="api-form-label">Password</span>
                <input id="create-api-auth-password-input" class="api-form-input" name="authPassword" type="password" autocomplete="off">
              </label>
              <label id="create-api-auth-header-name-field" class="api-form-field" hidden>
                <span id="create-api-auth-header-name-label" class="api-form-label">Header name</span>
                <input id="create-api-auth-header-name-input" class="api-form-input" name="authHeaderName" type="text" autocomplete="off" placeholder="X-API-Key">
              </label>
              <label id="create-api-auth-header-value-field" class="api-form-field" hidden>
                <span id="create-api-auth-header-value-label" class="api-form-label">Header value</span>
                <input id="create-api-auth-header-value-input" class="api-form-input" name="authHeaderValue" type="password" autocomplete="off">
              </label>
              <label id="create-api-payload-field" class="api-form-field api-form-field--full">
                <span id="create-api-payload-label" class="api-form-label">Payload template</span>
                <textarea id="create-api-payload-input" class="api-form-textarea" name="payloadTemplate" rows="8" spellcheck="false">{ "event": "scheduled.delivery", "sent_at": "{{timestamp}}" }</textarea>
              </label>
              <div id="create-api-test-actions-field" class="api-form-field api-form-field--full">
                <div id="create-api-test-actions" class="api-form-actions">
                  <button type="button" id="create-api-test-button" class="button button--secondary secondary-action-button">Send test payload</button>
                </div>
                <div id="create-api-test-feedback" class="api-form-feedback" aria-live="polite"></div>
              </div>
            </div>
          </section>
        </div>
        <div id="create-api-form-feedback" class="api-form-feedback" aria-live="polite"></div>
        <div id="create-api-form-actions" class="api-form-actions">
          <button type="submit" id="create-api-submit-button" class="button button--primary primary-action-button">Create inbound API</button>
        </div>
      </form>
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
  createTypeReturnFocusElement: null
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

const createTypeOptions = [
  {
    id: "incoming",
    buttonId: "apis-create-type-option-incoming",
    title: "Incoming",
    description: "Provision an authenticated inbound endpoint."
  },
  {
    id: "outgoing_scheduled",
    buttonId: "apis-create-type-option-outgoing-scheduled",
    title: "Outgoing scheduled",
    description: "Configure a timed outbound delivery."
  },
  {
    id: "outgoing_continuous",
    buttonId: "apis-create-type-option-outgoing-continuous",
    title: "Outgoing continuous",
    description: "Keep a continuous outbound stream ready."
  },
  {
    id: "webhook",
    buttonId: "apis-create-type-option-webhook",
    title: "Webhook",
    description: "Register a webhook callback definition."
  }
];

const sanitizeSlug = (value) => value
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9-]+/g, "-")
  .replace(/-{2,}/g, "-")
  .replace(/^-|-$/g, "");

const isOutgoingType = (type) => type === "outgoing_scheduled" || type === "outgoing_continuous";

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

const buildEndpointUrl = (apiId) => `${window.getBaseUrl()}/api/v1/inbound/${apiId}`;

const buildSampleCurl = (apiId, secret) => {
  const endpoint = buildEndpointUrl(apiId);
  const jsonPayload = JSON.stringify({ hello: "world" }, null, 2);

  return `curl -X POST "${endpoint}" \\
  -H "Authorization: Bearer ${secret}" \\
  -H "Content-Type: application/json" \\
  -d '${jsonPayload}'`;
};

const backendApi = {
  async list() {
    return window.Malcom?.requestJson?.("/api/v1/inbound");
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
    return window.Malcom?.requestJson?.("/api/v1/outgoing/scheduled");
  },
  async listOutgoingContinuous() {
    return window.Malcom?.requestJson?.("/api/v1/outgoing/continuous");
  },
  async listWebhooks() {
    return window.Malcom?.requestJson?.("/api/v1/webhooks");
  }
};

const syncSummary = () => {
  if (!hasOverviewElements()) {
    return;
  }
};

const closeOverviewTooltips = () => {
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

const bindOverviewTooltips = () => {
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
      closeOverviewTooltips();
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
      closeOverviewTooltips();
      return;
    }

    if (!target.closest(".api-tooltip-toggle") && !target.closest(".api-tooltip-content")) {
      closeOverviewTooltips();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeOverviewTooltips();
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

const renderLogs = (events) => {
  if (!hasOverviewElements()) {
    return;
  }

  apiElements.logList.textContent = "";
  apiElements.logsEmpty.hidden = events.length > 0;

  if (events.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  events.forEach((eventItem) => {
    const card = document.createElement("article");
    card.id = `api-log-card-${eventItem.event_id}`;
    card.className = "api-log-card";
    const payloadPreview = JSON.stringify(eventItem.payload_json, null, 2);
    const headersPreview = JSON.stringify(eventItem.request_headers_subset, null, 2);

    card.innerHTML = `
      <div id="api-log-header-${eventItem.event_id}" class="api-log-card__header">
        <div id="api-log-header-copy-${eventItem.event_id}" class="api-log-card__header-copy">
          <h5 id="api-log-title-${eventItem.event_id}" class="api-log-card__title">${escapeHtml(eventItem.event_id)}</h5>
          <p id="api-log-meta-${eventItem.event_id}" class="api-log-card__meta">${escapeHtml(formatDateTime(eventItem.received_at))} • ${escapeHtml(eventItem.source_ip || "Unknown source")}</p>
        </div>
        <span id="api-log-status-${eventItem.event_id}" class="status-badge ${eventItem.status === "accepted" ? "status-badge--success" : "status-badge--warning"}">${escapeHtml(eventItem.status)}</span>
      </div>
      <div id="api-log-grid-${eventItem.event_id}" class="api-log-card__grid">
        <div id="api-log-headers-panel-${eventItem.event_id}" class="api-log-card__panel">
          <p id="api-log-headers-label-${eventItem.event_id}" class="api-log-card__label">Headers</p>
          <pre id="api-log-headers-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(headersPreview)}</pre>
        </div>
        <div id="api-log-payload-panel-${eventItem.event_id}" class="api-log-card__panel">
          <p id="api-log-payload-label-${eventItem.event_id}" class="api-log-card__label">Payload</p>
          <pre id="api-log-payload-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(payloadPreview)}</pre>
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

  if (!entry) {
    setDetailState(false);
    return;
  }

  setDetailState(true);
  apiElements.detailTitle.textContent = entry.name;
  apiElements.detailDescription.textContent = entry.description || "No description provided.";
  apiElements.toggleStatusButton.textContent = entry.enabled ? "Disable endpoint" : "Enable endpoint";
  renderMetadata(entry);
  renderSecretPanel(entry);
  renderLogs(entry.events || []);
};

const loadApiDirectory = async () => {
  if (!hasOverviewElements()) {
    return;
  }

  apiState.entries = await backendApi.list();
  if (apiState.selectedApiId && !apiState.entries.some((entry) => entry.id === apiState.selectedApiId)) {
    apiState.selectedApiId = null;
  }

  syncSummary();
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
  const detail = await backendApi.detail(apiId);
  renderDetail(detail);

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

const ensureCreateTypePopover = () => {
  const createOpenButton = getCreateOpenButton();

  if (!createOpenButton || getCreateTypePopover()) {
    return getCreateTypePopover();
  }

  const footer = createOpenButton.closest(".sidenav__footer");

  if (!footer) {
    return null;
  }

  const popover = document.createElement("div");
  popover.id = "apis-create-type-popover";
  popover.className = "api-create-popover";
  popover.hidden = true;
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-modal", "false");
  popover.setAttribute("aria-labelledby", "apis-create-type-popover-title");
  popover.setAttribute("aria-describedby", "apis-create-type-popover-description");

  const title = document.createElement("p");
  title.id = "apis-create-type-popover-title";
  title.className = "api-create-popover__title";
  title.textContent = "Create API";

  const description = document.createElement("p");
  description.id = "apis-create-type-popover-description";
  description.className = "api-create-popover__description";
  description.textContent = "Choose a type to open the full create form.";

  const optionList = document.createElement("div");
  optionList.id = "apis-create-type-popover-options";
  optionList.className = "api-create-popover__options";

  createTypeOptions.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = option.buttonId;
    button.className = "api-create-popover__option";
    button.dataset.apiType = option.id;
    button.innerHTML = `
      <span id="${option.buttonId}-title" class="api-create-popover__option-title">${escapeHtml(option.title)}</span>
      <span id="${option.buttonId}-description" class="api-create-popover__option-description">${escapeHtml(option.description)}</span>
    `;
    optionList.appendChild(button);
  });

  popover.append(title, description, optionList);
  footer.appendChild(popover);
  return popover;
};

const openCreateTypePopover = () => {
  const popover = ensureCreateTypePopover();

  if (!popover) {
    openCreateModal("incoming");
    return;
  }

  apiState.createTypeReturnFocusElement = getCreateOpenButton();
  popover.hidden = false;
  popover.classList.add("api-create-popover--open");
  syncCreateTypeTriggerState(true);
  const firstOption = popover.querySelector(".api-create-popover__option");

  if (firstOption instanceof HTMLElement) {
    firstOption.focus();
  }
};

const closeCreateTypePopover = ({ restoreFocus = true } = {}) => {
  const popover = getCreateTypePopover();

  if (!popover) {
    return;
  }

  popover.hidden = true;
  popover.classList.remove("api-create-popover--open");
  syncCreateTypeTriggerState(false);

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

  setCreateModalType(selectedType);
  apiElements.createModal.classList.add("modal--open");
  apiElements.createModal.setAttribute("aria-hidden", "false");
  syncModalBodyState();
};

const closeCreateModal = () => {
  if (!apiElements.createModal) {
    return;
  }

  apiElements.createModal.classList.remove("modal--open");
  apiElements.createModal.setAttribute("aria-hidden", "true");
  syncModalBodyState();

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

const bindModalEvents = () => {
  if (hasCreateModalElements()) {
    document.addEventListener("click", (event) => {
      const openTarget = event.target.closest("#apis-create-button");

      if (openTarget) {
        event.preventDefault();

        if (getCreateTypePopover()?.hidden === false) {
          closeCreateTypePopover();
          return;
        }

        openCreateTypePopover();
        return;
      }

      const typeTarget = event.target.closest(".api-create-popover__option");

      if (typeTarget instanceof HTMLElement) {
        const selectedType = typeTarget.dataset.apiType || "incoming";
        apiState.createTypeReturnFocusElement = getCreateOpenButton();
        closeCreateTypePopover({ restoreFocus: false });
        openCreateModal(selectedType);
        return;
      }

      if (
        getCreateTypePopover()?.hidden === false
        && !event.target.closest("#apis-create-type-popover")
      ) {
        closeCreateTypePopover({ restoreFocus: false });
      }
    });

    apiElements.createModal.addEventListener("click", (event) => {
      const closeTarget = event.target.closest("[data-modal-close]");

      if (closeTarget) {
        closeCreateModal();
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

  if (!hasCreateModalElements() && !apiElements.detailModal) {
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

    if (apiElements.createModal?.classList.contains("modal--open")) {
      closeCreateModal();
      return;
    }

    if (getCreateTypePopover()?.hidden === false) {
      closeCreateTypePopover();
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

  const validateDraft = (draft, { requireName = true } = {}) => {
    if (requireName && (!draft.name || !draft.path_slug)) {
      return "Name and path slug are required.";
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
    setFormMessage(testFeedback, "", "info");
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
    } catch (error) {
      const { message: errorMessage } = normalizeError(error);
      setFormMessage(testFeedback, errorMessage, "error");
    } finally {
      testButton.disabled = false;
    }
  });

  syncOutgoingAuthFields();
  syncCreateModalType(getSelectedType());
  syncContinuousIntervalConstraints();
  syncOutgoingRepeatFields();

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

  entries.forEach((entry, index) => {
    const metadataItems = [];

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
    } else {
      metadataItems.push(
        { label: "Type", value: entry.type },
        { label: "Row slug", value: entry.path_slug },
        { label: "Created", value: formatDateTime(entry.created_at) }
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
      <div id="${sectionIdPrefix}-meta-${entry.id}" class="resource-card__meta">
        ${metadataItems.map((item, metaIndex) => `
          <div id="${sectionIdPrefix}-meta-${metaIndex}-${index}" class="resource-card__meta-item">
            <span id="${sectionIdPrefix}-meta-label-${metaIndex}-${index}" class="resource-card__meta-label">${escapeHtml(item.label)}</span>
            <span id="${sectionIdPrefix}-meta-value-${metaIndex}-${index}" class="resource-card__meta-value">${escapeHtml(item.value)}</span>
          </div>
        `).join("")}
      </div>
    `;
    fragment.appendChild(card);
  });

  container.appendChild(fragment);
};

const renderOverviewIncomingList = (entries) => {
  if (!apiElements.overviewIncomingList || !apiElements.overviewIncomingEmpty) {
    return;
  }

  apiElements.overviewIncomingList.textContent = "";
  apiElements.overviewIncomingEmpty.hidden = entries.length > 0;

  if (entries.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  entries.forEach((entry) => {
    const card = document.createElement("article");
    card.id = `apis-overview-incoming-card-${entry.id}`;
    card.className = "resource-card";
    card.innerHTML = `
      <div id="apis-overview-incoming-header-${entry.id}" class="resource-card__header">
        <div id="apis-overview-incoming-copy-${entry.id}">
          <h4 id="apis-overview-incoming-title-${entry.id}" class="resource-card__title">${escapeHtml(entry.name)}</h4>
          <p id="apis-overview-incoming-copy-text-${entry.id}" class="resource-card__description">${escapeHtml(entry.description || "No description provided.")}</p>
        </div>
        <span id="apis-overview-incoming-status-${entry.id}" class="status-badge ${getEntryStatusTone(entry)}">${escapeHtml(getEntryStatusLabel(entry))}</span>
      </div>
      <div id="apis-overview-incoming-meta-${entry.id}" class="resource-card__meta">
        <div id="apis-overview-incoming-meta-endpoint-${entry.id}" class="resource-card__meta-item">
          <span id="apis-overview-incoming-meta-endpoint-label-${entry.id}" class="resource-card__meta-label">Endpoint</span>
          <span id="apis-overview-incoming-meta-endpoint-value-${entry.id}" class="resource-card__meta-value">${escapeHtml(entry.endpoint_path || `/api/v1/inbound/${entry.id}`)}</span>
        </div>
        <div id="apis-overview-incoming-meta-last-received-${entry.id}" class="resource-card__meta-item">
          <span id="apis-overview-incoming-meta-last-received-label-${entry.id}" class="resource-card__meta-label">Last received</span>
          <span id="apis-overview-incoming-meta-last-received-value-${entry.id}" class="resource-card__meta-value">${escapeHtml(formatDateTime(entry.last_received_at))}</span>
        </div>
        <div id="apis-overview-incoming-meta-result-${entry.id}" class="resource-card__meta-item">
          <span id="apis-overview-incoming-meta-result-label-${entry.id}" class="resource-card__meta-label">Recent result</span>
          <span id="apis-overview-incoming-meta-result-value-${entry.id}" class="resource-card__meta-value">${escapeHtml(entry.last_delivery_status || "No deliveries")}</span>
        </div>
      </div>
    `;
    fragment.appendChild(card);
  });

  apiElements.overviewIncomingList.appendChild(fragment);
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
    ? "Across inbound, outbound, and webhook monitoring surfaces."
    : "Create an API to add it to the incoming, outgoing, or webhook registry.";
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

  const sortedIncomingEntries = [...incomingEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedScheduledEntries = [...scheduledEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedContinuousEntries = [...continuousEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const outgoingEntries = [...sortedScheduledEntries, ...sortedContinuousEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedWebhookEntries = [...webhookEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));

  renderOverviewIncomingList(sortedIncomingEntries);
  renderResourceList(apiElements.overviewOutgoingList, apiElements.overviewOutgoingEmpty, outgoingEntries, "apis-overview-outgoing-list");
  renderResourceList(apiElements.overviewWebhooksList, apiElements.overviewWebhooksEmpty, sortedWebhookEntries, "apis-overview-webhooks-list");
  syncOverviewLandingSummary({
    incomingEntries: sortedIncomingEntries,
    scheduledEntries: sortedScheduledEntries,
    continuousEntries: sortedContinuousEntries,
    webhookEntries: sortedWebhookEntries
  });
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
  renderResourceList(apiElements.outgoingList, apiElements.outgoingListEmpty, apiState.outgoingEntries, "apis-outgoing-list");
};

const loadWebhookRegistry = async () => {
  if (!hasWebhookRegistryElements()) {
    return;
  }

  apiState.webhookEntries = await backendApi.listWebhooks();
  renderResourceList(apiElements.webhooksList, apiElements.webhooksListEmpty, apiState.webhookEntries, "apis-webhooks-list");
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
    const response = await fetch(new URL("../modals/create-api-modal.html", window.location.href));

    if (!response.ok) {
      throw new Error("Unable to load modal template.");
    }

    apiElements.createModalContent.innerHTML = await response.text();
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

const initCreateModal = async () => {
  bindModalEvents();

  if (!hasCreateModalElements()) {
    return;
  }

  ensureCreateTypePopover();
  await initModalMarkup();
  setCreateModalType(apiState.createModalType);
};

const initApiOverview = async () => {
  if (!hasOverviewElements()) {
    return;
  }

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
  }
};

const initWebhookRegistry = async () => {
  if (!hasWebhookRegistryElements()) {
    return;
  }

  try {
    await loadWebhookRegistry();
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
  }
};

const initApiPage = async () => {
  await initCreateModal();
  if (hasOverviewLandingElements()) {
    bindOverviewTooltips();
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
};

initApiPage();
