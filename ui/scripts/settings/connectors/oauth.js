import { requestJson } from "../../request.js";
import { connectorElements, OAUTH_QUERY_KEYS } from "./dom.js";
import { buildDefaultConnectorRecord } from "./form.js";
import { closeDetailModal, openDetailModal } from "./modal.js";
import {
  canonicalizeProvider,
  connectorState,
  getProviderActionLabel,
  getDefaultScopesForProvider,
  createEmptyConnectorPayload,
  getGoogleConnector,
  getProviderMetadata,
  getProviderPreset,
  providerSupportsOauth,
  getStore
} from "./state.js";
import { setFeedback } from "./render.js";

export const startConnectorOauth = async (
  record,
  { clientSecretInput = "", closeDetailOnRedirect = false, renderAll }
) => {
  if (!record) {
    setFeedback("Choose a connector to authorize.", "error");
    return;
  }

  const provider = canonicalizeProvider(record.provider);
  const providerMetadata = getProviderMetadata(provider);
  if (!providerSupportsOauth(provider)) {
    setFeedback(`${providerMetadata?.name || provider} uses saved credentials and does not support browser OAuth.`, "error");
    return;
  }
  const clientIdInput = document.getElementById(`settings-connectors-${provider}-client-id-input`);
  const redirectUriInput = document.getElementById(`settings-connectors-${provider}-redirect-uri-input`);
  const fallbackRedirectPath = providerMetadata?.default_redirect_path || `/api/v1/connectors/${provider}/oauth/callback`;
  const redirectUri = (
    (redirectUriInput instanceof HTMLInputElement ? redirectUriInput.value : "")
    || record.auth_config?.redirect_uri
    || `${window.location.origin}${fallbackRedirectPath}`
  ).trim();

  const clientId = (
    (clientIdInput instanceof HTMLInputElement ? clientIdInput.value : "")
    || record.auth_config?.client_id
    || ""
  ).trim();
  if (!clientId) {
    setFeedback(`${providerMetadata?.name || provider} OAuth requires a Client ID. Enter it in the Client ID field.`, "error");
    return;
  }

  try {
    const parsedRedirectUri = new URL(redirectUri);
    if (!["http:", "https:"].includes(parsedRedirectUri.protocol)) {
      throw new Error("Invalid redirect URI protocol");
    }
  } catch {
    setFeedback(`${providerMetadata?.name || provider} OAuth requires a valid Redirect URI (http or https).`, "error");
    return;
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
  connectorState.connectors = await getStore().loadConnectors({ force: true });
  connectorState.selectedConnectorId = record.id;
  renderAll();
  if (closeDetailOnRedirect) {
    closeDetailModal({ restoreFocus: false });
  }
  setFeedback(`Redirecting to ${providerMetadata?.name || provider} login...`, "success");
  window.location.assign(response.authorization_url);
};

export const ensureGoogleConnectorRecord = async () => {
  const existingGoogle = getGoogleConnector();
  if (existingGoogle) {
    return existingGoogle;
  }

  const preset = getProviderPreset("google");
  if (!preset) {
    return null;
  }

  const nextRecord = buildDefaultConnectorRecord(preset);
  const response = await getStore().createConnector(nextRecord);
  connectorState.connectors = response;
  return getGoogleConnector();
};

export const handleOauthQueryState = async (renderAll) => {
  const params = new URLSearchParams(window.location.search);
  const oauthStatus = params.get("oauth_status");
  const oauthMessage = params.get("oauth_message");
  const connectorId = params.get("connector_id");

  if (oauthStatus && oauthMessage) {
    const tone = oauthStatus === "success" ? "success" : oauthStatus === "warning" ? "warning" : "error";
    setFeedback(oauthMessage, tone);
  }

  if (connectorId) {
    try {
      connectorState.connectors = await getStore().loadConnectors({ force: true });
    } catch {
      connectorState.connectors = getStore().getConnectors?.() || createEmptyConnectorPayload();
    }

    const selected = connectorState.connectors?.records?.find((record) => record.id === connectorId) || null;
    if (selected) {
      connectorState.selectedConnectorId = selected.id;
      renderAll();
      if (oauthStatus && oauthStatus !== "success") {
        openDetailModal();
      }
    }
  }

  if (OAUTH_QUERY_KEYS.some((key) => params.has(key))) {
    OAUTH_QUERY_KEYS.forEach((key) => params.delete(key));
    const nextQuery = params.toString();
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash}`;
    window.history.replaceState({}, "", nextUrl);
  }
};
