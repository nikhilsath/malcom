export const modalFallbackMarkup = `
  <div class="modal__panel" id="create-api-modal-panel">
    <div class="modal__header" id="create-api-modal-header">
      <div class="modal__header-copy" id="create-api-modal-header-copy">
        <p class="modal__eyebrow" id="create-api-modal-eyebrow">Create</p>
        <div class="api-panel-title-row" id="create-api-modal-title-row">
          <h3 class="modal__title" id="apis-create-modal-title">Create API</h3>
          <button type="button" id="create-api-modal-description-badge" class="info-badge" aria-label="More information" aria-expanded="false" aria-controls="create-api-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="modal__close-icon-button" id="create-api-modal-close" aria-label="Close create API modal" data-modal-close="apis-create-modal">×</button>
    </div>
    <p id="create-api-modal-description" class="section-header__description modal__description" hidden>The shared create form could not be loaded.</p>
    <div class="modal__body" id="create-api-modal-body">
      <p id="create-api-modal-fallback-copy" class="modal__description">Refresh and try again.</p>
    </div>
  </div>
`;

export const createTypeModalFallbackMarkup = `
  <div
    id="apis-create-type-modal"
    class="modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="apis-create-type-modal-title"
    aria-describedby="apis-create-type-modal-description"
    aria-hidden="true"
  >
    <div class="modal__backdrop" id="apis-create-type-modal-backdrop" data-modal-close="apis-create-type-modal"></div>
    <div class="modal__dialog" id="apis-create-type-modal-dialog">
      <div class="modal__content" id="apis-create-type-modal-content">
        <div class="modal__panel api-create-type-modal-panel" id="apis-create-type-modal-panel">
          <div class="modal__header" id="apis-create-type-modal-header">
            <div class="modal__header-copy" id="apis-create-type-modal-header-copy">
              <p class="modal__eyebrow" id="apis-create-type-modal-eyebrow">Create</p>
              <h3 class="modal__title" id="apis-create-type-modal-title">Choose an API surface</h3>
              <p class="modal__description" id="apis-create-type-modal-description">Choose the API type to continue.</p>
            </div>
            <button type="button" class="modal__close-icon-button" id="apis-create-type-modal-close" aria-label="Close create API type modal" data-modal-close="apis-create-type-modal">×</button>
          </div>
          <div class="modal__body modal__body--form api-create-type-modal-body" id="apis-create-type-modal-body">
            <div id="apis-create-type-modal-options" class="api-popup-option-grid">
              <button type="button" id="apis-create-type-option-incoming" class="api-popup-option" data-api-type="incoming">
                <span id="apis-create-type-option-incoming-title" class="api-popup-option__title">Incoming</span>
                <span id="apis-create-type-option-incoming-description" class="api-popup-option__description">Provision an authenticated inbound endpoint for JSON callbacks.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-scheduled" class="api-popup-option" data-api-type="outgoing_scheduled">
                <span id="apis-create-type-option-outgoing-scheduled-title" class="api-popup-option__title">Outgoing scheduled</span>
                <span id="apis-create-type-option-outgoing-scheduled-description" class="api-popup-option__description">Send a payload on a defined daily schedule.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-continuous" class="api-popup-option" data-api-type="outgoing_continuous">
                <span id="apis-create-type-option-outgoing-continuous-title" class="api-popup-option__title">Outgoing continuous</span>
                <span id="apis-create-type-option-outgoing-continuous-description" class="api-popup-option__description">Keep an outbound delivery ready on a repeating interval.</span>
              </button>
              <button type="button" id="apis-create-type-option-from-connector" class="api-popup-option" data-api-type="outgoing_scheduled" data-create-from-connector="true">
                <span id="apis-create-type-option-from-connector-title" class="api-popup-option__title">Create from connector</span>
                <span id="apis-create-type-option-from-connector-description" class="api-popup-option__description">Start from a saved connector and prefill auth defaults.</span>
              </button>
              <button type="button" id="apis-create-type-option-webhook" class="api-popup-option" data-api-type="webhook">
                <span id="apis-create-type-option-webhook-title" class="api-popup-option__title">Webhook</span>
                <span id="apis-create-type-option-webhook-description" class="api-popup-option__description">Store publisher verification and signing details.</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`;

export const outgoingEditModalFallbackMarkup = `
  <div class="modal__panel" id="outgoing-api-edit-modal-panel">
    <div class="modal__header" id="outgoing-api-edit-modal-header">
      <div class="modal__header-copy" id="outgoing-api-edit-modal-header-copy">
        <p class="modal__eyebrow" id="outgoing-api-edit-modal-eyebrow">Outgoing</p>
        <div class="api-panel-title-row" id="outgoing-api-edit-modal-title-row">
          <h3 class="modal__title" id="outgoing-api-edit-modal-title">Edit outgoing API</h3>
          <button type="button" id="outgoing-api-edit-modal-description-badge" class="info-badge" aria-label="More information" aria-expanded="false" aria-controls="outgoing-api-edit-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="modal__close-icon-button" id="outgoing-api-edit-modal-close" aria-label="Close outgoing API modal" data-modal-close="outgoing-api-edit-modal">×</button>
    </div>
    <p id="outgoing-api-edit-modal-description" class="section-header__description modal__description" hidden>The outgoing edit form could not be loaded.</p>
    <div class="modal__body" id="outgoing-api-edit-modal-body">
      <p id="outgoing-api-edit-modal-fallback-copy" class="modal__description">Refresh and try again.</p>
    </div>
  </div>
`;

export const apiResourceTypes = {
  incoming: {
    title: "New Incoming API",
    description: "Create an inbound endpoint.",
    authLabel: "Bearer secret",
    enabledCopy: "Accept requests immediately",
    submitLabel: "Create incoming API",
    successMessage: "Incoming API created.",
    alertMessage: "Incoming API created. Store the generated bearer token now; it will not be shown again.",
    redirectPath: "/ui/apis/incoming.html"
  },
  outgoing_scheduled: {
    title: "New Outgoing Scheduled API",
    description: "Set destination, auth, schedule, and payload.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Enable this scheduled delivery on create",
    submitLabel: "Create scheduled API",
    successMessage: "Scheduled outgoing API created.",
    alertMessage: "Scheduled outgoing API created.",
    redirectPath: "/ui/apis/outgoing.html"
  },
  outgoing_continuous: {
    title: "New Outgoing Continuous API",
    description: "Set destination, auth, payload, and repeat interval.",
    authLabel: "Managed by destination configuration",
    enabledCopy: "Enable this outbound delivery on create",
    submitLabel: "Create continuous API",
    successMessage: "Continuous outgoing API created.",
    alertMessage: "Continuous outgoing API created.",
    redirectPath: "/ui/apis/outgoing.html"
  },
  webhook: {
    title: "New Webhook",
    description: "Register callback and verification settings.",
    authLabel: "Defined per webhook publisher",
    enabledCopy: "Enable the webhook immediately",
    submitLabel: "Create webhook",
    successMessage: "Webhook created.",
    alertMessage: "Webhook created.",
    redirectPath: "/ui/apis/webhooks.html"
  }
};
