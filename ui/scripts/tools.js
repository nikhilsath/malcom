const toolsCatalog = Array.isArray(window.TOOLS_MANIFEST)
  ? window.TOOLS_MANIFEST.map((tool) => ({ ...tool }))
  : [];

const toolsGrid = document.getElementById("tools-grid");
const selectedToolsCount = document.getElementById("selected-tools-count");
const selectedToolsHelper = document.getElementById("selected-tools-helper");
const selectedToolsValue = document.getElementById("selected-tools-value");
const toolDetailModal = document.getElementById("tool-detail-modal");
const toolDetailModalTitle = document.getElementById("tool-detail-modal-title");
const toolDetailModalDescription = document.getElementById("tool-detail-modal-description");
const toolDetailForm = document.getElementById("tool-detail-form");
const toolDetailIdInput = document.getElementById("tool-detail-id-input");
const toolDetailNameInput = document.getElementById("tool-detail-name-input");
const toolDetailDescriptionInput = document.getElementById("tool-detail-description-input");
const toolDetailFormFeedback = document.getElementById("tool-detail-form-feedback");
const toolDetailSaveButton = document.getElementById("tool-detail-save-button");

let activeToolId = null;
let savingTool = false;

const formatPlaceholderLabel = (index) => {
  const numericLabel = String(index + 1).padStart(2, "0");
  return `Catalog Tool ${numericLabel}`;
};

const getBaseUrl = () => {
  if (window.location.protocol === "file:" || window.location.origin === "null") {
    return "http://localhost:8000";
  }

  if (window.location.origin === "http://localhost:8000" || window.location.origin === "http://127.0.0.1:8000") {
    return "";
  }

  return window.location.origin;
};

const setFormFeedback = (message, tone = "") => {
  toolDetailFormFeedback.textContent = message;
  toolDetailFormFeedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const buildToolCard = (tool, index) => {
  const card = document.createElement("button");
  const cardId = `tool-card-${tool.id}`;

  card.id = cardId;
  card.className = "tool-card";
  card.type = "button";
  card.dataset.toolId = tool.id;
  card.dataset.toolName = tool.name;
  card.setAttribute("aria-haspopup", "dialog");

  const badge = document.createElement("span");
  badge.id = `${cardId}-badge`;
  badge.className = "tool-card__badge";
  badge.textContent = formatPlaceholderLabel(index);

  const title = document.createElement("span");
  title.id = `${cardId}-title`;
  title.className = "tool-card__title";
  title.textContent = tool.name;

  const description = document.createElement("span");
  description.id = `${cardId}-description`;
  description.className = "tool-card__description";
  description.textContent = tool.description;

  card.append(badge, title, description);
  return card;
};

const syncToolSummary = () => {
  const activeTool = toolsCatalog.find((tool) => tool.id === activeToolId);

  selectedToolsCount.textContent = activeTool ? "Modal open ready" : "Modal launch";
  selectedToolsHelper.textContent = activeTool
    ? "Click any other card to switch the modal content."
    : "Select any card below to inspect that tool.";
  selectedToolsValue.textContent = activeTool
    ? activeTool.name
    : "No tool opened yet";
};

const openToolModal = (tool) => {
  activeToolId = tool.id;
  toolDetailModalTitle.textContent = tool.name;
  toolDetailModalDescription.textContent = "Review and edit the selected tool.";
  toolDetailIdInput.value = tool.id;
  toolDetailNameInput.value = tool.name;
  toolDetailDescriptionInput.value = tool.description;
  setFormFeedback("");
  toolDetailModal.classList.add("modal--open");
  toolDetailModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  syncToolSummary();
  toolDetailNameInput.focus();
};

const closeToolModal = () => {
  toolDetailModal.classList.remove("modal--open");
  toolDetailModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
};

const handleToolOpen = (event) => {
  const card = event.currentTarget;
  const { toolId } = card.dataset;
  const tool = toolsCatalog.find((entry) => entry.id === toolId);

  if (!tool) {
    return;
  }

  openToolModal(tool);
};

const bindModalEvents = () => {
  toolDetailModal.addEventListener("click", (event) => {
    const closeTarget = event.target.closest("[data-modal-close]");

    if (closeTarget) {
      closeToolModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && toolDetailModal.classList.contains("modal--open")) {
      closeToolModal();
    }
  });

  toolDetailForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!activeToolId || savingTool) {
      return;
    }

    const nextName = toolDetailNameInput.value.trim();
    const nextDescription = toolDetailDescriptionInput.value.trim();

    if (!nextName || !nextDescription) {
      setFormFeedback("Tool name and description are required.", "error");
      return;
    }

    savingTool = true;
    toolDetailSaveButton.disabled = true;
    toolDetailSaveButton.textContent = "Saving...";
    setFormFeedback("");

    try {
      const response = await fetch(`${getBaseUrl()}/api/v1/tools/${encodeURIComponent(activeToolId)}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: nextName,
          description: nextDescription
        })
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to save tool changes.");
      }

      const toolIndex = toolsCatalog.findIndex((tool) => tool.id === activeToolId);

      if (toolIndex >= 0) {
        toolsCatalog[toolIndex] = payload;
      }

      toolDetailModalTitle.textContent = payload.name;
      selectedToolsValue.textContent = payload.name;
      renderToolCards();
      setFormFeedback("Tool details saved.", "success");
    } catch (error) {
      setFormFeedback(error instanceof Error ? error.message : "Unable to save tool changes.", "error");
    } finally {
      savingTool = false;
      toolDetailSaveButton.disabled = false;
      toolDetailSaveButton.textContent = "Save tool";
    }
  });
};

const renderToolCards = () => {
  const fragment = document.createDocumentFragment();

  toolsCatalog.forEach((tool, index) => {
    const card = buildToolCard(tool, index);
    card.addEventListener("click", handleToolOpen);
    fragment.appendChild(card);
  });

  toolsGrid.replaceChildren(fragment);
};

if (toolsCatalog.length === 0) {
  selectedToolsHelper.textContent = "No registered tools were found in the generated manifest.";
  selectedToolsValue.textContent = "No tools available";
}

bindModalEvents();
renderToolCards();
syncToolSummary();
