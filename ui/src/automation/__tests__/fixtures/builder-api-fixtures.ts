export type SettingsOption = {
  value: string;
  label: string;
  description?: string;
};

export type WorkflowBuilderConnectorOption = {
  id: string;
  provider: string;
  provider_name?: string;
  name: string;
  status?: string;
  auth_type?: string;
  scopes?: string[];
  owner?: string;
  base_url?: string;
  source_path?: string;
};

export type ConnectorActivityRecord = {
  provider_id: string;
  activity_id: string;
  service: string;
  operation_type: string;
  label: string;
  description: string;
  required_scopes: string[];
  input_schema: Array<Record<string, unknown>>;
  output_schema: Array<Record<string, unknown>>;
  execution: Record<string, unknown>;
};

export type HttpPresetRecord = {
  preset_id: string;
  provider_id: string;
  service: string;
  operation: string;
  label: string;
  description: string;
  http_method: string;
  endpoint_path_template: string;
  payload_template: string;
  query_params: Record<string, unknown>;
  required_scopes: string[];
  input_schema: Array<Record<string, unknown>>;
};

export function buildAppSettingsFixture(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const base = {
    general: { environment: "live", timezone: "local" },
    logging: {
      max_stored_entries: 250,
      max_visible_entries: 50,
      max_detail_characters: 4000,
      max_file_size_mb: 5,
    },
    notifications: { channel: "email", digest: "hourly" },
    data: { payload_redaction: true, export_window_utc: "02:00" },
    automation: { default_tool_retries: 2 },
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

export function buildWorkflowBuilderConnectorOptions(
  overrides: WorkflowBuilderConnectorOption[] = [],
): WorkflowBuilderConnectorOption[] {
  if (overrides.length > 0) {
    return deepClone(overrides);
  }
  return [
    {
      id: "connector-main",
      provider: "http",
      provider_name: "HTTP",
      name: "Main webhook",
      auth_type: "none",
      base_url: "https://example.com",
      source_path: "connectors",
    },
  ];
}

export function buildConnectorActivityCatalog(
  overrides: ConnectorActivityRecord[] = [],
): ConnectorActivityRecord[] {
  if (overrides.length > 0) {
    return deepClone(overrides);
  }
  return [
    {
      provider_id: "google",
      activity_id: "gmail_send_email",
      service: "gmail",
      operation_type: "write",
      label: "Send email",
      description: "Send Gmail message.",
      required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
      input_schema: [
        { key: "recipients", label: "Recipients", type: "string", required: true },
        { key: "subject", label: "Subject", type: "string", required: true },
        { key: "body", label: "Body", type: "textarea", required: true },
      ],
      output_schema: [{ key: "message_id", label: "Message ID", type: "string" }],
      execution: {},
    },
    {
      provider_id: "google",
      activity_id: "sheets_update_range",
      service: "sheets",
      operation_type: "write",
      label: "Update range",
      description: "Write values into a sheet.",
      required_scopes: ["https://www.googleapis.com/auth/spreadsheets"],
      input_schema: [
        { key: "spreadsheet_id", label: "Spreadsheet ID", type: "string", required: true },
        { key: "range", label: "A1 range", type: "string", required: true },
        { key: "values_payload", label: "Values payload", type: "json", required: true },
      ],
      output_schema: [{ key: "updated_cells", label: "Updated cells", type: "integer" }],
      execution: {},
    },
  ];
}

export function buildHttpPresetCatalog(overrides: HttpPresetRecord[] = []): HttpPresetRecord[] {
  if (overrides.length > 0) {
    return deepClone(overrides);
  }
  return [];
}

export function buildAutomationBuilderMetadataFixture(): Record<string, unknown> {
  return {
    trigger_types: [
      { value: "manual", label: "Manual", description: "Run the automation only when an operator starts it." },
      { value: "schedule", label: "Schedule", description: "Start automatically at a set time each day." },
      { value: "inbound_api", label: "Inbound API", description: "Start when an inbound API endpoint receives an event." },
      { value: "smtp_email", label: "SMTP email", description: "Start when incoming email matches your filters." },
    ],
    step_types: [
      { value: "log", label: "Write", description: "Write a row to a managed database table." },
      { value: "connector_activity", label: "Connector action", description: "Call a provider-aware connector action." },
      { value: "outbound_request", label: "HTTP request", description: "Send a custom HTTP request." },
      { value: "script", label: "Script", description: "Run a stored script." },
      { value: "tool", label: "Tool", description: "Dispatch a configured tool." },
      { value: "condition", label: "Condition", description: "Evaluate a guard expression." },
      { value: "llm_chat", label: "LLM chat", description: "Prompt a language model." },
    ],
    http_methods: [
      { value: "GET", label: "GET" },
      { value: "POST", label: "POST" },
      { value: "PUT", label: "PUT" },
      { value: "PATCH", label: "PATCH" },
      { value: "DELETE", label: "DELETE" },
    ],
    storage_types: [
      { value: "table", label: "Database table" },
      { value: "csv", label: "CSV file" },
      { value: "json", label: "JSON file" },
      { value: "other", label: "Other" },
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

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function mergeDeep(base: Record<string, unknown>, patch: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = deepClone(base);
  for (const [key, value] of Object.entries(patch)) {
    if (Array.isArray(value)) {
      output[key] = deepClone(value);
      continue;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const current = output[key];
      output[key] = mergeDeep(
        current && typeof current === "object" && !Array.isArray(current)
          ? (current as Record<string, unknown>)
          : {},
        value as Record<string, unknown>,
      );
      continue;
    }
    output[key] = value;
  }
  return output;
}
