import { normalizeRequestError } from "../../request.js";
import { connectorElements } from "./dom.js";
import { bindFormEvents, buildDefaultConnectorRecord } from "./form.js";
import { bindModalEvents, closeModal, openDetailModal } from "./modal.js";
import { ensureGoogleConnectorRecord, handleOauthQueryState, startConnectorOauth } from "./oauth.js";
import { renderDetail, renderDirectory, renderModalProviders, renderPolicy, renderSummary, setFeedback } from "./render.js";
import { cloneValue, connectorState, getProviderPreset, getStore, slugifyConnectorId } from "./state.js";

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
      if (!(googleRecord.name || "").trim()) {
        connectorElements.nameInput?.focus();
      } else if ((googleRecord.auth_config?.client_id || "").trim()) {
        connectorElements.oauthStartButton?.focus();
      } else {
        connectorElements.clientIdInput?.focus();
      }
      setFeedback("Google connector draft ready. Enter Name and OAuth credentials, then continue with Google.", "success");
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
    connectorState.settings = await getStore().loadConnectors();
  } catch {
    connectorState.settings = {
      connectors: {
        catalog: [],
        records: [],
        auth_policy: {
          rotation_interval_days: 90,
          reconnect_requires_approval: true,
          credential_visibility: "masked"
        }
      }
    };
    setFeedback("Unable to load connectors from /api/v1/connectors.", "error");
  }

  connectorState.selectedConnectorId = null;
  renderAll();
  await handleOauthQueryState(renderAll);
};
