import { Page, Route } from "@playwright/test";
import { buildSettingsResponse, defaultToolsDirectory, stubSettings } from "./core.ts";

export type AutomationStepFixture = {
  id: string;
  type: "log" | "outbound_request" | "connector_activity" | "script" | "tool" | "condition" | "llm_chat";
  name: string;
  on_true_step_id?: string | null;
  on_false_step_id?: string | null;
  is_merge_target?: boolean;
  config: Record<string, unknown>;
};

export type AutomationFixture = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: "manual" | "schedule" | "inbound_api" | "smtp_email";
  trigger_config: Record<string, unknown>;
  step_count: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
  steps: AutomationStepFixture[];
};

export type ScriptFixture = {
  id: string;
  name: string;
  description: string;
  language: "python" | "javascript";
  sample_input: string;
  validation_status: "valid" | "invalid" | "unknown";
  validation_message: string | null;
  last_validated_at: string | null;
  created_at: string;
  updated_at: string;
  code: string;
};

type AutomationRunStepFixture = {
  step_id: string;
  run_id: string;
  step_name: string;
  status: string;
  request_summary: string | null;
  response_summary: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  detail_json: Record<string, unknown> | null;
  response_body_json: unknown | null;
  extracted_fields_json: Record<string, unknown> | null;
};

type AutomationRunFixture = {
  run_id: string;
  automation_id: string;
  trigger_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_summary: string | null;
  worker_id: string | null;
  worker_name: string | null;
  steps: AutomationRunStepFixture[];
};

type LogTableColumnFixture = {
  column_name: string;
  data_type: string;
};

export type LogTableFixture = {
  id: string;
  name: string;
  description: string;
  row_count: number;
  created_at: string;
  updated_at: string;
  columns: LogTableColumnFixture[];
};

type AutomationBrowserState = {
  settings: ReturnType<typeof buildSettingsResponse>;
  runtimeStatus: {
    active: boolean;
    last_tick_started_at: string | null;
    last_tick_finished_at: string | null;
    last_error: string | null;
    job_count: number;
  };
  tools: Array<{
    id: string;
    name: string;
    description: string;
    enabled: boolean;
    page_href: string;
  }>;
  inboundApis: Array<{ id: string; name: string }>;
  activityCatalog: Array<{
    provider_id: string;
    activity_id: string;
    service: string;
    operation_type: string;
    label: string;
    description: string;
    required_scopes: string[];
    input_schema: Array<{
      key: string;
      label: string;
      type: string;
      required?: boolean;
      default?: unknown;
      help_text?: string | null;
      placeholder?: string | null;
      options?: string[] | null;
      value_hint?: string | null;
    }>;
    output_schema: Array<{
      key: string;
      label: string;
      type: string;
    }>;
    execution: Record<string, unknown>;
  }>;
  automations: AutomationFixture[];
  scripts: ScriptFixture[];
  logTables: LogTableFixture[];
  rowsByTableId: Record<string, Array<Record<string, unknown>>>;
  validateResponses: Record<string, { valid: boolean; issues: string[] }>;
  runResponses: Record<string, AutomationRunFixture>;
  executeResponseDelayMs: number;
  executeRefreshResponseDelayMs: number;
  pendingExecuteRefreshResponseDelayMs: number;
  nextAutomationSequence: number;
  nextScriptSequence: number;
  nextTableSequence: number;
};

const iso = (value: string) => value;

const deepClone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const buildAutomationSummary = (automation: AutomationFixture) => ({
  id: automation.id,
  name: automation.name,
  description: automation.description,
  enabled: automation.enabled,
  trigger_type: automation.trigger_type,
  step_count: automation.steps.length,
  created_at: automation.created_at,
  updated_at: automation.updated_at,
  last_run_at: automation.last_run_at ?? null,
  next_run_at: automation.next_run_at ?? null
});

const buildAutomationDetail = (automation: AutomationFixture) => ({
  ...buildAutomationSummary(automation),
  trigger_config: deepClone(automation.trigger_config),
  steps: deepClone(automation.steps)
});

const buildRunResponse = (automation: AutomationFixture, runId: string): AutomationRunFixture => {
  const startedAt = iso("2026-03-23T09:00:00.000Z");
  return {
    run_id: runId,
    automation_id: automation.id,
    trigger_type: automation.trigger_type,
    status: "completed",
    started_at: startedAt,
    finished_at: iso("2026-03-23T09:00:01.000Z"),
    duration_ms: 1000,
    error_summary: null,
    worker_id: "worker-01",
    worker_name: "Automation Worker",
    steps: automation.steps.map((step, index) => ({
      step_id: step.id,
      run_id: runId,
      step_name: step.name,
      status: "completed",
      request_summary: step.type === "outbound_request" ? `Sent ${String(step.config.destination_url || "request")}` : `Executed ${step.name}`,
      response_summary: step.type === "outbound_request"
        ? "Response received."
        : step.type === "script"
          ? "Script executed successfully."
          : step.type === "connector_activity"
            ? "Connector activity completed."
            : "Step completed.",
      started_at: iso(`2026-03-23T09:00:0${index}.000Z`),
      finished_at: iso(`2026-03-23T09:00:0${index}.500Z`),
      duration_ms: 500,
      detail_json: {
        step_type: step.type,
        step_name: step.name
      },
      response_body_json: step.type === "outbound_request"
        ? {
            data: {
              customer: {
                name: "Ava"
              },
              order: {
                status: "queued"
              }
            }
          }
        : null,
      extracted_fields_json: step.type === "outbound_request"
        ? {
            customer_name: "Ava",
            order_status: "queued"
          }
        : null
    }))
  };
};

const buildScriptSummary = (script: ScriptFixture) => ({
  id: script.id,
  name: script.name,
  description: script.description,
  language: script.language,
  sample_input: script.sample_input,
  validation_status: script.validation_status,
  validation_message: script.validation_message,
  last_validated_at: script.last_validated_at,
  created_at: script.created_at,
  updated_at: script.updated_at
});

const buildScriptRecord = (script: ScriptFixture) => ({
  ...buildScriptSummary(script),
  code: script.code
});

const buildLogTableSummary = (table: LogTableFixture) => ({
  ...table,
  columns: deepClone(table.columns)
});

const createAutomationFixture = (automation: AutomationFixture): AutomationFixture => ({
  ...automation,
  trigger_config: deepClone(automation.trigger_config),
  steps: deepClone(automation.steps)
});

const defaultAutomationFixtures = (): AutomationFixture[] => ([
  {
    id: "automation-order-sync",
    name: "Order sync",
    description: "Refreshes the order feed and notifies the team.",
    enabled: true,
    trigger_type: "schedule",
    trigger_config: { schedule_time: "09:30" },
    step_count: 2,
    created_at: iso("2026-03-20T09:00:00.000Z"),
    updated_at: iso("2026-03-22T11:00:00.000Z"),
    last_run_at: iso("2026-03-23T08:30:00.000Z"),
    next_run_at: iso("2026-03-24T09:30:00.000Z"),
    steps: [
      {
        id: "step-fetch-order",
        type: "outbound_request",
        name: "Fetch order",
        config: {
          destination_url: "https://api.example.com/orders/42",
          http_method: "POST",
          auth_type: "none",
          payload_template: "{\"order_id\":\"42\"}",
          wait_for_response: true,
          response_mappings: []
        }
      },
      {
        id: "step-log-result",
        type: "log",
        name: "Log result",
        config: {
          message: "Customer {{steps.Fetch order.customer_name}}"
        }
      }
    ]
  },
  {
    id: "automation-weekly-summary",
    name: "Weekly summary",
    description: "Collects a summary and posts it to the team channel.",
    enabled: false,
    trigger_type: "manual",
    trigger_config: {},
    step_count: 1,
    created_at: iso("2026-03-18T09:00:00.000Z"),
    updated_at: iso("2026-03-22T10:00:00.000Z"),
    last_run_at: null,
    next_run_at: null,
    steps: [
      {
        id: "step-script-transform",
        type: "script",
        name: "Transform summary",
        config: {
          script_id: "script-normalize-summary",
          script_input_template: "{\"text\":\"ready\"}"
        }
      }
    ]
  }
]);

const defaultScriptFixtures = (): ScriptFixture[] => ([
  {
    id: "script-change-delimiter",
    name: "Change Delimiter",
    description: "Split text on one delimiter and join it with another.",
    language: "python",
    sample_input: "{\"text\":\"alpha,beta,gamma\"}",
    validation_status: "valid",
    validation_message: null,
    last_validated_at: iso("2026-03-20T09:00:00.000Z"),
    created_at: iso("2026-03-19T09:00:00.000Z"),
    updated_at: iso("2026-03-21T10:00:00.000Z"),
    code: [
      "def run(context, script_input=None):",
      "    payload = context.get('payload', {})",
      "    return script_input or payload",
      ""
    ].join("\n")
  },
  {
    id: "script-normalize-summary",
    name: "Normalize Summary",
    description: "Normalizes the text payload for downstream steps.",
    language: "javascript",
    sample_input: "{\"text\":\"Summary\"}",
    validation_status: "valid",
    validation_message: null,
    last_validated_at: iso("2026-03-21T10:00:00.000Z"),
    created_at: iso("2026-03-19T09:30:00.000Z"),
    updated_at: iso("2026-03-22T11:00:00.000Z"),
    code: [
      "function run(context, scriptInput) {",
      "  const payload = context?.payload ?? {};",
      "  return scriptInput || payload;",
      "}",
      ""
    ].join("\n")
  }
]);

const defaultLogTableFixtures = (): LogTableFixture[] => ([
  {
    id: "order-events",
    name: "Order events",
    description: "Rows written by order automations.",
    row_count: 3,
    created_at: iso("2026-03-20T09:00:00.000Z"),
    updated_at: iso("2026-03-22T12:00:00.000Z"),
    columns: [
      { column_name: "row_id", data_type: "integer" },
      { column_name: "order_id", data_type: "text" },
      { column_name: "status", data_type: "text" }
    ]
  },
  {
    id: "customer-events",
    name: "Customer events",
    description: "Rows written by customer automations.",
    row_count: 1,
    created_at: iso("2026-03-19T09:00:00.000Z"),
    updated_at: iso("2026-03-21T13:00:00.000Z"),
    columns: [
      { column_name: "row_id", data_type: "integer" },
      { column_name: "customer_id", data_type: "text" },
      { column_name: "event", data_type: "text" }
    ]
  }
]);

const defaultRowsByTableId = (): Record<string, Array<Record<string, unknown>>> => ({
  "order-events": [
    { row_id: 1, order_id: "ORD-1001", status: "queued" },
    { row_id: 2, order_id: "ORD-1002", status: "paid" },
    { row_id: 3, order_id: "ORD-1003", status: "warning" }
  ],
  "customer-events": [
    { row_id: 1, customer_id: "CUS-1", event: "created" }
  ]
});

const defaultRuntimeStatus = () => ({
  active: true,
  last_tick_started_at: iso("2026-03-23T08:58:00.000Z"),
  last_tick_finished_at: iso("2026-03-23T08:58:02.000Z"),
  last_error: null,
  job_count: 4
});

const defaultTools = () => ([
  ...defaultToolsDirectory,
  {
    id: "slack",
    name: "Slack",
    description: "Send Slack notifications from automation steps.",
    enabled: false,
    page_href: "/tools/catalog.html"
  }
]);

const defaultActivityCatalog = () => ([
  {
    provider_id: "google",
    activity_id: "gmail-send-email",
    service: "gmail",
    operation_type: "write",
    label: "Send email",
    description: "Send an email using a saved Google connector.",
    required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
    input_schema: [
      {
        key: "to",
        label: "To",
        type: "string",
        required: true,
        placeholder: "someone@example.com",
        help_text: "One recipient address.",
        value_hint: "Recipient"
      },
      {
        key: "subject",
        label: "Subject",
        type: "string",
        required: true,
        placeholder: "Shipping update"
      },
      {
        key: "body",
        label: "Body",
        type: "textarea",
        required: true,
        placeholder: "Hello from Malcom"
      }
    ],
    output_schema: [
      { key: "message_id", label: "Message ID", type: "string" },
      { key: "thread_id", label: "Thread ID", type: "string" }
    ],
    execution: { provider: "google", action: "send-email" }
  },
  {
    provider_id: "github",
    activity_id: "github-create-issue",
    service: "github",
    operation_type: "write",
    label: "Create issue",
    description: "Create an issue in a repository.",
    required_scopes: ["repo"],
    input_schema: [
      { key: "repository", label: "Repository", type: "string", required: true, placeholder: "owner/repo" },
      { key: "title", label: "Title", type: "string", required: true, placeholder: "Issue title" }
    ],
    output_schema: [
      { key: "issue_number", label: "Issue number", type: "integer" },
      { key: "issue_url", label: "Issue URL", type: "string" }
    ],
    execution: { provider: "github", action: "create-issue" }
  }
]);

export function createAutomationSuiteState(overrides: Partial<AutomationBrowserState> = {}): AutomationBrowserState {
  const automations = (overrides.automations || defaultAutomationFixtures()).map(createAutomationFixture);
  const scripts = (overrides.scripts || defaultScriptFixtures()).map((script) => deepClone(script));
  const logTables = (overrides.logTables || defaultLogTableFixtures()).map((table) => deepClone(table));
  const settings = overrides.settings || buildSettingsResponse({
    connectors: {
      records: [
        {
          id: "google-primary",
          provider: "google",
          name: "Google Primary",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/calendar"],
          owner: "Workspace",
          base_url: "https://www.googleapis.com"
        },
        {
          id: "github-primary",
          provider: "github",
          name: "GitHub Primary",
          status: "connected",
          auth_type: "bearer",
          scopes: ["repo"],
          owner: "Workspace",
          base_url: "https://api.github.com"
        }
      ]
    }
  });

  return {
    settings,
    runtimeStatus: overrides.runtimeStatus || defaultRuntimeStatus(),
    tools: overrides.tools || defaultTools(),
    inboundApis: overrides.inboundApis || [
      { id: "inbound-orders", name: "Orders webhook" },
      { id: "inbound-invoices", name: "Invoices webhook" }
    ],
    activityCatalog: overrides.activityCatalog || defaultActivityCatalog(),
    automations,
    scripts,
    logTables,
    rowsByTableId: overrides.rowsByTableId || defaultRowsByTableId(),
    validateResponses: overrides.validateResponses || {},
    runResponses: overrides.runResponses || {},
    executeResponseDelayMs: overrides.executeResponseDelayMs ?? 0,
    executeRefreshResponseDelayMs: overrides.executeRefreshResponseDelayMs ?? 0,
    pendingExecuteRefreshResponseDelayMs: 0,
    nextAutomationSequence: overrides.nextAutomationSequence || 1,
    nextScriptSequence: overrides.nextScriptSequence || scripts.length + 1,
    nextTableSequence: overrides.nextTableSequence || logTables.length + 1
  };
}

const ensureAutomationDetail = (state: AutomationBrowserState, automationId: string) => {
  const automation = state.automations.find((item) => item.id === automationId);
  if (!automation) {
    return null;
  }
  return automation;
};

const mapAutomationRoute = (state: AutomationBrowserState, requestUrl: string, method: string, body?: unknown) => {
  const url = new URL(requestUrl);
  const path = url.pathname;

  if (path === "/api/v1/automations" && method === "GET") {
    return { status: 200, body: state.automations.map(buildAutomationSummary) };
  }

  if (path === "/api/v1/automations" && method === "POST") {
    const payload = (body || {}) as Record<string, unknown>;
    const nextId = `automation-generated-${state.nextAutomationSequence}`;
    state.nextAutomationSequence += 1;
    const created: AutomationFixture = createAutomationFixture({
      id: nextId,
      name: String(payload.name || "Untitled automation"),
      description: String(payload.description || ""),
      enabled: Boolean(payload.enabled ?? true),
      trigger_type: (payload.trigger_type as AutomationFixture["trigger_type"]) || "manual",
      trigger_config: deepClone(payload.trigger_config || {}),
      step_count: Array.isArray(payload.steps) ? payload.steps.length : 0,
      created_at: iso("2026-03-23T09:00:00.000Z"),
      updated_at: iso("2026-03-23T09:00:00.000Z"),
      last_run_at: null,
      next_run_at: null,
      steps: Array.isArray(payload.steps) ? payload.steps as AutomationStepFixture[] : []
    });
    state.automations.unshift(created);
    return { status: 201, body: buildAutomationDetail(created) };
  }

  const automationMatch = path.match(/^\/api\/v1\/automations\/([^/]+)(?:\/(validate|execute|runs))?$/);
  if (!automationMatch) {
    if (path === "/api/v1/runs" && method === "GET") {
      return { status: 200, body: [] };
    }
    return null;
  }

  const automationId = automationMatch[1];
  const action = automationMatch[2];
  const automation = ensureAutomationDetail(state, automationId);
  if (!automation) {
    return { status: 404, body: { detail: "Automation not found." } };
  }

  if (!action && method === "GET") {
    return { status: 200, body: buildAutomationDetail(automation) };
  }

  if (!action && method === "PATCH") {
    const payload = (body || {}) as Record<string, unknown>;
    automation.name = String(payload.name || automation.name);
    automation.description = String(payload.description || automation.description);
    automation.enabled = Boolean(payload.enabled ?? automation.enabled);
    automation.trigger_type = (payload.trigger_type as AutomationFixture["trigger_type"]) || automation.trigger_type;
    automation.trigger_config = deepClone(payload.trigger_config || automation.trigger_config);
    automation.steps = Array.isArray(payload.steps) ? deepClone(payload.steps as AutomationStepFixture[]) : automation.steps;
    automation.step_count = automation.steps.length;
    automation.updated_at = iso("2026-03-23T09:01:00.000Z");
    return { status: 200, body: buildAutomationDetail(automation) };
  }

  if (!action && method === "DELETE") {
    state.automations = state.automations.filter((item) => item.id !== automationId);
    delete state.runResponses[automationId];
    delete state.validateResponses[automationId];
    return { status: 204, body: null };
  }

  if (action === "validate" && method === "POST") {
    const response = state.validateResponses[automationId] || { valid: true, issues: [] };
    return { status: 200, body: response };
  }

  if (action === "execute" && method === "POST") {
    const response = state.runResponses[automationId] || buildRunResponse(automation, `run-${automationId}`);
    state.runResponses[automationId] = response;
    state.pendingExecuteRefreshResponseDelayMs = state.executeRefreshResponseDelayMs;
    return { status: 200, body: response };
  }

  if (action === "runs" && method === "GET") {
    const run = state.runResponses[automationId];
    return { status: 200, body: run ? [run] : [] };
  }

  return null;
};

const mapScriptRoute = (state: AutomationBrowserState, requestUrl: string, method: string, body?: unknown) => {
  const url = new URL(requestUrl);
  const path = url.pathname;

  if (path === "/api/v1/scripts" && method === "GET") {
    return { status: 200, body: state.scripts.map(buildScriptSummary) };
  }

  if (path === "/api/v1/scripts" && method === "POST") {
    const payload = (body || {}) as Record<string, unknown>;
    const nextId = `script-generated-${state.nextScriptSequence}`;
    state.nextScriptSequence += 1;
    const created: ScriptFixture = {
      id: nextId,
      name: String(payload.name || "Untitled script"),
      description: String(payload.description || ""),
      language: (payload.language as ScriptFixture["language"]) || "python",
      sample_input: String(payload.sample_input || ""),
      validation_status: "valid",
      validation_message: null,
      last_validated_at: iso("2026-03-23T09:00:00.000Z"),
      created_at: iso("2026-03-23T09:00:00.000Z"),
      updated_at: iso("2026-03-23T09:00:00.000Z"),
      code: String(payload.code || "")
    };
    state.scripts.unshift(created);
    return { status: 201, body: buildScriptRecord(created) };
  }

  if (path === "/api/v1/scripts/validate" && method === "POST") {
    const payload = (body || {}) as Record<string, unknown>;
    const language = String(payload.language || "python");
    const code = String(payload.code || "");
    const valid = Boolean(code.trim()) && ((language === "python" && /def\s+run/.test(code)) || (language === "javascript" && /function\s+run/.test(code)));
    return valid
      ? { status: 200, body: { valid: true, issues: [] } }
      : {
          status: 200,
          body: {
            valid: false,
            issues: [
              {
                message: "Source code must define a run function.",
                line: 1,
                column: 1
              }
            ]
          }
        };
  }

  const scriptMatch = path.match(/^\/api\/v1\/scripts\/([^/]+)$/);
  if (!scriptMatch) {
    return null;
  }

  const scriptId = scriptMatch[1];
  const script = state.scripts.find((item) => item.id === scriptId);
  if (!script) {
    return { status: 404, body: { detail: "Script not found." } };
  }

  if (method === "GET") {
    return { status: 200, body: buildScriptRecord(script) };
  }

  if (method === "PATCH") {
    const payload = (body || {}) as Record<string, unknown>;
    script.name = String(payload.name || script.name);
    script.description = String(payload.description || script.description);
    script.language = (payload.language as ScriptFixture["language"]) || script.language;
    script.sample_input = String(payload.sample_input || script.sample_input);
    script.code = String(payload.code || script.code);
    script.validation_status = "valid";
    script.validation_message = null;
    script.last_validated_at = iso("2026-03-23T09:01:00.000Z");
    script.updated_at = iso("2026-03-23T09:01:00.000Z");
    return { status: 200, body: buildScriptRecord(script) };
  }

  return null;
};

const mapLogTableRoute = (state: AutomationBrowserState, requestUrl: string, method: string, body?: unknown) => {
  const url = new URL(requestUrl);
  const path = url.pathname;

  if (path === "/api/v1/log-tables" && method === "GET") {
    return { status: 200, body: state.logTables.map(buildLogTableSummary) };
  }

  if (path === "/api/v1/log-tables" && method === "POST") {
    const payload = (body || {}) as Record<string, unknown>;
    const nextId = `log-table-generated-${state.nextTableSequence}`;
    state.nextTableSequence += 1;
    const columns = Array.isArray(payload.columns)
      ? payload.columns as LogTableColumnFixture[]
      : [{ column_name: "row_id", data_type: "integer" }];
    const created: LogTableFixture = {
      id: nextId,
      name: String(payload.name || "Untitled table"),
      description: String(payload.description || ""),
      row_count: 0,
      created_at: iso("2026-03-23T09:00:00.000Z"),
      updated_at: iso("2026-03-23T09:00:00.000Z"),
      columns
    };
    state.logTables.unshift(created);
    state.rowsByTableId[nextId] = [];
    return { status: 201, body: buildLogTableSummary(created) };
  }

  const tableMatch = path.match(/^\/api\/v1\/log-tables\/([^/]+)(?:\/rows(?:\/clear)?)?$/);
  if (!tableMatch) {
    return null;
  }

  const tableId = tableMatch[1];
  const table = state.logTables.find((item) => item.id === tableId);
  if (!table) {
    return { status: 404, body: { detail: "Log table not found." } };
  }

  if (path.endsWith("/rows/clear") && method === "POST") {
    state.rowsByTableId[tableId] = [];
    table.row_count = 0;
    table.updated_at = iso("2026-03-23T09:01:00.000Z");
    return { status: 200, body: buildLogTableSummary(table) };
  }

  if (method === "DELETE") {
    state.logTables = state.logTables.filter((item) => item.id !== tableId);
    delete state.rowsByTableId[tableId];
    return { status: 204, body: null };
  }

  if (path.endsWith("/rows") && method === "GET") {
    const rows = state.rowsByTableId[tableId] || [];
    const limit = Number(url.searchParams.get("limit") || "100");
    const slicedRows = rows.slice(0, Number.isFinite(limit) ? limit : 100);
    return {
      status: 200,
      body: {
        table_id: tableId,
        table_name: table.name,
        columns: table.columns.map((column) => column.column_name),
        rows: slicedRows,
        total: rows.length
      }
    };
  }

  return null;
};

const mapMetadataRoute = (state: AutomationBrowserState, requestUrl: string, method: string) => {
  const url = new URL(requestUrl);
  if (url.pathname === "/api/v1/runtime/status" && method === "GET") {
    return { status: 200, body: state.runtimeStatus };
  }
  if (url.pathname === "/api/v1/tools" && method === "GET") {
    return { status: 200, body: state.tools };
  }
  if (url.pathname === "/api/v1/inbound" && method === "GET") {
    return { status: 200, body: state.inboundApis };
  }
  if (url.pathname === "/api/v1/connectors/activity-catalog" && method === "GET") {
    return { status: 200, body: state.activityCatalog };
  }
  if (url.pathname === "/api/v1/apis/test-delivery" && method === "POST") {
    return {
      status: 200,
      body: {
        ok: true,
        status_code: 200,
        response_body: JSON.stringify({
          data: {
            customer: {
              name: "Ava"
            },
            order: {
              status: "queued",
              total: 42
            }
          }
        }),
        sent_headers: {
          "Content-Type": "application/json"
        },
        destination_url: "https://api.example.com/orders/42"
      }
    };
  }
  return null;
};

const writeJsonResponse = async (route: Route, status: number, body: unknown) => {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: body === null ? "" : JSON.stringify(body)
  });
};

const readRequestBody = async (route: Route) => {
  const request = route.request();
  try {
    return request.postDataJSON();
  } catch {
    const raw = request.postData();
    return raw ? JSON.parse(raw) : {};
  }
};

export async function installAutomationSuiteRoutes(page: Page, state: AutomationBrowserState) {
  await stubSettings(page, state.settings);

  await page.route("**/api/v1/runtime/status", async (route) => {
    const response = mapMetadataRoute(state, route.request().url(), route.request().method());
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route("**/api/v1/tools", async (route) => {
    const response = mapMetadataRoute(state, route.request().url(), route.request().method());
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route("**/api/v1/inbound", async (route) => {
    const response = mapMetadataRoute(state, route.request().url(), route.request().method());
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route("**/api/v1/connectors/activity-catalog", async (route) => {
    const response = mapMetadataRoute(state, route.request().url(), route.request().method());
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route("**/api/v1/apis/test-delivery", async (route) => {
    const response = mapMetadataRoute(state, route.request().url(), route.request().method());
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route(/\/api\/v1\/automations(?:\/.*)?$/, async (route) => {
    const requestMethod = route.request().method();
    const requestUrl = route.request().url();
    const pathname = new URL(requestUrl).pathname;
    const body = requestMethod === "GET" ? undefined : await readRequestBody(route);
    const response = mapAutomationRoute(state, requestUrl, requestMethod, body);
    if (!response) {
      await route.fallback();
      return;
    }
    if (requestMethod === "POST" && /\/api\/v1\/automations\/[^/]+\/execute$/.test(pathname) && state.executeResponseDelayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, state.executeResponseDelayMs));
    }
    if (requestMethod === "GET" && /^\/api\/v1\/automations\/[^/]+$/.test(pathname) && state.pendingExecuteRefreshResponseDelayMs > 0) {
      const delayMs = state.pendingExecuteRefreshResponseDelayMs;
      state.pendingExecuteRefreshResponseDelayMs = 0;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route(/\/api\/v1\/scripts(?:\/.*)?$/, async (route) => {
    const body = route.request().method() === "GET" ? undefined : await readRequestBody(route);
    const response = mapScriptRoute(state, route.request().url(), route.request().method(), body);
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });

  await page.route(/\/api\/v1\/log-tables(?:\/.*)?$/, async (route) => {
    const body = route.request().method() === "GET" ? undefined : await readRequestBody(route);
    const response = mapLogTableRoute(state, route.request().url(), route.request().method(), body);
    if (!response) {
      await route.fallback();
      return;
    }
    await writeJsonResponse(route, response.status, response.body);
  });
}

export function buildAutomationRun(state: AutomationBrowserState, automationId: string, runId: string): AutomationRunFixture {
  const automation = state.automations.find((item) => item.id === automationId);
  if (!automation) {
    return {
      run_id: runId,
      automation_id: automationId,
      trigger_type: "manual",
      status: "completed",
      started_at: iso("2026-03-23T09:00:00.000Z"),
      finished_at: iso("2026-03-23T09:00:01.000Z"),
      duration_ms: 1000,
      error_summary: null,
      worker_id: "worker-01",
      worker_name: "Automation Worker",
      steps: []
    };
  }
  return buildRunResponse(automation, runId);
}

export function findAutomation(state: AutomationBrowserState, automationId: string) {
  return state.automations.find((item) => item.id === automationId) || null;
}

export function getAutomationDetail(state: AutomationBrowserState, automationId: string) {
  const automation = findAutomation(state, automationId);
  return automation ? buildAutomationDetail(automation) : null;
}
