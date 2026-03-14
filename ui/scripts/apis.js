const apiElements = {
  modal: document.getElementById("apis-create-modal"),
  modalContent: document.getElementById("apis-create-modal-content"),
  openButton: document.getElementById("apis-create-button"),
  alert: document.getElementById("api-system-alert"),
  overviewCount: document.getElementById("api-overview-count"),
  overviewHelper: document.getElementById("api-overview-helper"),
  activeCount: document.getElementById("api-summary-active-value"),
  eventCount: document.getElementById("api-summary-events-value"),
  lastEvent: document.getElementById("api-summary-last-event-value"),
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
  logList: document.getElementById("api-log-list")
};

const modalFallbackMarkup = `
  <div class="modal__panel" id="create-api-modal-panel">
    <div class="modal__header" id="create-api-modal-header">
      <div class="modal__header-copy" id="create-api-modal-header-copy">
        <p class="modal__eyebrow" id="create-api-modal-eyebrow">Create</p>
        <h3 class="modal__title" id="apis-create-modal-title">New Inbound API</h3>
        <p class="modal__description" id="create-api-modal-description">Provision a webhook endpoint with a bearer token for authenticated JSON requests.</p>
      </div>
      <button type="button" class="modal__close-button" id="create-api-modal-close" aria-label="Close create API modal" data-modal-close="apis-create-modal">Close</button>
    </div>
    <div class="modal__body modal__body--form" id="create-api-modal-body">
      <form id="create-api-form" class="api-form">
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
          <button type="submit" id="create-api-submit-button" class="primary-action-button">Create inbound API</button>
        </div>
      </form>
    </div>
  </div>
`;

const apiState = {
  entries: [],
  selectedApiId: null,
  lastSecretByApiId: {},
  useMockData: false
};

const developerModeEnabled = () => sessionStorage.getItem("developerMode") === "true";

const mockStorageKeys = {
  entries: "malcom.inboundApis",
  events: "malcom.inboundApiEvents"
};

const sanitizeSlug = (value) => value
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9-]+/g, "-")
  .replace(/-{2,}/g, "-")
  .replace(/^-|-$/g, "");

const createId = (prefix) => `${prefix}_${Math.random().toString(36).slice(2, 10)}`;

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

const getBaseUrl = () => window.location.protocol === "file:" || window.location.origin === "null"
  ? "http://localhost:8000"
  : window.location.origin;

const buildEndpointUrl = (apiId) => `${getBaseUrl()}/api/v1/inbound/${apiId}`;

const buildSampleCurl = (apiId, secret) => {
  const endpoint = buildEndpointUrl(apiId);
  const jsonPayload = JSON.stringify({ hello: "world" }, null, 2);

  return `curl -X POST "${endpoint}" \\
  -H "Authorization: Bearer ${secret}" \\
  -H "Content-Type: application/json" \\
  -d '${jsonPayload}'`;
};

const readMockEntries = () => {
  const raw = sessionStorage.getItem(mockStorageKeys.entries);

  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
};

const writeMockEntries = (entries) => {
  sessionStorage.setItem(mockStorageKeys.entries, JSON.stringify(entries));
};

const readMockEvents = () => {
  const raw = sessionStorage.getItem(mockStorageKeys.events);

  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
};

const writeMockEvents = (events) => {
  sessionStorage.setItem(mockStorageKeys.events, JSON.stringify(events));
};

const seedMockData = () => {
  if (readMockEntries().length > 0) {
    return;
  }

  const now = new Date().toISOString();
  const entry = {
    id: "demo_webhook",
    name: "Demo Webhook",
    description: "Seeded developer-mode endpoint for local UI verification.",
    path_slug: "demo-webhook",
    auth_type: "bearer",
    enabled: true,
    created_at: now,
    updated_at: now,
    endpoint_path: "/api/v1/inbound/demo_webhook",
    last_received_at: now,
    last_delivery_status: "accepted",
    events_count: 1
  };
  const event = {
    event_id: "evt_demo001",
    api_id: entry.id,
    received_at: now,
    status: "accepted",
    request_headers_subset: {
      "content-type": "application/json",
      "user-agent": "developer-mode"
    },
    payload_json: {
      source: "developer-mode",
      ok: true
    },
    source_ip: "127.0.0.1",
    error_message: null,
    runtime_trigger: {
      type: "inbound_api",
      api_id: entry.id,
      event_id: "evt_demo001",
      payload: {
        source: "developer-mode",
        ok: true
      },
      received_at: now
    }
  };

  writeMockEntries([entry]);
  writeMockEvents({ [entry.id]: [event] });
};

const mockApi = {
  async list() {
    return readMockEntries();
  },
  async create(payload) {
    const entries = readMockEntries();
    const now = new Date().toISOString();
    const id = createId("inbound");
    const secret = `malcom_${Math.random().toString(36).slice(2, 18)}`;
    const entry = {
      id,
      name: payload.name,
      description: payload.description,
      path_slug: payload.path_slug,
      auth_type: "bearer",
      enabled: payload.enabled,
      created_at: now,
      updated_at: now,
      endpoint_path: `/api/v1/inbound/${id}`,
      last_received_at: null,
      last_delivery_status: null,
      events_count: 0
    };
    entries.unshift(entry);
    writeMockEntries(entries);
    return {
      ...entry,
      secret,
      endpoint_url: buildEndpointUrl(id)
    };
  },
  async detail(apiId) {
    const entry = readMockEntries().find((item) => item.id === apiId);

    if (!entry) {
      throw new Error("Inbound API not found.");
    }

    const eventsByApiId = readMockEvents();
    return {
      ...entry,
      endpoint_url: buildEndpointUrl(apiId),
      events: eventsByApiId[apiId] || []
    };
  },
  async update(apiId, payload) {
    const entries = readMockEntries();
    const index = entries.findIndex((item) => item.id === apiId);

    if (index === -1) {
      throw new Error("Inbound API not found.");
    }

    entries[index] = {
      ...entries[index],
      ...payload,
      updated_at: new Date().toISOString()
    };
    writeMockEntries(entries);
    return entries[index];
  },
  async rotateSecret(apiId) {
    const entries = readMockEntries();
    const entry = entries.find((item) => item.id === apiId);

    if (!entry) {
      throw new Error("Inbound API not found.");
    }

    entry.updated_at = new Date().toISOString();
    writeMockEntries(entries);

    return {
      id: apiId,
      secret: `malcom_${Math.random().toString(36).slice(2, 18)}`,
      endpoint_url: buildEndpointUrl(apiId)
    };
  }
};

const parseErrorMessage = async (response) => {
  try {
    const data = await response.json();
    return data.detail || data.message || "Request failed.";
  } catch {
    return "Request failed.";
  }
};

const requestJson = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
};

const backendApi = {
  async list() {
    return requestJson("/api/v1/inbound");
  },
  async create(payload) {
    return requestJson("/api/v1/inbound", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  async detail(apiId) {
    return requestJson(`/api/v1/inbound/${apiId}`);
  },
  async update(apiId, payload) {
    return requestJson(`/api/v1/inbound/${apiId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  async rotateSecret(apiId) {
    return requestJson(`/api/v1/inbound/${apiId}/rotate-secret`, {
      method: "POST"
    });
  }
};

const getApiClient = () => apiState.useMockData ? mockApi : backendApi;

const syncSummary = () => {
  const entries = apiState.entries;
  const activeCount = entries.filter((entry) => entry.enabled).length;
  const eventCount = entries.reduce((sum, entry) => sum + (entry.events_count || 0), 0);
  const lastReceivedValues = entries
    .map((entry) => entry.last_received_at)
    .filter(Boolean)
    .sort((left, right) => new Date(right) - new Date(left));

  apiElements.overviewCount.textContent = `${entries.length} endpoint${entries.length === 1 ? "" : "s"}`;
  apiElements.overviewHelper.textContent = entries.length === 0
    ? "Create an inbound API to start receiving webhook traffic."
    : "Select an endpoint to inspect its webhook URL, logs, and latest secret action.";
  apiElements.activeCount.textContent = String(activeCount);
  apiElements.eventCount.textContent = String(eventCount);
  apiElements.lastEvent.textContent = lastReceivedValues.length > 0
    ? formatDateTime(lastReceivedValues[0])
    : "No events yet";
};

const renderTable = () => {
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
      loadApiDetail(entry.id);
    });

    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        loadApiDetail(entry.id);
      }
    });

    fragment.appendChild(row);
  });

  apiElements.tableBody.appendChild(fragment);
};

const renderMetadata = (entry) => {
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
  apiElements.detailEmpty.hidden = isVisible;
  apiElements.detailContent.hidden = !isVisible;
};

const renderDetail = (entry) => {
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
  const client = getApiClient();
  apiState.entries = await client.list();

  if (!apiState.selectedApiId && apiState.entries.length > 0) {
    apiState.selectedApiId = apiState.entries[0].id;
  }

  syncSummary();
  renderTable();

  if (apiState.selectedApiId) {
    await loadApiDetail(apiState.selectedApiId, false);
  } else {
    renderDetail(null);
  }
};

async function loadApiDetail(apiId, syncTableSelection = true) {
  const client = getApiClient();
  apiState.selectedApiId = apiId;
  const detail = await client.detail(apiId);
  renderDetail(detail);

  if (syncTableSelection) {
    renderTable();
  }
}

const openModal = () => {
  apiElements.modal.classList.add("modal--open");
  apiElements.modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

const closeModal = () => {
  apiElements.modal.classList.remove("modal--open");
  apiElements.modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  apiElements.openButton.focus();
};

const bindModalEvents = () => {
  apiElements.openButton.addEventListener("click", () => {
    openModal();
  });

  apiElements.modal.addEventListener("click", (event) => {
    const closeTarget = event.target.closest("[data-modal-close]");

    if (closeTarget) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && apiElements.modal.classList.contains("modal--open")) {
      closeModal();
    }
  });
};

const bindCreateForm = () => {
  const form = document.getElementById("create-api-form");
  const nameInput = document.getElementById("create-api-name-input");
  const slugInput = document.getElementById("create-api-slug-input");
  const descriptionInput = document.getElementById("create-api-description-input");
  const enabledInput = document.getElementById("create-api-enabled-input");
  const feedback = document.getElementById("create-api-form-feedback");

  if (!form || !nameInput || !slugInput || !descriptionInput || !enabledInput || !feedback) {
    return;
  }

  nameInput.addEventListener("input", () => {
    if (!slugInput.dataset.userEdited) {
      slugInput.value = sanitizeSlug(nameInput.value);
    }
  });

  slugInput.addEventListener("input", () => {
    slugInput.dataset.userEdited = "true";
    slugInput.value = sanitizeSlug(slugInput.value);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";

    const payload = {
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
      const created = await getApiClient().create(payload);
      apiState.lastSecretByApiId[created.id] = created.secret;
      apiState.selectedApiId = created.id;
      await loadApiDirectory();
      await loadApiDetail(created.id);
      form.reset();
      enabledInput.checked = true;
      delete slugInput.dataset.userEdited;
      feedback.textContent = "Inbound API created.";
      feedback.className = "api-form-feedback api-form-feedback--success";
      closeModal();
      setAlert("Inbound API created. Store the generated bearer token now; it will not be shown again.", "success");
    } catch (error) {
      feedback.textContent = error.message;
      feedback.className = "api-form-feedback api-form-feedback--error";
    }
  });
};

const bindDetailActions = () => {
  apiElements.rotateSecretButton.addEventListener("click", async () => {
    if (!apiState.selectedApiId) {
      return;
    }

    try {
      const rotated = await getApiClient().rotateSecret(apiState.selectedApiId);
      apiState.lastSecretByApiId[apiState.selectedApiId] = rotated.secret;
      await loadApiDirectory();
      await loadApiDetail(apiState.selectedApiId);
      setAlert("Bearer secret rotated. Update external callers to use the new token.", "success");
    } catch (error) {
      setAlert(error.message, "error");
    }
  });

  apiElements.toggleStatusButton.addEventListener("click", async () => {
    const entry = apiState.entries.find((item) => item.id === apiState.selectedApiId);

    if (!entry) {
      return;
    }

    try {
      await getApiClient().update(entry.id, { enabled: !entry.enabled });
      await loadApiDirectory();
      await loadApiDetail(entry.id);
      setAlert(entry.enabled ? "Inbound API disabled." : "Inbound API enabled.", "success");
    } catch (error) {
      setAlert(error.message, "error");
    }
  });
};

const initModalMarkup = async () => {
  if (!apiElements.modalContent) {
    return;
  }

  try {
    const response = await fetch("modals/create-api-modal.html");

    if (!response.ok) {
      throw new Error("Unable to load modal template.");
    }

    apiElements.modalContent.innerHTML = await response.text();
  } catch {
    apiElements.modalContent.innerHTML = modalFallbackMarkup;
  }

  bindCreateForm();
};

const initApiPage = async () => {
  if (!apiElements.modal || !apiElements.modalContent || !apiElements.openButton) {
    return;
  }

  if (developerModeEnabled()) {
    seedMockData();
  }

  bindModalEvents();
  bindDetailActions();
  await initModalMarkup();

  try {
    await loadApiDirectory();
    setAlert(apiState.useMockData ? "Developer mode data is active." : "", "info");
  } catch (error) {
    if (developerModeEnabled()) {
      apiState.useMockData = true;
      setAlert("Backend unavailable. Showing developer-mode sample data from session storage.", "warning");
      await loadApiDirectory();
      return;
    }

    setAlert("Unable to load inbound APIs. Start the FastAPI service and refresh the page.", "error");
    renderDetail(null);
  }
};

initApiPage();
