// Shared types and utilities for the automation builder.
// Imported by app.tsx and all step-modal components.

export type TriggerType = "manual" | "schedule" | "inbound_api" | "smtp_email";
export type StepType = "log" | "api" | "script" | "tool" | "condition" | "llm_chat" | "outbound_request" | "connector_activity";

export type AutomationBuilderOption = {
  value: string;
  label: string;
  description?: string;
};

export type StorageLocationOption = {
  id: string;
  name: string;
  location_type: "local" | "google_drive" | "repo";
  path?: string | null;
  connector_id?: string | null;
  folder_template?: string | null;
  file_name_template?: string | null;
  max_size_mb?: number | null;
  is_default_logs: boolean;
};

export type RepoCheckoutOption = {
  id: string;
  storage_location_id: string;
  repo_url: string;
  local_path: string;
  branch: string;
  last_synced_at?: string | null;
};

export type AutomationBuilderMetadata = {
  trigger_types: AutomationBuilderOption[];
  step_types: AutomationBuilderOption[];
  http_methods: AutomationBuilderOption[];
  storage_types: AutomationBuilderOption[];
  log_column_types: AutomationBuilderOption[];
  storage_locations: StorageLocationOption[];
  repo_checkouts: RepoCheckoutOption[];
};

declare global {
  interface Window {
    TOOLS_MANIFEST?: ToolManifestEntry[];
    INBOUND_APIS?: { id: string; name: string }[];
    CONNECTORS?: { id: string; name: string }[];
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<any>;
    };
  }
}

export const triggerTypeOptions: Array<{ value: TriggerType; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "schedule", label: "Schedule" },
  { value: "inbound_api", label: "Inbound API" },
  { value: "smtp_email", label: "SMTP email" }
];

export type ToolInputField = {
  key: string;
  label: string;
  type: "string" | "text" | "number" | "select";
  required: boolean;
  options?: string[];
};

export type ToolOutputField = {
  key: string;
  label: string;
  type: string;
};

export type ToolManifestEntry = {
  id: string;
  name: string;
  description: string;
  pageHref: string;
  inputs: ToolInputField[];
  outputs: ToolOutputField[];
};

export type ConnectorRecord = {
  id: string;
  provider: string;
  name: string;
  status: string;
  auth_type: string;
  scopes?: string[];
  owner?: string | null;
  base_url?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type WorkflowBuilderConnectorOption = ConnectorRecord & {
  provider_name?: string;
  docs_url?: string | null;
  source_path: string;
  last_tested_at?: string | null;
};

export type ConnectorActivitySchemaField = {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  default?: unknown;
  help_text?: string | null;
  placeholder?: string | null;
  options?: string[] | null;
  value_hint?: string | null;
};

export type ConnectorActivityDefinition = {
  provider_id: string;
  activity_id: string;
  service: string;
  operation_type: string;
  label: string;
  description: string;
  required_scopes: string[];
  input_schema: ConnectorActivitySchemaField[];
  output_schema: ConnectorActivitySchemaField[];
  execution: Record<string, unknown>;
};

export type HttpPreset = {
  preset_id: string;
  provider_id: string;
  service: string;
  operation: string;
  label: string;
  description: string;
  http_method: string;
  endpoint_path_template: string;
  payload_template: string;
  query_params: Record<string, string>;
  required_scopes: string[];
  input_schema: ConnectorActivitySchemaField[];
};

export type LogDbTableOption = {
  id: string;
  name: string;
  description: string;
  columns: Array<{ column_name: string; data_type: string }>;
};

export type LogDbColumnDef = {
  column_name: string;
  data_type: "text" | "integer" | "real" | "boolean" | "timestamp";
  nullable: boolean;
  default_value: string;
};

export type InboundApiOption = {
  id: string;
  name: string;
};

export type ScriptLibraryItem = {
  id: string;
  name: string;
  description: string;
  language: "python" | "javascript";
  sample_input: string;
  expected_output: string;
};

export type AutomationStep = {
  id?: string;
  type: StepType;
  name: string;
  on_true_step_id?: string | null;
  on_false_step_id?: string | null;
  is_merge_target?: boolean;
  config: {
    // API step branching
    api_mode?: "prebuilt" | "custom";
    // HTTP request fields
    message?: string;
    destination_url?: string;
    http_method?: string;
    auth_type?: string;
    connector_id?: string;
    http_preset_id?: string;
    payload_template?: string;
    wait_for_response?: boolean;
    response_mappings?: Array<{ key: string; path: string }>;
    // Connector activity fields
    activity_id?: string;
    activity_inputs?: Record<string, string | number | boolean>;
    // Script/tool/condition/llm fields
    script_id?: string;
    script_input_template?: string;
    tool_id?: string;
    tool_inputs?: Record<string, string>;
    expression?: string;
    stop_on_false?: boolean;
    system_prompt?: string;
    user_prompt?: string;
    model_identifier?: string;
    // Log / Write-to-DB fields
    log_table_id?: string;
    log_column_mappings?: Record<string, string>;
    // File-based write fields
    storage_type?: "csv" | "table" | "json" | "other";
    storage_target?: string;
    storage_new_file?: boolean;
    // Multi-location storage fields
    storage_location_id?: string;
    folder_template?: string;
    file_name_template?: string;
    // Repo-backed script step fields
    repo_checkout_id?: string;
    working_directory?: string;
    // Advanced overrides (legacy, not type-checked)
    storage_path?: string;
    storage_overrides?: string;
  };
};

export const stepTypeOptions: Array<{ value: StepType; label: string; description: string }> = [
  { value: "log", label: "Write", description: "Write data to a database table or file." },
  { value: "api", label: "API", description: "Call a prebuilt connector action or send a custom HTTP request." },
  { value: "script", label: "Script", description: "Run a stored script from the script library." },
  { value: "tool", label: "Tool", description: "Dispatch a configured tool from the tool catalog." },
  { value: "condition", label: "Condition", description: "Evaluate a guard expression and optionally halt the automation." },
  { value: "llm_chat", label: "LLM chat", description: "Prompt a language model with middleware context." }
];

export const stepTemplates: Record<StepType, AutomationStep> = {
  log: { type: "log", name: "Write step", config: { log_table_id: "", log_column_mappings: {} } },
  api: {
    type: "api",
    name: "API step",
    config: {
      api_mode: "prebuilt", // "prebuilt" or "custom"
      // Prebuilt connector activity fields
      connector_id: "",
      activity_id: "",
      activity_inputs: {},
      // Custom HTTP request fields
      destination_url: "https://example.com/hooks/run",
      http_method: "POST",
      auth_type: "none",
      payload_template: "{\"automation_id\":\"{{automation.id}}\"}",
      wait_for_response: true,
      response_mappings: [],
      http_preset_id: ""
    }
  },
  outbound_request: {
    type: "outbound_request",
    name: "HTTP request",
    config: {
      api_mode: "custom",
      connector_id: "",
      http_preset_id: "",
      destination_url: "https://example.com/hooks/run",
      http_method: "POST",
      auth_type: "none",
      payload_template: "{\"automation_id\":\"{{automation.id}}\"}",
      wait_for_response: true,
      response_mappings: []
    }
  },
  connector_activity: {
    type: "connector_activity",
    name: "Connector action",
    config: {
      api_mode: "prebuilt",
      connector_id: "",
      activity_id: "",
      activity_inputs: {}
    }
  },
  script: { type: "script", name: "Script step", config: { script_id: "", script_input_template: "" } },
  tool: { type: "tool", name: "Tool step", config: { tool_id: "" } },
  condition: { type: "condition", name: "Guard condition", config: { expression: "true", stop_on_false: true } },
  llm_chat: {
    type: "llm_chat",
    name: "LLM chat",
    config: {
      system_prompt: "You are a helpful middleware automation assistant.",
      user_prompt: "Summarize the current payload and propose the next middleware action.",
      model_identifier: ""
    }
  }
};

let _draftStepSequence = 1;
export const createDraftStepId = () => `draft-step-${_draftStepSequence++}`;

export const getDefaultStepName = (stepType: StepType) => stepTemplates[stepType].name;

export const cloneStepTemplate = (stepType: StepType): AutomationStep => ({
  ...stepTemplates[stepType],
  id: createDraftStepId(),
  config: { ...stepTemplates[stepType].config }
});
