import type { ConnectorActivityDefinition, ScriptLibraryItem, StepType, ToolManifestEntry, AutomationStep } from "./types";

export type DataFlowToken = {
  id: string;
  token: string;
  label: string;
  source: string;
};

const uniqueByToken = (tokens: DataFlowToken[]) => {
  const seen = new Set<string>();
  return tokens.filter((token) => {
    if (seen.has(token.token)) {
      return false;
    }
    seen.add(token.token);
    return true;
  });
};

const getStepOutputKeys = (
  step: AutomationStep,
  toolsManifest: ToolManifestEntry[],
  activityCatalog: ConnectorActivityDefinition[],
  scriptLibrary: ScriptLibraryItem[]
): string[] => {
  if (step.type === "outbound_request") {
    const mappingKeys = (step.config.response_mappings || [])
      .map((mapping) => String(mapping.key || "").trim())
      .filter(Boolean);
    return ["ok", "status_code", "destination_url", ...mappingKeys, "response_body_json"];
  }

  if (step.type === "connector_activity") {
    const connectorActivityId = step.config.activity_id || "";
    const activity = activityCatalog.find((candidate) => candidate.activity_id === connectorActivityId);
    return (activity?.output_schema || []).map((field) => field.key).filter(Boolean);
  }

  if (step.type === "tool") {
    const tool = toolsManifest.find((candidate) => candidate.id === (step.config.tool_id || ""));
    return (tool?.outputs || []).map((field) => field.key).filter(Boolean);
  }

  if (step.type === "llm_chat") {
    return ["response_text", "model_used"];
  }

  if (step.type === "condition") {
    return ["result"];
  }

  if (step.type === "script") {
    const script = scriptLibrary.find((candidate) => candidate.id === (step.config.script_id || ""));
    if (script?.expected_output) {
      try {
        const parsed = JSON.parse(script.expected_output) as Record<string, unknown>;
        const keys = Object.keys(parsed).filter(Boolean);
        if (keys.length > 0) {
          return keys;
        }
      } catch {
        // fall through to default
      }
    }
    return [];
  }

  if (step.type === "log") {
    return ["message", "table", "row_id"];
  }

  return [];
};

const normalizeTokenSource = (stepType: StepType) => {
  if (stepType === "outbound_request") return "HTTP step";
  if (stepType === "connector_activity") return "Connector activity";
  if (stepType === "llm_chat") return "LLM step";
  if (stepType === "script") return "Script step";
  if (stepType === "condition") return "Condition step";
  if (stepType === "tool") return "Tool step";
  return "Write step";
};

export const buildDataFlowTokens = (
  steps: AutomationStep[],
  currentStepId: string | null,
  toolsManifest: ToolManifestEntry[],
  activityCatalog: ConnectorActivityDefinition[],
  scriptLibrary: ScriptLibraryItem[] = []
): DataFlowToken[] => {
  const baseline: DataFlowToken[] = [
    { id: "token-automation-id", token: "{{automation.id}}", label: "Automation ID", source: "Workflow" },
    { id: "token-automation-name", token: "{{automation.name}}", label: "Automation name", source: "Workflow" },
    { id: "token-timestamp", token: "{{timestamp}}", label: "Execution timestamp", source: "Workflow" },
    { id: "token-payload", token: "{{payload}}", label: "Trigger payload", source: "Trigger" }
  ];

  const currentStepIndex = currentStepId ? steps.findIndex((step) => step.id === currentStepId) : -1;
  const priorSteps = currentStepIndex >= 0 ? steps.slice(0, currentStepIndex) : steps;

  const stepTokens = priorSteps.flatMap((step, index) => {
    const stepKey = step.id || `step_${index + 1}`;
    const sourceLabel = `${normalizeTokenSource(step.type)} · ${step.name}`;
    const outputKeys = getStepOutputKeys(step, toolsManifest, activityCatalog, scriptLibrary);
    const fieldTokens = outputKeys.map((outputKey) => ({
      id: `token-${stepKey}-${outputKey}`,
      token: `{{steps.${stepKey}.${outputKey}}}`,
      label: `${step.name} → ${outputKey}`,
      source: sourceLabel
    }));
    const baseToken: DataFlowToken = {
      id: `token-${stepKey}-base`,
      token: `{{steps.${stepKey}}}`,
      label: `${step.name} output`,
      source: sourceLabel
    };
    return [baseToken, ...fieldTokens];
  });

  return uniqueByToken([...baseline, ...stepTokens]);
};
