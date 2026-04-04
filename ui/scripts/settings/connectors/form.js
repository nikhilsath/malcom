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
  const defaultScopes = preset.id === "github" ? [] : getDefaultScopesForProvider(preset.id, preset);
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

const resolveInput = (cachedElement, fallbackId) => cachedElement || document.getElementById(fallbackId);
const getLiveProviderInput = (provider, fieldKey, fallbackElement = null) => (
  resolveInput(fallbackElement, `settings-connectors-${provider}-${fieldKey}-input`)
);

const readScopeValues = (scopeInput) => {
  if (scopeInput instanceof HTMLSelectElement) {
    return Array.from(scopeInput.selectedOptions)
      .map((option) => option.value.trim())
      .filter(Boolean);
  }
  return (scopeInput?.value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
};

const getProviderInputSet = (record) => {
  const provider = record?.provider;
  if (provider === "google") {
    return {
      nameInput: resolveInput(connectorElements.googleNameInput, "settings-connectors-google-name-input"),
      providerInput: resolveInput(connectorElements.googleProviderInput, "settings-connectors-google-provider-input"),
      clientIdInput: resolveInput(connectorElements.googleClientIdInput, "settings-connectors-google-client-id-input"),
      clientSecretInput: resolveInput(connectorElements.googleClientSecretInput, "settings-connectors-google-client-secret-input"),
      scopesInput: resolveInput(connectorElements.googleScopesInput, "settings-connectors-google-scopes-input"),
      redirectUriInput: resolveInput(connectorElements.googleRedirectUriInput, "settings-connectors-google-redirect-uri-input"),
      apiKeyInput: null,
      accessTokenInput: null
    };
  }
  if (provider === "github") {
    return {
      nameInput: resolveInput(connectorElements.githubNameInput, "settings-connectors-github-name-input"),
      providerInput: resolveInput(connectorElements.githubProviderInput, "settings-connectors-github-provider-input"),
      clientIdInput: null,
      clientSecretInput: null,
      scopesInput: resolveInput(connectorElements.githubScopesInput, "settings-connectors-github-scopes-input"),
      redirectUriInput: null,
      apiKeyInput: null,
      accessTokenInput: resolveInput(connectorElements.githubAccessTokenInput, "settings-connectors-github-access-token-input")
    };
  }
  if (provider === "notion") {
    return {
      nameInput: resolveInput(connectorElements.notionNameInput, "settings-connectors-notion-name-input"),
      providerInput: resolveInput(connectorElements.notionProviderInput, "settings-connectors-notion-provider-input"),
      clientIdInput: resolveInput(connectorElements.notionClientIdInput, "settings-connectors-notion-client-id-input"),
      clientSecretInput: resolveInput(connectorElements.notionClientSecretInput, "settings-connectors-notion-client-secret-input"),
      scopesInput: null,
      redirectUriInput: resolveInput(connectorElements.notionRedirectUriInput, "settings-connectors-notion-redirect-uri-input"),
      apiKeyInput: null,
      accessTokenInput: null
    };
  }
  if (provider === "trello") {
    return {
      nameInput: resolveInput(connectorElements.trelloNameInput, "settings-connectors-trello-name-input"),
      providerInput: resolveInput(connectorElements.trelloProviderInput, "settings-connectors-trello-provider-input"),
      clientIdInput: resolveInput(connectorElements.trelloClientIdInput, "settings-connectors-trello-client-id-input"),
      clientSecretInput: resolveInput(connectorElements.trelloClientSecretInput, "settings-connectors-trello-client-secret-input"),
      scopesInput: null,
      redirectUriInput: resolveInput(connectorElements.trelloRedirectUriInput, "settings-connectors-trello-redirect-uri-input"),
      apiKeyInput: null,
      accessTokenInput: null
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
  const name = (getLiveProviderInput(provider, "name", inputSet.nameInput)?.value || "").trim();
  const clientId = (getLiveProviderInput(provider, "client-id", inputSet.clientIdInput)?.value || "").trim();
  const clientSecretInput = getLiveProviderInput(provider, "client-secret", inputSet.clientSecretInput)?.value || "";
  const selectedScopes = readScopeValues(inputSet.scopesInput);
  const redirectUri = getLiveProviderInput(provider, "redirect-uri", inputSet.redirectUriInput)?.value || "";
  const providerAccessTokenInput = inputSet.accessTokenInput?.value || "";

  return {
    name,
    status: providerPanel ? record.status : connectorElements.statusInput.value,
    auth_type: oauthProvider
      ? "oauth2"
      : connectorElements.authTypeInput.value,
    owner: providerPanel ? (record.owner || "Workspace") : (connectorElements.ownerInput.value.trim() || "Workspace"),
    base_url: providerPanel ? (record.base_url || preset?.base_url || "") : connectorElements.baseUrlInput.value.trim(),
    scopes: oauthProvider
      ? (
        providerMetadata?.scopes_locked
          ? getDefaultScopesForProvider(record.provider, preset)
          : selectedScopes
      )
      : (
        providerMetadata?.scopes_locked
          ? (record.scopes || [])
          : selectedScopes
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
      access_token_input: provider === "github" ? providerAccessTokenInput : (providerPanel ? "" : connectorElements.accessTokenInput.value),
      refresh_token_input: providerPanel ? "" : connectorElements.refreshTokenInput.value,
      api_key_input: providerPanel ? "" : connectorElements.apiKeyInput.value,
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
    const clientSecretInput = getLiveProviderInput(selected.provider, "client-secret", inputSet.clientSecretInput)?.value || "";
    const clientId = getLiveProviderInput(selected.provider, "client-id", inputSet.clientIdInput)?.value.trim() || "";
    const providerMetadata = getProviderMetadata(selected.provider);
    const requiresClientSecret = Boolean(providerMetadata?.required_fields?.includes("client_secret"));

    if (providerSupportsOauth(selected.provider)) {
      if (!clientId) {
        setFeedback(`${titleCase(selected.provider)} OAuth requires a Client ID. Enter it in the Client ID field.`, "error");
        inputSet.clientIdInput?.focus();
        return;
      }
      if (requiresClientSecret && !clientSecretInput.trim()) {
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

      const oauthRecord = {
        ...saved,
        auth_config: {
          ...(saved.auth_config || {}),
          client_id: (saved.auth_config?.client_id || clientId).trim(),
          redirect_uri: (
            (saved.auth_config?.redirect_uri || "")
            || (getLiveProviderInput(saved.provider, "redirect-uri", inputSet.redirectUriInput)?.value || "")
          ).trim()
        }
      };

      renderAll();
      await startConnectorOauth(oauthRecord, {
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
