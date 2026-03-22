import { createElementMap } from "./format-utils.js";

const imageMagicElements = createElementMap({
  statusValue: "tools-image-magic-status-value",
  statusMessage: "tools-image-magic-status-message",
  form: "tools-image-magic-form",
  enabledInput: "tools-image-magic-enabled-input",
  enabledCopy: "tools-image-magic-enabled-copy",
  machineInput: "tools-image-magic-machine-input",
  commandInput: "tools-image-magic-command-input",
  defaultRetriesValue: "tools-image-magic-default-retries-value",
  feedback: "tools-image-magic-form-feedback",
  saveButton: "tools-image-magic-save-button"
});

let currentTool = null;
let pendingSave = false;

const setFeedback = (message, tone = "") => {
  if (!imageMagicElements.feedback) {
    return;
  }

  imageMagicElements.feedback.textContent = message;
  imageMagicElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const syncEnabledCopy = () => {
  if (!imageMagicElements.enabledCopy || !imageMagicElements.enabledInput) {
    return;
  }

  imageMagicElements.enabledCopy.textContent = imageMagicElements.enabledInput.checked
    ? "Tool is enabled"
    : "Tool is disabled";
};

const renderMachines = (machines, selectedWorkerId) => {
  if (!imageMagicElements.machineInput) {
    return;
  }

  const options = machines.map((machine) => {
    const option = document.createElement("option");
    option.value = machine.id;
    option.textContent = machine.is_local ? `${machine.name} (local)` : machine.name;
    return option;
  });

  imageMagicElements.machineInput.replaceChildren(...options);

  const nextSelected = selectedWorkerId || machines[0]?.id || "";
  imageMagicElements.machineInput.value = nextSelected;
};

const applyToolState = (tool) => {
  currentTool = tool;

  if (imageMagicElements.enabledInput) {
    imageMagicElements.enabledInput.checked = Boolean(tool.config.enabled);
  }
  syncEnabledCopy();

  if (imageMagicElements.commandInput) {
    imageMagicElements.commandInput.value = tool.config.command || "magick";
  }

  renderMachines(tool.machines || [], tool.config.target_worker_id || "");

  if (imageMagicElements.defaultRetriesValue) {
    imageMagicElements.defaultRetriesValue.textContent = String(tool.config.default_retries ?? 2);
  }

  if (imageMagicElements.statusValue) {
    imageMagicElements.statusValue.textContent = tool.config.enabled ? "Enabled" : "Disabled";
  }

  if (imageMagicElements.statusMessage) {
    const selectedOption = imageMagicElements.machineInput?.selectedOptions?.[0];
    imageMagicElements.statusMessage.textContent = selectedOption
      ? `Conversions run on ${selectedOption.textContent}.`
      : "Select a machine for conversions.";
  }
};

const loadTool = async () => {
  const requestJson = window.Malcom?.requestJson;
  if (!requestJson) {
    return;
  }

  try {
    const tool = await requestJson("/api/v1/tools/image-magic");
    applyToolState(tool);
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to load Image Magic tool.", "error");
  }
};

imageMagicElements.enabledInput?.addEventListener("change", syncEnabledCopy);
imageMagicElements.machineInput?.addEventListener("change", () => {
  if (!imageMagicElements.statusMessage || !imageMagicElements.machineInput) {
    return;
  }
  const selectedOption = imageMagicElements.machineInput.selectedOptions[0];
  imageMagicElements.statusMessage.textContent = selectedOption
    ? `Conversions run on ${selectedOption.textContent}.`
    : "Select a machine for conversions.";
});

imageMagicElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (pendingSave) {
    return;
  }

  const command = imageMagicElements.commandInput?.value.trim() || "";
  const targetWorkerId = imageMagicElements.machineInput?.value || "";

  if (!command) {
    setFeedback("ImageMagick command is required.", "error");
    return;
  }

  pendingSave = true;
  setFeedback("");

  if (imageMagicElements.saveButton) {
    imageMagicElements.saveButton.disabled = true;
  }

  try {
    const requestJson = window.Malcom?.requestJson;
    if (!requestJson) {
      throw new Error("Request helper unavailable.");
    }

    await requestJson("/api/v1/tools/image-magic", {
      method: "PATCH",
      body: JSON.stringify({
        enabled: imageMagicElements.enabledInput?.checked ?? false,
        target_worker_id: targetWorkerId || null,
        command
      })
    });

    const refreshed = await requestJson("/api/v1/tools/image-magic");
    applyToolState(refreshed);
    setFeedback("Settings saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save settings.", "error");
  } finally {
    pendingSave = false;
    if (imageMagicElements.saveButton) {
      imageMagicElements.saveButton.disabled = false;
    }
  }
});

loadTool().catch(() => {});
