// Shared types and utilities for the automation builder.
// Imported by app.tsx and all step-modal components.

export type TriggerType = "manual" | "schedule" | "inbound_api" | "smtp_email";
export type StepType = "log" | "outbound_request" | "connector_activity" | "script" | "tool" | "condition" | "llm_chat";

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

export type ConnectorActivitySchemaField = {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  default?: unknown;
  help_text?: string | null;
  placeholder?: string | null;
  options?: string[] | null;
};

export type ConnectorActivityDefinition = {
  provider_id: string;
  activity_id: string;
  label: string;
  description: string;
  required_scopes: string[];
  input_schema: ConnectorActivitySchemaField[];
  output_schema: ConnectorActivitySchemaField[];
  execution: Record<string, unknown>;
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
};

export type AutomationStep = {
  id?: string;
  type: StepType;
  name: string;
  on_true_step_id?: string | null;
  on_false_step_id?: string | null;
  is_merge_target?: boolean;
  config: {
    message?: string;
    destination_url?: string;
    http_method?: string;
    auth_type?: string;
    connector_id?: string;
    payload_template?: string;
    wait_for_response?: boolean;
    response_mappings?: Array<{ key: string; path: string }>;
    activity_id?: string;
    activity_inputs?: Record<string, string | number>;
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
  };
};

export const stepTypeOptions: Array<{ value: StepType; label: string; description: string }> = [
  { value: "log", label: "Log", description: "Write a row to a managed database table." },
  { value: "outbound_request", label: "HTTP request", description: "Send an HTTP request to a remote endpoint." },
  { value: "connector_activity", label: "Connector activity", description: "Run a provider-aware prebuilt connector action." },
  { value: "script", label: "Script", description: "Run a stored script from the script library." },
  { value: "tool", label: "Tool", description: "Dispatch a configured tool from the tool catalog." },
  { value: "condition", label: "Condition", description: "Evaluate a guard expression and optionally halt the workflow." },
  { value: "llm_chat", label: "LLM chat", description: "Prompt a language model with middleware context." }
];

export const stepTemplates: Record<StepType, AutomationStep> = {
  log: { type: "log", name: "Log step", config: { log_table_id: "", log_column_mappings: {} } },
  outbound_request: {
    type: "outbound_request",
    name: "HTTP request",
    config: {
      destination_url: "https://example.com/hooks/run",
      http_method: "POST",
      auth_type: "none",
      connector_id: "",
      payload_template: "{\"automation_id\":\"{{automation.id}}\"}",
      wait_for_response: true,
      response_mappings: []
    }
  },
  connector_activity: {
    type: "connector_activity",
    name: "Connector activity",
    config: {
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
