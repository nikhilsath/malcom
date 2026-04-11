import { createElementMap } from "../format-utils.js";
import { normalizeRequestError } from "../request.js";

const coquiElements = createElementMap({
  enabledInput: "tools-coqui-enabled-input",
  enabledCopy: "tools-coqui-enabled-copy",
  statusValue: "tools-coqui-status-value",
  statusMessage: "tools-coqui-status-message",
  summaryCommandValue: "tools-coqui-summary-command-value",
  summaryModelValue: "tools-coqui-summary-model-value",
  summaryVoiceValue: "tools-coqui-summary-voice-value",
  form: "tools-coqui-form",
  configRegion: "tools-coqui-config-region",
  commandInput: "tools-coqui-command-input",
  modelInput: "tools-coqui-model-input",
  speakerInput: "tools-coqui-speaker-input",
  languageInput: "tools-coqui-language-input",
  feedback: "tools-coqui-form-feedback",
  saveButton: "tools-coqui-save-button"
});

let currentTool = null;
let runtimePreview = null;
let pendingSave = false;
let pendingRuntimeRefresh = false;
let runtimeRefreshToken = 0;

const setFeedback = (message, tone = "") => {
  if (!coquiElements.feedback) {
    return;
  }

  coquiElements.feedback.textContent = message;
  coquiElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const emitToolsDirectoryUpdated = () => {
  window.dispatchEvent(new CustomEvent("malcom:tools-directory-updated"));
};

const createOptionElement = ({ value, label, disabled = false }) => {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  option.disabled = disabled;
  return option;
};

const setSelectOptions = (
  selectElement,
  options,
  {
    selectedValue = "",
    placeholderLabel = "Unavailable",
    allowBlank = false,
    blankLabel = "Use model default"
  } = {},
) => {
  if (!selectElement) {
    return;
  }

  const optionElements = [];
  if (allowBlank) {
    optionElements.push(createOptionElement({ value: "", label: blankLabel }));
  }

  if (Array.isArray(options) && options.length > 0) {
    options.forEach((option) => {
      optionElements.push(
        createOptionElement({
          value: option.value,
          label: option.label || option.value
        })
      );
    });
  } else if (!allowBlank) {
    optionElements.push(
      createOptionElement({
        value: "",
        label: placeholderLabel,
        disabled: true
      })
    );
  }

  selectElement.replaceChildren(...optionElements);

  if (allowBlank) {
    const hasSelectedOption = Array.isArray(options) && options.some((option) => option.value === selectedValue);
    selectElement.value = hasSelectedOption ? selectedValue : "";
    return;
  }

  if (Array.isArray(options) && options.some((option) => option.value === selectedValue)) {
    selectElement.value = selectedValue;
    return;
  }

  selectElement.selectedIndex = optionElements.length > 0 ? 0 : -1;
};

const getSelectValue = (element, fallback = "") => {
  if (!element) {
    return fallback;
  }
  return element.value || fallback;
};

const formatVoiceDefaults = (speaker, language) => {
  const values = [speaker, language].filter(Boolean);
  return values.length > 0 ? values.join(" / ") : "Model defaults";
};

const syncEnabledCopy = () => {
  if (!coquiElements.enabledCopy || !coquiElements.enabledInput) {
    return;
  }

  coquiElements.enabledCopy.textContent = coquiElements.enabledInput.checked
    ? "Tool is enabled"
    : "Tool is disabled";
};

const syncConfigVisibility = () => {
  if (!coquiElements.configRegion || !coquiElements.enabledInput) {
    return;
  }

  coquiElements.configRegion.hidden = !coquiElements.enabledInput.checked;
};

const setConfigInputsDisabled = (disabled) => {
  [
    coquiElements.commandInput,
    coquiElements.modelInput,
    coquiElements.speakerInput,
    coquiElements.languageInput
  ].forEach((element) => {
    if (element) {
      element.disabled = disabled;
    }
  });
};

const shouldDisableConfigInputs = () => {
  if (!runtimePreview) {
    return true;
  }

  return !runtimePreview.command_available || !Array.isArray(runtimePreview.model_options) || runtimePreview.model_options.length === 0;
};

const updateSummaryValues = () => {
  const savedConfig = currentTool?.config || {};
  const command = getSelectValue(coquiElements.commandInput, savedConfig.command || "");
  const modelName = getSelectValue(coquiElements.modelInput, savedConfig.model_name || "");
  const speaker = getSelectValue(coquiElements.speakerInput, savedConfig.speaker || "");
  const language = getSelectValue(coquiElements.languageInput, savedConfig.language || "");

  if (coquiElements.summaryCommandValue) {
    coquiElements.summaryCommandValue.textContent = command || savedConfig.command || "Not configured";
  }
  if (coquiElements.summaryModelValue) {
    coquiElements.summaryModelValue.textContent = modelName || savedConfig.model_name || "Not configured";
  }
  if (coquiElements.summaryVoiceValue) {
    coquiElements.summaryVoiceValue.textContent = formatVoiceDefaults(speaker || savedConfig.speaker || "", language || savedConfig.language || "");
  }
};

const renderRuntime = () => {
  if (!runtimePreview) {
    return;
  }

  if (coquiElements.statusValue) {
    coquiElements.statusValue.textContent = runtimePreview.ready ? "Ready" : "Unavailable";
  }

  if (coquiElements.statusMessage) {
    coquiElements.statusMessage.textContent = runtimePreview.message || "Coqui runtime status unavailable.";
  }
};

const renderSelects = (config) => {
  const runtime = runtimePreview || currentTool?.runtime;
  if (!runtime) {
    return;
  }

  setSelectOptions(coquiElements.commandInput, runtime.command_options, {
    selectedValue: config.command || "",
    placeholderLabel: "No runtime command detected"
  });
  setSelectOptions(coquiElements.modelInput, runtime.model_options, {
    selectedValue: config.model_name || "",
    placeholderLabel: runtime.command_available ? "No Coqui models detected" : "No models available"
  });
  setSelectOptions(coquiElements.speakerInput, runtime.speaker_options, {
    selectedValue: config.speaker || "",
    allowBlank: true,
    blankLabel: "Use model default speaker"
  });
  setSelectOptions(coquiElements.languageInput, runtime.language_options, {
    selectedValue: config.language || "",
    allowBlank: true,
    blankLabel: "Use model default language"
  });

  setConfigInputsDisabled(shouldDisableConfigInputs());
};

const renderTool = () => {
  if (!currentTool) {
    return;
  }

  if (coquiElements.enabledInput) {
    coquiElements.enabledInput.checked = Boolean(currentTool.config.enabled);
  }
  syncEnabledCopy();
  syncConfigVisibility();
  renderRuntime();
  renderSelects(currentTool.config);
  updateSummaryValues();
};

const buildRuntimePreviewUrl = () => {
  const command = getSelectValue(coquiElements.commandInput, currentTool?.config.command || "");
  const modelName = getSelectValue(coquiElements.modelInput, currentTool?.config.model_name || "");
  const params = new URLSearchParams();
  if (command) {
    params.set("command", command);
  }
  if (modelName) {
    params.set("model_name", modelName);
  }
  const query = params.toString();
  return query ? `/api/v1/tools/coqui-tts?${query}` : "/api/v1/tools/coqui-tts";
};

const refreshRuntimePreview = async () => {
  if (!currentTool) {
    return;
  }

  pendingRuntimeRefresh = true;
  const refreshToken = ++runtimeRefreshToken;
  try {
    const response = await window.Malcom.requestJson(buildRuntimePreviewUrl());
    if (refreshToken !== runtimeRefreshToken) {
      return;
    }
    runtimePreview = response.runtime;
    renderRuntime();
    renderSelects({
      command: getSelectValue(coquiElements.commandInput, currentTool.config.command || ""),
      model_name: getSelectValue(coquiElements.modelInput, currentTool.config.model_name || ""),
      speaker: getSelectValue(coquiElements.speakerInput, currentTool.config.speaker || ""),
      language: getSelectValue(coquiElements.languageInput, currentTool.config.language || "")
    });
    updateSummaryValues();
  } catch (error) {
    setFeedback(normalizeRequestError(error, "Unable to refresh Coqui runtime details.").message, "error");
  } finally {
    pendingRuntimeRefresh = false;
  }
};

const loadTool = async () => {
  currentTool = await window.Malcom.requestJson("/api/v1/tools/coqui-tts");
  runtimePreview = currentTool.runtime;
  renderTool();
};

coquiElements.enabledInput?.addEventListener("change", () => {
  syncEnabledCopy();
  syncConfigVisibility();
  setConfigInputsDisabled(shouldDisableConfigInputs());
});

coquiElements.commandInput?.addEventListener("change", async () => {
  updateSummaryValues();
  await refreshRuntimePreview();
});

coquiElements.modelInput?.addEventListener("change", async () => {
  updateSummaryValues();
  await refreshRuntimePreview();
});

coquiElements.speakerInput?.addEventListener("change", updateSummaryValues);
coquiElements.languageInput?.addEventListener("change", updateSummaryValues);

coquiElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!currentTool || pendingSave || pendingRuntimeRefresh) {
    return;
  }

  const enabled = coquiElements.enabledInput?.checked ?? false;
  const command = getSelectValue(coquiElements.commandInput, currentTool.config.command || "");
  const modelName = getSelectValue(coquiElements.modelInput, currentTool.config.model_name || "");
  const speaker = getSelectValue(coquiElements.speakerInput, "");
  const language = getSelectValue(coquiElements.languageInput, "");

  if (enabled && (!command || !modelName)) {
    setFeedback("Choose a detected Coqui command and model before enabling the tool.", "error");
    return;
  }

  pendingSave = true;
  coquiElements.saveButton.disabled = true;
  coquiElements.saveButton.textContent = "Saving...";
  setFeedback("");

  const payload = {
    enabled,
    ...(command ? { command } : {}),
    ...(modelName ? { model_name: modelName } : {}),
    speaker,
    language
  };

  try {
    currentTool = await window.Malcom.requestJson("/api/v1/tools/coqui-tts", {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    runtimePreview = currentTool.runtime;
    renderTool();
    emitToolsDirectoryUpdated();
    setFeedback("Coqui TTS configuration saved.", "success");
  } catch (error) {
    setFeedback(normalizeRequestError(error, "Unable to save Coqui TTS configuration.").message, "error");
  } finally {
    pendingSave = false;
    coquiElements.saveButton.disabled = false;
    coquiElements.saveButton.textContent = "Save configuration";
  }
});

loadTool().catch((error) => {
  setFeedback(normalizeRequestError(error, "Unable to load Coqui TTS configuration.").message, "error");
});
