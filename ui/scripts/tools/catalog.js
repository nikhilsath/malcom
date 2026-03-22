import { requestJson as fetchJson } from "../request.js";

const toolsElements = {
  grid: document.getElementById("tools-grid"),
  selectedCount: document.getElementById("selected-tools-count"),
  selectedHelper: document.getElementById("selected-tools-helper"),
  detailTitle: document.getElementById("tool-detail-title"),
  detailDescription: document.getElementById("tool-detail-description"),
  form: document.getElementById("tool-detail-form"),
  idInput: document.getElementById("tool-detail-id-input"),
  enabledInput: document.getElementById("tool-detail-enabled-input"),
  enabledCopy: document.getElementById("tool-detail-enabled-copy"),
  nameInput: document.getElementById("tool-detail-name-input"),
  descriptionInput: document.getElementById("tool-detail-description-input"),
  feedback: document.getElementById("tool-detail-form-feedback"),
  saveButton: document.getElementById("tool-detail-save-button"),
  configLink: document.getElementById("tool-detail-config-link"),
  detailModal: document.getElementById("tool-detail-modal"),
  modalCloseButtons: Array.from(document.querySelectorAll("[data-modal-close='tool-detail-modal']")),
};

let toolsCatalog = [];
let activeToolId = null;
let savingTool = false;

const openDetailModal = () => {
  if (!toolsElements.detailModal) {
    return;
  }
  toolsElements.detailModal.classList.add("modal--open");
  document.body.classList.add("modal-open");
};

const closeDetailModal = () => {
  if (!toolsElements.detailModal) {
    return;
  }
  toolsElements.detailModal.classList.remove("modal--open");
  document.body.classList.remove("modal-open");
};

const emitToolsDirectoryUpdated = () => {
  window.dispatchEvent(new CustomEvent("malcom:tools-directory-updated"));
};

const setFormFeedback = (message, tone = "") => {
  toolsElements.feedback.textContent = message;
  toolsElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const getActiveTool = () => toolsCatalog.find((tool) => tool.id === activeToolId) || null;

const syncEnabledCopy = (enabled) => {
  if (!toolsElements.enabledCopy) {
    return;
  }
  toolsElements.enabledCopy.textContent = enabled ? "Tool is enabled" : "Tool is disabled";
};

const updateHeaderSummary = () => {
  toolsElements.selectedCount.textContent = `${toolsCatalog.length} loaded`;
  const activeTool = getActiveTool();
  toolsElements.selectedHelper.textContent = activeTool
    ? `${activeTool.enabled ? "Enabled" : "Disabled"} tool selected. Save changes here or open the config page.`
    : "Select a tool to update metadata or open its configuration page.";
};

const buildToolCard = (tool) => {
  const card = document.createElement("button");
  card.id = `tool-card-${tool.id}`;
  card.className = activeToolId === tool.id ? "tool-card tool-card--selected" : "tool-card";
  card.type = "button";
  card.dataset.toolId = tool.id;

  const header = document.createElement("div");
  header.id = `${card.id}-header`;
  header.className = "tool-card__header";

  const title = document.createElement("span");
  title.id = `${card.id}-title`;
  title.className = "tool-card__title";
  title.textContent = tool.name;

  const stateBadge = document.createElement("span");
  stateBadge.id = `${card.id}-state`;
  stateBadge.className = tool.enabled ? "tool-card__state tool-card__state--enabled" : "tool-card__state tool-card__state--disabled";
  stateBadge.textContent = tool.enabled ? "Enabled" : "Disabled";

  const description = document.createElement("span");
  description.id = `${card.id}-description`;
  description.className = "tool-card__description";
  description.textContent = tool.description;

  const path = document.createElement("span");
  path.id = `${card.id}-path`;
  path.className = "tool-card__meta";
  path.textContent = tool.page_href;

  header.append(title, stateBadge);
  card.append(header, description, path);
  card.addEventListener("click", () => {
    activeToolId = tool.id;
    render();
    openDetailModal();
  });
  return card;
};

const renderGrid = () => {
  const fragment = document.createDocumentFragment();
  toolsCatalog.forEach((tool) => {
    fragment.appendChild(buildToolCard(tool));
  });
  toolsElements.grid.replaceChildren(fragment);
};

const renderDetail = () => {
  const activeTool = getActiveTool();

  if (!activeTool) {
    toolsElements.detailTitle.textContent = "Choose a tool";
    toolsElements.detailDescription.textContent = "Tool metadata and enablement are managed here.";
    toolsElements.idInput.value = "";
    toolsElements.enabledInput.checked = false;
    syncEnabledCopy(false);
    toolsElements.nameInput.value = "";
    toolsElements.descriptionInput.value = "";
    toolsElements.configLink.href = "../tools/catalog.html";
    toolsElements.configLink.setAttribute("aria-disabled", "true");
    toolsElements.configLink.tabIndex = -1;
    toolsElements.configLink.hidden = true;
    return;
  }

  toolsElements.detailTitle.textContent = activeTool.name;
  toolsElements.detailDescription.textContent = activeTool.description;
  toolsElements.idInput.value = activeTool.id;
  toolsElements.enabledInput.checked = Boolean(activeTool.enabled);
  syncEnabledCopy(Boolean(activeTool.enabled));
  toolsElements.nameInput.value = activeTool.name;
  toolsElements.descriptionInput.value = activeTool.description;
  toolsElements.configLink.href = `..${activeTool.page_href}`;
  toolsElements.configLink.hidden = !activeTool.enabled;
  if (activeTool.enabled) {
    toolsElements.configLink.removeAttribute("aria-disabled");
    toolsElements.configLink.tabIndex = 0;
  } else {
    toolsElements.configLink.setAttribute("aria-disabled", "true");
    toolsElements.configLink.tabIndex = -1;
  }
};

const render = () => {
  renderGrid();
  renderDetail();
  updateHeaderSummary();
};

const loadTools = async () => {
  toolsCatalog = await fetchJson("/api/v1/tools");
  if (!activeToolId && toolsCatalog[0]) {
    activeToolId = toolsCatalog[0].id;
  }
  render();
};

toolsElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const activeTool = getActiveTool();

  if (!activeTool || savingTool) {
    return;
  }

  const nextName = toolsElements.nameInput.value.trim();
  const nextDescription = toolsElements.descriptionInput.value.trim();

  if (!nextName || !nextDescription) {
    setFormFeedback("Tool name and description are required.", "error");
    return;
  }

  savingTool = true;
  toolsElements.saveButton.disabled = true;
  toolsElements.saveButton.textContent = "Saving...";
  setFormFeedback("");

  try {
    const payload = await fetchJson(`/api/v1/tools/${encodeURIComponent(activeTool.id)}/directory`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name: nextName,
        description: nextDescription,
        enabled: toolsElements.enabledInput.checked
      })
    });

    toolsCatalog = toolsCatalog.map((tool) => (tool.id === payload.id ? payload : tool));
    render();
    emitToolsDirectoryUpdated();
    setFormFeedback("Tool details saved.", "success");
  } catch (error) {
    setFormFeedback(error instanceof Error ? error.message : "Unable to save tool changes.", "error");
  } finally {
    savingTool = false;
    toolsElements.saveButton.disabled = false;
    toolsElements.saveButton.textContent = "Save tool";
  }
});

toolsElements.enabledInput?.addEventListener("change", () => {
  syncEnabledCopy(toolsElements.enabledInput.checked);
});

toolsElements.modalCloseButtons.forEach((button) => {
  button.addEventListener("click", closeDetailModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && toolsElements.detailModal?.classList.contains("modal--open")) {
    closeDetailModal();
  }
});

loadTools().catch((error) => {
  toolsElements.selectedHelper.textContent = "Unable to load registered tools.";
  setFormFeedback(error instanceof Error ? error.message : "Unable to load registered tools.", "error");
});
