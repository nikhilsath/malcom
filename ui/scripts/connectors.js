import { formatDateTime, createElementMap } from "./format-utils.js";
import { normalizeRequestError, requestJson } from "./request.js";

const connectorElements = createElementMap({
  feedback: "settings-connectors-feedback",
  createButton: "settings-connectors-create-button",
  tableBody: "settings-connectors-table-body",
  tableShell: "settings-connectors-table-shell",
  empty: "settings-connectors-empty",
  summaryConnected: "settings-connectors-summary-connected-value",
  summaryOauth: "settings-connectors-summary-oauth-value",
  summaryAttention: "settings-connectors-summary-attention-value",
  form: "settings-connectors-form",
  policyForm: "settings-connectors-policy-form",
  nameInput: "settings-connectors-name-input",
  providerInput: "settings-connectors-provider-input",
  statusInput: "settings-connectors-status-input",
  authTypeInput: "settings-connectors-auth-type-input",
  ownerInput: "settings-connectors-owner-input",
  baseUrlInput: "settings-connectors-base-url-input",
  scopesInput: "settings-connectors-scopes-input",
  clientIdInput: "settings-connectors-client-id-input",
  clientSecretInput: "settings-connectors-client-secret-input",
  redirectUriInput: "settings-connectors-redirect-uri-input",
  usernameInput: "settings-connectors-username-input",
  passwordInput: "settings-connectors-password-input",
  accessTokenInput: "settings-connectors-access-token-input",
  refreshTokenInput: "settings-connectors-refresh-token-input",
  apiKeyInput: "settings-connectors-api-key-input",
  headerNameInput: "settings-connectors-header-name-input",
  headerValueInput: "settings-connectors-header-value-input",
  credentialSummary: "settings-connectors-credential-summary-value",
  testButton: "settings-connectors-test-button",
  saveButton: "settings-connectors-save-button",
  oauthStartButton: "settings-connectors-oauth-start-button",
  refreshButton: "settings-connectors-refresh-button",
  revokeButton: "settings-connectors-revoke-button",
  policyRotationInput: "settings-connectors-policy-rotation-input",
  policyApprovalInput: "settings-connectors-policy-approval-input",
  policyVisibilityInput: "settings-connectors-policy-visibility-input",
  modal: "settings-connectors-modal",
  modalProviderGrid: "settings-connectors-modal-provider-grid",
  detailModal: "settings-connectors-detail-modal",
  detailTitle: "settings-connectors-detail-title",
  // Google connector card
  googleSection: "settings-connectors-google-section",
  googleStatusValue: "settings-connectors-google-status-value",
  googleConnectHint: "settings-connectors-google-connect-hint",
  googleDisconnectButton: "settings-connectors-google-disconnect-button",
  googleFeedback: "settings-connectors-google-feedback"
});

const connectorState = {
  settings: null,
  selectedConnectorId: null,
  pendingOauth: {},
  detailReturnFocusElement: null
};

const GOOGLE_RECOMMENDED_SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/calendar.readonly",
  "https://www.googleapis.com/auth/spreadsheets.readonly"
];

const OAUTH_QUERY_KEYS = ["oauth_status", "oauth_message", "connector_id"];

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

const isGoogleConnector = (record) => {
  const provider = (record?.provider || "").toString().trim().toLowerCase();
  return provider === "google" || provider.startsWith("google_");
};

const canonicalizeProvider = (provider) => {
  const normalized = (provider || "").toString().trim().toLowerCase();
  return normalized.startsWith("google_") ? "google" : normalized;
};

const setFieldVisibility = (fieldId, visible) => {
  const field = document.getElementById(fieldId);
  if (!field) {
    return;
  }

  field.hidden = !visible;
  const inputElement = field.querySelector("input, select, textarea");
  if (inputElement) {
    inputElement.disabled = !visible;
  }
};

const applyProviderFieldVisibility = (record) => {
  const google = isGoogleConnector(record);

  setFieldVisibility("settings-connectors-status-field", !google);
  setFieldVisibility("settings-connectors-auth-type-field", !google);
  setFieldVisibility("settings-connectors-owner-field", !google);
  setFieldVisibility("settings-connectors-base-url-field", !google);
  setFieldVisibility("settings-connectors-username-field", !google);
  setFieldVisibility("settings-connectors-password-field", !google);
  setFieldVisibility("settings-connectors-access-token-field", !google);
  setFieldVisibility("settings-connectors-refresh-token-field", !google);
  setFieldVisibility("settings-connectors-api-key-field", !google);
  setFieldVisibility("settings-connectors-header-name-field", !google);
  setFieldVisibility("settings-connectors-header-value-field", !google);

  const googleOauthGuidance = document.getElementById("settings-connectors-google-oauth-guidance");
  if (googleOauthGuidance) {
    googleOauthGuidance.hidden = !google;
  }

  if (connectorElements.testButton) {
    connectorElements.testButton.hidden = google;
  }
  if (connectorElements.saveButton) {
    connectorElements.saveButton.hidden = google;
  }
  if (connectorElements.refreshButton) {
    connectorElements.refreshButton.hidden = google;
  }
  if (connectorElements.revokeButton) {
    connectorElements.revokeButton.hidden = google;
  }
  if (connectorElements.oauthStartButton) {
    connectorElements.oauthStartButton.hidden = !google;
    connectorElements.oauthStartButton.textContent = google ? "Continue with Google" : "Start OAuth";
  }
};

const getProviderPreset = (providerId) => connectorState.settings?.connectors?.catalog?.find((item) => item.id === providerId) || null;

const getDefaultScopesForProvider = (providerId, preset = null) => {
  const presetScopes = preset?.default_scopes || [];
  if (presetScopes.length > 0) {
    return [...presetScopes];
  }
  if (providerId === "google") {
    return [...GOOGLE_RECOMMENDED_SCOPES];
  }
  return [];
};

const openModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.classList.add("modal--open");
  connectorElements.modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

const openDetailModal = () => {
  if (!connectorElements.detailModal || !getSelectedConnector()) {
    return;
  }

  connectorElements.detailModal.classList.add("modal--open");
  connectorElements.detailModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

const closeDetailModal = ({ restoreFocus = true } = {}) => {
  if (!connectorElements.detailModal) {
    return;
  }

  connectorElements.detailModal.classList.remove("modal--open");
  connectorElements.detailModal.setAttribute("aria-hidden", "true");
  if (!document.querySelector(".modal.modal--open")) {
    document.body.classList.remove("modal-open");
  }

  if (restoreFocus && connectorState.detailReturnFocusElement instanceof HTMLElement) {
    connectorState.detailReturnFocusElement.focus();
  }
};

const closeModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.classList.remove("modal--open");
  connectorElements.modal.setAttribute("aria-hidden", "true");
  if (!document.querySelector(".modal.modal--open")) {
    document.body.classList.remove("modal-open");
  }
};

const buildDefaultConnectorRecord = (preset) => {
  const connectorId = preset.id === "google" ? "google" : slugifyConnectorId(`${preset.id}-${preset.name}`);
  const defaultScopes = getDefaultScopesForProvider(preset.id, preset);
  const redirectPath = preset.id === "google"
    ? `/api/v1/connectors/${preset.id}/oauth/callback/ui`
    : `/api/v1/connectors/${preset.id}/oauth/callback`;

  return {
    id: connectorId,
    provider: preset.id,
    name: preset.name,
    status: "draft",
    auth_type: preset.auth_types[0] || "bearer",
    scopes: defaultScopes,
    base_url: preset.base_url || "",
    owner: "Workspace",
    docs_url: preset.docs_url,
    credential_ref: `connector/${connectorId}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_tested_at: null,
    auth_config: {
      client_id: "",
      username: "",
      header_name: "",
      scope_preset: preset.id,
      redirect_uri: `${window.location.origin}${redirectPath}`,
      expires_at: null,
      has_refresh_token: false
    }
  };
};

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
  const records = (connectorState.settings?.connectors?.records || []).filter((r) => !isGoogleConnector(r));
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
    row.setAttribute("aria-haspopup", "dialog");
    const handleSelect = () => {
      connectorState.selectedConnectorId = record.id;
      connectorState.detailReturnFocusElement = row;
      renderAll();
      openDetailModal();
    };
    row.addEventListener("click", handleSelect);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        handleSelect();
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
    if (connectorElements.authTypeInput) {
      connectorElements.authTypeInput.innerHTML = "";
    }
    if (connectorElements.detailTitle) {
      connectorElements.detailTitle.textContent = "Choose a connector";
    }
    if (connectorElements.credentialSummary) {
      connectorElements.credentialSummary.textContent = "Select a connector to edit its settings.";
    }
    applyProviderFieldVisibility(null);
    return;
  }

  if (connectorElements.detailTitle) {
    connectorElements.detailTitle.textContent = record.name || "Connector details";
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
  applyProviderFieldVisibility(record);
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

const startConnectorOauth = async (record, { clientSecretInput = "", closeDetailOnRedirect = false } = {}) => {
  if (!record) {
    setFeedback("Choose a connector to authorize.", "error");
    return;
  }

  const provider = canonicalizeProvider(record.provider);
  const fallbackRedirectPath = provider === "google"
    ? `/api/v1/connectors/${provider}/oauth/callback/ui`
    : `/api/v1/connectors/${provider}/oauth/callback`;
  const redirectUri = (record.auth_config?.redirect_uri || `${window.location.origin}${fallbackRedirectPath}`).trim();

  if (provider === "google") {
    const clientId = (record.auth_config?.client_id || "").trim();
    if (!clientId) {
      setFeedback("Google OAuth requires a Client ID. Enter it in the Client ID field.", "error");
      connectorElements.clientIdInput?.focus();
      return;
    }
    try {
      const parsedRedirectUri = new URL(redirectUri);
      if (!["http:", "https:"].includes(parsedRedirectUri.protocol)) {
        throw new Error("Invalid redirect URI protocol");
      }
    } catch {
      setFeedback("Google OAuth requires a valid Redirect URI (http or https).", "error");
      return;
    }
  }

  const response = await requestJson(`/api/v1/connectors/${provider}/oauth/start`, {
    method: "POST",
    body: JSON.stringify({
      connector_id: record.id,
      name: record.name,
      redirect_uri: redirectUri,
      owner: record.owner || "Workspace",
      scopes: (record.scopes || []).length > 0
        ? record.scopes
        : getDefaultScopesForProvider(provider),
      client_id: (record.auth_config?.client_id || "").trim(),
      client_secret_input: clientSecretInput
    })
  });

  connectorState.pendingOauth[record.id] = response;
  const nextSettings = await getStore().ready();
  connectorState.settings = nextSettings;
  connectorState.selectedConnectorId = record.id;
  renderAll();
  if (closeDetailOnRedirect) {
    closeDetailModal({ restoreFocus: false });
  }
  setFeedback(`Redirecting to ${titleCase(provider)} login...`, "success");
  window.location.assign(response.authorization_url);
};

const ensureGoogleConnectorRecord = async () => {
  const existingGoogle = getGoogleConnector();
  if (existingGoogle) {
    return existingGoogle;
  }

  const preset = getProviderPreset("google");
  if (!preset) {
    return null;
  }

  const nextSettings = cloneValue(connectorState.settings);
  const nextRecord = buildDefaultConnectorRecord(preset);
  nextSettings.connectors.records = [nextRecord, ...nextSettings.connectors.records];
  const response = await getStore().updateAppSettings(nextSettings);
  connectorState.settings = response;
  return getGoogleConnector();
};

const renderModalProviders = () => {
  if (!connectorElements.modalProviderGrid) {
    return;
  }

  const catalog = connectorState.settings?.connectors?.catalog || [];
  connectorElements.modalProviderGrid.innerHTML = catalog.map((preset) => `
    <button type="button" id="settings-connectors-provider-option-${preset.id}" class="api-entry-card" data-provider-id="${preset.id}">
      <span id="settings-connectors-provider-option-title-${preset.id}" class="api-entry-card__title">${preset.name}</span>
      <span id="settings-connectors-provider-option-description-${preset.id}" class="api-entry-card__description">${preset.id === "google" ? "Continue with Google to connect your workspace." : preset.description}</span>
    </button>
  `).join("");

  connectorElements.modalProviderGrid.querySelectorAll("[data-provider-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const preset = getProviderPreset(button.getAttribute("data-provider-id"));
      if (!preset) {
        return;
      }

      if (preset.id === "google") {
        try {
          closeModal();
          const googleRecord = await ensureGoogleConnectorRecord();
          if (!googleRecord) {
            setFeedback("Google preset is unavailable in this workspace.", "error");
            return;
          }
          connectorState.selectedConnectorId = googleRecord.id;
          connectorState.detailReturnFocusElement = connectorElements.createButton;
          renderAll();
          openDetailModal();
          if ((googleRecord.auth_config?.client_id || "").trim()) {
            connectorElements.oauthStartButton?.focus();
          } else {
            connectorElements.clientIdInput?.focus();
          }
          setFeedback("Google connector draft ready. Review the OAuth fields, then click Authorize.", "success");
        } catch (error) {
          setFeedback(normalizeRequestError(error).message, "error");
        }
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
      openDetailModal();
      setFeedback(`Prepared ${preset.name} connector draft. Add credentials and save to persist the record.`, "success");
    });
  });
};

const renderAll = () => {
  renderSummary();
  renderGoogleCard();
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
  const google = isGoogleConnector(record);

  record.name = connectorElements.nameInput.value.trim() || record.name;
  record.status = google ? record.status : connectorElements.statusInput.value;
  record.auth_type = google ? "oauth2" : connectorElements.authTypeInput.value;
  record.owner = google ? (record.owner || "Workspace") : (connectorElements.ownerInput.value.trim() || "Workspace");
  record.base_url = google ? (record.base_url || "https://www.googleapis.com") : connectorElements.baseUrlInput.value.trim();
  record.scopes = connectorElements.scopesInput.value.split(",").map((item) => item.trim()).filter(Boolean);
  record.updated_at = new Date().toISOString();
  record.auth_config = {
    client_id: connectorElements.clientIdInput.value.trim(),
    username: google ? (record.auth_config?.username || "") : connectorElements.usernameInput.value.trim(),
    header_name: google ? (record.auth_config?.header_name || "") : connectorElements.headerNameInput.value.trim(),
    scope_preset: record.provider,
    redirect_uri: connectorElements.redirectUriInput.value.trim(),
    expires_at: record.auth_config?.expires_at || null,
    has_refresh_token: Boolean(record.auth_config?.has_refresh_token),
    client_secret_input: connectorElements.clientSecretInput.value,
    access_token_input: google ? "" : connectorElements.accessTokenInput.value,
    refresh_token_input: google ? "" : connectorElements.refreshTokenInput.value,
    api_key_input: google ? "" : connectorElements.apiKeyInput.value,
    password_input: google ? "" : connectorElements.passwordInput.value,
    header_value_input: google ? "" : connectorElements.headerValueInput.value
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

const getGoogleConnector = () => connectorState.settings?.connectors?.records?.find((r) => isGoogleConnector(r)) || null;

const renderGoogleCard = () => {
  const connector = getGoogleConnector();
  if (!connectorElements.googleStatusValue) {
    return;
  }

  if (connector?.status === "connected") {
    connectorElements.googleStatusValue.textContent = "Connected";
    connectorElements.googleStatusValue.className = "google-connector-status-value google-connector-status-value--connected";
    if (connectorElements.googleConnectHint) {
      connectorElements.googleConnectHint.hidden = true;
    }
    if (connectorElements.googleDisconnectButton) {
      connectorElements.googleDisconnectButton.hidden = false;
    }
  } else {
    connectorElements.googleStatusValue.textContent = "Not connected";
    connectorElements.googleStatusValue.className = "google-connector-status-value";
    if (connectorElements.googleConnectHint) {
      connectorElements.googleConnectHint.hidden = false;
    }
    if (connectorElements.googleDisconnectButton) {
      connectorElements.googleDisconnectButton.hidden = true;
    }
  }
};

const setGoogleFeedback = (message, tone = "") => {
  if (!connectorElements.googleFeedback) {
    return;
  }

  connectorElements.googleFeedback.textContent = message;
  connectorElements.googleFeedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const bindGoogleEvents = () => {
  connectorElements.googleDisconnectButton?.addEventListener("click", async () => {
    try {
      const connector = getGoogleConnector();
      if (!connector) {
        setGoogleFeedback("No Google connector to disconnect.", "error");
        return;
      }

      if (!confirm("Disconnect your Google account? Malcom will no longer have access to your Google services.")) {
        return;
      }

      const nextSettings = cloneValue(connectorState.settings);
      const idx = nextSettings.connectors.records.findIndex((r) => r.id === connector.id);
      if (idx >= 0) {
        nextSettings.connectors.records[idx].status = "revoked";
        nextSettings.connectors.records[idx].auth_config = {
          client_id: "",
          client_secret_input: "",
          redirect_uri: `${window.location.origin}/api/v1/connectors/google/oauth/callback/ui`,
          expires_at: null,
          has_refresh_token: false,
          clear_credentials: true
        };
      }
      const response = await getStore().updateAppSettings(nextSettings);
      connectorState.settings = response;
      renderGoogleCard();
      setGoogleFeedback("Google account disconnected.", "success");
    } catch (error) {
      setGoogleFeedback(normalizeRequestError(error).message, "error");
    }
  });
};

const bindModalEvents = () => {
  connectorElements.createButton?.addEventListener("click", openModal);
  document.querySelectorAll("[data-modal-close=\"settings-connectors-modal\"]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });
  document.querySelectorAll("[data-modal-close=\"settings-connectors-detail-modal\"]").forEach((element) => {
    element.addEventListener("click", () => closeDetailModal());
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (connectorElements.detailModal?.classList.contains("modal--open")) {
        closeDetailModal();
      } else if (connectorElements.modal?.classList.contains("modal--open")) {
        closeModal();
      }
    }
  });
};

const bindFormEvents = () => {
  connectorElements.form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveConnectorSettings();
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
  });

  connectorElements.policyForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveConnectorSettings("Connector policy saved.");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
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
      openDetailModal();
      setFeedback(response.message, response.ok ? "success" : "warning");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
  });

  connectorElements.oauthStartButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to authorize.", "error");
      return;
    }

    // Capture secret before saveConnectorSettings calls renderAll which clears the input
    const clientSecretInput = connectorElements.clientSecretInput?.value || "";

    if (isGoogleConnector(selected)) {
      const clientId = connectorElements.clientIdInput?.value.trim() || "";
      if (!clientId) {
        setFeedback("Google OAuth requires a Client ID. Enter it in the Client ID field.", "error");
        connectorElements.clientIdInput?.focus();
        return;
      }
    }

    try {
      const saved = await saveConnectorSettings("Connector draft saved.");
      if (!saved) {
        return;
      }

      await startConnectorOauth(saved, {
        clientSecretInput,
        closeDetailOnRedirect: true
      });
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
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
      openDetailModal();
      setFeedback(response.message, "success");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
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
      openDetailModal();
      setFeedback("Connector revoked and stored credentials cleared.", "success");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
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

const handleOauthQueryState = async () => {
  const params = new URLSearchParams(window.location.search);
  const oauthStatus = params.get("oauth_status");
  const oauthMessage = params.get("oauth_message");
  const connectorId = params.get("connector_id");

  if (oauthStatus && oauthMessage) {
    const tone = oauthStatus === "success" ? "success" : oauthStatus === "warning" ? "warning" : "error";
    setFeedback(oauthMessage, tone);
  }

  if (connectorId) {
    // Reload settings from backend to get the updated connector status
    try {
      connectorState.settings = await getStore().ready();
    } catch {
      connectorState.settings = getStore().getAppSettings();
    }
    
    const selected = connectorState.settings?.connectors?.records?.find((record) => record.id === connectorId) || null;
    if (selected) {
      connectorState.selectedConnectorId = selected.id;
      renderAll();
      openDetailModal();
    }
  }

  if (OAUTH_QUERY_KEYS.some((key) => params.has(key))) {
    OAUTH_QUERY_KEYS.forEach((key) => params.delete(key));
    const nextQuery = params.toString();
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash}`;
    window.history.replaceState({}, "", nextUrl);
  }
};

const initConnectorsPage = async () => {
  if (!connectorElements.tableBody || !connectorElements.form) {
    return;
  }

  bindModalEvents();
  bindFormEvents();
  bindGoogleEvents();

  try {
    connectorState.settings = await getStore().ready();
  } catch {
    connectorState.settings = getStore().getAppSettings();
    setFeedback("Using fallback settings because the database is unavailable.", "warning");
  }

  connectorState.selectedConnectorId = null;
  renderAll();
  await handleOauthQueryState();
};

initConnectorsPage();
