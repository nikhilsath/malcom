import { formatDateTime } from "./format-utils.js";

const connectorElements = {
  feedback: document.getElementById("settings-connectors-feedback"),
  createButton: document.getElementById("settings-connectors-create-button"),
  tableBody: document.getElementById("settings-connectors-table-body"),
  tableShell: document.getElementById("settings-connectors-table-shell"),
  empty: document.getElementById("settings-connectors-empty"),
  summaryConnected: document.getElementById("settings-connectors-summary-connected-value"),
  summaryOauth: document.getElementById("settings-connectors-summary-oauth-value"),
  summaryAttention: document.getElementById("settings-connectors-summary-attention-value"),
  form: document.getElementById("settings-connectors-form"),
  policyForm: document.getElementById("settings-connectors-policy-form"),
  nameInput: document.getElementById("settings-connectors-name-input"),
  providerInput: document.getElementById("settings-connectors-provider-input"),
  statusInput: document.getElementById("settings-connectors-status-input"),
  authTypeInput: document.getElementById("settings-connectors-auth-type-input"),
  ownerInput: document.getElementById("settings-connectors-owner-input"),
  baseUrlInput: document.getElementById("settings-connectors-base-url-input"),
  scopesInput: document.getElementById("settings-connectors-scopes-input"),
  clientIdInput: document.getElementById("settings-connectors-client-id-input"),
  clientSecretInput: document.getElementById("settings-connectors-client-secret-input"),
  redirectUriInput: document.getElementById("settings-connectors-redirect-uri-input"),
  usernameInput: document.getElementById("settings-connectors-username-input"),
  passwordInput: document.getElementById("settings-connectors-password-input"),
  accessTokenInput: document.getElementById("settings-connectors-access-token-input"),
  refreshTokenInput: document.getElementById("settings-connectors-refresh-token-input"),
  apiKeyInput: document.getElementById("settings-connectors-api-key-input"),
  headerNameInput: document.getElementById("settings-connectors-header-name-input"),
  headerValueInput: document.getElementById("settings-connectors-header-value-input"),
  credentialSummary: document.getElementById("settings-connectors-credential-summary-value"),
  testButton: document.getElementById("settings-connectors-test-button"),
  oauthStartButton: document.getElementById("settings-connectors-oauth-start-button"),
  oauthCompleteButton: document.getElementById("settings-connectors-oauth-complete-button"),
  refreshButton: document.getElementById("settings-connectors-refresh-button"),
  revokeButton: document.getElementById("settings-connectors-revoke-button"),
  policyRotationInput: document.getElementById("settings-connectors-policy-rotation-input"),
  policyApprovalInput: document.getElementById("settings-connectors-policy-approval-input"),
  policyVisibilityInput: document.getElementById("settings-connectors-policy-visibility-input"),
  modal: document.getElementById("settings-connectors-modal"),
  modalProviderGrid: document.getElementById("settings-connectors-modal-provider-grid")
};

const connectorState = {
  settings: null,
  selectedConnectorId: null,
  pendingOauth: {}
};

const requestJson = (path, options) => {
  if (!window.Malcom?.requestJson) {
    throw new Error("Malcom request helper is unavailable.");
  }
  return window.Malcom.requestJson(path, options);
};

const getStore = () => window.MalcomLogStore;

const cloneValue = (value) => JSON.parse(JSON.stringify(value));

const slugifyConnectorId = (value) => value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 100) || `connector_${Date.now()}`;

const setFeedback = (message, tone = "") => {
  if (!connectorElements.feedback) {
    return;
  }

  connectorElements.feedback.textContent = message;
  connectorElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const titleCase = (value) => value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());

const getSelectedConnector = () => connectorState.settings?.connectors?.records?.find((record) => record.id === connectorState.selectedConnectorId) || null;

const getProviderPreset = (providerId) => connectorState.settings?.connectors?.catalog?.find((item) => item.id === providerId) || null;

const openModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

const closeModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
};

const buildDefaultConnectorRecord = (preset) => ({
  id: slugifyConnectorId(`${preset.id}-${preset.name}`),
  provider: preset.id,
  name: preset.name,
  status: "draft",
  auth_type: preset.auth_types[0] || "bearer",
  scopes: [...(preset.default_scopes || [])],
  base_url: preset.base_url || "",
  owner: "Workspace",
  docs_url: preset.docs_url,
  credential_ref: `connector/${slugifyConnectorId(`${preset.id}-${preset.name}`)}`,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  last_tested_at: null,
  auth_config: {
    client_id: "",
    username: "",
    header_name: "",
    scope_preset: preset.id,
    redirect_uri: `${window.location.origin}/api/v1/connectors/${preset.id}/oauth/callback`,
    expires_at: null,
    has_refresh_token: false
  }
});

const renderSummary = () => {
  const records = connectorState.settings?.connectors?.records || [];
  const connected = records.filter((item) => item.status === "connected").length;
  const oauth = records.filter((item) => item.auth_type === "oauth2").length;
  const attention = records.filter((item) => ["needs_attention", "expired", "revoked"].includes(item.status)).length;

  if (connectorElements.summaryConnected) {
    connectorElements.summaryConnected.textContent = String(connected);
  }
  if (connectorElements.summaryOauth) {
    connectorElements.summaryOauth.textContent = String(oauth);
  }
  if (connectorElements.summaryAttention) {
    connectorElements.summaryAttention.textContent = String(attention);
  }
};

const renderDirectory = () => {
  const records = connectorState.settings?.connectors?.records || [];
  const hasRecords = records.length > 0;

  if (connectorElements.empty) {
    connectorElements.empty.hidden = hasRecords;
  }
  if (connectorElements.tableShell) {
    connectorElements.tableShell.hidden = !hasRecords;
  }
  if (!connectorElements.tableBody) {
    return;
  }

  connectorElements.tableBody.textContent = "";

  records.forEach((record) => {
    const row = document.createElement("tr");
    row.id = `settings-connectors-row-${record.id}`;
    row.className = "api-directory-row";
    row.tabIndex = 0;
    if (record.id === connectorState.selectedConnectorId) {
      row.classList.add("api-directory-row--selected");
    }
    row.innerHTML = `
      <td id="settings-connectors-row-name-${record.id}" class="api-directory-cell api-directory-cell--name">
        <span id="settings-connectors-row-name-value-${record.id}" class="api-directory-name">${record.name}</span>
        <span id="settings-connectors-row-name-meta-${record.id}" class="api-directory-description">${record.docs_url || "No provider docs recorded."}</span>
      </td>
      <td id="settings-connectors-row-provider-${record.id}" class="api-directory-cell">${titleCase(record.provider)}</td>
      <td id="settings-connectors-row-status-${record.id}" class="api-directory-cell"><span class="status-badge ${record.status === "connected" ? "status-badge--success" : record.status === "needs_attention" || record.status === "expired" ? "status-badge--warning" : "status-badge--muted"}">${titleCase(record.status)}</span></td>
      <td id="settings-connectors-row-auth-${record.id}" class="api-directory-cell">${titleCase(record.auth_type)}</td>
      <td id="settings-connectors-row-owner-${record.id}" class="api-directory-cell">${record.owner || "Workspace"}</td>
    `;
    row.addEventListener("click", () => {
      connectorState.selectedConnectorId = record.id;
      renderAll();
    });
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        connectorState.selectedConnectorId = record.id;
        renderAll();
      }
    });
    connectorElements.tableBody.appendChild(row);
  });
};

const renderAuthTypeOptions = (record) => {
  if (!connectorElements.authTypeInput) {
    return;
  }

  const preset = getProviderPreset(record.provider);
  const authTypes = preset?.auth_types || [record.auth_type];
  connectorElements.authTypeInput.innerHTML = authTypes.map((authType) => `<option value="${authType}">${titleCase(authType)}</option>`).join("");
  connectorElements.authTypeInput.value = record.auth_type;
};

const renderCredentialSummary = (record) => {
  const authConfig = record.auth_config || {};
  const maskedValues = [
    authConfig.client_secret_masked && `client secret ${authConfig.client_secret_masked}`,
    authConfig.access_token_masked && `access token ${authConfig.access_token_masked}`,
    authConfig.refresh_token_masked && `refresh token ${authConfig.refresh_token_masked}`,
    authConfig.api_key_masked && `api key ${authConfig.api_key_masked}`,
    authConfig.password_masked && `password ${authConfig.password_masked}`,
    authConfig.header_value_masked && `header value ${authConfig.header_value_masked}`
  ].filter(Boolean);

  if (connectorElements.credentialSummary) {
    connectorElements.credentialSummary.textContent = maskedValues.length > 0
      ? `${maskedValues.join(", ")}. Last tested ${formatDateTime(record.last_tested_at, "Not tested")}.`
      : "No masked credential values stored yet.";
  }
};

const renderDetail = () => {
  const record = getSelectedConnector();

  if (!record) {
    connectorElements.form?.reset();
    if (connectorElements.credentialSummary) {
      connectorElements.credentialSummary.textContent = "Select a connector to edit its settings.";
    }
    return;
  }

  renderAuthTypeOptions(record);
  connectorElements.nameInput.value = record.name || "";
  connectorElements.providerInput.value = titleCase(record.provider);
  connectorElements.statusInput.value = record.status;
  connectorElements.ownerInput.value = record.owner || "";
  connectorElements.baseUrlInput.value = record.base_url || "";
  connectorElements.scopesInput.value = (record.scopes || []).join(", ");
  connectorElements.clientIdInput.value = record.auth_config?.client_id || "";
  connectorElements.clientSecretInput.value = "";
  connectorElements.redirectUriInput.value = record.auth_config?.redirect_uri || "";
  connectorElements.usernameInput.value = record.auth_config?.username || "";
  connectorElements.passwordInput.value = "";
  connectorElements.accessTokenInput.value = "";
  connectorElements.refreshTokenInput.value = "";
  connectorElements.apiKeyInput.value = "";
  connectorElements.headerNameInput.value = record.auth_config?.header_name || "";
  connectorElements.headerValueInput.value = "";
  renderCredentialSummary(record);
};

const renderPolicy = () => {
  const policy = connectorState.settings?.connectors?.auth_policy;
  if (!policy) {
    return;
  }

  connectorElements.policyRotationInput.value = String(policy.rotation_interval_days);
  connectorElements.policyApprovalInput.checked = Boolean(policy.reconnect_requires_approval);
  connectorElements.policyApprovalInput.closest(".toggle")?.classList.toggle("toggle--on", connectorElements.policyApprovalInput.checked);
  const approvalLabel = document.getElementById("settings-connectors-policy-approval-label");
  if (approvalLabel) {
    approvalLabel.textContent = connectorElements.policyApprovalInput.checked ? "Required" : "Optional";
  }
  connectorElements.policyVisibilityInput.value = policy.credential_visibility;
};

const renderModalProviders = () => {
  if (!connectorElements.modalProviderGrid) {
    return;
  }

  const catalog = connectorState.settings?.connectors?.catalog || [];
  connectorElements.modalProviderGrid.innerHTML = catalog.map((preset) => `
    <button type="button" id="settings-connectors-provider-option-${preset.id}" class="api-entry-card" data-provider-id="${preset.id}">
      <span id="settings-connectors-provider-option-title-${preset.id}" class="api-entry-card__title">${preset.name}</span>
      <span id="settings-connectors-provider-option-description-${preset.id}" class="api-entry-card__description">${preset.description}</span>
    </button>
  `).join("");

  connectorElements.modalProviderGrid.querySelectorAll("[data-provider-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const preset = getProviderPreset(button.getAttribute("data-provider-id"));
      if (!preset) {
        return;
      }

      const nextSettings = cloneValue(connectorState.settings);
      const nextRecord = buildDefaultConnectorRecord(preset);
      nextRecord.id = slugifyConnectorId(`${preset.id}-${Date.now()}`);
      nextRecord.credential_ref = `connector/${nextRecord.id}`;
      nextSettings.connectors.records = [nextRecord, ...nextSettings.connectors.records];
      connectorState.settings = nextSettings;
      connectorState.selectedConnectorId = nextRecord.id;
      closeModal();
      renderAll();
      setFeedback(`Prepared ${preset.name} connector draft. Save it to persist the record.`, "success");
    });
  });
};

const renderAll = () => {
  renderSummary();
  renderDirectory();
  renderDetail();
  renderPolicy();
  renderModalProviders();
};

const saveConnectorSettings = async (message = "Connector saved.") => {
  const selected = getSelectedConnector();
  if (!selected) {
    setFeedback("Choose or create a connector first.", "error");
    return null;
  }

  const nextSettings = cloneValue(connectorState.settings);
  const connectorIndex = nextSettings.connectors.records.findIndex((item) => item.id === selected.id);
  const record = nextSettings.connectors.records[connectorIndex];

  record.name = connectorElements.nameInput.value.trim() || record.name;
  record.status = connectorElements.statusInput.value;
  record.auth_type = connectorElements.authTypeInput.value;
  record.owner = connectorElements.ownerInput.value.trim() || "Workspace";
  record.base_url = connectorElements.baseUrlInput.value.trim();
  record.scopes = connectorElements.scopesInput.value.split(",").map((item) => item.trim()).filter(Boolean);
  record.updated_at = new Date().toISOString();
  record.auth_config = {
    client_id: connectorElements.clientIdInput.value.trim(),
    username: connectorElements.usernameInput.value.trim(),
    header_name: connectorElements.headerNameInput.value.trim(),
    scope_preset: record.provider,
    redirect_uri: connectorElements.redirectUriInput.value.trim(),
    expires_at: record.auth_config?.expires_at || null,
    has_refresh_token: Boolean(record.auth_config?.has_refresh_token),
    client_secret_input: connectorElements.clientSecretInput.value,
    access_token_input: connectorElements.accessTokenInput.value,
    refresh_token_input: connectorElements.refreshTokenInput.value,
    api_key_input: connectorElements.apiKeyInput.value,
    password_input: connectorElements.passwordInput.value,
    header_value_input: connectorElements.headerValueInput.value
  };

  nextSettings.connectors.auth_policy = {
    rotation_interval_days: Number.parseInt(connectorElements.policyRotationInput.value, 10),
    reconnect_requires_approval: connectorElements.policyApprovalInput.checked,
    credential_visibility: connectorElements.policyVisibilityInput.value
  };

  const response = await getStore().updateAppSettings(nextSettings);
  connectorState.settings = response;
  connectorState.selectedConnectorId = selected.id;
  renderAll();
  setFeedback(message, "success");
  return getSelectedConnector();
};

const bindModalEvents = () => {
  connectorElements.createButton?.addEventListener("click", openModal);
  document.querySelectorAll("[data-modal-close=\"settings-connectors-modal\"]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });
};

const bindFormEvents = () => {
  connectorElements.form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveConnectorSettings();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.policyForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveConnectorSettings("Connector policy saved.");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.testButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to test.", "error");
      return;
    }

    try {
      await saveConnectorSettings("Connector saved before test.");
      const response = await requestJson(`/api/v1/connectors/${selected.id}/test`, { method: "POST" });
      const nextSettings = await getStore().ready();
      connectorState.settings = nextSettings;
      connectorState.selectedConnectorId = response.connector.id;
      renderAll();
      setFeedback(response.message, response.ok ? "success" : "warning");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.oauthStartButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to authorize.", "error");
      return;
    }

    try {
      const saved = await saveConnectorSettings("Connector draft saved.");
      if (!saved) {
        return;
      }

      const response = await requestJson(`/api/v1/connectors/${saved.provider}/oauth/start`, {
        method: "POST",
        body: JSON.stringify({
          connector_id: saved.id,
          name: saved.name,
          redirect_uri: connectorElements.redirectUriInput.value.trim() || saved.auth_config?.redirect_uri,
          owner: saved.owner,
          scopes: saved.scopes || [],
          client_id: connectorElements.clientIdInput.value.trim(),
          client_secret_input: connectorElements.clientSecretInput.value
        })
      });
      connectorState.pendingOauth[saved.id] = response;
      const nextSettings = await getStore().ready();
      connectorState.settings = nextSettings;
      connectorState.selectedConnectorId = saved.id;
      renderAll();
      setFeedback(`OAuth started. Use Complete OAuth to simulate the callback. Auth URL: ${response.authorization_url}`, "success");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.oauthCompleteButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    const pending = selected ? connectorState.pendingOauth[selected.id] : null;
    if (!selected || !pending) {
      setFeedback("Start OAuth first.", "error");
      return;
    }

    try {
      const response = await requestJson(
        `/api/v1/connectors/${selected.provider}/oauth/callback?state=${encodeURIComponent(pending.state)}&code=${encodeURIComponent(`demo_${selected.id}`)}&scope=${encodeURIComponent((selected.scopes || []).join(" "))}`
      );
      connectorState.pendingOauth[selected.id] = null;
      const nextSettings = await getStore().ready();
      connectorState.settings = nextSettings;
      connectorState.selectedConnectorId = response.connector.id;
      renderAll();
      setFeedback(response.message, response.ok ? "success" : "warning");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.refreshButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to refresh.", "error");
      return;
    }

    try {
      const response = await requestJson(`/api/v1/connectors/${selected.id}/refresh`, { method: "POST" });
      const nextSettings = await getStore().ready();
      connectorState.settings = nextSettings;
      connectorState.selectedConnectorId = response.connector.id;
      renderAll();
      setFeedback(response.message, "success");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.revokeButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to revoke.", "error");
      return;
    }

    try {
      connectorElements.statusInput.value = "revoked";
      connectorElements.clientSecretInput.value = "";
      connectorElements.accessTokenInput.value = "";
      connectorElements.refreshTokenInput.value = "";
      connectorElements.apiKeyInput.value = "";
      connectorElements.passwordInput.value = "";
      connectorElements.headerValueInput.value = "";
      const nextSettings = cloneValue(connectorState.settings);
      const connectorIndex = nextSettings.connectors.records.findIndex((item) => item.id === selected.id);
      nextSettings.connectors.records[connectorIndex] = {
        ...nextSettings.connectors.records[connectorIndex],
        status: "revoked",
        auth_config: {
          ...nextSettings.connectors.records[connectorIndex].auth_config,
          clear_credentials: true
        }
      };
      const response = await getStore().updateAppSettings(nextSettings);
      connectorState.settings = response;
      connectorState.selectedConnectorId = selected.id;
      renderAll();
      setFeedback("Connector revoked and stored credentials cleared.", "success");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : String(error), "error");
    }
  });

  connectorElements.policyApprovalInput?.addEventListener("change", () => {
    connectorElements.policyApprovalInput.closest(".toggle")?.classList.toggle("toggle--on", connectorElements.policyApprovalInput.checked);
    const approvalLabel = document.getElementById("settings-connectors-policy-approval-label");
    if (approvalLabel) {
      approvalLabel.textContent = connectorElements.policyApprovalInput.checked ? "Required" : "Optional";
    }
  });
};

const initConnectorsPage = async () => {
  if (!connectorElements.tableBody || !connectorElements.form) {
    return;
  }

  bindModalEvents();
  bindFormEvents();

  try {
    connectorState.settings = await getStore().ready();
  } catch {
    connectorState.settings = getStore().getAppSettings();
    setFeedback("Using fallback settings because the database is unavailable.", "warning");
  }

  connectorState.selectedConnectorId = connectorState.settings.connectors.records[0]?.id || null;
  renderAll();
};

initConnectorsPage();
