import { normalizeRequestError, requestJson } from "../../request.js";
import { connectorElements } from "./dom.js";
import { openDetailModal, closeDetailModal } from "./modal.js";
import {
  connectorState,
  getDefaultScopesForProvider,
  getProviderMetadata,
  getProviderPreset,
  providerSupportsOauth,
  getSelectedConnector,
  slugifyConnectorId,
  titleCase,
  usesProviderSetupPanel,
  getStore
} from "./state.js";
import { setFeedback } from "./render.js";

export const buildDefaultConnectorRecord = (preset) => {
  const connectorId = preset.id === "google" ? "google" : slugifyConnectorId(`${preset.id}-${preset.name}`);
  const defaultScopes = getDefaultScopesForProvider(preset.id, preset);
  const providerMetadata = getProviderMetadata(preset.id);
  const redirectPath = providerMetadata?.default_redirect_path;

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
      redirect_uri: redirectPath ? `${window.location.origin}${redirectPath}` : "",
      expires_at: null,
      has_refresh_token: false
    }
  };
};

const getProviderInputSet = (record) => {
  const provider = record?.provider;
  if (provider === "google") {
    return {
      nameInput: connectorElements.googleNameInput,
      providerInput: connectorElements.googleProviderInput,
      clientIdInput: connectorElements.googleClientIdInput,
      clientSecretInput: connectorElements.googleClientSecretInput,
      scopesInput: connectorElements.googleScopesInput,
      redirectUriInput: connectorElements.googleRedirectUriInput,
      apiKeyInput: null,
      accessTokenInput: null
    };
  }
  if (provider === "github") {
    return {
      nameInput: connectorElements.githubNameInput,
      providerInput: connectorElements.githubProviderInput,
      clientIdInput: connectorElements.githubClientIdInput,
      clientSecretInput: connectorElements.githubClientSecretInput,
      scopesInput: connectorElements.githubScopesInput,
      redirectUriInput: connectorElements.githubRedirectUriInput,
      apiKeyInput: null,
      accessTokenInput: null
    };
  }
  if (provider === "notion") {
    return {
      nameInput: connectorElements.notionNameInput,
      providerInput: connectorElements.notionProviderInput,
      clientIdInput: connectorElements.notionClientIdInput,
      clientSecretInput: connectorElements.notionClientSecretInput,
      scopesInput: null,
      redirectUriInput: connectorElements.notionRedirectUriInput,
      apiKeyInput: null,
      accessTokenInput: null
    };
  }
  if (provider === "trello") {
    return {
      nameInput: connectorElements.trelloNameInput,
      providerInput: connectorElements.trelloProviderInput,
      clientIdInput: null,
      clientSecretInput: null,
      scopesInput: null,
      redirectUriInput: null,
      apiKeyInput: connectorElements.trelloApiKeyInput,
      accessTokenInput: connectorElements.trelloAccessTokenInput
    };
  }
  return {
    nameInput: connectorElements.nameInput,
    providerInput: connectorElements.providerInput,
    clientIdInput: connectorElements.clientIdInput,
    clientSecretInput: connectorElements.clientSecretInput,
    scopesInput: connectorElements.scopesInput,
    redirectUriInput: connectorElements.redirectUriInput,
    apiKeyInput: connectorElements.apiKeyInput,
    accessTokenInput: connectorElements.accessTokenInput
  };
};

const buildConnectorUpdatePayload = (record) => {
  const provider = record?.provider || "";
  const preset = getProviderPreset(provider);
  const providerMetadata = getProviderMetadata(provider);
  const inputSet = getProviderInputSet(record);
  const providerPanel = usesProviderSetupPanel(record);
  const oauthProvider = providerSupportsOauth(provider);
  const name = (inputSet.nameInput?.value || "").trim();
  const clientId = (inputSet.clientIdInput?.value || "").trim();
  const clientSecretInput = inputSet.clientSecretInput?.value || "";
  const scopesText = inputSet.scopesInput?.value || "";
  const redirectUri = inputSet.redirectUriInput?.value || "";
  const apiKeyInput = inputSet.apiKeyInput?.value || "";
  const providerAccessTokenInput = inputSet.accessTokenInput?.value || "";

  return {
    name,
    status: providerPanel ? record.status : connectorElements.statusInput.value,
    auth_type: oauthProvider
      ? "oauth2"
      : (provider === "trello" ? "api_key" : connectorElements.authTypeInput.value),
    owner: providerPanel ? (record.owner || "Workspace") : (connectorElements.ownerInput.value.trim() || "Workspace"),
    base_url: providerPanel ? (record.base_url || preset?.base_url || "") : connectorElements.baseUrlInput.value.trim(),
    scopes: oauthProvider
      ? (
        providerMetadata?.scopes_locked
          ? getDefaultScopesForProvider(record.provider, preset)
          : scopesText.split(",").map((item) => item.trim()).filter(Boolean)
      )
      : (
        provider === "trello"
          ? getDefaultScopesForProvider(record.provider, preset)
          : scopesText.split(",").map((item) => item.trim()).filter(Boolean)
      ),
    auth_config: {
      client_id: clientId,
      username: providerPanel ? (record.auth_config?.username || "") : connectorElements.usernameInput.value.trim(),
      header_name: providerPanel ? (record.auth_config?.header_name || "") : connectorElements.headerNameInput.value.trim(),
      scope_preset: record.provider,
      redirect_uri: oauthProvider
        ? (
          redirectUri.trim()
          || (providerMetadata?.default_redirect_path ? `${window.location.origin}${providerMetadata.default_redirect_path}` : "")
        )
        : "",
      expires_at: record.auth_config?.expires_at || null,
      has_refresh_token: Boolean(record.auth_config?.has_refresh_token),
      client_secret_input: clientSecretInput,
      access_token_input: provider === "trello" ? providerAccessTokenInput : (providerPanel ? "" : connectorElements.accessTokenInput.value),
      refresh_token_input: providerPanel ? "" : connectorElements.refreshTokenInput.value,
      api_key_input: provider === "trello" ? apiKeyInput : (providerPanel ? "" : connectorElements.apiKeyInput.value),
      password_input: providerPanel ? "" : connectorElements.passwordInput.value,
      header_value_input: providerPanel ? "" : connectorElements.headerValueInput.value
    }
  };
};

export const saveConnector = async (message = "Connector saved.") => {
  const selected = getSelectedConnector();
  if (!selected) {
    setFeedback("Choose or create a connector first.", "error");
    return null;
  }

  const { nameInput } = getProviderInputSet(selected);
  const name = (nameInput?.value || "").trim();
  if (!name) {
    setFeedback("Name is required.", "error");
    nameInput?.focus();
    return null;
  }

  const response = await getStore().updateConnector(selected.id, buildConnectorUpdatePayload(selected));
  connectorState.connectors = response;
  connectorState.selectedConnectorId = selected.id;
  setFeedback(message, "success");
  return getSelectedConnector();
};

const saveConnectorPolicy = async () => {
  const response = await getStore().updateConnectorAuthPolicy({
    auth_policy: {
      rotation_interval_days: Number.parseInt(connectorElements.policyRotationInput.value, 10),
      reconnect_requires_approval: connectorElements.policyApprovalInput.checked,
      credential_visibility: connectorElements.policyVisibilityInput.value
    }
  });
  connectorState.connectors = response;
  setFeedback("Connector policy saved.", "success");
  return response;
};

export const bindFormEvents = ({ renderAll, startConnectorOauth }) => {
  connectorElements.form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const saved = await saveConnector();
      if (!saved) {
        return;
      }
      renderAll();
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
  });

  connectorElements.policyForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveConnectorPolicy();
      renderAll();
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
      const saved = await saveConnector("Connector saved before test.");
      if (!saved) {
        return;
      }
      const response = await requestJson(`/api/v1/connectors/${selected.id}/test`, { method: "POST" });
      connectorState.connectors = await getStore().loadConnectors({ force: true });
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

    const inputSet = getProviderInputSet(selected);
    const clientSecretInput = inputSet.clientSecretInput?.value || "";
    const clientId = inputSet.clientIdInput?.value.trim() || "";

    if (providerSupportsOauth(selected.provider)) {
      if (!clientId) {
        setFeedback(`${titleCase(selected.provider)} OAuth requires a Client ID. Enter it in the Client ID field.`, "error");
        inputSet.clientIdInput?.focus();
        return;
      }
      if ((selected.provider === "github" || selected.provider === "notion") && !clientSecretInput.trim()) {
        setFeedback(`${titleCase(selected.provider)} OAuth requires a Client secret. Enter it before continuing.`, "error");
        inputSet.clientSecretInput?.focus();
        return;
      }
    }

    try {
      const saved = await saveConnector("Connector draft saved.");
      if (!saved) {
        return;
      }

      renderAll();
      await startConnectorOauth(saved, {
        clientSecretInput,
        closeDetailOnRedirect: true,
        renderAll
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
      connectorState.connectors = await getStore().loadConnectors({ force: true });
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
      const response = await requestJson(`/api/v1/connectors/${selected.id}/revoke`, { method: "POST" });
      connectorState.connectors = await getStore().loadConnectors({ force: true });
      connectorState.selectedConnectorId = response.connector.id;
      renderAll();
      openDetailModal();
      setFeedback(response.message, "success");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
  });

  connectorElements.removeButton?.addEventListener("click", async () => {
    const selected = getSelectedConnector();
    if (!selected) {
      setFeedback("Choose a connector to remove.", "error");
      return;
    }

    const connectorLabel = `${selected.name || selected.id} (${titleCase(selected.provider)})`;
    if (!confirm(`Remove connector ${connectorLabel}? This deletes the saved connection from this workspace.`)) {
      return;
    }

    try {
      connectorState.connectors = await getStore().deleteConnector(selected.id);
      connectorState.selectedConnectorId = null;
      closeDetailModal({ restoreFocus: false });
      connectorElements.createButton?.focus();
      renderAll();
      setFeedback(`Removed connector ${connectorLabel}.`, "success");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
  });

  connectorElements.policyApprovalInput?.addEventListener("change", () => {
    connectorElements.policyApprovalInput.closest(".toggle")?.classList.toggle(
      "toggle--on",
      connectorElements.policyApprovalInput.checked
    );
    const approvalLabel = document.getElementById("settings-connectors-policy-approval-label");
    if (approvalLabel) {
      approvalLabel.textContent = connectorElements.policyApprovalInput.checked ? "Required" : "Optional";
    }
  });
};
