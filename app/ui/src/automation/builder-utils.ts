import type { AutomationStep, ConnectorActivityDefinition, ConnectorRecord, InboundApiOption, ScriptLibraryItem, StepType, ToolManifestEntry, TriggerType } from "./types";
import type { AutomationDetail, StepAccentMap, StepSummaryArgs } from "./builder-types";
import { AUTOMATION_TRIGGER_LABELS } from "./constants";
import { createDraftStepId, getDefaultStepName } from "./types";

export const stepAccentByType: StepAccentMap = {
  log: "log",
  outbound_request: "http",
  connector_activity: "connector",
  script: "script",
  tool: "tool",
  condition: "condition",
  llm_chat: "llm"
};

export const mapToolDirectoryEntry = (tool: {
  id: string;
  name: string;
  description: string;
  page_href: string;
  inputs: ToolManifestEntry["inputs"];
  outputs: ToolManifestEntry["outputs"];
}): ToolManifestEntry => ({
  id: tool.id,
  name: tool.name,
  description: tool.description,
  pageHref: String(tool.page_href || "").replace(/^\/+/, ""),
  inputs: Array.isArray(tool.inputs) ? tool.inputs : [],
  outputs: Array.isArray(tool.outputs) ? tool.outputs : []
});

export const getToolDefinition = (toolsManifest: ToolManifestEntry[], toolId: string | undefined) => (
  toolsManifest.find((tool) => tool.id === toolId) || null
);

export const normalizeLegacyApiStep = (step: AutomationStep): AutomationStep => {
  if (step.type !== "api") {
    return step;
  }

  return {
    ...step,
    type: step.config.api_mode === "prebuilt" ? "connector_activity" : "outbound_request"
  };
};

export const normalizeStep = (step: AutomationStep): AutomationStep => {
  const normalizedStep = normalizeLegacyApiStep(step);
  return {
    ...normalizedStep,
    id: normalizedStep.id || createDraftStepId(),
    name: normalizedStep.name || getDefaultStepName(normalizedStep.type),
    config: { ...normalizedStep.config }
  };
};

export const emptyDetail = (): AutomationDetail => ({
  id: "",
  name: "",
  description: "",
  enabled: true,
  trigger_type: "manual",
  trigger_config: {},
  step_count: 0,
  created_at: "",
  updated_at: "",
  last_run_at: null,
  next_run_at: null,
  steps: []
});

export const formatDateTime = (value?: string | null) => {
  if (!value) {
    return "Not scheduled";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
};

export const formatDuration = (value?: number | null) => {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return `${value} ms`;
};

export const getTriggerTypeLabel = (value: TriggerType) => AUTOMATION_TRIGGER_LABELS[value] || value;

export const getStepTypeLabel = (value: StepType) => {
  const labels: Record<StepType, string> = {
    log: "Write",
    api: "API",
    script: "Script",
    tool: "Tool",
    condition: "Condition",
    llm_chat: "LLM chat",
    outbound_request: "HTTP request",
    connector_activity: "Connector action"
  };
  return labels[value] || value;
};

export const getRunStatusTone = (value: string) => {
  if (value === "success" || value === "completed") {
    return "success";
  }
  if (value === "failed" || value === "error") {
    return "error";
  }
  return "neutral";
};

export const getTriggerSummary = (automation: AutomationDetail, inboundApis: InboundApiOption[]) => {
  if (automation.trigger_type === "schedule") {
    return automation.trigger_config.schedule_time ? `Runs daily at ${automation.trigger_config.schedule_time}` : "Choose a daily schedule.";
  }
  if (automation.trigger_type === "inbound_api") {
    if (!automation.trigger_config.inbound_api_id) {
      return "Attach an inbound API endpoint.";
    }
    const matchedInboundApi = inboundApis.find((api) => api.id === automation.trigger_config.inbound_api_id);
    return `Watches inbound API ${matchedInboundApi?.name || automation.trigger_config.inbound_api_id}`;
  }
  if (automation.trigger_type === "smtp_email") {
    const smtpSubject = automation.trigger_config.smtp_subject?.trim();
    const smtpRecipient = automation.trigger_config.smtp_recipient_email?.trim();
    if (smtpSubject && smtpRecipient) {
      return `Matches subject ${smtpSubject} to ${smtpRecipient}`;
    }
    if (smtpSubject) {
      return `Matches subject ${smtpSubject}`;
    }
    if (smtpRecipient) {
      return `Matches recipient ${smtpRecipient}`;
    }
    return "Runs for any inbound email.";
  }
  return "Runs on operator demand.";
};

export const isInboundApiSelectionMissing = (automation: AutomationDetail, inboundApis: InboundApiOption[]) => {
  if (automation.trigger_type !== "inbound_api") {
    return false;
  }
  const inboundApiId = automation.trigger_config.inbound_api_id;
  if (!inboundApiId) {
    return false;
  }
  return !inboundApis.some((option) => option.id === inboundApiId);
};

export const getStepSummary = ({
  step,
  scripts,
  activityCatalog = [],
  toolsManifest = []
}: StepSummaryArgs) => {
  if (step.type === "log") {
    if (step.config.log_table_id) {
      const colCount = Object.keys(step.config.log_column_mappings || {}).length;
      return `Write to table · ${colCount} column${colCount !== 1 ? "s" : ""}`;
    }
    return step.config.message || "Write a row to a managed database table.";
  }
  if (step.type === "outbound_request") {
    return step.config.destination_url || step.config.connector_id || "Send a request to a remote endpoint.";
  }
  if (step.type === "connector_activity") {
    const activity = activityCatalog.find((item) => item.activity_id === step.config.activity_id);
    return step.config.activity_id ? `${step.config.connector_id || "Connector"} · ${activity?.label || step.config.activity_id}` : "Select a connector-backed activity.";
  }
  if (step.type === "script") {
    if (!step.config.script_id) {
      return "Select a script to run.";
    }
    const selectedScript = scripts.find((script) => script.id === step.config.script_id);
    return selectedScript ? `Execute ${selectedScript.name}` : `Execute script ${step.config.script_id}`;
  }
  if (step.type === "tool") {
    if (step.config.tool_id) {
      const manifest = getToolDefinition(toolsManifest, step.config.tool_id);
      const toolName = manifest?.name || step.config.tool_id;
      const firstInputKey = manifest?.inputs?.[0]?.key;
      const firstInputValue = firstInputKey ? step.config.tool_inputs?.[firstInputKey] : undefined;
      return firstInputValue ? `${toolName}: ${firstInputValue.slice(0, 48)}` : `Invoke ${toolName}`;
    }
    return "Choose a tool to dispatch.";
  }
  if (step.type === "condition") {
    return step.config.expression || "Evaluate a runtime condition.";
  }
  return step.config.model_identifier ? `Use model ${step.config.model_identifier}` : "Prompt an LLM with middleware context.";
};

export const validateAutomationDefinition = (
  automation: AutomationDetail,
  inboundApis: InboundApiOption[],
  activityCatalog: ConnectorActivityDefinition[],
  connectors: ConnectorRecord[],
  toolsManifest: ToolManifestEntry[]
) => {
  const issues: string[] = [];
  if (!automation.name.trim()) {
    issues.push("Name is required.");
  }
  if (automation.trigger_type === "schedule" && !automation.trigger_config.schedule_time) {
    issues.push("Schedule time is required for scheduled automations.");
  }
  if (automation.trigger_type === "inbound_api" && !automation.trigger_config.inbound_api_id) {
    issues.push("Inbound API id is required for inbound-triggered automations.");
  }
  if (isInboundApiSelectionMissing(automation, inboundApis)) {
    issues.push("Selected inbound API is unavailable. Choose a currently configured inbound API.");
  }
  if (automation.steps.length === 0) {
    issues.push("At least one step is required.");
  }
  const stepIdSet = new Set(automation.steps.map((s) => s.id).filter((id): id is string => Boolean(id)));
  automation.steps.forEach((step, index) => {
    if (step.type === "condition") {
      if (step.on_true_step_id && !stepIdSet.has(step.on_true_step_id)) {
        issues.push(`Step ${index + 1}: TRUE branch target does not exist in this automation.`);
      }
      if (step.on_false_step_id && !stepIdSet.has(step.on_false_step_id)) {
        issues.push(`Step ${index + 1}: FALSE branch target does not exist in this automation.`);
      }
    }
    if (step.type === "tool" && step.config.tool_id) {
      const manifest = getToolDefinition(toolsManifest, step.config.tool_id);
      if (manifest) {
        const toolInputs = step.config.tool_inputs || {};
        for (const field of manifest.inputs) {
          if (field.required && !toolInputs[field.key]?.trim()) {
            issues.push(`Step ${index + 1} requires '${field.label}' for ${manifest.name}.`);
          }
        }
        if (manifest.id === "smtp" && toolInputs.relay_port?.trim() && !/^\d+$/.test(toolInputs.relay_port.trim())) {
          issues.push(`Step ${index + 1} requires a numeric 'Relay Port' for SMTP.`);
        }
      }
    }
    if (step.type === "script" && !step.config.script_id) {
      issues.push(`Step ${index + 1} requires a script selection.`);
    }
    if (step.type === "connector_activity") {
      if (!step.config.connector_id) {
        issues.push(`Step ${index + 1} requires a saved connector.`);
      }
      const selectedConnector = connectors.find((connector) => connector.id === step.config.connector_id);
      const selectedActivity = activityCatalog.find((activity) => activity.provider_id === (selectedConnector?.provider || "") && activity.activity_id === step.config.activity_id);
      if (!step.config.activity_id) {
        issues.push(`Step ${index + 1} requires a prebuilt activity selection.`);
      } else if (!selectedActivity) {
        issues.push(`Step ${index + 1} references an unavailable connector action.`);
      } else {
        for (const field of selectedActivity.input_schema) {
          const value = step.config.activity_inputs?.[field.key];
          const missing = value === undefined || value === null || (typeof value === "string" && !value.trim());
          if (field.required && missing) {
            issues.push(`Step ${index + 1} requires '${field.label}' for ${selectedActivity.label}.`);
          }
          if (field.type === "json" && typeof value === "string" && value.trim()) {
            try {
              JSON.parse(value);
            } catch {
              issues.push(`Step ${index + 1} has invalid JSON for '${field.label}'.`);
            }
          }
        }
      }
    }
  });
  return issues;
};

export const reorderSteps = (steps: AutomationStep[], fromIndex: number, toIndex: number) => {
  const nextSteps = [...steps];
  const [movedStep] = nextSteps.splice(fromIndex, 1);
  nextSteps.splice(toIndex, 0, movedStep);
  return nextSteps;
};

export const sanitizeAutomationDetail = (detail: AutomationDetail): AutomationDetail => ({
  ...detail,
  step_count: detail.steps.length,
  steps: detail.steps.map(normalizeStep)
});

export const getNodeMenuLabel = (nodeId: string, steps: AutomationStep[]) => {
  if (nodeId === "trigger-node") {
    return "Trigger";
  }
  const step = steps.find((candidate) => `step-node-${candidate.id}` === nodeId);
  return step?.name || "Step";
};

export const appendToken = (value: string, token: string) => {
  if (!value) {
    return token;
  }
  if (value.endsWith(" ") || value.endsWith("\n")) {
    return `${value}${token}`;
  }
  return `${value} ${token}`;
};

export const isTriggerConfigured = (automation: AutomationDetail) => {
  if (automation.trigger_type === "schedule") {
    return Boolean(automation.trigger_config.schedule_time);
  }
  if (automation.trigger_type === "inbound_api") {
    return Boolean(automation.trigger_config.inbound_api_id);
  }
  return true;
};

export const inferBuilderModeFromSearch = (search: string) => {
  const params = new URLSearchParams(search);
  const explicitMode = params.get("mode");
  if (explicitMode === "guided" || explicitMode === "canvas") {
    return explicitMode;
  }
  return params.get("new") === "true" ? "guided" : "canvas";
};

export const getInitialBuilderMode = () => {
  if (typeof window === "undefined") {
    return "canvas";
  }
  return inferBuilderModeFromSearch(window.location.search);
};
