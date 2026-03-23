import { apiResourceTypes, modalFallbackMarkup, outgoingEditModalFallbackMarkup } from "./config.js";
import {
  getCreateOpenButton,
  hasCreateModalElements,
  hasOutgoingEditModalElements,
  hasOutgoingRegistryElements,
  hasOverviewElements,
  hasOverviewLandingElements,
  hasWebhookRegistryElements
} from "./dom.js";
import { normalizeError, resolvePageHref, setFormMessage, stringifyPreviewValue } from "./utils.js";

export const createApiPageController = ({
  elements,
  state,
  client,
  render,
  modals,
  forms,
  emitApiLog,
  loadConnectorEntries,
  createApiModalMarkup,
  outgoingApiEditModalMarkup
}) => {
  const actions = {
    hasOverviewElements: () => hasOverviewElements(elements),
    hasOutgoingRegistryElements: () => hasOutgoingRegistryElements(elements),
    hasWebhookRegistryElements: () => hasWebhookRegistryElements(elements),
    navigateToResourcePage: (type) => {
      const targetHref = resolvePageHref(apiResourceTypes[type].redirectPath);

      if (window.location.href !== targetHref) {
        window.location.assign(targetHref);
      }
    },
    resolvePageHref,
    loadApiDetail: async (apiId, options = {}) => {
      if (!hasOverviewElements(elements)) {
        return;
      }

      const {
        syncTableSelection = true,
        openDetailModal = true
      } = options;

      state.selectedApiId = apiId;
      elements.detailTitle.textContent = "Loading inbound API";
      elements.detailDescription.textContent = "Fetching endpoint metadata and recent events.";
      render.setDetailState(true);

      if (syncTableSelection) {
        render.renderTable();
      }

      const detail = await client.detail(apiId);
      render.renderDetail(detail);
      emitApiLog({
        action: "inbound_api_detail_viewed",
        message: `Viewed inbound API "${detail.name}".`,
        details: {
          apiId: detail.id,
          eventCount: Array.isArray(detail.events) ? detail.events.length : 0
        }
      });

      if (openDetailModal) {
        modals.openDetailModalView();
      }

      if (syncTableSelection) {
        render.renderTable();
      }
    },
    loadApiDirectory: async () => {
      if (!hasOverviewElements(elements)) {
        return;
      }

      state.entries = await client.list();
      if (state.selectedApiId && !state.entries.some((entry) => entry.id === state.selectedApiId)) {
        state.selectedApiId = null;
      }

      render.renderTable();

      if (state.selectedApiId) {
        await actions.loadApiDetail(state.selectedApiId, {
          syncTableSelection: false,
          openDetailModal: false
        });
      } else {
        render.renderDetail(null);
      }
    },
    loadOutgoingEditDetail: async (entryId, entryType, triggerElement = null) => {
      try {
        const feedback = document.getElementById("outgoing-api-edit-form-feedback");

        state.selectedOutgoingApiId = entryId;
        state.outgoingEditReturnFocusElement = triggerElement instanceof HTMLElement ? triggerElement : null;
        render.syncOutgoingEditRowSelection();

        if (feedback) {
          setFormMessage(feedback, "Loading outgoing API...", "info");
        }

        const detail = await client.detailOutgoing(entryId, entryType);
        const form = document.getElementById("outgoing-api-edit-form");
        const title = document.getElementById("outgoing-api-edit-modal-title");
        const typeInput = document.getElementById("outgoing-api-edit-type-input");
        const idInput = document.getElementById("outgoing-api-edit-id-input");
        const nameInput = document.getElementById("outgoing-api-edit-name-input");
        const slugInput = document.getElementById("outgoing-api-edit-slug-input");
        const descriptionInput = document.getElementById("outgoing-api-edit-description-input");
        const enabledInput = document.getElementById("outgoing-api-edit-enabled-input");
        const destinationInput = document.getElementById("outgoing-api-edit-destination-input");
        const methodInput = document.getElementById("outgoing-api-edit-method-input");
        const scheduledTimeInput = document.getElementById("outgoing-api-edit-scheduled-time-input");
        const scheduledRepeatInput = document.getElementById("outgoing-api-edit-scheduled-repeat-input");
        const continuousRepeatInput = document.getElementById("outgoing-api-edit-continuous-repeat-input");
        const continuousIntervalValueInput = document.getElementById("outgoing-api-edit-continuous-interval-value-input");
        const continuousIntervalUnitInput = document.getElementById("outgoing-api-edit-continuous-interval-unit-input");
        const authTypeInput = document.getElementById("outgoing-api-edit-auth-type-input");
        const authTokenInput = document.getElementById("outgoing-api-edit-auth-token-input");
        const authUsernameInput = document.getElementById("outgoing-api-edit-auth-username-input");
        const authPasswordInput = document.getElementById("outgoing-api-edit-auth-password-input");
        const authHeaderNameInput = document.getElementById("outgoing-api-edit-auth-header-name-input");
        const authHeaderValueInput = document.getElementById("outgoing-api-edit-auth-header-value-input");
        const payloadInput = document.getElementById("outgoing-api-edit-payload-input");

        if (!form || !typeInput || !idInput || !nameInput || !slugInput || !descriptionInput || !enabledInput || !destinationInput || !methodInput || !authTypeInput || !payloadInput) {
          return;
        }

        if (title) {
          title.textContent = detail.type === "outgoing_scheduled" ? "Edit scheduled API" : "Edit continuous API";
        }

        typeInput.value = detail.type;
        idInput.value = detail.id;
        nameInput.value = detail.name || "";
        slugInput.value = detail.path_slug || "";
        descriptionInput.value = detail.description || "";
        enabledInput.checked = Boolean(detail.enabled);
        destinationInput.value = detail.destination_url || "";
        methodInput.value = detail.http_method || "POST";
        if (scheduledTimeInput) {
          scheduledTimeInput.value = detail.scheduled_time || "09:00";
        }
        if (scheduledRepeatInput) {
          scheduledRepeatInput.checked = Boolean(detail.repeat_enabled);
        }
        if (continuousRepeatInput) {
          continuousRepeatInput.checked = Boolean(detail.repeat_enabled);
        }
        if (continuousIntervalValueInput && continuousIntervalUnitInput) {
          const repeatInterval = Number(detail.repeat_interval_minutes || 5);
          if (repeatInterval % 60 === 0) {
            continuousIntervalUnitInput.value = "hours";
            continuousIntervalValueInput.value = String(Math.max(1, repeatInterval / 60));
          } else {
            continuousIntervalUnitInput.value = "minutes";
            continuousIntervalValueInput.value = String(Math.max(1, repeatInterval));
          }
        }
        authTypeInput.value = detail.auth_type || "none";
        authTokenInput.value = detail.auth_config?.token || "";
        authUsernameInput.value = detail.auth_config?.username || "";
        authPasswordInput.value = detail.auth_config?.password || "";
        authHeaderNameInput.value = detail.auth_config?.header_name || "";
        authHeaderValueInput.value = detail.auth_config?.header_value || "";
        payloadInput.value = detail.payload_template || "{}";

        form.dataset.outgoingType = detail.type;
        form.dataset.outgoingId = detail.id;
        form.dispatchEvent(new CustomEvent("outgoing-edit-sync"));
        setFormMessage(feedback, "", "info");
        modals.openOutgoingEditModal();
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        render.setAlert(errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "outgoing_api_detail_load_failed",
          message: "Failed to load outgoing API detail.",
          details: {
            apiId: entryId,
            type: entryType,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    },
    loadOutgoingRegistries: async () => {
      if (!hasOutgoingRegistryElements(elements)) {
        return;
      }

      const [scheduledEntries, continuousEntries] = await Promise.all([
        client.listOutgoingScheduled(),
        client.listOutgoingContinuous()
      ]);
      state.outgoingEntries = [...scheduledEntries, ...continuousEntries]
        .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
      if (state.selectedOutgoingApiId && !state.outgoingEntries.some((entry) => entry.id === state.selectedOutgoingApiId)) {
        state.selectedOutgoingApiId = null;
      }
      render.renderOutgoingRegistryList(elements.outgoingList, elements.outgoingListEmpty, state.outgoingEntries, "apis-outgoing-list");
    },
    loadWebhookRegistry: async () => {
      if (!hasWebhookRegistryElements(elements)) {
        return;
      }

      state.webhookEntries = await client.listWebhooks();
      render.renderResourceList(elements.webhooksList, elements.webhooksListEmpty, state.webhookEntries, "apis-webhooks-list");
    }
  };

  const bindLogControls = () => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    const rerenderLogs = () => render.renderLogs(state.detailEvents);

    elements.logsSearchInput.addEventListener("input", () => {
      state.detailLogFilters.search = elements.logsSearchInput.value || "";
      rerenderLogs();
    });

    elements.logsStatusFilter.addEventListener("change", () => {
      state.detailLogFilters.status = elements.logsStatusFilter.value || "all";
      rerenderLogs();
    });

    elements.logsSourceFilter.addEventListener("change", () => {
      state.detailLogFilters.source = elements.logsSourceFilter.value || "all";
      rerenderLogs();
    });

    elements.logsSortInput.addEventListener("change", () => {
      state.detailLogFilters.sort = elements.logsSortInput.value || "newest";
      rerenderLogs();
    });

    elements.logsResetButton.addEventListener("click", () => {
      state.detailLogFilters = {
        search: "",
        status: "all",
        source: "all",
        sort: "newest"
      };
      elements.logsSearchInput.value = "";
      elements.logsStatusFilter.value = "all";
      elements.logsSourceFilter.value = "all";
      elements.logsSortInput.value = "newest";
      rerenderLogs();
    });

    elements.logList.addEventListener("click", async (event) => {
      const trigger = event.target.closest("[data-copy-log]");

      if (!(trigger instanceof HTMLElement)) {
        return;
      }

      const copyTarget = trigger.dataset.copyLog;
      const eventId = trigger.dataset.eventId;
      const eventItem = state.detailEvents.find((entry) => entry.event_id === eventId);

      if (!eventItem) {
        return;
      }

      const textToCopy = copyTarget === "headers"
        ? stringifyPreviewValue(eventItem.request_headers_subset)
        : stringifyPreviewValue(eventItem.payload_json);

      try {
        await navigator.clipboard.writeText(textToCopy);
        render.setAlert(`${copyTarget === "headers" ? "Headers" : "Payload"} copied for ${eventId}.`, "success");
        emitApiLog({
          action: "inbound_log_payload_copied",
          message: `Copied ${copyTarget} from inbound API log ${eventId}.`,
          details: {
            apiId: state.selectedApiId,
            eventId,
            target: copyTarget
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        render.setAlert(`Unable to copy ${copyTarget}.`, "error");
        emitApiLog({
          level: "error",
          action: "inbound_log_copy_failed",
          message: `Failed to copy ${copyTarget} from an inbound API log.`,
          details: {
            apiId: state.selectedApiId,
            eventId,
            target: copyTarget,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    });
  };

  const bindResourceCardActions = () => {
    document.addEventListener("click", async (event) => {
      const trigger = event.target.closest("[data-resource-action]");

      if (!(trigger instanceof HTMLElement)) {
        return;
      }

      const action = trigger.dataset.resourceAction || "";

      if (action !== "copy-entry-value") {
        return;
      }

      const value = trigger.dataset.resourceValue || "";
      const label = trigger.dataset.resourceLabel || "Value";
      const entryId = trigger.dataset.resourceEntryId || "";

      if (!value) {
        render.setAlert(`${label} is not available for this record.`, "error");
        return;
      }

      try {
        await navigator.clipboard.writeText(value);
        render.setAlert(`${label} copied for ${entryId}.`, "success");
        emitApiLog({
          action: "resource_value_copied",
          message: `Copied ${label.toLowerCase()} for API resource ${entryId}.`,
          details: {
            entryId,
            label,
            page: window.location.pathname
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        render.setAlert(`Unable to copy ${label}.`, "error");
        emitApiLog({
          level: "error",
          action: "resource_value_copy_failed",
          message: `Failed to copy ${label.toLowerCase()} for API resource ${entryId}.`,
          details: {
            entryId,
            label,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    });
  };

  const bindDetailActions = () => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    elements.rotateSecretButton.addEventListener("click", async () => {
      if (!state.selectedApiId) {
        return;
      }

      try {
        const rotated = await client.rotateSecret(state.selectedApiId);
        state.lastSecretByApiId[state.selectedApiId] = rotated.secret;
        await actions.loadApiDirectory();
        await actions.loadApiDetail(state.selectedApiId);
        render.setAlert("Bearer secret rotated. Update external callers to use the new token.", "success");
        emitApiLog({
          action: "inbound_api_secret_rotated",
          message: "Rotated inbound API bearer secret.",
          details: {
            apiId: state.selectedApiId
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        console.error("Failed to rotate inbound API bearer secret", error);
        render.setAlert(errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "inbound_api_secret_rotate_failed",
          message: "Failed to rotate inbound API bearer secret.",
          details: {
            apiId: state.selectedApiId,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    });

    elements.toggleStatusButton.addEventListener("click", async () => {
      const entry = state.entries.find((item) => item.id === state.selectedApiId);

      if (!entry) {
        return;
      }

      try {
        await client.update(entry.id, { enabled: !entry.enabled });
        await actions.loadApiDirectory();
        await actions.loadApiDetail(entry.id);
        render.setAlert(entry.enabled ? "Inbound API disabled." : "Inbound API enabled.", "success");
        emitApiLog({
          action: entry.enabled ? "inbound_api_disabled" : "inbound_api_enabled",
          message: `${entry.enabled ? "Disabled" : "Enabled"} inbound API "${entry.name}".`,
          details: {
            apiId: entry.id,
            enabled: !entry.enabled
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        console.error("Failed to update inbound API status", error);
        render.setAlert(errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "inbound_api_toggle_failed",
          message: "Failed to update inbound API status.",
          details: {
            apiId: entry.id,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    });
  };

  const loadOverviewLanding = async () => {
    if (!hasOverviewLandingElements(elements)) {
      return;
    }

    const [incomingEntries, scheduledEntries, continuousEntries, webhookEntries] = await Promise.all([
      client.list(),
      client.listOutgoingScheduled(),
      client.listOutgoingContinuous(),
      client.listWebhooks()
    ]);

    const sortedScheduledEntries = [...scheduledEntries]
      .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
    const sortedContinuousEntries = [...continuousEntries]
      .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
    const sortedWebhookEntries = [...webhookEntries]
      .sort((left, right) => new Date(right.created_at) - new Date(left.created_at));

    render.syncOverviewLandingSummary({
      incomingEntries,
      scheduledEntries: sortedScheduledEntries,
      continuousEntries: sortedContinuousEntries,
      webhookEntries: sortedWebhookEntries
    });
    render.renderResourceList(
      elements.overviewIncomingList,
      elements.overviewIncomingEmpty,
      incomingEntries,
      "apis-overview-incoming-list"
    );
    render.renderResourceList(
      elements.overviewOutgoingList,
      elements.overviewOutgoingEmpty,
      [...sortedScheduledEntries, ...sortedContinuousEntries],
      "apis-overview-outgoing-list"
    );
    render.renderResourceList(
      elements.overviewWebhooksList,
      elements.overviewWebhooksEmpty,
      sortedWebhookEntries,
      "apis-overview-webhooks-list"
    );
    render.setAlert("", "info");
  };

  const initModalMarkup = async () => {
    if (!hasCreateModalElements(elements)) {
      return;
    }

    try {
      if (!createApiModalMarkup.trim()) {
        throw new Error("Create API modal template is empty.");
      }

      elements.createModalContent.innerHTML = createApiModalMarkup;
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Failed to load create API modal template", error);
      emitApiLog({
        level: "error",
        action: "modal_template_load_failed",
        message: "Unable to load create API modal template.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
      elements.createModalContent.innerHTML = modalFallbackMarkup;
    }

    forms.bindCreateForm();
  };

  const initOutgoingEditModalMarkup = async () => {
    if (!hasOutgoingEditModalElements(elements)) {
      return;
    }

    try {
      if (!outgoingApiEditModalMarkup.trim()) {
        throw new Error("Outgoing API edit modal template is empty.");
      }

      elements.outgoingEditModalContent.innerHTML = outgoingApiEditModalMarkup;
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Failed to load outgoing API edit modal template", error);
      emitApiLog({
        level: "error",
        action: "outgoing_edit_modal_template_load_failed",
        message: "Unable to load outgoing API edit modal template.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
      elements.outgoingEditModalContent.innerHTML = outgoingEditModalFallbackMarkup;
    }

    forms.bindOutgoingEditForm();
  };

  const initCreateModal = async () => {
    modals.bindModalEvents(actions);

    if (!hasCreateModalElements(elements)) {
      return;
    }

    modals.ensureCreateTypeModal();
    await initModalMarkup();
    modals.setCreateModalType(state.createModalType);
  };

  const initOutgoingEditModal = async () => {
    if (!hasOutgoingEditModalElements(elements)) {
      return;
    }

    await initOutgoingEditModalMarkup();
  };

  const initApiOverview = async () => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    bindLogControls();
    bindDetailActions();

    try {
      await actions.loadApiDirectory();
      render.setAlert("", "info");
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Unable to load inbound APIs", error);
      render.setAlert("Unable to load inbound APIs. Start the FastAPI service and refresh the page.", "error");
      render.renderDetail(null);
      emitApiLog({
        level: "error",
        action: "inbound_api_load_failed",
        message: "Unable to load inbound APIs from the backend.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
    }
  };

  const initOutgoingRegistry = async () => {
    if (!hasOutgoingRegistryElements(elements)) {
      return;
    }

    try {
      await actions.loadOutgoingRegistries();
      render.setAlert("", "info");
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Unable to load outgoing APIs", error);
      emitApiLog({
        level: "error",
        action: "outgoing_api_load_failed",
        message: "Unable to load outgoing APIs from the backend.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
      render.setAlert("Unable to load outgoing APIs. Start the FastAPI service and refresh the page.", "error");
    }
  };

  const initWebhookRegistry = async () => {
    if (!hasWebhookRegistryElements(elements)) {
      return;
    }

    try {
      await actions.loadWebhookRegistry();
      render.setAlert("", "info");
    } catch (error) {
      const { message: errorMessage, stack: errorStack } = normalizeError(error);
      console.error("Unable to load webhooks", error);
      emitApiLog({
        level: "error",
        action: "webhook_load_failed",
        message: "Unable to load webhooks from the backend.",
        details: {
          error: errorMessage,
          stack: errorStack
        }
      });
      render.setAlert("Unable to load webhooks. Start the FastAPI service and refresh the page.", "error");
    }
  };

  const initApiPage = async () => {
    bindResourceCardActions();
    state.connectorEntries = await loadConnectorEntries();
    await initCreateModal();
    await initOutgoingEditModal();
    if (hasOverviewLandingElements(elements)) {
      try {
        await loadOverviewLanding();
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        console.error("Unable to load API overview", error);
        render.setAlert("Unable to load API overview. Start the FastAPI service and refresh the page.", "error");
        emitApiLog({
          level: "error",
          action: "api_overview_load_failed",
          message: "Unable to load API overview registries from the backend.",
          details: {
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    }
    await initApiOverview();
    await initOutgoingRegistry();
    await initWebhookRegistry();

    window.addEventListener("malcom:app-settings-updated", (event) => {
      state.connectorEntries = event.detail?.settings?.connectors?.records || [];
    });
  };

  return {
    initApiPage,
    actions
  };
};
