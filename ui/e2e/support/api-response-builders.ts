type JsonRecord = Record<string, unknown>;

export type ConnectorRecord = {
  id: string;
  provider: string;
  name: string;
  status: string;
  auth_type: string;
  request_auth_type: string;
  scopes: string[];
  base_url: string;
  owner: string;
  docs_url?: string;
  credential_ref?: string;
  created_at: string;
  updated_at: string;
  last_tested_at: string | null;
  auth_config: JsonRecord;
};

export const INACTIVE_WORKFLOW_CONNECTOR_STATUSES = new Set(["draft", "expired", "revoked"]);

const GITHUB_AVAILABLE_SCOPES = [
  "repo",
  "repo:status",
  "repo_deployment",
  "public_repo",
  "repo:invite",
  "security_events",
  "admin:repo_hook",
  "write:repo_hook",
  "read:repo_hook",
  "admin:org",
  "write:org",
  "read:org",
  "admin:public_key",
  "write:public_key",
  "read:public_key",
  "admin:org_hook",
  "gist",
  "notifications",
  "user",
  "read:user",
  "user:email",
  "user:follow",
  "delete_repo",
  "write:discussion",
  "read:discussion",
  "write:packages",
  "read:packages",
  "delete:packages",
  "workflow",
  "admin:gpg_key",
  "write:gpg_key",
  "read:gpg_key",
  "admin:ssh_signing_key",
  "write:ssh_signing_key",
  "read:ssh_signing_key",
];

const normalizeRequestAuthType = (authType: string) => {
  if (authType === "oauth2") {
    return "bearer";
  }
  if (authType === "api_key") {
    return "header";
  }
  return authType || "none";
};

export function buildAppSettingsResponse(overrides: JsonRecord = {}): JsonRecord {
  const base = {
    general: {
      environment: "live",
      timezone: "local",
    },
    logging: {
      max_stored_entries: 250,
      max_visible_entries: 50,
      max_detail_characters: 4000,
      max_file_size_mb: 5,
    },
    notifications: {
      channel: "email",
      digest: "hourly",
    },
    security: {
      session_timeout_minutes: 60,
      dual_approval_required: false,
      token_rotation_days: 30,
    },
    data: {
      payload_redaction: true,
    },
    automation: {
      default_tool_retries: 2,
    },
    proxy: {
      domain: "",
      http_port: 80,
      https_port: 443,
      enabled: false,
    },
    options: {
      notification_channels: [
        { value: "email", label: "Email" },
        { value: "pager", label: "Pager" },
      ],
      notification_digests: [
        { value: "realtime", label: "Realtime" },
        { value: "hourly", label: "Hourly" },
        { value: "daily", label: "Daily" },
      ],
      // data_export_windows removed
    },
  };
  return mergeDeep(base, overrides);
}

export function buildConnectorCatalog(): JsonRecord[] {
  return [
    {
      id: "google",
      name: "Google",
      description: "Google Workspace OAuth provider.",
      auth_types: ["oauth2"],
      base_url: "https://www.googleapis.com",
      docs_url: "https://developers.google.com",
      default_scopes: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
      ],
      recommended_scopes: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
      ],
    },
    {
      id: "github",
      name: "GitHub",
      description: "GitHub API connector using personal access tokens.",
      auth_types: ["bearer"],
      base_url: "https://api.github.com",
      docs_url: "https://docs.github.com",
      default_scopes: ["repo", "read:user"],
      recommended_scopes: [...GITHUB_AVAILABLE_SCOPES],
    },
    {
      id: "notion",
      name: "Notion",
      description: "Notion API connector.",
      auth_types: ["oauth2", "bearer"],
      base_url: "https://api.notion.com/v1",
      docs_url: "https://developers.notion.com/guides/get-started/authorization",
      default_scopes: ["read", "write"],
      recommended_scopes: ["read", "write"],
    },
    {
      id: "trello",
      name: "Trello",
      description: "Trello OAuth connector.",
      auth_types: ["oauth2"],
      base_url: "https://api.trello.com/1",
      docs_url: "https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/",
      default_scopes: [],
      recommended_scopes: [],
    },
  ];
}

export function buildConnectorProviderMetadata(): JsonRecord[] {
  return [
    {
      id: "google",
      name: "Google",
      onboarding_mode: "oauth",
      oauth_supported: true,
      callback_supported: true,
      refresh_supported: true,
      revoke_supported: true,
      redirect_uri_required: true,
      redirect_uri_readonly: true,
      scopes_locked: true,
      default_redirect_path: "/api/v1/connectors/google/oauth/callback",
      required_fields: ["name", "client_id", "client_secret", "redirect_uri"],
      setup_fields: [
        { key: "name", label: "Integration name", input_type: "text", required: true },
        { key: "client_id", label: "Client ID", input_type: "text", required: true },
        { key: "client_secret", label: "Client secret", input_type: "password", required: true, secret: true },
        { key: "redirect_uri", label: "Redirect URI", input_type: "url", required: true, readonly: true },
      ],
      ui_copy: {
        eyebrow: "Google",
        title: "Google OAuth setup",
        description: "Add your Google OAuth client details, then continue with Google to authorize this workspace.",
        last_checked_empty: "Google connection has not been checked yet.",
      },
      action_labels: {
        save: "Save connector",
        test: "Check connection",
        connect: "Continue with Google",
        reconnect: "Reconnect Google",
        refresh: "Refresh Google token",
        revoke: "Revoke Google connector",
      },
      status_messages: {
        draft: "Add your Google OAuth client details to begin, then continue with Google.",
        pending_oauth: "Complete the Google sign-in flow in the browser to finish setup.",
        connected: "Google OAuth is complete. Use Check connection to verify the saved token before using this integration in workflows or API resources.",
        needs_attention: "Google needs attention. Check the connection or reconnect to repair the saved credentials.",
        expired: "The saved Google token has expired. Refresh it or reconnect Google to continue.",
        revoked: "Google access has been revoked. Reconnect Google to restore this integration.",
      },
    },
    {
      id: "github",
      name: "GitHub",
      onboarding_mode: "credentials",
      oauth_supported: false,
      callback_supported: false,
      refresh_supported: false,
      revoke_supported: true,
      redirect_uri_required: false,
      redirect_uri_readonly: false,
      scopes_locked: false,
      default_redirect_path: null,
      required_fields: ["name", "access_token_input"],
      setup_fields: [
        { key: "name", label: "Integration name", input_type: "text", required: true },
        { key: "access_token_input", label: "Personal access token", input_type: "password", required: true, secret: true },
        { key: "scopes", label: "Scopes", input_type: "multiselect" },
      ],
      ui_copy: {
        eyebrow: "GitHub",
        title: "GitHub PAT setup",
        description: "Add a GitHub personal access token to authorize this workspace.",
        last_checked_empty: "GitHub connection has not been checked yet.",
      },
      action_labels: {
        save: "Save connector",
        test: "Check connection",
        connect: "Save token",
        reconnect: "Replace token",
        refresh: "Rotate token",
        revoke: "Revoke GitHub connector",
      },
      status_messages: {
        draft: "Add a GitHub personal access token to begin.",
        pending_oauth: "GitHub does not use browser OAuth setup in this workspace.",
        connected: "GitHub token is saved. Use Check connection to verify access before using this connector in workflow actions or API resources.",
        needs_attention: "GitHub needs attention. Check the connection or replace the saved token.",
        expired: "The saved GitHub token has expired. Replace it to continue.",
        revoked: "GitHub credentials were cleared. Save a new token to restore this integration.",
      },
    },
    {
      id: "notion",
      name: "Notion",
      onboarding_mode: "oauth",
      oauth_supported: true,
      callback_supported: true,
      refresh_supported: true,
      revoke_supported: true,
      redirect_uri_required: true,
      redirect_uri_readonly: true,
      scopes_locked: false,
      default_redirect_path: "/api/v1/connectors/notion/oauth/callback",
      required_fields: ["name", "client_id", "client_secret", "redirect_uri"],
      setup_fields: [
        { key: "name", label: "Integration name", input_type: "text", required: true },
        { key: "client_id", label: "Client ID", input_type: "text", required: true },
        { key: "client_secret", label: "Client secret", input_type: "password", required: true, secret: true },
        { key: "redirect_uri", label: "Redirect URI", input_type: "url", required: true, readonly: true },
      ],
      ui_copy: {
        eyebrow: "Notion",
        title: "Notion OAuth setup",
        description: "Add your Notion public integration details, then continue with Notion to authorize this workspace.",
        last_checked_empty: "Notion connection has not been checked yet.",
      },
      action_labels: {
        save: "Save connector",
        test: "Check connection",
        connect: "Continue with Notion",
        reconnect: "Reconnect Notion",
        refresh: "Refresh Notion token",
        revoke: "Revoke Notion connector",
      },
      status_messages: {
        draft: "Add your Notion integration details to begin, then continue with Notion.",
        pending_oauth: "Complete the Notion authorization flow in the browser to finish setup.",
        connected: "Notion OAuth is complete. Use Check connection to verify the saved token before using this integration in workflows or API resources.",
        needs_attention: "Notion needs attention. Check the connection or reconnect to repair the saved credentials.",
        expired: "The saved Notion token has expired. Refresh it or reconnect Notion to continue.",
        revoked: "Notion access has been revoked. Reconnect Notion to restore this integration.",
      },
    },
    {
      id: "trello",
      name: "Trello",
      onboarding_mode: "oauth",
      oauth_supported: true,
      callback_supported: true,
      refresh_supported: false,
      revoke_supported: true,
      redirect_uri_required: true,
      redirect_uri_readonly: true,
      scopes_locked: true,
      default_redirect_path: "/api/v1/connectors/trello/oauth/callback",
      required_fields: ["name", "client_id", "redirect_uri"],
      setup_fields: [
        { key: "name", label: "Integration name", input_type: "text", required: true },
        { key: "client_id", label: "Client ID", input_type: "text", required: true },
        { key: "client_secret", label: "Client secret", input_type: "password", secret: true },
        { key: "redirect_uri", label: "Redirect URI", input_type: "url", required: true, readonly: true },
      ],
      ui_copy: {
        eyebrow: "Trello",
        title: "Trello OAuth setup",
        description: "Add your Trello app client details, then continue with Trello to authorize this workspace.",
        last_checked_empty: "Trello connection has not been checked yet.",
      },
      action_labels: {
        save: "Save connector",
        test: "Check connection",
        connect: "Continue with Trello",
        reconnect: "Reconnect Trello",
        refresh: "Refresh Trello token",
        revoke: "Revoke Trello connector",
      },
      status_messages: {
        draft: "Add your Trello app details to begin, then continue with Trello.",
        pending_oauth: "Complete the Trello authorization flow in the browser to finish setup.",
        connected: "Trello OAuth is complete. Use Check connection to verify the saved token before using this integration.",
        needs_attention: "Trello needs attention. Check the connection or reconnect to repair the saved credentials.",
        expired: "The saved Trello token has expired. Reconnect Trello and try again.",
        revoked: "Trello access has been revoked. Reconnect Trello to restore this integration.",
      },
    },
  ];
}

export function buildConnectorSettingsPayload(overrides: JsonRecord = {}): JsonRecord {
  const base = {
    catalog: buildConnectorCatalog(),
    records: [],
    auth_policy: {
      rotation_interval_days: 90,
      reconnect_requires_approval: true,
      credential_visibility: "masked",
    },
    metadata: {
      statuses: [
        { value: "draft", label: "Draft" },
        { value: "pending_oauth", label: "Pending OAuth" },
        { value: "connected", label: "Connected" },
        { value: "needs_attention", label: "Needs attention" },
        { value: "expired", label: "Expired" },
        { value: "revoked", label: "Revoked" },
      ],
      active_storage_statuses: ["connected", "needs_attention", "pending_oauth"],
      auth_policy: {
        rotation_intervals: [
          { value: "30", label: "30 days" },
          { value: "60", label: "60 days" },
          { value: "90", label: "90 days" },
        ],
        credential_visibility_options: [
          { value: "masked", label: "Masked" },
          { value: "admin_only", label: "Admin only" },
        ],
      },
      providers: buildConnectorProviderMetadata(),
    },
  };
  return mergeDeep(base, overrides);
}

export function buildWorkflowBuilderConnectorOptions(records: Array<Record<string, unknown>>): Array<Record<string, unknown>> {
  return records
    .filter((record) => !INACTIVE_WORKFLOW_CONNECTOR_STATUSES.has(String(record.status || "").toLowerCase()))
    .map((record) => ({
      ...record,
      provider_name: record.provider === "google"
        ? "Google"
        : record.provider === "github"
          ? "GitHub"
          : record.provider === "notion"
            ? "Notion"
            : record.provider === "trello"
              ? "Trello"
              : String(record.provider || ""),
      source_path: "connectors",
    }));
}

export function buildConnectorActivityCatalog(overrides: Array<Record<string, unknown>> = []): Array<Record<string, unknown>> {
  if (overrides.length > 0) {
    return deepClone(overrides);
  }
  return [
    {
      provider_id: "google",
      activity_id: "gmail-send-email",
      service: "gmail",
      operation_type: "write",
      label: "Send email",
      description: "Send an email using a saved Google connector.",
      required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
      input_schema: [
        { key: "to", label: "To", type: "string", required: true },
      ],
      output_schema: [
        { key: "message_id", label: "Message ID", type: "string" },
      ],
      execution: { provider: "google", action: "send-email" },
    },
  ];
}

export function buildHttpPresetCatalog(overrides: Array<Record<string, unknown>> = []): Array<Record<string, unknown>> {
  if (overrides.length > 0) {
    return deepClone(overrides);
  }
  return [];
}

export function buildAutomationBuilderMetadataResponse(): JsonRecord {
  return {
    trigger_types: [
      { value: "manual", label: "Manual", description: "Run the automation only when an operator starts it." },
      { value: "schedule", label: "Schedule", description: "Start automatically at a set time each day." },
      { value: "inbound_api", label: "Inbound API", description: "Start when an inbound API endpoint receives an event." },
      { value: "smtp_email", label: "SMTP email", description: "Start when incoming email matches your filters." },
    ],
    step_types: [
      { value: "log", label: "Write", description: "Write a row to a managed database table." },
      { value: "connector_activity", label: "Connector action", description: "Call a provider-aware action backed by a saved connector." },
      { value: "outbound_request", label: "HTTP request", description: "Send a custom or connector-backed HTTP request." },
      { value: "script", label: "Script", description: "Run a stored script from the script library." },
      { value: "tool", label: "Tool", description: "Dispatch a configured tool from the tool catalog." },
      { value: "condition", label: "Condition", description: "Evaluate a guard expression and optionally halt the automation." },
      { value: "llm_chat", label: "LLM chat", description: "Prompt a language model with workflow context." },
    ],
    http_methods: [
      { value: "GET", label: "GET" },
      { value: "POST", label: "POST" },
      { value: "PUT", label: "PUT" },
      { value: "PATCH", label: "PATCH" },
      { value: "DELETE", label: "DELETE" },
    ],
    storage_types: [
      { value: "table", label: "Database table", description: "Write rows into a managed log table." },
      { value: "csv", label: "CSV file", description: "Append rows to a CSV file target." },
      { value: "json", label: "JSON file", description: "Write structured JSON output to a file target." },
      { value: "other", label: "Other", description: "Write to another file-backed target identifier." },
    ],
    log_column_types: [
      { value: "text", label: "Text" },
      { value: "integer", label: "Integer" },
      { value: "real", label: "Real" },
      { value: "boolean", label: "Boolean" },
      { value: "timestamp", label: "Timestamp" },
    ],
  };
}

export function createConnectorRecord(overrides: Partial<ConnectorRecord> & { id: string; provider: string; name: string }): ConnectorRecord {
  const now = new Date("2026-03-23T12:00:00.000Z").toISOString();
  return {
    id: overrides.id,
    provider: overrides.provider,
    name: overrides.name,
    status: overrides.status || "draft",
    auth_type: overrides.auth_type || "oauth2",
    request_auth_type: overrides.request_auth_type || normalizeRequestAuthType(overrides.auth_type || "oauth2"),
    scopes: overrides.scopes || [],
    base_url: overrides.base_url || "",
    owner: overrides.owner || "Workspace",
    docs_url: overrides.docs_url,
    credential_ref: overrides.credential_ref || `connector/${overrides.id}`,
    created_at: overrides.created_at || now,
    updated_at: overrides.updated_at || now,
    last_tested_at: overrides.last_tested_at ?? null,
    auth_config: overrides.auth_config || {},
  };
}

export function createGoogleOAuthConnector(id = "google", overrides: Partial<ConnectorRecord> = {}): ConnectorRecord {
  return createConnectorRecord({
    id,
    provider: "google",
    name: "Google",
    status: "connected",
    auth_type: "oauth2",
    scopes: [
      "https://www.googleapis.com/auth/gmail.readonly",
      "https://www.googleapis.com/auth/calendar.readonly",
    ],
    base_url: "https://www.googleapis.com",
    owner: "Workspace",
    docs_url: "https://developers.google.com",
    auth_config: {
      client_id: "google-client-id",
      client_secret_masked: "goog••••cret",
      access_token_masked: "goog••••oken",
      refresh_token_masked: "goog••••resh",
      redirect_uri: "http://localhost:8000/api/v1/connectors/google/oauth/callback",
      has_refresh_token: true,
      scope_preset: "google",
    },
    ...overrides,
  });
}

export function createGithubOAuthConnector(id = "github-oauth", overrides: Partial<ConnectorRecord> = {}): ConnectorRecord {
  return createConnectorRecord({
    id,
    provider: "github",
    name: "GitHub Primary",
    status: "connected",
    auth_type: "bearer",
    scopes: ["repo", "read:user"],
    base_url: "https://api.github.com",
    owner: "Workspace",
    docs_url: "https://docs.github.com",
    auth_config: {
      access_token_masked: "gith••••oken",
      has_refresh_token: false,
      scope_preset: "github",
    },
    ...overrides,
  });
}

export function createNotionOAuthConnector(id = "notion-oauth", overrides: Partial<ConnectorRecord> = {}): ConnectorRecord {
  return createConnectorRecord({
    id,
    provider: "notion",
    name: "Notion Primary",
    status: "connected",
    auth_type: "oauth2",
    scopes: ["read", "write"],
    base_url: "https://api.notion.com/v1",
    owner: "Workspace",
    docs_url: "https://developers.notion.com/guides/get-started/authorization",
    auth_config: {
      client_id: "notion-client-id",
      client_secret_masked: "noti••••cret",
      access_token_masked: "noti••••oken",
      refresh_token_masked: "noti••••resh",
      redirect_uri: "http://localhost:8000/api/v1/connectors/notion/oauth/callback",
      has_refresh_token: true,
      scope_preset: "notion",
    },
    ...overrides,
  });
}

export function createTrelloConnector(id = "trello-primary", overrides: Partial<ConnectorRecord> = {}): ConnectorRecord {
  return createConnectorRecord({
    id,
    provider: "trello",
    name: "Trello Primary",
    status: "connected",
    auth_type: "oauth2",
    scopes: [],
    base_url: "https://api.trello.com/1",
    owner: "Workspace",
    docs_url: "https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/",
    auth_config: {
      client_id: "trello-client-id",
      client_secret_masked: "trel••••cret",
      access_token_masked: "trel••••oken",
      redirect_uri: "http://localhost:8000/api/v1/connectors/trello/oauth/callback",
      scope_preset: "trello",
      has_refresh_token: false,
    },
    ...overrides,
  });
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function mergeDeep(base: JsonRecord, patch: JsonRecord): JsonRecord {
  const output: JsonRecord = deepClone(base);
  for (const [key, value] of Object.entries(patch)) {
    if (Array.isArray(value)) {
      output[key] = deepClone(value);
      continue;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const current = output[key];
      output[key] = mergeDeep(
        current && typeof current === "object" && !Array.isArray(current)
          ? (current as JsonRecord)
          : {},
        value as JsonRecord,
      );
      continue;
    }
    output[key] = value;
  }
  return output;
}
