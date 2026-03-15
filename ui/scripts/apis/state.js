export const createApiState = () => ({
  entries: [],
  selectedApiId: null,
  detailReturnFocusElement: null,
  lastSecretByApiId: {},
  outgoingEntries: [],
  webhookEntries: [],
  connectorEntries: [],
  createModalType: "incoming",
  createFromConnector: false,
  createTypeReturnFocusElement: null,
  outgoingEditReturnFocusElement: null,
  selectedOutgoingApiId: null,
  detailEvents: [],
  detailLogFilters: {
    search: "",
    status: "all",
    source: "all",
    sort: "newest"
  }
});
