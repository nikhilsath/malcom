import createApiModalMarkup from "../../modals/create-api-modal.html?raw";
import createApiTypeModalMarkup from "../../modals/create-api-type-modal.html?raw";
import outgoingApiEditModalMarkup from "../../modals/outgoing-api-edit-modal.html?raw";

import { createApiClient, emitApiLog, loadConnectorEntries } from "./client.js";
import { apiResourceTypes } from "./config.js";
import { createApiElements } from "./dom.js";
import { createApiFormBindings } from "./forms.js";
import { createApiModalController } from "./modals.js";
import { createApiPageController } from "./page.js";
import { createApiRenderer } from "./render.js";
import { createApiState } from "./state.js";

export const initApisPage = async () => {
  const elements = createApiElements();
  const state = createApiState();
  const client = createApiClient();
  const actions = {};

  const render = createApiRenderer({
    elements,
    state,
    actions: {
      loadApiDetail: (...args) => actions.loadApiDetail(...args),
      loadOutgoingEditDetail: (...args) => actions.loadOutgoingEditDetail(...args),
      resolvePageHref: (...args) => actions.resolvePageHref(...args)
    }
  });

  const forms = createApiFormBindings({
    elements,
    state,
    client,
    render,
    modals: null,
    actions,
    emitApiLog
  });

  const modals = createApiModalController({
    elements,
    state,
    render: {
      syncCreateModalType: (...args) => forms.syncCreateModalType(...args)
    },
    createTypeModalMarkup: createApiTypeModalMarkup,
    closeApiTooltips: () => {}
  });

  const page = createApiPageController({
    elements,
    state,
    client,
    render,
    modals,
    forms,
    emitApiLog,
    loadConnectorEntries,
    createApiModalMarkup,
    outgoingApiEditModalMarkup
  });

  Object.assign(actions, page.actions);
  forms.modals = modals;

  if (!apiResourceTypes.incoming) {
    throw new Error("API resource types failed to initialize.");
  }

  await page.initApiPage();
};
