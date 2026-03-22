import { requestJson as fetchJson } from "./request.js";

const toolConfigElements = {
  title: document.getElementById("tools-config-title"),
  description: document.getElementById("tools-config-description"),
  statusValue: document.getElementById("tools-config-status-value"),
  statusMessage: document.getElementById("tools-config-status-message"),
  metadataNameValue: document.getElementById("tools-config-metadata-name-value"),
  metadataIdValue: document.getElementById("tools-config-metadata-id-value"),
  metadataPathValue: document.getElementById("tools-config-metadata-path-value"),
  form: document.getElementById("tools-config-form"),
  enabledInput: document.getElementById("tools-config-enabled-input"),
  nameInput: document.getElementById("tools-config-name-input"),
  descriptionInput: document.getElementById("tools-config-description-input"),
  feedback: document.getElementById("tools-config-form-feedback"),
  checklist: document.getElementById("tools-config-checklist"),
  saveButton: document.getElementById("tools-config-save-button")
};

const toolId = document.body?.dataset.toolId || "";
let currentTool = null;
let pendingSave = false;

const emitToolsDirectoryUpdated = () => {
  window.dispatchEvent(new CustomEvent("malcom:tools-directory-updated"));
};

const setupGuidance = {
  "convert-audio": [
    "Confirm which input and output formats the worker supports before enabling production automations.",
    "Document any codec or bitrate expectations in the description so downstream steps stay predictable.",
    "Open the tool folder and keep transformation scripts or binaries colocated with the tool registration metadata."
  ],
  "convert-video": [
    "Decide whether this tool will prioritize archival quality or delivery-ready compression before enabling it.",
    "Capture required container, resolution, and codec expectations in the metadata description.",
    "Keep ffmpeg presets or wrapper scripts under the tool folder so the registration stays discoverable."
  ],
  "grafana": [
    "Record the dashboard source, host, or provisioning assumptions before operators depend on the tool.",
    "Use the description to explain whether Grafana is read-only reporting or part of an active incident workflow.",
    "Add environment-specific connection details in runtime config when the integration is implemented."
  ],
  "llm-deepl": [
    "Confirm which local runtime preset and server base URL the workspace should use before enabling the tool.",
    "Set the saved model identifier to the exact value exposed by your local inference server.",
    "Keep endpoint paths aligned with the selected local API implementation."
  ],
  "ocr-transcribe": [
    "Describe whether this tool is optimized for images, audio, or mixed media before enabling it widely.",
    "Capture expected file size or language constraints so automations can validate inputs early.",
    "Store model, binary, or service wiring within the tool folder as implementation code lands."
  ],
  "smtp": [
    "Use the SMTP page actions to assign a machine, bind address, and recipient mailbox.",
    "Start the listener only after the selected machine and recipient restrictions are confirmed.",
    "Review runtime activity on this page after test mail is delivered."
  ]
};

const setFeedback = (message, tone = "") => {
  toolConfigElements.feedback.textContent = message;
  toolConfigElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const renderChecklist = () => {
  const steps = setupGuidance[toolId] || [
    "Add runtime-specific configuration on this page as the tool implementation becomes available.",
    "Keep the stored tool name and description aligned with the actual tool behavior.",
    "Regenerate the manifest after metadata changes so overview and sidenav labels stay current."
  ];
  const fragment = document.createDocumentFragment();

  steps.forEach((step, index) => {
    const item = document.createElement("li");
    item.id = `tools-config-checklist-item-${index + 1}`;
    item.textContent = step;
    fragment.appendChild(item);
  });

  toolConfigElements.checklist.replaceChildren(fragment);
};

const renderTool = () => {
  if (!currentTool) {
    return;
  }

  toolConfigElements.title.textContent = `${currentTool.name} configuration`;
  toolConfigElements.description.textContent = currentTool.description;
  toolConfigElements.statusValue.textContent = currentTool.enabled ? "Enabled" : "Disabled";
  toolConfigElements.statusMessage.textContent = currentTool.enabled
    ? "This tool is available to the middleware."
    : "Enable this tool after its runtime configuration is complete.";
  toolConfigElements.metadataNameValue.textContent = currentTool.name;
  toolConfigElements.metadataIdValue.textContent = currentTool.id;
  toolConfigElements.metadataPathValue.textContent = currentTool.page_href;
  toolConfigElements.enabledInput.value = String(Boolean(currentTool.enabled));
  toolConfigElements.nameInput.value = currentTool.name;
  toolConfigElements.descriptionInput.value = currentTool.description;
  renderChecklist();
};

const loadTool = async () => {
  const tools = await fetchJson("/api/v1/tools");
  currentTool = tools.find((tool) => tool.id === toolId) || null;

  if (!currentTool) {
    throw new Error("Tool not found in the registered directory.");
  }

  renderTool();
};

toolConfigElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!currentTool || pendingSave) {
    return;
  }

  const nextName = toolConfigElements.nameInput.value.trim();
  const nextDescription = toolConfigElements.descriptionInput.value.trim();

  if (!nextName || !nextDescription) {
    setFeedback("Tool name and description are required.", "error");
    return;
  }

  pendingSave = true;
  toolConfigElements.saveButton.disabled = true;
  toolConfigElements.saveButton.textContent = "Saving...";
  setFeedback("");

  try {
    currentTool = await fetchJson(`/api/v1/tools/${encodeURIComponent(toolId)}/directory`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        enabled: toolConfigElements.enabledInput.value === "true",
        name: nextName,
        description: nextDescription
      })
    });
    renderTool();
    emitToolsDirectoryUpdated();
    setFeedback("Tool configuration saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save tool configuration.", "error");
  } finally {
    pendingSave = false;
    toolConfigElements.saveButton.disabled = false;
    toolConfigElements.saveButton.textContent = "Save configuration";
  }
});

loadTool().catch((error) => {
  setFeedback(error instanceof Error ? error.message : "Unable to load tool configuration.", "error");
});
