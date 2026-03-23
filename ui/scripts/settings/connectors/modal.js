import { connectorElements } from "./dom.js";
import { connectorState, getSelectedConnector } from "./state.js";

export const openModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.classList.add("modal--open");
  connectorElements.modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

export const openDetailModal = () => {
  if (!connectorElements.detailModal || !getSelectedConnector()) {
    return;
  }

  connectorElements.detailModal.classList.add("modal--open");
  connectorElements.detailModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
};

export const closeDetailModal = ({ restoreFocus = true } = {}) => {
  if (!connectorElements.detailModal) {
    return;
  }

  connectorElements.detailModal.classList.remove("modal--open");
  connectorElements.detailModal.setAttribute("aria-hidden", "true");
  if (!document.querySelector(".modal.modal--open")) {
    document.body.classList.remove("modal-open");
  }

  if (restoreFocus && connectorState.detailReturnFocusElement instanceof HTMLElement) {
    connectorState.detailReturnFocusElement.focus();
  }
};

export const closeModal = () => {
  if (!connectorElements.modal) {
    return;
  }

  connectorElements.modal.classList.remove("modal--open");
  connectorElements.modal.setAttribute("aria-hidden", "true");
  if (!document.querySelector(".modal.modal--open")) {
    document.body.classList.remove("modal-open");
  }
};

export const bindModalEvents = () => {
  connectorElements.createButton?.addEventListener("click", openModal);
  document.querySelectorAll("[data-modal-close=\"settings-connectors-modal\"]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });
  document.querySelectorAll("[data-modal-close=\"settings-connectors-detail-modal\"]").forEach((element) => {
    element.addEventListener("click", () => closeDetailModal());
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (connectorElements.detailModal?.classList.contains("modal--open")) {
        closeDetailModal();
      } else if (connectorElements.modal?.classList.contains("modal--open")) {
        closeModal();
      }
    }
  });
};
