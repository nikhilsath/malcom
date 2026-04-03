type JsonRecord = Record<string, unknown>;

export type ConnectorRecord = {
  id: string;
  provider: string;
  name: string;
  status: string;
  auth_type: string;
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
    data: {
      payload_redaction: true,
      export_window_utc: "02:00",
    },
    automation: {
      default_tool_retries: 2,
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
      data_export_windows: [
        { value: "00:00", label: "00:00" },
        { value: "02:00", label: "02:00" },
        { value: "04:00", label: "04:00" },
      ],
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
    },
    {
      id: "github",
      name: "GitHub",
      description: "GitHub API connector.",
      auth_types: ["oauth2", "bearer"],
      base_url: "https://api.github.com",
      docs_url: "https://docs.github.com",
      default_scopes: ["repo"],
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
    },
  };
  return mergeDeep(base, overrides);
}

export function buildWorkflowBuilderConnectorOptions(records: Array<Record<string, unknown>>): Array<Record<string, unknown>> {
  return records
    .filter((record) => !INACTIVE_WORKFLOW_CONNECTOR_STATUSES.has(String(record.status || "").toLowerCase()))
    .map((record) => ({
      ...record,
      provider_name: record.provider === "google" ? "Google" : record.provider === "github" ? "GitHub" : String(record.provider || ""),
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
