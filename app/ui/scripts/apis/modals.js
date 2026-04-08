import {
  getCreateOpenButton,
  getCreateTypeModal,
  hasCreateModalElements
} from "./dom.js";
import { apiResourceTypes, createTypeModalFallbackMarkup } from "./config.js";

export const createApiModalController = ({
  elements,
  state,
  render,
  createTypeModalMarkup,
  closeApiTooltips
}) => {
  const syncModalBodyState = () => {
    document.body.classList.toggle(
      "modal-open",
      Boolean(document.querySelector(".modal.modal--open"))
    );
  };

  const syncCreateTypeTriggerState = (isExpanded) => {
    const createOpenButton = getCreateOpenButton();

    if (createOpenButton) {
      createOpenButton.setAttribute("aria-expanded", String(isExpanded));
    }
  };

  const ensureCreateTypeModal = () => {
    const createOpenButton = getCreateOpenButton();

    if (!createOpenButton) {
      return null;
    }

    let modal = getCreateTypeModal();

    if (modal) {
      return modal;
    }

    const modalHost = document.createElement("div");
    modalHost.id = "apis-create-type-modal-host";
    modalHost.innerHTML = createTypeModalMarkup.trim() || createTypeModalFallbackMarkup.trim();
    document.body.appendChild(modalHost);
    modal = getCreateTypeModal();

    if (!modal) {
      modalHost.innerHTML = createTypeModalFallbackMarkup.trim();
      modal = getCreateTypeModal();
    }

    return modal;
  };

  const closeCreateTypeModal = ({ restoreFocus = true } = {}) => {
    const modal = getCreateTypeModal();

    if (!modal) {
      return;
    }

    modal.classList.remove("modal--open");
    modal.setAttribute("aria-hidden", "true");
    syncCreateTypeTriggerState(false);
    syncModalBodyState();

    if (restoreFocus && state.createTypeReturnFocusElement instanceof HTMLElement) {
      state.createTypeReturnFocusElement.focus();
    }
  };

  const setCreateModalType = (selectedType) => {
    const nextType = apiResourceTypes[selectedType] ? selectedType : "incoming";
    const typeInput = document.getElementById("create-api-type-input");

    state.createModalType = nextType;

    if (typeInput) {
      typeInput.value = nextType;
    }

    render.syncCreateModalType(nextType);
  };

  const openCreateTypeModal = () => {
    const modal = ensureCreateTypeModal();

    if (!modal) {
      openCreateModal("incoming");
      return;
    }

    state.createTypeReturnFocusElement = getCreateOpenButton();
    modal.classList.add("modal--open");
    modal.setAttribute("aria-hidden", "false");
    syncCreateTypeTriggerState(true);
    syncModalBodyState();
    const firstOption = modal.querySelector(".api-popup-option, .api-create-type-modal-option");

    if (firstOption instanceof HTMLElement) {
      firstOption.focus();
    }
  };

  const openCreateModal = (selectedType = state.createModalType) => {
    if (!elements.createModal) {
      return;
    }

    closeApiTooltips();
    setCreateModalType(selectedType);
    document.getElementById("create-api-form")?.dispatchEvent(new CustomEvent("create-modal-open"));
    elements.createModal.classList.add("modal--open");
    elements.createModal.setAttribute("aria-hidden", "false");
    syncModalBodyState();
  };

  const closeCreateModal = () => {
    if (!elements.createModal) {
      return;
    }

    closeApiTooltips();
    elements.createModal.classList.remove("modal--open");
    elements.createModal.setAttribute("aria-hidden", "true");
    syncModalBodyState();

    const createOpenButton = state.createTypeReturnFocusElement || getCreateOpenButton();

    if (createOpenButton) {
      createOpenButton.focus();
    }
  };

  const openOutgoingEditModal = () => {
    if (!elements.outgoingEditModal) {
      return;
    }

    closeApiTooltips();
    elements.outgoingEditModal.classList.add("modal--open");
    elements.outgoingEditModal.setAttribute("aria-hidden", "false");
    syncModalBodyState();
  };

  const closeOutgoingEditModal = () => {
    if (!elements.outgoingEditModal) {
      return;
    }

    closeApiTooltips();
    elements.outgoingEditModal.classList.remove("modal--open");
    elements.outgoingEditModal.setAttribute("aria-hidden", "true");
    syncModalBodyState();

    if (state.outgoingEditReturnFocusElement instanceof HTMLElement) {
      state.outgoingEditReturnFocusElement.focus();
    }
  };

  const openDetailModalView = () => {
    if (!elements.detailModal) {
      return;
    }

    elements.detailModal.classList.add("modal--open");
    elements.detailModal.setAttribute("aria-hidden", "false");
    syncModalBodyState();
  };

  const closeDetailModalView = () => {
    if (!elements.detailModal) {
      return;
    }

    elements.detailModal.classList.remove("modal--open");
    elements.detailModal.setAttribute("aria-hidden", "true");
    syncModalBodyState();

    const returnFocusElement = state.detailReturnFocusElement instanceof HTMLElement
      ? document.getElementById(state.detailReturnFocusElement.id) || state.detailReturnFocusElement
      : null;

    if (returnFocusElement instanceof HTMLElement) {
      returnFocusElement.focus();
    }
  };

  const bindModalEvents = (actions) => {
    if (hasCreateModalElements(elements)) {
      document.addEventListener("click", (event) => {
        const openTarget = event.target.closest("#apis-create-button");

        if (openTarget) {
          event.preventDefault();

          if (getCreateTypeModal()?.classList.contains("modal--open")) {
            closeCreateTypeModal();
            return;
          }

          openCreateTypeModal();
          return;
        }

        const directCreateTarget = event.target.closest("[data-create-api-type]");

        if (directCreateTarget instanceof HTMLElement) {
          const selectedType = directCreateTarget.dataset.createApiType || "incoming";
          state.createFromConnector = directCreateTarget.dataset.createFromConnector === "true";
          state.createTypeReturnFocusElement = directCreateTarget;
          closeCreateTypeModal({ restoreFocus: false });
          openCreateModal(selectedType);
          return;
        }

        const typeTarget = event.target.closest(".api-popup-option, .api-create-type-modal-option");

        if (typeTarget instanceof HTMLElement) {
          const selectedType = typeTarget.dataset.apiType || "incoming";
          state.createFromConnector = typeTarget.dataset.createFromConnector === "true";
          state.createTypeReturnFocusElement = getCreateOpenButton();
          closeCreateTypeModal({ restoreFocus: false });

          openCreateModal(selectedType);
        }
      });

      ensureCreateTypeModal()?.addEventListener("click", (event) => {
        const closeTarget = event.target.closest("[data-modal-close]");

        if (closeTarget) {
          closeCreateTypeModal();
        }
      });

      elements.createModal.addEventListener("click", (event) => {
        if (event.target.closest("[data-modal-close]")) {
          closeCreateModal();
        }
      });

      elements.outgoingEditModal?.addEventListener("click", (event) => {
        if (event.target.closest("[data-modal-close]")) {
          closeOutgoingEditModal();
        }
      });
    }

    if (elements.detailModal) {
      elements.detailModal.addEventListener("click", (event) => {
        if (event.target.closest("[data-modal-close]")) {
          closeDetailModalView();
        }
      });
    }

    if (!hasCreateModalElements(elements) && !elements.detailModal && !elements.outgoingEditModal) {
      return;
    }

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }

      if (elements.detailModal?.classList.contains("modal--open")) {
        closeDetailModalView();
        return;
      }

      if (elements.createModal?.classList.contains("modal--open")) {
        closeCreateModal();
        return;
      }

      if (elements.outgoingEditModal?.classList.contains("modal--open")) {
        closeOutgoingEditModal();
        return;
      }

      if (getCreateTypeModal()?.classList.contains("modal--open")) {
        closeCreateTypeModal();
      }
    });
  };

  return {
    syncModalBodyState,
    syncCreateTypeTriggerState,
    ensureCreateTypeModal,
    openCreateTypeModal,
    closeCreateTypeModal,
    setCreateModalType,
    openCreateModal,
    closeCreateModal,
    openOutgoingEditModal,
    closeOutgoingEditModal,
    openDetailModalView,
    closeDetailModalView,
    bindModalEvents
  };
};
