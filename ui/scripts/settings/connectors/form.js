import { normalizeRequestError, requestJson } from "../../request.js";
import { connectorElements } from "./dom.js";
import { openDetailModal, closeDetailModal } from "./modal.js";
import {
  connectorState,
  getDefaultScopesForProvider,
  getProviderPreset,
  getSelectedConnector,
  isGoogleConnector,
  slugifyConnectorId,
  titleCase,
  getStore
} from "./state.js";
import { setFeedback } from "./render.js";

export const buildDefaultConnectorRecord = (preset) => {
  const connectorId = preset.id === "google" ? "google" : slugifyConnectorId(`${preset.id}-${preset.name}`);
  const defaultScopes = getDefaultScopesForProvider(preset.id, preset);
  const redirectPath = `/api/v1/connectors/${preset.id}/oauth/callback`;

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

const buildConnectorUpdatePayload = (record) => {
  const google = isGoogleConnector(record);
  const name = connectorElements.nameInput.value.trim();

  return {
    name,
    status: google ? record.status : connectorElements.statusInput.value,
    auth_type: google ? "oauth2" : connectorElements.authTypeInput.value,
    owner: google ? (record.owner || "Workspace") : (connectorElements.ownerInput.value.trim() || "Workspace"),
    base_url: google ? (record.base_url || "https://www.googleapis.com") : connectorElements.baseUrlInput.value.trim(),
    scopes: google
      ? getDefaultScopesForProvider(record.provider, getProviderPreset(record.provider))
      : connectorElements.scopesInput.value.split(",").map((item) => item.trim()).filter(Boolean),
    auth_config: {
      client_id: connectorElements.clientIdInput.value.trim(),
      username: google ? (record.auth_config?.username || "") : connectorElements.usernameInput.value.trim(),
      header_name: google ? (record.auth_config?.header_name || "") : connectorElements.headerNameInput.value.trim(),
      scope_preset: record.provider,
      redirect_uri: google
        ? (connectorElements.redirectUriInput.value.trim() || `${window.location.origin}/api/v1/connectors/google/oauth/callback`)
        : connectorElements.redirectUriInput.value.trim(),
      expires_at: record.auth_config?.expires_at || null,
      has_refresh_token: Boolean(record.auth_config?.has_refresh_token),
      client_secret_input: connectorElements.clientSecretInput.value,
      access_token_input: google ? "" : connectorElements.accessTokenInput.value,
      refresh_token_input: google ? "" : connectorElements.refreshTokenInput.value,
      api_key_input: google ? "" : connectorElements.apiKeyInput.value,
      password_input: google ? "" : connectorElements.passwordInput.value,
      header_value_input: google ? "" : connectorElements.headerValueInput.value
    }
  };
};

export const saveConnector = async (message = "Connector saved.") => {
  const selected = getSelectedConnector();
  if (!selected) {
    setFeedback("Choose or create a connector first.", "error");
    return null;
  }

  const name = connectorElements.nameInput.value.trim();
  if (!name) {
    setFeedback("Name is required.", "error");
    connectorElements.nameInput.focus();
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
