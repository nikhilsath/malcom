import { formatDateTime } from "./format-utils.js";

const convertAudioElements = {
  statusValue: document.getElementById("tools-convert-audio-status-value"),
  statusMessage: document.getElementById("tools-convert-audio-status-message"),
  form: document.getElementById("tools-convert-audio-form"),
  enabledInput: document.getElementById("tools-convert-audio-enabled-input"),
  feedback: document.getElementById("tools-convert-audio-form-feedback"),
  saveButton: document.getElementById("tools-convert-audio-save-button")
};

let currentTool = null;
let pendingSave = false;

const setFeedback = (message, tone = "") => {
  if (!convertAudioElements.feedback) {
    return;
  }

  convertAudioElements.feedback.textContent = message;
  convertAudioElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const applyToolState = (tool) => {
  currentTool = tool;

  if (convertAudioElements.enabledInput) {
    convertAudioElements.enabledInput.checked = Boolean(tool.enabled);
  }

  if (convertAudioElements.statusValue) {
    convertAudioElements.statusValue.textContent = tool.enabled ? "Enabled" : "Disabled";
  }
};

const loadTool = async () => {
  const requestJson = window.Malcom?.requestJson;
  if (!requestJson) {
    return;
  }

  try {
    const tool = await requestJson("/api/v1/tools/convert-audio/directory");
    applyToolState(tool);
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to load Convert Audio tool.", "error");
  }
};

convertAudioElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (pendingSave) {
    return;
  }

  pendingSave = true;
  setFeedback("");

  if (convertAudioElements.saveButton) {
    convertAudioElements.saveButton.disabled = true;
  }

  const enabled = convertAudioElements.enabledInput?.checked ?? false;

  try {
    const requestJson = window.Malcom?.requestJson;
    if (!requestJson) {
      throw new Error("Request helper unavailable.");
    }

    const tool = await requestJson("/api/v1/tools/convert-audio/directory", {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    });

    applyToolState(tool);
    setFeedback("Settings saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save settings.", "error");
  } finally {
    pendingSave = false;
    if (convertAudioElements.saveButton) {
      convertAudioElements.saveButton.disabled = false;
    }
  }
});

loadTool().catch(() => {});
