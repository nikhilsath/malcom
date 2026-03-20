import { createElementMap } from "./format-utils.js";

const coquiElements = createElementMap({
  title: "tools-coqui-title",
  description: "tools-coqui-description",
  statusValue: "tools-coqui-status-value",
  statusMessage: "tools-coqui-status-message",
  summaryModelValue: "tools-coqui-summary-model-value",
  summaryCommandValue: "tools-coqui-summary-command-value",
  summaryOutputValue: "tools-coqui-summary-output-value",
  form: "tools-coqui-form",
  enabledInput: "tools-coqui-enabled-input",
  commandInput: "tools-coqui-command-input",
  modelInput: "tools-coqui-model-input",
  speakerInput: "tools-coqui-speaker-input",
  languageInput: "tools-coqui-language-input",
  outputInput: "tools-coqui-output-input",
  feedback: "tools-coqui-form-feedback",
  saveButton: "tools-coqui-save-button"
});

let currentTool = null;
let pendingSave = false;

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

const renderTool = () => {
  if (!currentTool) {
    return;
  }

  const { config } = currentTool;
  coquiElements.title.textContent = "Coqui TTS configuration";
  coquiElements.description.textContent = "Save the Coqui CLI runtime and defaults used by workflow tool steps.";
  coquiElements.statusValue.textContent = config.enabled ? "Enabled" : "Disabled";
  coquiElements.statusMessage.textContent = config.enabled
    ? "Workflow tool steps can generate speech audio with the saved CLI settings."
    : "Enable this tool after the Coqui CLI and model are available on the backend host.";
  coquiElements.summaryModelValue.textContent = config.model_name || "Not configured";
  coquiElements.summaryCommandValue.textContent = config.command || "Not configured";
  coquiElements.summaryOutputValue.textContent = config.output_directory || "Not configured";
  coquiElements.enabledInput.value = String(Boolean(config.enabled));
  coquiElements.commandInput.value = config.command || "";
  coquiElements.modelInput.value = config.model_name || "";
  coquiElements.speakerInput.value = config.speaker || "";
  coquiElements.languageInput.value = config.language || "";
  coquiElements.outputInput.value = config.output_directory || "";
};

const loadTool = async () => {
  currentTool = await window.Malcom.requestJson("/api/v1/tools/coqui-tts");
  renderTool();
};

coquiElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (pendingSave) {
    return;
  }

  const command = coquiElements.commandInput.value.trim();
  const modelName = coquiElements.modelInput.value.trim();
  const outputDirectory = coquiElements.outputInput.value.trim();

  if (!command || !modelName || !outputDirectory) {
    setFeedback("Command, model name, and output directory are required.", "error");
    return;
  }

  pendingSave = true;
  coquiElements.saveButton.disabled = true;
  coquiElements.saveButton.textContent = "Saving...";
  setFeedback("");

  try {
    currentTool = await window.Malcom.requestJson("/api/v1/tools/coqui-tts", {
      method: "PATCH",
      body: JSON.stringify({
        enabled: coquiElements.enabledInput.value === "true",
        command,
        model_name: modelName,
        speaker: coquiElements.speakerInput.value.trim(),
        language: coquiElements.languageInput.value.trim(),
        output_directory: outputDirectory
      })
    });
    renderTool();
    emitToolsDirectoryUpdated();
    setFeedback("Coqui TTS configuration saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save Coqui TTS configuration.", "error");
  } finally {
    pendingSave = false;
    coquiElements.saveButton.disabled = false;
    coquiElements.saveButton.textContent = "Save configuration";
  }
});

loadTool().catch((error) => {
  setFeedback(error instanceof Error ? error.message : "Unable to load Coqui TTS configuration.", "error");
});
