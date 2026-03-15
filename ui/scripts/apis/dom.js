export const createApiElements = () => ({
  createModal: document.getElementById("apis-create-modal"),
  createModalContent: document.getElementById("apis-create-modal-content"),
  detailModal: document.getElementById("api-detail-modal"),
  automationPlaceholderModal: document.getElementById("apis-automation-placeholder-modal"),
  automationAlert: document.getElementById("api-automation-alert"),
  alert: document.getElementById("api-system-alert"),
  tableBody: document.getElementById("api-directory-body"),
  tableShell: document.getElementById("api-table-shell"),
  directoryEmpty: document.getElementById("api-directory-empty"),
  detailEmpty: document.getElementById("api-detail-empty"),
  detailContent: document.getElementById("api-detail-content"),
  detailTitle: document.getElementById("api-detail-title"),
  detailDescription: document.getElementById("api-detail-description"),
  detailMetadata: document.getElementById("api-detail-metadata"),
  rotateSecretButton: document.getElementById("api-detail-rotate-secret-button"),
  toggleStatusButton: document.getElementById("api-detail-toggle-status-button"),
  secretPanel: document.getElementById("api-secret-panel"),
  secretValue: document.getElementById("api-secret-value"),
  secretCurl: document.getElementById("api-secret-curl"),
  logsSummaryTotalValue: document.getElementById("api-logs-summary-total-value"),
  logsSummaryAcceptedValue: document.getElementById("api-logs-summary-accepted-value"),
  logsSummaryErrorsValue: document.getElementById("api-logs-summary-errors-value"),
  logsSearchInput: document.getElementById("api-logs-search-input"),
  logsStatusFilter: document.getElementById("api-logs-status-filter"),
  logsSourceFilter: document.getElementById("api-logs-source-filter"),
  logsSortInput: document.getElementById("api-logs-sort-input"),
  logsResetButton: document.getElementById("api-logs-reset-button"),
  logsEmpty: document.getElementById("api-logs-empty"),
  logList: document.getElementById("api-log-list"),
  outgoingList: document.getElementById("apis-outgoing-list"),
  outgoingListEmpty: document.getElementById("apis-outgoing-list-empty"),
  outgoingEditModal: document.getElementById("outgoing-api-edit-modal"),
  outgoingEditModalContent: document.getElementById("outgoing-api-edit-modal-content"),
  webhooksList: document.getElementById("apis-webhooks-list"),
  webhooksListEmpty: document.getElementById("apis-webhooks-list-empty"),
  overviewAlert: document.getElementById("api-system-alert"),
  overviewTotalCount: document.getElementById("apis-overview-total-count"),
  overviewHelper: document.getElementById("apis-overview-helper"),
  overviewScheduledActiveCount: document.getElementById("apis-overview-summary-scheduled-active-value"),
  overviewCallsPerHour: document.getElementById("apis-overview-summary-calls-hour-value"),
  overviewCallsPerDay: document.getElementById("apis-overview-summary-calls-day-value"),
  overviewMonitoredWebhooksCount: document.getElementById("apis-overview-summary-monitored-webhooks-value"),
  overviewIncomingList: document.getElementById("apis-overview-incoming-list"),
  overviewIncomingEmpty: document.getElementById("apis-overview-incoming-empty"),
  overviewOutgoingList: document.getElementById("apis-overview-outgoing-list"),
  overviewOutgoingEmpty: document.getElementById("apis-overview-outgoing-empty"),
  overviewWebhooksList: document.getElementById("apis-overview-webhooks-list"),
  overviewWebhooksEmpty: document.getElementById("apis-overview-webhooks-empty")
});

export const getCreateOpenButton = () => document.getElementById("apis-create-button");

export const getCreateTypeModal = () => document.getElementById("apis-create-type-modal");

export const hasCreateModalElements = (elements) => Boolean(
  elements.createModal && elements.createModalContent
);

export const hasAutomationPlaceholderElements = (elements) => Boolean(
  elements.automationPlaceholderModal
);

export const isAutomationPage = (elements) => Boolean(elements.automationAlert);

export const hasOverviewElements = (elements) => Boolean(
  elements.alert
  && elements.tableBody
  && elements.tableShell
  && elements.directoryEmpty
  && elements.detailEmpty
  && elements.detailContent
  && elements.detailTitle
  && elements.detailDescription
  && elements.detailMetadata
  && elements.rotateSecretButton
  && elements.toggleStatusButton
  && elements.secretPanel
  && elements.secretValue
  && elements.secretCurl
  && elements.logsSummaryTotalValue
  && elements.logsSummaryAcceptedValue
  && elements.logsSummaryErrorsValue
  && elements.logsSearchInput
  && elements.logsStatusFilter
  && elements.logsSourceFilter
  && elements.logsSortInput
  && elements.logsResetButton
  && elements.logsEmpty
  && elements.logList
);

export const hasOutgoingRegistryElements = (elements) => Boolean(
  elements.outgoingList && elements.outgoingListEmpty
);

export const hasOutgoingEditModalElements = (elements) => Boolean(
  elements.outgoingEditModal && elements.outgoingEditModalContent
);

export const hasWebhookRegistryElements = (elements) => Boolean(
  elements.webhooksList && elements.webhooksListEmpty
);

export const hasOverviewLandingElements = (elements) => Boolean(
  elements.overviewTotalCount
  && elements.overviewHelper
  && elements.overviewScheduledActiveCount
  && elements.overviewCallsPerHour
  && elements.overviewCallsPerDay
  && elements.overviewMonitoredWebhooksCount
);
