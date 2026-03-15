import { apiResourceTypes } from "./config.js";
import { hasCreateModalElements } from "./dom.js";
import {
  escapeHtml,
  extractPayloadVariables,
  isOutgoingType,
  normalizeError,
  sanitizeSlug,
  setFormMessage,
  titleCase
} from "./utils.js";

export const createApiFormBindings = ({
  elements,
  state,
  client,
  render,
  modals,
  actions,
  emitApiLog
}) => {
  const getModals = () => modals || {};

  const syncCreateModalType = (selectedType) => {
    const config = apiResourceTypes[selectedType] || apiResourceTypes.incoming;
    const title = document.getElementById("apis-create-modal-title");
    const description = document.getElementById("create-api-modal-description");
    const authInput = document.getElementById("create-api-auth-input");
    const enabledCopy = document.getElementById("create-api-enabled-copy");
    const submitButton = document.getElementById("create-api-submit-button");
    const outgoingPanel = document.getElementById("create-api-outgoing-panel");
    const webhookPanel = document.getElementById("create-api-webhook-panel");
    const scheduledTimeField = document.getElementById("create-api-scheduled-time-field");
    const scheduledRepeatField = document.getElementById("create-api-scheduled-repeat-field");
    const continuousRepeatField = document.getElementById("create-api-continuous-repeat-field");
    const continuousIntervalValueField = document.getElementById("create-api-continuous-interval-value-field");
    const continuousIntervalUnitField = document.getElementById("create-api-continuous-interval-unit-field");
    const continuousRepeatInput = document.getElementById("create-api-continuous-repeat-input");
    const showContinuousIntervalFields = selectedType === "outgoing_continuous" && Boolean(continuousRepeatInput?.checked);

    if (title) {
      title.textContent = config.title;
    }

    if (description) {
      description.textContent = config.description;
      description.hidden = true;
    }

    if (authInput) {
      authInput.value = config.authLabel;
    }

    if (enabledCopy) {
      enabledCopy.textContent = config.enabledCopy;
    }

    if (submitButton) {
      submitButton.textContent = config.submitLabel;
    }

    if (outgoingPanel) {
      outgoingPanel.hidden = !isOutgoingType(selectedType);
    }

    if (webhookPanel) {
      webhookPanel.hidden = selectedType !== "webhook";
    }

    if (scheduledTimeField) {
      scheduledTimeField.hidden = selectedType !== "outgoing_scheduled";
    }

    if (scheduledRepeatField) {
      scheduledRepeatField.hidden = selectedType !== "outgoing_scheduled";
    }

    if (continuousRepeatField) {
      continuousRepeatField.hidden = selectedType !== "outgoing_continuous";
    }

    if (continuousIntervalValueField) {
      continuousIntervalValueField.hidden = !showContinuousIntervalFields;
    }

    if (continuousIntervalUnitField) {
      continuousIntervalUnitField.hidden = !showContinuousIntervalFields;
    }

    const payloadInput = document.getElementById("create-api-payload-input");

    if (payloadInput instanceof HTMLTextAreaElement) {
      payloadInput.dispatchEvent(new Event("input"));
    }
  };

  const bindCreateForm = () => {
    const form = document.getElementById("create-api-form");
    const typeInput = document.getElementById("create-api-type-input");
    const nameInput = document.getElementById("create-api-name-input");
    const slugInput = document.getElementById("create-api-slug-input");
    const descriptionInput = document.getElementById("create-api-description-input");
    const enabledInput = document.getElementById("create-api-enabled-input");
    const feedback = document.getElementById("create-api-form-feedback");
    const connectorInput = document.getElementById("create-api-connector-input");
    const destinationInput = document.getElementById("create-api-destination-input");
    const methodInput = document.getElementById("create-api-method-input");
    const scheduledTimeInput = document.getElementById("create-api-scheduled-time-input");
    const scheduledRepeatInput = document.getElementById("create-api-scheduled-repeat-input");
    const continuousRepeatInput = document.getElementById("create-api-continuous-repeat-input");
    const continuousIntervalValueInput = document.getElementById("create-api-continuous-interval-value-input");
    const continuousIntervalUnitInput = document.getElementById("create-api-continuous-interval-unit-input");
    const outgoingAuthTypeInput = document.getElementById("create-api-outgoing-auth-type-input");
    const authTokenInput = document.getElementById("create-api-auth-token-input");
    const authUsernameInput = document.getElementById("create-api-auth-username-input");
    const authPasswordInput = document.getElementById("create-api-auth-password-input");
    const authHeaderNameInput = document.getElementById("create-api-auth-header-name-input");
    const authHeaderValueInput = document.getElementById("create-api-auth-header-value-input");
    const payloadTemplateInput = document.getElementById("create-api-payload-input");
    const payloadLayout = document.getElementById("create-api-payload-layout");
    const payloadVariablesPanel = document.getElementById("create-api-payload-variables-panel");
    const payloadVariablesList = document.getElementById("create-api-payload-variables-list");
    const createModalDialog = document.getElementById("apis-create-modal-dialog");
    const webhookCallbackPathInput = document.getElementById("create-api-webhook-callback-input");
    const webhookVerificationTokenInput = document.getElementById("create-api-webhook-verification-input");
    const webhookSigningSecretInput = document.getElementById("create-api-webhook-signing-input");
    const webhookSignatureHeaderInput = document.getElementById("create-api-webhook-header-input");
    const webhookEventFilterInput = document.getElementById("create-api-webhook-event-input");
    const testButton = document.getElementById("create-api-test-button");
    const testFeedback = document.getElementById("create-api-test-feedback");

    if (!form || !typeInput || !nameInput || !slugInput || !descriptionInput || !enabledInput || !feedback) {
      return;
    }

    const getSelectedType = () => typeInput.value || state.createModalType || "incoming";
    const outgoingAuthFields = {
      bearer: [document.getElementById("create-api-auth-token-field")],
      basic: [
        document.getElementById("create-api-auth-username-field"),
        document.getElementById("create-api-auth-password-field")
      ],
      header: [
        document.getElementById("create-api-auth-header-name-field"),
        document.getElementById("create-api-auth-header-value-field")
      ]
    };

    const convertIntervalToMinutes = () => {
      const intervalValue = Number.parseInt(continuousIntervalValueInput?.value || "", 10);
      const intervalUnit = continuousIntervalUnitInput?.value || "minutes";

      if (!Number.isFinite(intervalValue) || intervalValue <= 0) {
        return null;
      }

      return intervalUnit === "hours" ? intervalValue * 60 : intervalValue;
    };

    const syncContinuousIntervalConstraints = () => {
      if (!continuousIntervalValueInput) {
        return;
      }

      const intervalUnit = continuousIntervalUnitInput?.value || "minutes";
      continuousIntervalValueInput.min = "1";
      continuousIntervalValueInput.max = intervalUnit === "hours" ? "168" : "10080";
    };

    const syncConnectorOptions = () => {
      if (!connectorInput) {
        return;
      }

      const connectorOptions = [
        '<option value="">Custom destination</option>',
        ...state.connectorEntries.map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.name)} (${escapeHtml(titleCase(entry.provider || "connector"))})</option>`)
      ];
      connectorInput.innerHTML = connectorOptions.join("");
    };

    const syncConnectorSelection = () => {
      if (!connectorInput || !connectorInput.value) {
        return;
      }

      const selectedConnector = state.connectorEntries.find((entry) => entry.id === connectorInput.value);

      if (!selectedConnector) {
        return;
      }

      if (destinationInput && !destinationInput.value.trim()) {
        destinationInput.value = selectedConnector.base_url || "";
      }

      if (outgoingAuthTypeInput) {
        outgoingAuthTypeInput.value = selectedConnector.auth_type === "oauth2"
          ? "bearer"
          : selectedConnector.auth_type === "api_key"
            ? "header"
            : selectedConnector.auth_type || "none";
      }

      if (authUsernameInput && !authUsernameInput.value.trim()) {
        authUsernameInput.value = selectedConnector.auth_config?.username || "";
      }

      if (authHeaderNameInput && !authHeaderNameInput.value.trim()) {
        authHeaderNameInput.value = selectedConnector.auth_config?.header_name || "";
      }
    };

    const syncOutgoingAuthFields = () => {
      const authType = outgoingAuthTypeInput?.value || "none";

      Object.values(outgoingAuthFields).flat().forEach((field) => {
        if (field) {
          field.hidden = true;
        }
      });

      (outgoingAuthFields[authType] || []).forEach((field) => {
        if (field) {
          field.hidden = false;
        }
      });
    };

    const syncOutgoingRepeatFields = () => {
      const selectedType = getSelectedType();
      const continuousIntervalValueField = document.getElementById("create-api-continuous-interval-value-field");
      const continuousIntervalUnitField = document.getElementById("create-api-continuous-interval-unit-field");
      const continuousRepeating = Boolean(continuousRepeatInput?.checked);

      if (continuousIntervalValueField) {
        continuousIntervalValueField.hidden = selectedType !== "outgoing_continuous" || !continuousRepeating;
      }

      if (continuousIntervalUnitField) {
        continuousIntervalUnitField.hidden = selectedType !== "outgoing_continuous" || !continuousRepeating;
      }
    };

    const syncPayloadVariablePreview = () => {
      if (!payloadLayout || !payloadVariablesPanel || !payloadVariablesList || !createModalDialog) {
        return;
      }

      const selectedType = getSelectedType();
      const variables = isOutgoingType(selectedType)
        ? extractPayloadVariables(payloadTemplateInput?.value || "")
        : [];
      const hasVariables = variables.length > 0;

      payloadVariablesList.textContent = "";

      variables.forEach((variableName, index) => {
        const chip = document.createElement("span");
        chip.id = `create-api-payload-variable-${variableName
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "") || "value"}-${index + 1}`;
        chip.className = "api-payload-variable-chip";
        chip.textContent = `{{${variableName}}}`;
        payloadVariablesList.appendChild(chip);
      });

      payloadVariablesPanel.hidden = !hasVariables;
      payloadLayout.classList.toggle("api-payload-layout--expanded", hasVariables);
      createModalDialog.classList.toggle("modal__dialog--payload-expanded", hasVariables);
    };

    const buildOutgoingDraft = () => {
      const selectedType = getSelectedType();

      if (!isOutgoingType(selectedType)) {
        return null;
      }

      const authType = outgoingAuthTypeInput?.value || "none";
      const repeatEnabled = selectedType === "outgoing_scheduled"
        ? Boolean(scheduledRepeatInput?.checked)
        : Boolean(continuousRepeatInput?.checked);

      return {
        type: selectedType,
        repeat_enabled: repeatEnabled,
        repeat_interval_minutes: selectedType === "outgoing_continuous" && repeatEnabled ? convertIntervalToMinutes() : null,
        destination_url: destinationInput?.value.trim() || "",
        http_method: methodInput?.value || "POST",
        auth_type: authType,
        connector_id: connectorInput?.value || "",
        auth_config: {
          token: authTokenInput?.value || "",
          username: authUsernameInput?.value || "",
          password: authPasswordInput?.value || "",
          header_name: authHeaderNameInput?.value || "",
          header_value: authHeaderValueInput?.value || ""
        },
        payload_template: payloadTemplateInput?.value.trim() || "",
        scheduled_time: scheduledTimeInput?.value || ""
      };
    };

    const buildWebhookDraft = () => ({
      callback_path: webhookCallbackPathInput?.value.trim() || "",
      verification_token: webhookVerificationTokenInput?.value || "",
      signing_secret: webhookSigningSecretInput?.value || "",
      signature_header: webhookSignatureHeaderInput?.value.trim() || "",
      event_filter: webhookEventFilterInput?.value.trim() || ""
    });

    const validateDraft = (draft, { requireName = true } = {}) => {
      if (requireName && (!draft.name || !draft.path_slug)) {
        return "Name and path slug are required.";
      }

      if (draft.type === "webhook") {
        if (!draft.callback_path) {
          return "Callback path is required for webhooks.";
        }
        if (!draft.callback_path.startsWith("/")) {
          return "Callback path must start with '/'.";
        }
        if (!draft.verification_token) {
          return "Verification token is required for webhooks.";
        }
        if (!draft.signing_secret) {
          return "Signing secret is required for webhooks.";
        }
        if (!draft.signature_header) {
          return "Signature header is required for webhooks.";
        }
        return "";
      }

      if (!isOutgoingType(draft.type)) {
        return "";
      }

      if (!draft.destination_url && !draft.connector_id) {
        return "Destination URL is required for outgoing APIs.";
      }
      if (draft.destination_url && !/^https?:\/\//i.test(draft.destination_url)) {
        return "Destination URL must start with http:// or https://.";
      }
      if (!draft.payload_template) {
        return "A JSON payload template is required for outgoing APIs.";
      }
      try {
        JSON.parse(draft.payload_template);
      } catch {
        return "Payload template must be valid JSON.";
      }
      if (draft.type === "outgoing_scheduled" && !draft.scheduled_time) {
        return "Choose a send time for the scheduled outgoing API.";
      }
      if (draft.type === "outgoing_continuous" && draft.repeat_enabled) {
        if (!draft.repeat_interval_minutes) {
          return "Choose a repeat interval for the continuous outgoing API.";
        }
        if (draft.repeat_interval_minutes < 1) {
          return "Continuous repeat intervals must be at least 1 minute.";
        }
        if (draft.repeat_interval_minutes > 10080) {
          return "Continuous repeat intervals cannot exceed 168 hours.";
        }
      }
      if (draft.auth_type === "bearer" && !draft.auth_config.token && !draft.connector_id) {
        return "Enter a bearer token or switch destination auth to None.";
      }
      if (draft.auth_type === "basic" && (!draft.auth_config.username || !draft.auth_config.password) && !draft.connector_id) {
        return "Basic auth requires both a username and password.";
      }
      if (draft.auth_type === "header" && (!draft.auth_config.header_name || !draft.auth_config.header_value) && !draft.connector_id) {
        return "Custom header auth requires both a header name and value.";
      }
      return "";
    };

    const resetOutgoingFields = () => {
      if (connectorInput) {
        connectorInput.value = state.createFromConnector ? connectorInput.options[1]?.value || "" : "";
      }
      if (destinationInput) {
        destinationInput.value = "";
      }
      if (methodInput) {
        methodInput.value = "POST";
      }
      if (scheduledTimeInput) {
        scheduledTimeInput.value = "09:00";
      }
      if (scheduledRepeatInput) {
        scheduledRepeatInput.checked = false;
      }
      if (continuousRepeatInput) {
        continuousRepeatInput.checked = false;
      }
      if (continuousIntervalValueInput) {
        continuousIntervalValueInput.value = "5";
      }
      if (continuousIntervalUnitInput) {
        continuousIntervalUnitInput.value = "minutes";
      }
      syncContinuousIntervalConstraints();
      if (outgoingAuthTypeInput) {
        outgoingAuthTypeInput.value = "none";
      }
      if (authTokenInput) {
        authTokenInput.value = "";
      }
      if (authUsernameInput) {
        authUsernameInput.value = "";
      }
      if (authPasswordInput) {
        authPasswordInput.value = "";
      }
      if (authHeaderNameInput) {
        authHeaderNameInput.value = "";
      }
      if (authHeaderValueInput) {
        authHeaderValueInput.value = "";
      }
      if (payloadTemplateInput) {
        payloadTemplateInput.value = '{ "event": "scheduled.delivery", "sent_at": "{{timestamp}}" }';
      }
      syncConnectorSelection();
      syncOutgoingAuthFields();
      syncOutgoingRepeatFields();
      syncPayloadVariablePreview();
      setFormMessage(testFeedback, "", "info");
    };

    const resetWebhookFields = () => {
      if (webhookCallbackPathInput) {
        webhookCallbackPathInput.value = "";
      }
      if (webhookVerificationTokenInput) {
        webhookVerificationTokenInput.value = "";
      }
      if (webhookSigningSecretInput) {
        webhookSigningSecretInput.value = "";
      }
      if (webhookSignatureHeaderInput) {
        webhookSignatureHeaderInput.value = "";
      }
      if (webhookEventFilterInput) {
        webhookEventFilterInput.value = "";
      }
    };

    nameInput.addEventListener("input", () => {
      if (!slugInput.dataset.userEdited) {
        slugInput.value = sanitizeSlug(nameInput.value);
      }
    });

    slugInput.addEventListener("input", () => {
      slugInput.dataset.userEdited = "true";
      slugInput.value = sanitizeSlug(slugInput.value);
    });

    outgoingAuthTypeInput?.addEventListener("change", syncOutgoingAuthFields);
    connectorInput?.addEventListener("change", syncConnectorSelection);
    scheduledRepeatInput?.addEventListener("change", syncOutgoingRepeatFields);
    continuousRepeatInput?.addEventListener("change", syncOutgoingRepeatFields);
    continuousIntervalUnitInput?.addEventListener("change", syncContinuousIntervalConstraints);
    payloadTemplateInput?.addEventListener("input", syncPayloadVariablePreview);

    syncConnectorOptions();

    testButton?.addEventListener("click", async () => {
      const selectedType = getSelectedType();
      if (!isOutgoingType(selectedType)) {
        return;
      }

      const draft = buildOutgoingDraft();
      const validationMessage = validateDraft(draft, { requireName: false });

      if (validationMessage) {
        setFormMessage(testFeedback, validationMessage, "error");
        return;
      }

      testButton.disabled = true;
      setFormMessage(testFeedback, "Sending test payload...", "info");

      try {
        const result = await client.testOutgoingDelivery(draft);
        const responsePreview = result.response_body ? ` Response: ${result.response_body}` : "";
        setFormMessage(testFeedback, `Test delivery returned ${result.status_code}.${responsePreview}`.trim(), result.ok ? "success" : "error");
        emitApiLog({
          level: result.ok ? "info" : "warning",
          action: "outgoing_api_test_delivery_completed",
          message: `Test delivery returned ${result.status_code}.`,
          details: {
            type: selectedType,
            destinationUrl: draft?.destination_url || "",
            statusCode: result.status_code,
            ok: result.ok
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        setFormMessage(testFeedback, errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "outgoing_api_test_delivery_failed",
          message: "Test delivery failed before a response was returned.",
          details: {
            type: selectedType,
            destinationUrl: draft?.destination_url || "",
            error: errorMessage,
            stack: errorStack
          }
        });
      } finally {
        testButton.disabled = false;
      }
    });

    syncOutgoingAuthFields();
    syncCreateModalType(getSelectedType());
    syncContinuousIntervalConstraints();
    syncOutgoingRepeatFields();
    syncPayloadVariablePreview();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setFormMessage(feedback, "", "info");
      const selectedType = getSelectedType();

      const payload = {
        type: selectedType,
        name: nameInput.value.trim(),
        path_slug: sanitizeSlug(slugInput.value),
        description: descriptionInput.value.trim(),
        enabled: enabledInput.checked
      };

      if (isOutgoingType(selectedType)) {
        Object.assign(payload, buildOutgoingDraft());
      }

      if (selectedType === "webhook") {
        Object.assign(payload, buildWebhookDraft());
      }

      const validationMessage = validateDraft(payload);

      if (validationMessage) {
        setFormMessage(feedback, validationMessage, "error");
        return;
      }

      try {
        const created = await client.create(payload);
        if (created.secret) {
          state.lastSecretByApiId[created.id] = created.secret;
        }

        if (selectedType === "incoming" && actions.hasOverviewElements()) {
          state.selectedApiId = created.id;
          await actions.loadApiDirectory();
          await actions.loadApiDetail(created.id);
        }

        if (selectedType !== "incoming") {
          if (actions.hasOutgoingRegistryElements()) {
            await actions.loadOutgoingRegistries();
          }
          if (actions.hasWebhookRegistryElements()) {
            await actions.loadWebhookRegistry();
          }
        }

        form.reset();
        enabledInput.checked = true;
        delete slugInput.dataset.userEdited;
        resetOutgoingFields();
        resetWebhookFields();
        getModals().setCreateModalType?.("incoming");
        setFormMessage(feedback, apiResourceTypes[selectedType].successMessage, "success");
        getModals().closeCreateModal?.();
        render.setAlert(apiResourceTypes[selectedType].alertMessage, "success");
        emitApiLog({
          action: `${selectedType}_created`,
          message: `Created ${selectedType} "${created.name}".`,
          details: {
            type: selectedType,
            apiId: created.id,
            pathSlug: created.path_slug,
            enabled: created.enabled
          }
        });

        if (selectedType !== "incoming" || !actions.hasOverviewElements()) {
          actions.navigateToResourcePage(selectedType);
        }
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        console.error(`Failed to create ${selectedType}`, error);
        setFormMessage(feedback, errorMessage, "error");
        emitApiLog({
          level: "error",
          action: `${selectedType}_create_failed`,
          message: `Failed to create ${selectedType}.`,
          details: {
            error: errorMessage,
            stack: errorStack,
            type: selectedType,
            attemptedName: payload.name,
            attemptedSlug: payload.path_slug
          }
        });
      }
    });
  };

  const bindOutgoingEditForm = () => {
    const form = document.getElementById("outgoing-api-edit-form");

    if (!(form instanceof HTMLFormElement) || form.dataset.bound === "true") {
      return;
    }

    form.dataset.bound = "true";

    const idInput = document.getElementById("outgoing-api-edit-id-input");
    const typeInput = document.getElementById("outgoing-api-edit-type-input");
    const nameInput = document.getElementById("outgoing-api-edit-name-input");
    const slugInput = document.getElementById("outgoing-api-edit-slug-input");
    const descriptionInput = document.getElementById("outgoing-api-edit-description-input");
    const enabledInput = document.getElementById("outgoing-api-edit-enabled-input");
    const destinationInput = document.getElementById("outgoing-api-edit-destination-input");
    const methodInput = document.getElementById("outgoing-api-edit-method-input");
    const scheduledTimeInput = document.getElementById("outgoing-api-edit-scheduled-time-input");
    const scheduledTimeField = document.getElementById("outgoing-api-edit-scheduled-time-field");
    const scheduledRepeatInput = document.getElementById("outgoing-api-edit-scheduled-repeat-input");
    const scheduledRepeatField = document.getElementById("outgoing-api-edit-scheduled-repeat-field");
    const continuousRepeatInput = document.getElementById("outgoing-api-edit-continuous-repeat-input");
    const continuousRepeatField = document.getElementById("outgoing-api-edit-continuous-repeat-field");
    const continuousIntervalValueInput = document.getElementById("outgoing-api-edit-continuous-interval-value-input");
    const continuousIntervalValueField = document.getElementById("outgoing-api-edit-continuous-interval-value-field");
    const continuousIntervalUnitInput = document.getElementById("outgoing-api-edit-continuous-interval-unit-input");
    const continuousIntervalUnitField = document.getElementById("outgoing-api-edit-continuous-interval-unit-field");
    const authTypeInput = document.getElementById("outgoing-api-edit-auth-type-input");
    const authTokenInput = document.getElementById("outgoing-api-edit-auth-token-input");
    const authTokenField = document.getElementById("outgoing-api-edit-auth-token-field");
    const authUsernameInput = document.getElementById("outgoing-api-edit-auth-username-input");
    const authUsernameField = document.getElementById("outgoing-api-edit-auth-username-field");
    const authPasswordInput = document.getElementById("outgoing-api-edit-auth-password-input");
    const authPasswordField = document.getElementById("outgoing-api-edit-auth-password-field");
    const authHeaderNameInput = document.getElementById("outgoing-api-edit-auth-header-name-input");
    const authHeaderNameField = document.getElementById("outgoing-api-edit-auth-header-name-field");
    const authHeaderValueInput = document.getElementById("outgoing-api-edit-auth-header-value-input");
    const authHeaderValueField = document.getElementById("outgoing-api-edit-auth-header-value-field");
    const payloadInput = document.getElementById("outgoing-api-edit-payload-input");
    const testButton = document.getElementById("outgoing-api-edit-test-button");
    const testFeedback = document.getElementById("outgoing-api-edit-test-feedback");
    const feedback = document.getElementById("outgoing-api-edit-form-feedback");

    const getSelectedType = () => typeInput?.value || form.dataset.outgoingType || "outgoing_scheduled";

    const syncAuthFields = () => {
      const authType = authTypeInput?.value || "none";
      [authTokenField, authUsernameField, authPasswordField, authHeaderNameField, authHeaderValueField].forEach((field) => {
        if (field) {
          field.hidden = true;
        }
      });

      if (authType === "bearer" && authTokenField) {
        authTokenField.hidden = false;
      }
      if (authType === "basic") {
        if (authUsernameField) {
          authUsernameField.hidden = false;
        }
        if (authPasswordField) {
          authPasswordField.hidden = false;
        }
      }
      if (authType === "header") {
        if (authHeaderNameField) {
          authHeaderNameField.hidden = false;
        }
        if (authHeaderValueField) {
          authHeaderValueField.hidden = false;
        }
      }
    };

    const syncTypeFields = () => {
      const selectedType = getSelectedType();
      const isScheduled = selectedType === "outgoing_scheduled";
      const isContinuous = selectedType === "outgoing_continuous";
      const continuousRepeating = Boolean(continuousRepeatInput?.checked);

      if (scheduledTimeField) {
        scheduledTimeField.hidden = !isScheduled;
      }
      if (scheduledRepeatField) {
        scheduledRepeatField.hidden = !isScheduled;
      }
      if (continuousRepeatField) {
        continuousRepeatField.hidden = !isContinuous;
      }
      if (continuousIntervalValueField) {
        continuousIntervalValueField.hidden = !isContinuous || !continuousRepeating;
      }
      if (continuousIntervalUnitField) {
        continuousIntervalUnitField.hidden = !isContinuous || !continuousRepeating;
      }
    };

    const buildRepeatIntervalMinutes = () => {
      const rawValue = Number(continuousIntervalValueInput?.value || "0");
      const unit = continuousIntervalUnitInput?.value || "minutes";
      return unit === "hours" ? rawValue * 60 : rawValue;
    };

    const buildPayload = () => ({
      type: getSelectedType(),
      name: nameInput?.value.trim() || "",
      path_slug: sanitizeSlug(slugInput?.value || ""),
      description: descriptionInput?.value.trim() || "",
      enabled: Boolean(enabledInput?.checked),
      repeat_enabled: getSelectedType() === "outgoing_scheduled"
        ? Boolean(scheduledRepeatInput?.checked)
        : Boolean(continuousRepeatInput?.checked),
      repeat_interval_minutes: getSelectedType() === "outgoing_continuous" && continuousRepeatInput?.checked
        ? buildRepeatIntervalMinutes()
        : null,
      destination_url: destinationInput?.value.trim() || "",
      http_method: methodInput?.value || "POST",
      auth_type: authTypeInput?.value || "none",
      auth_config: {
        token: authTokenInput?.value || "",
        username: authUsernameInput?.value || "",
        password: authPasswordInput?.value || "",
        header_name: authHeaderNameInput?.value || "",
        header_value: authHeaderValueInput?.value || ""
      },
      payload_template: payloadInput?.value.trim() || "",
      scheduled_time: getSelectedType() === "outgoing_scheduled" ? (scheduledTimeInput?.value || "") : undefined
    });

    const validatePayload = (payload) => {
      if (!payload.name || !payload.path_slug) {
        return "Name and path slug are required.";
      }
      if (!payload.destination_url) {
        return "Destination URL is required.";
      }
      if (!/^https?:\/\//i.test(payload.destination_url)) {
        return "Destination URL must start with http:// or https://.";
      }
      if (!payload.payload_template) {
        return "A JSON payload template is required.";
      }
      try {
        JSON.parse(payload.payload_template);
      } catch {
        return "Payload template must be valid JSON.";
      }
      if (payload.type === "outgoing_scheduled" && !payload.scheduled_time) {
        return "Choose a send time for the scheduled outgoing API.";
      }
      if (payload.type === "outgoing_continuous" && payload.repeat_enabled) {
        if (!payload.repeat_interval_minutes) {
          return "Choose a repeat interval for the continuous outgoing API.";
        }
        if (payload.repeat_interval_minutes < 1 || payload.repeat_interval_minutes > 10080) {
          return "Continuous repeat intervals must be between 1 minute and 168 hours.";
        }
      }
      if (payload.auth_type === "bearer" && !payload.auth_config.token) {
        return "Enter a bearer token or change destination auth.";
      }
      if (payload.auth_type === "basic" && (!payload.auth_config.username || !payload.auth_config.password)) {
        return "Basic auth requires both a username and password.";
      }
      if (payload.auth_type === "header" && (!payload.auth_config.header_name || !payload.auth_config.header_value)) {
        return "Custom header auth requires both a header name and value.";
      }
      return "";
    };

    authTypeInput?.addEventListener("change", syncAuthFields);
    scheduledRepeatInput?.addEventListener("change", syncTypeFields);
    continuousRepeatInput?.addEventListener("change", syncTypeFields);
    form.addEventListener("outgoing-edit-sync", () => {
      syncAuthFields();
      syncTypeFields();
    });

    testButton?.addEventListener("click", async () => {
      const payload = buildPayload();
      const validationMessage = validatePayload(payload);

      if (validationMessage) {
        setFormMessage(testFeedback, validationMessage, "error");
        return;
      }

      testButton.disabled = true;
      setFormMessage(testFeedback, "Sending test payload...", "info");

      try {
        const result = await client.testOutgoingDelivery(payload);
        const responsePreview = result.response_body ? ` Response: ${result.response_body}` : "";
        setFormMessage(testFeedback, `Test delivery returned ${result.status_code}.${responsePreview}`.trim(), result.ok ? "success" : "error");
      } catch (error) {
        const { message: errorMessage } = normalizeError(error);
        setFormMessage(testFeedback, errorMessage, "error");
      } finally {
        testButton.disabled = false;
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const entryId = idInput?.value || form.dataset.outgoingId || "";
      const payload = buildPayload();
      const validationMessage = validatePayload(payload);

      if (!entryId) {
        setFormMessage(feedback, "Outgoing API id is missing.", "error");
        return;
      }

      if (validationMessage) {
        setFormMessage(feedback, validationMessage, "error");
        return;
      }

      setFormMessage(feedback, "Saving outgoing API...", "info");

      try {
        await client.updateOutgoing(entryId, payload);
        await actions.loadOutgoingRegistries();
        setFormMessage(feedback, "Outgoing API saved.", "success");
        render.setAlert("Outgoing API updated.", "success");
        getModals().closeOutgoingEditModal?.();
        emitApiLog({
          action: "outgoing_api_updated",
          message: `Updated outgoing API "${payload.name}".`,
          details: {
            apiId: entryId,
            type: payload.type,
            enabled: payload.enabled
          }
        });
      } catch (error) {
        const { message: errorMessage, stack: errorStack } = normalizeError(error);
        setFormMessage(feedback, errorMessage, "error");
        emitApiLog({
          level: "error",
          action: "outgoing_api_update_failed",
          message: "Failed to update outgoing API.",
          details: {
            apiId: entryId,
            error: errorMessage,
            stack: errorStack
          }
        });
      }
    });

    syncAuthFields();
    syncTypeFields();
  };

  return {
    set modals(nextModals) {
      modals = nextModals;
    },
    syncCreateModalType,
    bindCreateForm,
    bindOutgoingEditForm
  };
};
