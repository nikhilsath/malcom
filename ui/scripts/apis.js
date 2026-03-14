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
  overviewIncomingCount: document.getElementById("apis-overview-summary-incoming-value"),
  overviewOutgoingCount: document.getElementById("apis-overview-summary-outgoing-value"),
  overviewWebhooksCount: document.getElementById("apis-overview-summary-webhooks-value"),
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
  && apiElements.overviewIncomingCount
  && apiElements.overviewOutgoingCount
  && apiElements.overviewWebhooksCount
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
        <div id="create-api-form-grid" class="api-form-grid">
          <fieldset id="create-api-type-field" class="api-form-field api-form-field--full api-type-tabs">
            <legend id="create-api-type-label" class="api-form-label">API type</legend>
            <div id="create-api-type-options" class="api-type-tabs__list">
              <label id="create-api-type-option-incoming" class="api-type-tab">
                <input id="create-api-type-input-incoming" class="api-type-tab__input" name="resourceType" type="radio" value="incoming" checked>
                <span id="create-api-type-copy-incoming" class="api-type-tab__label">
                  <span id="create-api-type-title-incoming" class="api-type-tab__title">Incoming</span>
                </span>
              </label>
              <label id="create-api-type-option-outgoing-scheduled" class="api-type-tab">
                <input id="create-api-type-input-outgoing-scheduled" class="api-type-tab__input" name="resourceType" type="radio" value="outgoing_scheduled">
                <span id="create-api-type-copy-outgoing-scheduled" class="api-type-tab__label">
                  <span id="create-api-type-title-outgoing-scheduled" class="api-type-tab__title">Outgoing (scheduled)</span>
                </span>
              </label>
              <label id="create-api-type-option-outgoing-continuous" class="api-type-tab">
                <input id="create-api-type-input-outgoing-continuous" class="api-type-tab__input" name="resourceType" type="radio" value="outgoing_continuous">
                <span id="create-api-type-copy-outgoing-continuous" class="api-type-tab__label">
                  <span id="create-api-type-title-outgoing-continuous" class="api-type-tab__title">Outgoing (continuous)</span>
                </span>
              </label>
              <label id="create-api-type-option-webhook" class="api-type-tab">
                <input id="create-api-type-input-webhook" class="api-type-tab__input" name="resourceType" type="radio" value="webhook">
                <span id="create-api-type-copy-webhook" class="api-type-tab__label">
                  <span id="create-api-type-title-webhook" class="api-type-tab__title">Webhook</span>
                </span>
              </label>
            </div>
          </fieldset>
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
            <input id="create-api-auth-input" class="api-form-input" name="authType" type="text" value="Bearer secret" readonly>
          </label>
          <label id="create-api-enabled-field" class="api-form-field api-form-field--toggle">
            <span id="create-api-enabled-label" class="api-form-label">Enabled on create</span>
            <span id="create-api-enabled-control" class="api-inline-toggle">
              <input id="create-api-enabled-input" name="enabled" type="checkbox" checked>
              <span id="create-api-enabled-copy" class="api-inline-toggle__label">Accept requests immediately</span>
            </span>
          </label>
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
  webhookEntries: []
};

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
    description: "Register a scheduled outbound API and store it in the scheduled delivery registry.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Activate the schedule immediately",
    submitLabel: "Create scheduled API",
    successMessage: "Scheduled outgoing API created.",
    alertMessage: "Scheduled outgoing API created.",
    redirectPath: "/ui/apis/outgoing.html"
  },
  outgoing_continuous: {
    title: "New Outgoing Continuous API",
    description: "Register a continuous outbound API and store it in the continuous delivery registry.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Start the stream immediately",
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
    return window.requestJson("/api/v1/outgoing/scheduled");
  },
  async listOutgoingContinuous() {
    return window.requestJson("/api/v1/outgoing/continuous");
  },
  async listWebhooks() {
    return window.requestJson("/api/v1/webhooks");
  }
};

const syncSummary = () => {
  if (!hasOverviewElements()) {
    return;
  }
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

const openCreateModal = () => {
  if (!apiElements.createModal) {
    return;
  }

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

  const createOpenButton = getCreateOpenButton();

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
        openCreateModal();
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
};

const navigateToResourcePage = (type) => {
  const targetHref = resolvePageHref(apiResourceTypes[type].redirectPath);

  if (window.location.href !== targetHref) {
    window.location.assign(targetHref);
  }
};

const bindCreateForm = () => {
  const form = document.getElementById("create-api-form");
  const nameInput = document.getElementById("create-api-name-input");
  const slugInput = document.getElementById("create-api-slug-input");
  const descriptionInput = document.getElementById("create-api-description-input");
  const enabledInput = document.getElementById("create-api-enabled-input");
  const feedback = document.getElementById("create-api-form-feedback");
  const typeInputs = Array.from(document.querySelectorAll('input[name="resourceType"]'));

  if (!form || !nameInput || !slugInput || !descriptionInput || !enabledInput || !feedback || typeInputs.length === 0) {
    return;
  }

  const getSelectedType = () => typeInputs.find((input) => input.checked)?.value || "incoming";

  nameInput.addEventListener("input", () => {
    if (!slugInput.dataset.userEdited) {
      slugInput.value = sanitizeSlug(nameInput.value);
    }
  });

  slugInput.addEventListener("input", () => {
    slugInput.dataset.userEdited = "true";
    slugInput.value = sanitizeSlug(slugInput.value);
  });

  typeInputs.forEach((input) => {
    input.addEventListener("change", () => {
      syncCreateModalType(getSelectedType());
    });
  });

  syncCreateModalType(getSelectedType());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    const selectedType = getSelectedType();

    const payload = {
      type: selectedType,
      name: nameInput.value.trim(),
      path_slug: sanitizeSlug(slugInput.value),
      description: descriptionInput.value.trim(),
      enabled: enabledInput.checked
    };

    if (!payload.name || !payload.path_slug) {
      feedback.textContent = "Name and path slug are required.";
      feedback.className = "api-form-feedback api-form-feedback--error";
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
      typeInputs[0].checked = true;
      syncCreateModalType("incoming");
      feedback.textContent = apiResourceTypes[selectedType].successMessage;
      feedback.className = "api-form-feedback api-form-feedback--success";
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
      feedback.textContent = error.message;
      feedback.className = "api-form-feedback api-form-feedback--error";
      emitApiLog({
        level: "error",
        action: `${selectedType}_create_failed`,
        message: `Failed to create ${selectedType}.`,
        details: {
          error: error.message,
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
    const card = document.createElement("article");
    card.id = `${sectionIdPrefix}-card-${entry.id}`;
    card.className = "resource-card";
    card.innerHTML = `
      <div id="${sectionIdPrefix}-header-${entry.id}" class="resource-card__header">
        <div id="${sectionIdPrefix}-copy-${entry.id}">
          <h4 id="${sectionIdPrefix}-title-${entry.id}" class="resource-card__title">${escapeHtml(entry.name)}</h4>
          <p id="${sectionIdPrefix}-description-${entry.id}" class="resource-card__description">${escapeHtml(entry.description || "No description provided.")}</p>
        </div>
        <span id="${sectionIdPrefix}-status-${entry.id}" class="status-badge ${entry.enabled ? "status-badge--success" : "status-badge--muted"}">${entry.enabled ? "Enabled" : "Disabled"}</span>
      </div>
      <div id="${sectionIdPrefix}-meta-${entry.id}" class="resource-card__meta">
        <div id="${sectionIdPrefix}-meta-type-${index}" class="resource-card__meta-item">
          <span id="${sectionIdPrefix}-meta-type-label-${index}" class="resource-card__meta-label">Type</span>
          <span id="${sectionIdPrefix}-meta-type-value-${index}" class="resource-card__meta-value">${escapeHtml(entry.type)}</span>
        </div>
        <div id="${sectionIdPrefix}-meta-path-${index}" class="resource-card__meta-item">
          <span id="${sectionIdPrefix}-meta-path-label-${index}" class="resource-card__meta-label">Row slug</span>
          <span id="${sectionIdPrefix}-meta-path-value-${index}" class="resource-card__meta-value">${escapeHtml(entry.path_slug)}</span>
        </div>
        <div id="${sectionIdPrefix}-meta-created-${index}" class="resource-card__meta-item">
          <span id="${sectionIdPrefix}-meta-created-label-${index}" class="resource-card__meta-label">Created</span>
          <span id="${sectionIdPrefix}-meta-created-value-${index}" class="resource-card__meta-value">${escapeHtml(formatDateTime(entry.created_at))}</span>
        </div>
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
        <span id="apis-overview-incoming-status-${entry.id}" class="status-badge ${entry.enabled ? "status-badge--success" : "status-badge--muted"}">${entry.enabled ? "Enabled" : "Disabled"}</span>
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

const syncOverviewLandingSummary = ({ incomingEntries, outgoingEntries, webhookEntries }) => {
  if (!hasOverviewLandingElements()) {
    return;
  }

  const totalCount = incomingEntries.length + outgoingEntries.length + webhookEntries.length;
  apiElements.overviewTotalCount.textContent = `${totalCount} configured APIs`;
  apiElements.overviewHelper.textContent = totalCount > 0
    ? "Open any registry below to review the full configured API inventory."
    : "Create an API to add it to the incoming, outgoing, or webhook registry.";
  apiElements.overviewIncomingCount.textContent = String(incomingEntries.length);
  apiElements.overviewOutgoingCount.textContent = String(outgoingEntries.length);
  apiElements.overviewWebhooksCount.textContent = String(webhookEntries.length);
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
  const outgoingEntries = [...scheduledEntries, ...continuousEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
  const sortedWebhookEntries = [...webhookEntries]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));

  renderOverviewIncomingList(sortedIncomingEntries);
  renderResourceList(apiElements.overviewOutgoingList, apiElements.overviewOutgoingEmpty, outgoingEntries, "apis-overview-outgoing-list");
  renderResourceList(apiElements.overviewWebhooksList, apiElements.overviewWebhooksEmpty, sortedWebhookEntries, "apis-overview-webhooks-list");
  syncOverviewLandingSummary({
    incomingEntries: sortedIncomingEntries,
    outgoingEntries,
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
      setAlert(error.message, "error");
      emitApiLog({
        level: "error",
        action: "inbound_api_secret_rotate_failed",
        message: "Failed to rotate inbound API bearer secret.",
        details: {
          apiId: apiState.selectedApiId,
          error: error.message
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
      setAlert(error.message, "error");
      emitApiLog({
        level: "error",
        action: "inbound_api_toggle_failed",
        message: "Failed to update inbound API status.",
        details: {
          apiId: entry.id,
          error: error.message
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
  } catch {
    apiElements.createModalContent.innerHTML = modalFallbackMarkup;
  }

  bindCreateForm();
};

const initCreateModal = async () => {
  bindModalEvents();

  if (!hasCreateModalElements()) {
    return;
  }

  await initModalMarkup();
};

const initApiOverview = async () => {
  if (!hasOverviewElements()) {
    return;
  }

  bindDetailActions();

  try {
    await loadApiDirectory();
    setAlert(
      window.developerModeEnabled() ? "Developer mode is enabled. Database-backed sample endpoints are included." : "",
      "info"
    );
  } catch (error) {
    setAlert("Unable to load inbound APIs. Start the FastAPI service and refresh the page.", "error");
    renderDetail(null);
    emitApiLog({
      level: "error",
      action: "inbound_api_load_failed",
      message: "Unable to load inbound APIs from the backend.",
      details: {
        error: error.message
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
    emitApiLog({
      level: "error",
      action: "outgoing_api_load_failed",
      message: "Unable to load outgoing APIs from the backend.",
      details: {
        error: error.message
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
    emitApiLog({
      level: "error",
      action: "webhook_load_failed",
      message: "Unable to load webhooks from the backend.",
      details: {
        error: error.message
      }
    });
  }
};

const initApiPage = async () => {
  await initCreateModal();
  if (hasOverviewLandingElements()) {
    try {
      await loadOverviewLanding();
    } catch (error) {
      setAlert("Unable to load API overview. Start the FastAPI service and refresh the page.", "error");
      emitApiLog({
        level: "error",
        action: "api_overview_load_failed",
        message: "Unable to load API overview registries from the backend.",
        details: {
          error: error.message
        }
      });
    }
  }
  await initApiOverview();
  await initOutgoingRegistry();
  await initWebhookRegistry();
};

initApiPage();
