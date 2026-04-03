import { normalizeRequestError } from "../../request.js";
import { connectorElements } from "./dom.js";
import { bindFormEvents, buildDefaultConnectorRecord } from "./form.js";
import { bindModalEvents, closeModal, openDetailModal } from "./modal.js";
import { ensureGoogleConnectorRecord, handleOauthQueryState, startConnectorOauth } from "./oauth.js";
import { renderDetail, renderDirectory, renderModalProviders, renderPolicy, renderSummary, setFeedback } from "./render.js";
import { connectorState, createEmptyConnectorPayload, getProviderActionLabel, getProviderPreset, getStore, providerSupportsOauth, slugifyConnectorId, usesProviderSetupPanel } from "./state.js";

const handleSelectRecord = (recordId, returnFocusElement) => {
  connectorState.selectedConnectorId = recordId;
  connectorState.detailReturnFocusElement = returnFocusElement;
  renderAll();
  openDetailModal();
};

const handleSelectPreset = async (providerId) => {
  const preset = getProviderPreset(providerId);
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
        connectorElements.googleClientIdInput?.focus();
      }
      setFeedback("Google integration ready. Enter Name and OAuth credentials, then continue with Google.", "success");
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
    return;
  }

  const nextRecord = buildDefaultConnectorRecord(preset);
  nextRecord.id = slugifyConnectorId(`${preset.id}-${Date.now()}`);
  nextRecord.credential_ref = `connector/${nextRecord.id}`;

  try {
    connectorState.connectors = await getStore().createConnector(nextRecord);
    connectorState.selectedConnectorId = nextRecord.id;
    closeModal();
    renderAll();
    openDetailModal();
    if (usesProviderSetupPanel(preset.id)) {
      const connectLabel = getProviderActionLabel(preset.id, "connect", `Continue with ${preset.name}`);
      setFeedback(
        providerSupportsOauth(preset.id)
          ? `Prepared ${preset.name} connector draft. Enter provider credentials, then ${connectLabel.toLowerCase()}.`
          : `Prepared ${preset.name} connector draft. Enter provider credentials, then save the connector.`,
        "success"
      );
    } else {
      setFeedback(`Prepared ${preset.name} connector draft. Add credentials and save to persist the record.`, "success");
    }
    } catch (error) {
      setFeedback(normalizeRequestError(error).message, "error");
    }
};

const renderAll = () => {
  renderSummary();
  renderDirectory(handleSelectRecord);
  renderDetail();
  renderPolicy();
  renderModalProviders(handleSelectPreset);
};

export const initConnectorsPage = async () => {
  if (!connectorElements.tableBody || !connectorElements.form) {
    return;
  }

  bindModalEvents();
  bindFormEvents({ renderAll, startConnectorOauth });

  try {
    connectorState.connectors = await getStore().loadConnectors();
  } catch {
    connectorState.connectors = createEmptyConnectorPayload();
    setFeedback("Unable to load connectors from /api/v1/connectors.", "error");
  }

  connectorState.selectedConnectorId = null;
  renderAll();
  await handleOauthQueryState(renderAll);
};
