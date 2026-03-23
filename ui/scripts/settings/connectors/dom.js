import { createElementMap } from "../../format-utils.js";

export const connectorElements = createElementMap({
  feedback: "settings-connectors-feedback",
  createButton: "settings-connectors-create-button",
  tableBody: "settings-connectors-table-body",
  tableShell: "settings-connectors-table-shell",
  empty: "settings-connectors-empty",
  summaryConnected: "settings-connectors-summary-connected-value",
  summaryOauth: "settings-connectors-summary-oauth-value",
  summaryAttention: "settings-connectors-summary-attention-value",
  form: "settings-connectors-form",
  policyForm: "settings-connectors-policy-form",
  nameInput: "settings-connectors-name-input",
  providerInput: "settings-connectors-provider-input",
  statusInput: "settings-connectors-status-input",
  authTypeInput: "settings-connectors-auth-type-input",
  ownerInput: "settings-connectors-owner-input",
  baseUrlInput: "settings-connectors-base-url-input",
  scopesInput: "settings-connectors-scopes-input",
  clientIdInput: "settings-connectors-client-id-input",
  clientSecretInput: "settings-connectors-client-secret-input",
  redirectUriInput: "settings-connectors-redirect-uri-input",
  usernameInput: "settings-connectors-username-input",
  passwordInput: "settings-connectors-password-input",
  accessTokenInput: "settings-connectors-access-token-input",
  refreshTokenInput: "settings-connectors-refresh-token-input",
  apiKeyInput: "settings-connectors-api-key-input",
  headerNameInput: "settings-connectors-header-name-input",
  headerValueInput: "settings-connectors-header-value-input",
  credentialSummary: "settings-connectors-credential-summary-value",
  testButton: "settings-connectors-test-button",
  saveButton: "settings-connectors-save-button",
  oauthStartButton: "settings-connectors-oauth-start-button",
  refreshButton: "settings-connectors-refresh-button",
  revokeButton: "settings-connectors-revoke-button",
  removeButton: "settings-connectors-remove-button",
  policyRotationInput: "settings-connectors-policy-rotation-input",
  policyApprovalInput: "settings-connectors-policy-approval-input",
  policyVisibilityInput: "settings-connectors-policy-visibility-input",
  modal: "settings-connectors-modal",
  modalProviderGrid: "settings-connectors-modal-provider-grid",
  detailModal: "settings-connectors-detail-modal",
  detailEyebrow: "settings-connectors-detail-eyebrow",
  detailTitle: "settings-connectors-detail-title",
  detailDescription: "settings-connectors-detail-description",
  detailDescriptionBadge: "settings-connectors-detail-description-badge"
});

export const GOOGLE_RECOMMENDED_SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/calendar.readonly",
  "https://www.googleapis.com/auth/spreadsheets.readonly"
];

export const OAUTH_QUERY_KEYS = ["oauth_status", "oauth_message", "connector_id"];
