import { formatDateTime } from "../../format-utils.js";
import { connectorElements } from "./dom.js";
import {
  connectorState,
  getDefaultScopesForProvider,
  getProviderPreset,
  getSelectedConnector,
  isGoogleConnector,
  titleCase
} from "./state.js";

export const setFeedback = (message, tone = "") => {
  if (!connectorElements.feedback) {
    return;
  }

  connectorElements.feedback.textContent = message;
  connectorElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const renderSelectOptions = (element, options, { selectedValue = "" } = {}) => {
  if (!element) {
    return;
  }

  element.innerHTML = options
    .map((option) => `<option value="${option.value}">${option.label}</option>`)
    .join("");
  if (selectedValue) {
    element.value = selectedValue;
  }
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

  if (connectorElements.credentialSummary) {
    connectorElements.credentialSummary.closest("#settings-connectors-credential-summary")?.toggleAttribute("hidden", google);
  }

  if (connectorElements.scopesInput) {
    connectorElements.scopesInput.readOnly = google;
    connectorElements.scopesInput.disabled = google;
    connectorElements.scopesInput.classList.toggle("api-form-input--locked", google);
    connectorElements.scopesInput.placeholder = google
      ? "Google default scopes"
      : "Leave empty or enter comma-separated scopes";
  }

  if (connectorElements.redirectUriInput) {
    connectorElements.redirectUriInput.readOnly = false;
    connectorElements.redirectUriInput.disabled = false;
    connectorElements.redirectUriInput.classList.remove("api-form-input--locked");
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

const renderAuthTypeOptions = (record) => {
  if (!connectorElements.authTypeInput) {
    return;
  }

  const preset = getProviderPreset(record.provider);
  const authTypes = preset?.auth_types || [record.auth_type];
  connectorElements.authTypeInput.innerHTML = authTypes
    .map((authType) => `<option value="${authType}">${titleCase(authType)}</option>`)
    .join("");
  connectorElements.authTypeInput.value = record.auth_type;
};

const renderStatusOptions = (record) => {
  const statusOptions = connectorState.connectors?.metadata?.statuses || [];
  renderSelectOptions(connectorElements.statusInput, statusOptions, { selectedValue: record?.status || "" });
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

export const renderSummary = () => {
  const records = connectorState.connectors?.records || [];
  const connected = records.filter((item) => item.status === "connected").length;
  const oauth = records.filter((item) => item.auth_type === "oauth2").length;
  const attention = records.filter((item) => item.status !== "connected" && item.status !== "draft" && item.status !== "pending_oauth").length;

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

export const renderDirectory = (onSelectRecord) => {
  const records = connectorState.connectors?.records || [];
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
    const handleSelect = () => onSelectRecord(record.id, row);
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

export const renderDetail = () => {
  const record = getSelectedConnector();

  if (!record) {
    connectorElements.form?.reset();
    if (connectorElements.authTypeInput) {
      connectorElements.authTypeInput.innerHTML = "";
    }
    if (connectorElements.detailEyebrow) {
      connectorElements.detailEyebrow.textContent = "Connector setup";
    }
    if (connectorElements.detailTitle) {
      connectorElements.detailTitle.textContent = "Connector setup";
    }
    if (connectorElements.detailDescription) {
      connectorElements.detailDescription.textContent = "Enter credentials and complete provider-specific setup for this connector.";
    }
    if (connectorElements.credentialSummary) {
      connectorElements.credentialSummary.textContent = "Select a connector to edit its settings.";
    }
    applyProviderFieldVisibility(null);
    return;
  }

  const google = isGoogleConnector(record);
  if (connectorElements.detailTitle) {
    connectorElements.detailTitle.textContent = google ? "Google OAuth setup" : (record.name || "Connector details");
  }
  if (connectorElements.detailEyebrow) {
    connectorElements.detailEyebrow.textContent = google ? "Google" : "Connector setup";
  }
  if (connectorElements.detailDescription) {
    connectorElements.detailDescription.textContent = google
      ? "Use Google OAuth Web Application credentials. Enter Name, Client ID, Client secret, and a redirect URI that exactly matches Google Cloud."
      : "Provider metadata, scope selection, and saved auth settings appear here.";
  }
  if (connectorElements.detailDescriptionBadge) {
    connectorElements.detailDescriptionBadge.setAttribute(
      "aria-label",
      google ? "Google OAuth setup information" : "More information"
    );
  }
  renderStatusOptions(record);
  renderAuthTypeOptions(record);
  connectorElements.nameInput.value = record.name || "";
  connectorElements.providerInput.value = getProviderPreset(record.provider)?.name || titleCase(record.provider);
  connectorElements.ownerInput.value = record.owner || "";
  connectorElements.baseUrlInput.value = record.base_url || "";
  connectorElements.scopesInput.value = (
    google
      ? getDefaultScopesForProvider(record.provider, getProviderPreset(record.provider)).map((scope) => scope.trim()).filter(Boolean)
      : (record.scopes || [])
  ).join(", ");
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

export const renderPolicy = () => {
  const policy = connectorState.connectors?.auth_policy;
  const policyMetadata = connectorState.connectors?.metadata?.auth_policy;
  if (
    !policy
    || !policyMetadata
    || !connectorElements.policyRotationInput
    || !connectorElements.policyApprovalInput
    || !connectorElements.policyVisibilityInput
  ) {
    return;
  }

  renderSelectOptions(connectorElements.policyRotationInput, policyMetadata.rotation_intervals, {
    selectedValue: String(policy.rotation_interval_days)
  });
  renderSelectOptions(connectorElements.policyVisibilityInput, policyMetadata.credential_visibility_options, {
    selectedValue: policy.credential_visibility
  });
  connectorElements.policyRotationInput.value = String(policy.rotation_interval_days);
  connectorElements.policyApprovalInput.checked = Boolean(policy.reconnect_requires_approval);
  connectorElements.policyApprovalInput.closest(".toggle")?.classList.toggle(
    "toggle--on",
    connectorElements.policyApprovalInput.checked
  );
  const approvalLabel = document.getElementById("settings-connectors-policy-approval-label");
  if (approvalLabel) {
    approvalLabel.textContent = connectorElements.policyApprovalInput.checked ? "Required" : "Optional";
  }
};

export const renderModalProviders = (onSelectPreset) => {
  if (!connectorElements.modalProviderGrid) {
    return;
  }

  const catalog = connectorState.connectors?.catalog || [];
  connectorElements.modalProviderGrid.innerHTML = catalog.map((preset) => `
    <button type="button" id="settings-connectors-provider-option-${preset.id}" class="api-popup-option" data-provider-id="${preset.id}">
      <span id="settings-connectors-provider-option-title-${preset.id}" class="api-popup-option__title">${preset.name}</span>
      <span id="settings-connectors-provider-option-description-${preset.id}" class="api-popup-option__description">${preset.id === "google" ? "Continue with Google to connect your workspace." : preset.description}</span>
    </button>
  `).join("");

  connectorElements.modalProviderGrid.querySelectorAll("[data-provider-id]").forEach((button) => {
    button.addEventListener("click", () => {
      onSelectPreset(button.getAttribute("data-provider-id"), button);
    });
  });
};
