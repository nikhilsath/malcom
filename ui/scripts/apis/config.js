export const modalFallbackMarkup = `
  <div class="modal__panel" id="create-api-modal-panel">
    <div class="modal__header" id="create-api-modal-header">
      <div class="modal__header-copy" id="create-api-modal-header-copy">
        <p class="modal__eyebrow" id="create-api-modal-eyebrow">Create</p>
        <div class="api-panel-title-row" id="create-api-modal-title-row">
          <h3 class="modal__title" id="apis-create-modal-title">Create API</h3>
          <button type="button" id="create-api-modal-description-tooltip-toggle" class="api-tooltip-toggle api-tooltip-toggle--compact" aria-label="Explain this API type" aria-expanded="false" aria-controls="create-api-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="button button--secondary modal__close-button" id="create-api-modal-close" aria-label="Close create API modal" data-modal-close="apis-create-modal">Close</button>
    </div>
    <div id="create-api-modal-description" class="api-tooltip-content api-tooltip-content--section" role="tooltip" hidden>The shared create form could not be loaded.</div>
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
            <button type="button" class="button button--secondary modal__close-button" id="apis-create-type-modal-close" aria-label="Close create API type modal" data-modal-close="apis-create-type-modal">Close</button>
          </div>
          <div class="modal__body modal__body--form api-create-type-modal-body" id="apis-create-type-modal-body">
            <div id="apis-create-type-modal-options" class="api-create-type-modal-options">
              <button type="button" id="apis-create-type-option-incoming" class="api-create-type-modal-option" data-api-type="incoming">
                <span id="apis-create-type-option-incoming-title" class="api-create-type-modal-option__title">Incoming</span>
                <span id="apis-create-type-option-incoming-description" class="api-create-type-modal-option__description">Provision an authenticated inbound endpoint for JSON callbacks.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-scheduled" class="api-create-type-modal-option" data-api-type="outgoing_scheduled">
                <span id="apis-create-type-option-outgoing-scheduled-title" class="api-create-type-modal-option__title">Outgoing scheduled</span>
                <span id="apis-create-type-option-outgoing-scheduled-description" class="api-create-type-modal-option__description">Send a payload on a defined daily schedule.</span>
              </button>
              <button type="button" id="apis-create-type-option-outgoing-continuous" class="api-create-type-modal-option" data-api-type="outgoing_continuous">
                <span id="apis-create-type-option-outgoing-continuous-title" class="api-create-type-modal-option__title">Outgoing continuous</span>
                <span id="apis-create-type-option-outgoing-continuous-description" class="api-create-type-modal-option__description">Keep an outbound delivery ready on a repeating interval.</span>
              </button>
              <button type="button" id="apis-create-type-option-webhook" class="api-create-type-modal-option" data-api-type="webhook">
                <span id="apis-create-type-option-webhook-title" class="api-create-type-modal-option__title">Webhook</span>
                <span id="apis-create-type-option-webhook-description" class="api-create-type-modal-option__description">Store publisher verification and signing details.</span>
              </button>
              <button type="button" id="apis-create-type-option-automation" class="api-create-type-modal-option" data-api-type="automation">
                <span id="apis-create-type-option-automation-title" class="api-create-type-modal-option__title">Automation</span>
                <span id="apis-create-type-option-automation-description" class="api-create-type-modal-option__description">Open the automation workspace and start a new live workflow.</span>
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
          <button type="button" id="outgoing-api-edit-modal-tooltip-toggle" class="api-tooltip-toggle api-tooltip-toggle--compact" aria-label="Explain outgoing API editing" aria-expanded="false" aria-controls="outgoing-api-edit-modal-description">i</button>
        </div>
      </div>
      <button type="button" class="button button--secondary modal__close-button" id="outgoing-api-edit-modal-close" aria-label="Close outgoing API modal" data-modal-close="outgoing-api-edit-modal">Close</button>
    </div>
    <div id="outgoing-api-edit-modal-description" class="api-tooltip-content api-tooltip-content--section" role="tooltip" hidden>The outgoing edit form could not be loaded.</div>
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
