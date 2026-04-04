import { formatDateTime } from "../../format-utils.js";
import { connectorElements } from "./dom.js";
import {
  canonicalizeProvider,
  connectorState,
  getDefaultScopesForProvider,
  getProviderActionLabel,
  getProviderMetadata,
  getProviderPreset,
  getSelectedConnector,
  providerSupportsOauth,
  titleCase,
  usesProviderSetupPanel
} from "./state.js";

const PROVIDER_PANEL_ELEMENTS = {
  google: {
    panel: connectorElements.googleSetupPanel,
    formGrid: connectorElements.googleFormGrid,
    statusBadge: connectorElements.googleStatusBadge,
    statusMessage: connectorElements.googleStatusMessage,
    lastChecked: connectorElements.googleLastChecked,
    nameInput: connectorElements.googleNameInput,
    providerInput: connectorElements.googleProviderInput,
    clientIdInput: connectorElements.googleClientIdInput,
    clientSecretInput: connectorElements.googleClientSecretInput,
    scopesInput: connectorElements.googleScopesInput,
    redirectUriInput: connectorElements.googleRedirectUriInput
  },
  github: {
    panel: connectorElements.githubSetupPanel,
    formGrid: connectorElements.githubFormGrid,
    statusBadge: connectorElements.githubStatusBadge,
    statusMessage: connectorElements.githubStatusMessage,
    lastChecked: connectorElements.githubLastChecked,
    nameInput: connectorElements.githubNameInput,
    providerInput: connectorElements.githubProviderInput,
    accessTokenInput: connectorElements.githubAccessTokenInput,
    scopesInput: connectorElements.githubScopesInput,
  },
  notion: {
    panel: connectorElements.notionSetupPanel,
    formGrid: connectorElements.notionFormGrid,
    statusBadge: connectorElements.notionStatusBadge,
    statusMessage: connectorElements.notionStatusMessage,
    lastChecked: connectorElements.notionLastChecked,
    nameInput: connectorElements.notionNameInput,
    providerInput: connectorElements.notionProviderInput,
    clientIdInput: connectorElements.notionClientIdInput,
    clientSecretInput: connectorElements.notionClientSecretInput,
    redirectUriInput: connectorElements.notionRedirectUriInput
  },
  trello: {
    panel: connectorElements.trelloSetupPanel,
    formGrid: connectorElements.trelloFormGrid,
    statusBadge: connectorElements.trelloStatusBadge,
    statusMessage: connectorElements.trelloStatusMessage,
    lastChecked: connectorElements.trelloLastChecked,
    nameInput: connectorElements.trelloNameInput,
    providerInput: connectorElements.trelloProviderInput,
    clientIdInput: connectorElements.trelloClientIdInput,
    clientSecretInput: connectorElements.trelloClientSecretInput,
    redirectUriInput: connectorElements.trelloRedirectUriInput
  }
};

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

const setSectionVisibility = (section, visible) => {
  if (!section) {
    return;
  }

  section.hidden = !visible;
  if (visible) {
    section.style.removeProperty("display");
  } else {
    section.style.setProperty("display", "none", "important");
  }
  section.querySelectorAll("input, select, textarea, button").forEach((element) => {
    element.disabled = !visible;
  });
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

const getStatusBadgeClassName = (status) => {
  if (status === "connected") {
    return "status-badge status-badge--success";
  }
  if (status === "needs_attention" || status === "expired") {
    return "status-badge status-badge--warning";
  }
  if (status === "revoked") {
    return "status-badge status-badge--danger";
  }
  return "status-badge status-badge--muted";
};

const hasStoredConnectionMaterial = (record) => Boolean(
  record?.auth_config?.has_refresh_token
  || record?.auth_config?.refresh_token_masked
  || record?.auth_config?.access_token_masked
  || record?.auth_config?.api_key_masked
  || record?.auth_config?.password_masked
  || record?.auth_config?.header_value_masked
);

const getDisplayStatus = (record) => {
  const provider = canonicalizeProvider(record?.provider);
  if (providerSupportsOauth(provider) && record?.status === "draft" && hasStoredConnectionMaterial(record)) {
    return "connected";
  }
  return record?.status || "draft";
};

const getProviderStatusMessage = (record) => {
  const providerMetadata = getProviderMetadata(record?.provider);
  const displayStatus = getDisplayStatus(record);
  return providerMetadata?.status_messages?.[displayStatus]
    || providerMetadata?.status_messages?.draft
    || "Enter credentials and complete provider-specific setup for this connector.";
};

const clearProviderPanelInputs = () => {
  Object.values(PROVIDER_PANEL_ELEMENTS).forEach((elements) => {
    Object.values(elements).forEach((element) => {
      if (element instanceof HTMLInputElement) {
        element.value = "";
      }
      if (element instanceof HTMLSelectElement) {
        element.innerHTML = "";
      }
    });
  });
};

const renderProviderSetupState = (record) => {
  const provider = canonicalizeProvider(record?.provider);

  Object.entries(PROVIDER_PANEL_ELEMENTS).forEach(([providerId, elements]) => {
    const visible = record && providerId === provider;
    elements.panel?.toggleAttribute("hidden", !visible);

    if (!visible) {
      if (elements.statusBadge) {
        elements.statusBadge.textContent = "Draft";
        elements.statusBadge.className = getStatusBadgeClassName("draft");
      }
      if (elements.statusMessage) {
        const emptyCopy = getProviderMetadata(providerId)?.status_messages?.draft || "Connector setup is not active.";
        elements.statusMessage.textContent = emptyCopy;
      }
      if (elements.lastChecked) {
        const emptyMessage = getProviderMetadata(providerId)?.ui_copy?.last_checked_empty || "Connector has not been checked yet.";
        elements.lastChecked.textContent = emptyMessage;
      }
      return;
    }

    const providerMetadata = getProviderMetadata(providerId);
    const displayStatus = getDisplayStatus(record);
    if (elements.statusBadge) {
      elements.statusBadge.textContent = titleCase(displayStatus);
      elements.statusBadge.className = getStatusBadgeClassName(displayStatus);
    }
    if (elements.statusMessage) {
      elements.statusMessage.textContent = getProviderStatusMessage(record);
    }
    if (elements.lastChecked) {
      elements.lastChecked.textContent = record.last_tested_at
        ? `Last checked ${formatDateTime(record.last_tested_at, "Not checked")}.`
        : (providerMetadata?.ui_copy?.last_checked_empty || "Connector has not been checked yet.");
    }
  });
};

const applyProviderFieldVisibility = (record) => {
  const provider = canonicalizeProvider(record?.provider);
  const providerMetadata = getProviderMetadata(provider);
  const providerPanel = usesProviderSetupPanel(record);
  const oauthProvider = providerSupportsOauth(provider);
  const displayStatus = getDisplayStatus(record);
  const hasStoredMaterial = hasStoredConnectionMaterial(record);

  setSectionVisibility(connectorElements.formGrid, !providerPanel);
  Object.entries(PROVIDER_PANEL_ELEMENTS).forEach(([providerId, elements]) => {
    setSectionVisibility(elements.formGrid, providerPanel && providerId === provider);
  });

  const hideGenericFields = providerPanel;
  setFieldVisibility("settings-connectors-status-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-auth-type-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-owner-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-base-url-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-username-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-password-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-access-token-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-refresh-token-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-api-key-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-header-name-field", !hideGenericFields);
  setFieldVisibility("settings-connectors-header-value-field", !hideGenericFields);

  if (connectorElements.credentialSummary) {
    connectorElements.credentialSummary.closest("#settings-connectors-credential-summary")?.toggleAttribute("hidden", providerPanel);
  }

  if (connectorElements.scopesInput) {
    connectorElements.scopesInput.readOnly = oauthProvider;
    connectorElements.scopesInput.disabled = oauthProvider;
    connectorElements.scopesInput.classList.toggle("api-form-input--locked", oauthProvider);
    connectorElements.scopesInput.placeholder = oauthProvider
      ? "Default provider scopes"
      : "Leave empty or enter comma-separated scopes";
  }

  if (connectorElements.redirectUriInput) {
    connectorElements.redirectUriInput.readOnly = oauthProvider;
    connectorElements.redirectUriInput.disabled = false;
    connectorElements.redirectUriInput.classList.toggle("api-form-input--locked", oauthProvider);
  }

  if (connectorElements.saveButton) {
    connectorElements.saveButton.hidden = providerPanel && oauthProvider;
    connectorElements.saveButton.textContent = getProviderActionLabel(provider, "save", "Save connector");
  }
  if (connectorElements.testButton) {
    connectorElements.testButton.hidden = providerPanel && oauthProvider ? !record || displayStatus === "pending_oauth" : false;
    connectorElements.testButton.textContent = getProviderActionLabel(provider, "test", "Test connector");
  }
  if (connectorElements.oauthStartButton) {
    const reconnecting = displayStatus === "connected" || displayStatus === "needs_attention" || displayStatus === "revoked" || hasStoredMaterial;
    connectorElements.oauthStartButton.hidden = !oauthProvider;
    connectorElements.oauthStartButton.textContent = reconnecting
      ? getProviderActionLabel(provider, "reconnect", "Reconnect provider")
      : getProviderActionLabel(provider, "connect", "Start OAuth");
  }
  if (connectorElements.refreshButton) {
    const showRefresh = Boolean(providerMetadata?.refresh_supported) && Boolean(record?.auth_config?.has_refresh_token || record?.auth_config?.refresh_token_masked);
    connectorElements.refreshButton.hidden = !showRefresh;
    connectorElements.refreshButton.textContent = getProviderActionLabel(provider, "refresh", "Refresh token");
  }
  if (connectorElements.revokeButton) {
    const showRevoke = Boolean(providerMetadata?.revoke_supported || !providerPanel) && Boolean(record) && (hasStoredMaterial || displayStatus !== "draft");
    connectorElements.revokeButton.hidden = !showRevoke;
    connectorElements.revokeButton.textContent = getProviderActionLabel(provider, "revoke", "Revoke connector");
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
    const displayStatus = getDisplayStatus(record);
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
      <td id="settings-connectors-row-status-${record.id}" class="api-directory-cell"><span class="${getStatusBadgeClassName(displayStatus)}">${titleCase(displayStatus)}</span></td>
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
    clearProviderPanelInputs();
    renderProviderSetupState(null);
    applyProviderFieldVisibility(null);
    return;
  }

  const provider = canonicalizeProvider(record.provider);
  const providerMetadata = getProviderMetadata(provider);
  const preset = getProviderPreset(record.provider);
  const providerPanel = usesProviderSetupPanel(record);
  const providerUiCopy = providerMetadata?.ui_copy;

  if (connectorElements.detailTitle) {
    connectorElements.detailTitle.textContent = providerPanel
      ? (providerUiCopy?.title || `${titleCase(provider)} setup`)
      : (record.name || "Connector details");
  }
  if (connectorElements.detailEyebrow) {
    connectorElements.detailEyebrow.textContent = providerPanel
      ? (providerUiCopy?.eyebrow || titleCase(provider))
      : "Connector setup";
  }
  if (connectorElements.detailDescription) {
    connectorElements.detailDescription.textContent = providerPanel
      ? (providerUiCopy?.description || "Enter credentials and complete provider-specific setup for this connector.")
      : "Provider metadata, scope selection, and saved auth settings appear here.";
  }
  if (connectorElements.detailDescriptionBadge) {
    connectorElements.detailDescriptionBadge.setAttribute(
      "aria-label",
      providerPanel ? `${titleCase(provider)} setup information` : "More information"
    );
  }

  renderStatusOptions(record);
  renderAuthTypeOptions(record);
  connectorElements.nameInput.value = record.name || "";
  connectorElements.providerInput.value = preset?.name || titleCase(record.provider);
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

  clearProviderPanelInputs();
  const panelElements = PROVIDER_PANEL_ELEMENTS[provider];
  if (panelElements) {
    if (panelElements.nameInput) {
      panelElements.nameInput.value = record.name || "";
    }
    if (panelElements.providerInput) {
      panelElements.providerInput.value = preset?.name || titleCase(record.provider);
    }
    if (panelElements.clientIdInput) {
      panelElements.clientIdInput.value = record.auth_config?.client_id || "";
    }
    if (panelElements.clientSecretInput) {
      panelElements.clientSecretInput.value = "";
    }
    if (panelElements.scopesInput) {
      const scopes = providerMetadata?.scopes_locked
        ? (provider === "github" ? (record.scopes || []) : getDefaultScopesForProvider(record.provider, preset))
        : (record.scopes || []);
      const scopeOptions = (preset?.recommended_scopes?.length ? preset.recommended_scopes : preset?.default_scopes || []);
      if (panelElements.scopesInput instanceof HTMLSelectElement) {
        const optionValues = provider === "github" && providerMetadata?.scopes_locked
          ? Array.from(new Set(scopes))
          : Array.from(new Set([...scopeOptions, ...scopes]));
        panelElements.scopesInput.innerHTML = optionValues
          .map((scope) => `<option value="${scope}">${scope}</option>`)
          .join("");
        Array.from(panelElements.scopesInput.options).forEach((option) => {
          option.selected = scopes.includes(option.value);
        });
        panelElements.scopesInput.disabled = Boolean(providerMetadata?.scopes_locked);
        panelElements.scopesInput.classList.toggle("api-form-input--locked", Boolean(providerMetadata?.scopes_locked));
      } else {
        panelElements.scopesInput.value = scopes.join(", ");
        panelElements.scopesInput.readOnly = Boolean(providerMetadata?.scopes_locked);
        panelElements.scopesInput.classList.toggle("api-form-input--locked", Boolean(providerMetadata?.scopes_locked));
      }
    }
    if (panelElements.redirectUriInput) {
      const redirectUri = record.auth_config?.redirect_uri
        || (providerMetadata?.default_redirect_path ? `${window.location.origin}${providerMetadata.default_redirect_path}` : "");
      panelElements.redirectUriInput.value = redirectUri;
    }
    if (panelElements.apiKeyInput) {
      panelElements.apiKeyInput.value = "";
    }
    if (panelElements.accessTokenInput) {
      panelElements.accessTokenInput.value = "";
    }
  }

  renderProviderSetupState(record);
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
  connectorElements.modalProviderGrid.innerHTML = catalog.map((preset) => {
    const providerMetadata = getProviderMetadata(preset.id);
    const connectLabel = getProviderActionLabel(preset.id, "connect", preset.description);
    const description = providerMetadata?.ui_copy?.description
      || (providerSupportsOauth(preset.id) ? connectLabel : preset.description);
    return `
      <button type="button" id="settings-connectors-provider-option-${preset.id}" class="api-popup-option" data-provider-id="${preset.id}">
        <span id="settings-connectors-provider-option-title-${preset.id}" class="api-popup-option__title">${preset.name}</span>
        <span id="settings-connectors-provider-option-description-${preset.id}" class="api-popup-option__description">${description}</span>
      </button>
    `;
  }).join("");

  connectorElements.modalProviderGrid.querySelectorAll("[data-provider-id]").forEach((button) => {
    button.addEventListener("click", () => {
      onSelectPreset(button.getAttribute("data-provider-id"), button);
    });
  });
};
