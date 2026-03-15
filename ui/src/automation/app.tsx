import { useDeferredValue, useEffect, useState, startTransition } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Select } from "@base-ui/react/select";
import { Switch } from "@base-ui/react/switch";
import { Tabs } from "@base-ui/react/tabs";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  MiniMap,
  type Edge,
  type Node,
  type NodeProps,
  Position,
  Handle
} from "@xyflow/react";

type TriggerType = "manual" | "schedule" | "inbound_api" | "smtp_email";
type StepType = "log" | "outbound_request" | "script" | "tool" | "condition" | "llm_chat";

type AutomationStep = {
  id?: string;
  type: StepType;
  name: string;
  config: {
    message?: string;
    destination_url?: string;
    http_method?: string;
    auth_type?: string;
    connector_id?: string;
    payload_template?: string;
    script_id?: string;
    tool_id?: string;
    tool_text?: string;
    tool_output_filename?: string;
    tool_speaker?: string;
    tool_language?: string;
    expression?: string;
    stop_on_false?: boolean;
    system_prompt?: string;
    user_prompt?: string;
    model_identifier?: string;
  };
};

type Automation = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: TriggerType;
  trigger_config: {
    schedule_time?: string | null;
    inbound_api_id?: string | null;
    smtp_subject?: string | null;
    smtp_recipient_email?: string | null;
  };
  step_count: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
};

type AutomationDetail = Automation & {
  steps: AutomationStep[];
};

type AutomationRun = {
  run_id: string;
  automation_id: string;
  trigger_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_summary: string | null;
  worker_id?: string | null;
  worker_name?: string | null;
};

type AutomationRunDetail = AutomationRun & {
  steps: Array<{
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
  }>;
};

type RuntimeStatus = {
  active: boolean;
  last_tick_started_at: string | null;
  last_tick_finished_at: string | null;
  last_error: string | null;
  job_count: number;
};

type ConnectorRecord = {
  id: string;
  provider: string;
  name: string;
  auth_type: string;
  base_url?: string | null;
};

type WorkflowNodeData = {
  canvasNodeId: string;
  kind: "trigger" | "step";
  label: string;
  subtitle: string;
  summary: string;
  accent: "trigger" | "log" | "http" | "script" | "tool" | "condition" | "llm";
  selected: boolean;
};

declare global {
  interface Window {
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<any>;
    };
  }
}

const triggerTypeOptions: Array<{ value: TriggerType; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "schedule", label: "Schedule" },
  { value: "inbound_api", label: "Inbound API" },
  { value: "smtp_email", label: "SMTP email" }
];

const stepTypeOptions: Array<{ value: StepType; label: string }> = [
  { value: "log", label: "Log" },
  { value: "outbound_request", label: "HTTP request" },
  { value: "script", label: "Script" },
  { value: "tool", label: "Tool" },
  { value: "condition", label: "Condition" },
  { value: "llm_chat", label: "LLM chat" }
];

const stepTemplates: Record<StepType, AutomationStep> = {
  log: { type: "log", name: "Log step", config: { message: "Reached {{timestamp}}" } },
  outbound_request: {
    type: "outbound_request",
    name: "HTTP request",
    config: {
      destination_url: "https://example.com/hooks/run",
      http_method: "POST",
      auth_type: "none",
      connector_id: "",
      payload_template: "{\"automation_id\":\"{{automation.id}}\"}"
    }
  },
  script: { type: "script", name: "Script step", config: { script_id: "" } },
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

const stepAccentByType: Record<StepType, WorkflowNodeData["accent"]> = {
  log: "log",
  outbound_request: "http",
  script: "script",
  tool: "tool",
  condition: "condition",
  llm_chat: "llm"
};

let draftStepSequence = 1;

const createDraftStepId = () => `draft-step-${draftStepSequence++}`;

const normalizeStep = (step: AutomationStep): AutomationStep => ({
  ...step,
  id: step.id || createDraftStepId(),
  config: { ...step.config }
});

const cloneStepTemplate = (stepType: StepType): AutomationStep => ({
  ...stepTemplates[stepType],
  id: createDraftStepId(),
  config: { ...stepTemplates[stepType].config }
});

const emptyDetail = (): AutomationDetail => ({
  id: "",
  name: "",
  description: "",
  enabled: true,
  trigger_type: "manual",
  trigger_config: {},
  step_count: 1,
  created_at: "",
  updated_at: "",
  last_run_at: null,
  next_run_at: null,
  steps: [cloneStepTemplate("log")]
});

const requestJson = (path: string, options?: RequestInit) => {
  if (!window.Malcom?.requestJson) {
    throw new Error("Malcom request helper is unavailable.");
  }
  return window.Malcom.requestJson(path, options);
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return "Not scheduled";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
};

const formatDuration = (value?: number | null) => {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return `${value} ms`;
};

const getTriggerTypeLabel = (value: TriggerType) => triggerTypeOptions.find((option) => option.value === value)?.label || value;

const getStepTypeLabel = (value: StepType) => stepTypeOptions.find((option) => option.value === value)?.label || value;

const getRunStatusTone = (value: string) => {
  if (value === "success" || value === "completed") {
    return "success";
  }
  if (value === "failed" || value === "error") {
    return "error";
  }
  return "neutral";
};

const getTriggerSummary = (automation: AutomationDetail) => {
  if (automation.trigger_type === "schedule") {
    return automation.trigger_config.schedule_time ? `Runs daily at ${automation.trigger_config.schedule_time}` : "Choose a daily schedule.";
  }
  if (automation.trigger_type === "inbound_api") {
    return automation.trigger_config.inbound_api_id ? `Watches inbound API ${automation.trigger_config.inbound_api_id}` : "Attach an inbound API endpoint.";
  }
  if (automation.trigger_type === "smtp_email") {
    return automation.trigger_config.smtp_subject ? `Matches messages with subject ${automation.trigger_config.smtp_subject}` : "Provide the inbound subject filter.";
  }
  return "Runs on operator demand.";
};

const getStepSummary = (step: AutomationStep) => {
  if (step.type === "log") {
    return step.config.message || "Emit a log message.";
  }
  if (step.type === "outbound_request") {
    return step.config.destination_url || "Send a request to a remote endpoint.";
  }
  if (step.type === "script") {
    return step.config.script_id ? `Execute script ${step.config.script_id}` : "Select a script to run.";
  }
  if (step.type === "tool") {
    if (step.config.tool_id === "coqui-tts") {
      return step.config.tool_text
        ? `Generate speech with Coqui from ${step.config.tool_text.slice(0, 48)}`
        : "Provide text to synthesize with Coqui TTS.";
    }
    return step.config.tool_id ? `Invoke tool ${step.config.tool_id}` : "Choose a tool to dispatch.";
  }
  if (step.type === "condition") {
    return step.config.expression || "Evaluate a runtime condition.";
  }
  return step.config.model_identifier ? `Use model ${step.config.model_identifier}` : "Prompt an LLM with middleware context.";
};

const validateAutomationDefinition = (automation: AutomationDetail) => {
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
  if (automation.trigger_type === "smtp_email" && !automation.trigger_config.smtp_subject) {
    issues.push("Email subject is required for SMTP-triggered automations.");
  }
  if (automation.steps.length === 0) {
    issues.push("At least one step is required.");
  }
  automation.steps.forEach((step, index) => {
    if (step.type === "tool" && step.config.tool_id === "coqui-tts" && !(step.config.tool_text || "").trim()) {
      issues.push(`Step ${index + 1} requires speech text for Coqui TTS.`);
    }
  });
  return issues;
};

const reorderSteps = (steps: AutomationStep[], fromIndex: number, toIndex: number) => {
  const nextSteps = [...steps];
  const [movedStep] = nextSteps.splice(fromIndex, 1);
  nextSteps.splice(toIndex, 0, movedStep);
  return nextSteps;
};

const sanitizeAutomationDetail = (detail: AutomationDetail): AutomationDetail => ({
  ...detail,
  step_count: detail.steps.length,
  steps: detail.steps.map(normalizeStep)
});

const FlowAutomationNode = ({ data }: NodeProps<Node<WorkflowNodeData>>) => (
  <div
    id={data.canvasNodeId}
    className={`automation-node automation-node--${data.kind} automation-node--accent-${data.accent}${data.selected ? " automation-node--selected" : ""}`}
  >
    <Handle type="target" position={Position.Top} className="automation-node__handle" isConnectable={false} />
    <div id={`${data.canvasNodeId}-eyebrow`} className="automation-node__eyebrow">
      {data.kind === "trigger" ? "Trigger" : data.subtitle}
    </div>
    <div id={`${data.canvasNodeId}-title`} className="automation-node__title">
      {data.label}
    </div>
    <div id={`${data.canvasNodeId}-summary`} className="automation-node__summary">
      {data.summary}
    </div>
    <Handle type="source" position={Position.Bottom} className="automation-node__handle" isConnectable={false} />
  </div>
);

const nodeTypes = {
  automationNode: FlowAutomationNode
};

const FlowSelect = <T extends string>({
  rootId,
  labelId,
  value,
  placeholder,
  options,
  onValueChange
}: {
  rootId: string;
  labelId: string;
  value: T;
  placeholder: string;
  options: Array<{ value: T; label: string }>;
  onValueChange: (value: T) => void;
}) => (
  <Select.Root value={value} onValueChange={(nextValue) => onValueChange(String(nextValue) as T)}>
    <Select.Trigger id={rootId} className="automation-select-trigger" aria-labelledby={labelId}>
      <Select.Value placeholder={placeholder} />
      <Select.Icon className="automation-select-trigger__icon">▾</Select.Icon>
    </Select.Trigger>
    <Select.Portal>
      <Select.Positioner className="automation-select-positioner">
        <Select.Popup className="automation-select-popup">
          <Select.List className="automation-select-list">
            {options.map((option) => (
              <Select.Item
                key={option.value}
                id={`${rootId}-option-${option.value}`}
                className="automation-select-item"
                value={option.value}
              >
                <Select.ItemText>{option.label}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.List>
        </Select.Popup>
      </Select.Positioner>
    </Select.Portal>
  </Select.Root>
);

export const AutomationApp = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [currentAutomation, setCurrentAutomation] = useState<AutomationDetail>(emptyDetail);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("trigger-node");
  const [selectedRun, setSelectedRun] = useState<AutomationRunDetail | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [schedulerJobs, setSchedulerJobs] = useState<Array<Record<string, unknown>>>([]);
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [feedback, setFeedback] = useState("");
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error" | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [inspectorTab, setInspectorTab] = useState("configure");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const deferredQuery = useDeferredValue(searchQuery);

  const visibleAutomations = automations.filter((automation) => {
    const query = deferredQuery.trim().toLowerCase();
    if (!query) {
      return true;
    }
    return `${automation.name} ${automation.description}`.toLowerCase().includes(query);
  });

  const selectedStep = currentAutomation.steps.find((step) => `step-node-${step.id}` === selectedNodeId) || null;
  const selectedStepIndex = selectedStep ? currentAutomation.steps.findIndex((step) => step.id === selectedStep.id) : -1;

  const flowNodes: Array<Node<WorkflowNodeData>> = [
    {
      id: "trigger-node",
      type: "automationNode",
      position: { x: 40, y: 48 },
      draggable: false,
      selectable: true,
      data: {
        canvasNodeId: "automation-canvas-node-trigger",
        kind: "trigger",
        label: getTriggerTypeLabel(currentAutomation.trigger_type),
        subtitle: "Trigger",
        summary: getTriggerSummary(currentAutomation),
        accent: "trigger",
        selected: selectedNodeId === "trigger-node"
      }
    },
    ...currentAutomation.steps.map((step, index) => ({
      id: `step-node-${step.id}`,
      type: "automationNode",
      position: { x: 40, y: 220 + (index * 164) },
      draggable: true,
      selectable: true,
      data: {
        canvasNodeId: `automation-canvas-node-step-${step.id}`,
        kind: "step",
        label: step.name,
        subtitle: `${index + 1}. ${getStepTypeLabel(step.type)}`,
        summary: getStepSummary(step),
        accent: stepAccentByType[step.type],
        selected: selectedNodeId === `step-node-${step.id}`
      }
    }))
  ];

  const flowEdges: Edge[] = currentAutomation.steps.map((step, index) => ({
    id: `automation-canvas-edge-${step.id}`,
    source: index === 0 ? "trigger-node" : `step-node-${currentAutomation.steps[index - 1].id}`,
    target: `step-node-${step.id}`,
    type: "smoothstep",
    animated: selectedNodeId === `step-node-${step.id}`,
    markerEnd: { type: MarkerType.ArrowClosed }
  }));

  const loadRuntime = async () => {
    const [status, jobs, settings] = await Promise.all([
      requestJson("/api/v1/runtime/status"),
      requestJson("/api/v1/scheduler/jobs"),
      requestJson("/api/v1/settings")
    ]);
    setRuntimeStatus(status);
    setSchedulerJobs(jobs);
    setConnectors(settings.connectors?.records || []);
  };

  const applyNewAutomationDraft = () => {
    startTransition(() => {
      setCurrentAutomation(emptyDetail());
      setSelectedNodeId("trigger-node");
      setSelectedRun(null);
      setRuns([]);
      setInspectorTab("configure");
      setDeleteDialogOpen(false);
    });
    setFeedback("");
    setFeedbackTone("");
  };

  const selectAutomation = async (automationId: string) => {
    const [detail, automationRuns] = await Promise.all([
      requestJson(`/api/v1/automations/${automationId}`),
      requestJson(`/api/v1/automations/${automationId}/runs`)
    ]);

    startTransition(() => {
      setCurrentAutomation(sanitizeAutomationDetail(detail));
      setRuns(automationRuns);
      setSelectedNodeId("trigger-node");
      setSelectedRun(null);
      setInspectorTab("configure");
    });
  };

  const loadAutomations = async (nextSelectedId?: string) => {
    const list = (await requestJson("/api/v1/automations")) as Automation[];
    setAutomations(list);
    const matchingCurrentId = list.some((automation) => automation.id === currentAutomation.id) ? currentAutomation.id : "";
    const targetId = nextSelectedId || matchingCurrentId || list[0]?.id;
    if (!targetId) {
      applyNewAutomationDraft();
      return;
    }
    await selectAutomation(targetId);
  };

  const loadRunDetail = async (runId: string) => {
    const detail = (await requestJson(`/api/v1/runs/${runId}`)) as AutomationRunDetail;
    setSelectedRun(detail);
    setInspectorTab("activity");
  };

  useEffect(() => {
    loadAutomations().catch((error: Error) => {
      setFeedback(error.message);
      setFeedbackTone("error");
    });
    loadRuntime().catch(() => undefined);
  }, []);

  useEffect(() => {
    const createButton = document.getElementById("automations-create-button");
    createButton?.addEventListener("click", applyNewAutomationDraft);
    return () => createButton?.removeEventListener("click", applyNewAutomationDraft);
  }, []);

  const patchAutomation = (patch: Partial<AutomationDetail>) => {
    setCurrentAutomation((current) => ({
      ...current,
      ...patch,
      step_count: patch.steps ? patch.steps.length : current.steps.length
    }));
  };

  const updateSelectedStep = (updater: (step: AutomationStep) => AutomationStep) => {
    if (!selectedStep) {
      return;
    }
    setCurrentAutomation((current) => ({
      ...current,
      steps: current.steps.map((step) => (step.id === selectedStep.id ? normalizeStep(updater(step)) : step))
    }));
  };

  const updateStepOrder = (nextSteps: AutomationStep[]) => {
    setCurrentAutomation((current) => ({
      ...current,
      steps: nextSteps,
      step_count: nextSteps.length
    }));
  };

  const addStep = (stepType: StepType) => {
    const nextStep = cloneStepTemplate(stepType);
    const nextSteps = [...currentAutomation.steps, nextStep];
    updateStepOrder(nextSteps);
    setSelectedNodeId(`step-node-${nextStep.id}`);
  };

  const moveSelectedStep = (offset: number) => {
    if (!selectedStep || selectedStepIndex < 0) {
      return;
    }
    const nextIndex = Math.min(currentAutomation.steps.length - 1, Math.max(0, selectedStepIndex + offset));
    if (nextIndex === selectedStepIndex) {
      return;
    }
    updateStepOrder(reorderSteps(currentAutomation.steps, selectedStepIndex, nextIndex));
  };

  const removeSelectedStep = () => {
    if (!selectedStep) {
      return;
    }
    const nextSteps = currentAutomation.steps.filter((step) => step.id !== selectedStep.id);
    updateStepOrder(nextSteps.length > 0 ? nextSteps : [cloneStepTemplate("log")]);
    setSelectedNodeId("trigger-node");
  };

  const saveAutomation = async () => {
    const issues = validateAutomationDefinition(currentAutomation);
    if (issues.length > 0) {
      setFeedback(issues.join(" "));
      setFeedbackTone("error");
      return;
    }

    const payload = {
      name: currentAutomation.name,
      description: currentAutomation.description,
      enabled: currentAutomation.enabled,
      trigger_type: currentAutomation.trigger_type,
      trigger_config: currentAutomation.trigger_config,
      steps: currentAutomation.steps
    };

    const response = currentAutomation.id
      ? await requestJson(`/api/v1/automations/${currentAutomation.id}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await requestJson("/api/v1/automations", { method: "POST", body: JSON.stringify(payload) });

    setFeedback(currentAutomation.id ? "Automation updated." : "Automation created.");
    setFeedbackTone("success");
    await loadAutomations(response.id);
    await loadRuntime();
  };

  const executeAutomation = async () => {
    if (!currentAutomation.id) {
      setFeedback("Save the automation before running it.");
      setFeedbackTone("error");
      return;
    }
    const run = (await requestJson(`/api/v1/automations/${currentAutomation.id}/execute`, { method: "POST" })) as AutomationRunDetail;
    setSelectedRun(run);
    setFeedback("Automation executed.");
    setFeedbackTone("success");
    await selectAutomation(currentAutomation.id);
    await loadRunDetail(run.run_id);
    await loadRuntime();
  };

  const validateAutomation = async () => {
    const issues = validateAutomationDefinition(currentAutomation);
    if (!currentAutomation.id) {
      setFeedback(issues.length > 0 ? issues.join(" ") : "Automation is valid.");
      setFeedbackTone(issues.length > 0 ? "error" : "success");
      return;
    }
    const response = await requestJson(`/api/v1/automations/${currentAutomation.id}/validate`, { method: "POST" });
    setFeedback(response.valid ? "Automation definition is valid." : response.issues.join(" "));
    setFeedbackTone(response.valid ? "success" : "error");
  };

  const deleteAutomation = async () => {
    if (!currentAutomation.id) {
      applyNewAutomationDraft();
      return;
    }
    await requestJson(`/api/v1/automations/${currentAutomation.id}`, { method: "DELETE" });
    setDeleteDialogOpen(false);
    setFeedback("Automation deleted.");
    setFeedbackTone("success");
    await loadAutomations();
    await loadRuntime();
  };

  return (
    <div id="automations-app-shell" className="automations-app">
      <section id="automations-summary-banner" className="automation-hero">
        <div id="automations-summary-copy" className="automation-hero__copy">
          <p id="automations-summary-eyebrow" className="automation-hero__eyebrow">Middleware orchestration</p>
          <h3 id="automations-summary-title" className="automation-hero__title">{currentAutomation.name || "New automation draft"}</h3>
          <p id="automations-summary-description" className="automation-hero__description">
            Visualize the linear middleware path, adjust trigger settings, and inspect runtime activity without leaving the automation control room.
          </p>
        </div>
        <div id="automations-summary-stats" className="automation-hero__stats">
          <article id="automations-summary-trigger-card" className="automation-hero-stat">
            <span id="automations-summary-trigger-label" className="automation-hero-stat__label">Trigger</span>
            <span id="automations-summary-trigger-value" className="automation-hero-stat__value">{getTriggerTypeLabel(currentAutomation.trigger_type)}</span>
          </article>
          <article id="automations-summary-steps-card" className="automation-hero-stat">
            <span id="automations-summary-steps-label" className="automation-hero-stat__label">Steps</span>
            <span id="automations-summary-steps-value" className="automation-hero-stat__value">{currentAutomation.steps.length}</span>
          </article>
          <article id="automations-summary-runs-card" className="automation-hero-stat">
            <span id="automations-summary-runs-label" className="automation-hero-stat__label">Latest run</span>
            <span id="automations-summary-runs-value" className="automation-hero-stat__value">{formatDateTime(currentAutomation.last_run_at)}</span>
          </article>
        </div>
        <div id="automations-summary-actions" className="automation-hero__actions">
          <button id="automations-save-button" type="button" className="primary-action-button" onClick={() => saveAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
            Save
          </button>
          <button id="automations-validate-button" type="button" className="button button--secondary" onClick={() => validateAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
            Validate
          </button>
          <button id="automations-run-button" type="button" className="button button--secondary" onClick={() => executeAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
            Run now
          </button>
          <button id="automations-new-button" type="button" className="button button--secondary" onClick={applyNewAutomationDraft}>
            New draft
          </button>
          <button id="automations-delete-button" type="button" className="button button--secondary" onClick={() => setDeleteDialogOpen(true)}>
            Delete
          </button>
        </div>
      </section>

      <div
        id="automations-feedback-banner"
        className={feedbackTone ? `automation-feedback automation-feedback--${feedbackTone}` : "automation-feedback"}
        hidden={!feedback}
      >
        {feedback}
      </div>

      <section id="automations-workspace" className="automation-workspace-grid">
        <aside id="automations-left-rail" className="automation-panel automation-panel--rail">
          <div id="automations-library-header" className="automation-panel__header">
            <div id="automations-library-copy" className="automation-panel__copy">
              <p id="automations-library-eyebrow" className="automation-panel__eyebrow">Library</p>
              <h3 id="automations-library-title" className="automation-panel__title">Saved automations</h3>
              <p id="automations-library-description" className="automation-panel__description">Filter the workflow catalog and load an automation into the canvas.</p>
            </div>
          </div>
          <label id="automations-search-field" className="automation-field automation-field--full">
            <span id="automations-search-label" className="automation-field__label">Search</span>
            <input
              id="automations-search-input"
              className="automation-input"
              value={searchQuery}
              placeholder="Find an automation"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
          <div id="automations-library-list" className="automation-library-list">
            {visibleAutomations.length > 0 ? visibleAutomations.map((automation) => (
              <button
                key={automation.id}
                id={`automations-library-item-${automation.id}`}
                type="button"
                className={currentAutomation.id === automation.id ? "automation-library-card automation-library-card--selected" : "automation-library-card"}
                aria-pressed={currentAutomation.id === automation.id}
                onClick={() => {
                  selectAutomation(automation.id).catch((error: Error) => {
                    setFeedback(error.message);
                    setFeedbackTone("error");
                  });
                }}
              >
                <span id={`automations-library-item-name-${automation.id}`} className="automation-library-card__title">{automation.name}</span>
                <span id={`automations-library-item-description-${automation.id}`} className="automation-library-card__description">{automation.description || "No description provided."}</span>
                <span id={`automations-library-item-meta-${automation.id}`} className="automation-library-card__meta">
                  {getTriggerTypeLabel(automation.trigger_type)} · {automation.step_count} steps
                </span>
              </button>
            )) : (
              <div id="automations-library-empty-state" className="automation-empty-state">
                No automations match the current filter.
              </div>
            )}
          </div>

          <div id="automations-runtime-panel" className="automation-runtime-panel">
            <div id="automations-runtime-header" className="automation-panel__header automation-panel__header--compact">
              <div id="automations-runtime-copy" className="automation-panel__copy">
                <h4 id="automations-runtime-title" className="automation-panel__title automation-panel__title--compact">Runtime</h4>
                <p id="automations-runtime-description" className="automation-panel__description">Scheduler health and scheduled jobs.</p>
              </div>
            </div>
            <div id="automations-runtime-stats" className="automation-runtime-stats">
              <article id="automations-runtime-active-card" className="automation-runtime-stat">
                <span id="automations-runtime-active-label" className="automation-runtime-stat__label">Scheduler</span>
                <span id="automations-runtime-active-value" className="automation-runtime-stat__value">{runtimeStatus?.active ? "Active" : "Inactive"}</span>
              </article>
              <article id="automations-runtime-jobs-card" className="automation-runtime-stat">
                <span id="automations-runtime-jobs-label" className="automation-runtime-stat__label">Jobs</span>
                <span id="automations-runtime-jobs-value" className="automation-runtime-stat__value">{runtimeStatus?.job_count ?? 0}</span>
              </article>
            </div>
            <div id="automations-runtime-jobs-list" className="automation-job-list">
              {schedulerJobs.length > 0 ? schedulerJobs.map((job, index) => (
                <article key={`${job.id}-${index}`} id={`automations-runtime-job-${index}`} className="automation-job-card">
                  <span id={`automations-runtime-job-name-${index}`} className="automation-job-card__title">{String(job.name ?? "Unnamed job")}</span>
                  <span id={`automations-runtime-job-kind-${index}`} className="automation-job-card__meta">{String(job.kind ?? "automation")}</span>
                  <span id={`automations-runtime-job-next-run-${index}`} className="automation-job-card__meta">{formatDateTime(String(job.next_run_at ?? ""))}</span>
                </article>
              )) : (
                <div id="automations-runtime-empty-state" className="automation-empty-state">No scheduled jobs registered.</div>
              )}
            </div>
          </div>
        </aside>

        <section id="automations-canvas-panel" className="automation-panel automation-panel--canvas">
          <div id="automations-canvas-header" className="automation-panel__header">
            <div id="automations-canvas-copy" className="automation-panel__copy">
              <p id="automations-canvas-eyebrow" className="automation-panel__eyebrow">Canvas</p>
              <h3 id="automations-canvas-title" className="automation-panel__title">Workflow path</h3>
              <p id="automations-canvas-description" className="automation-panel__description">Drag steps vertically to reorder the linear execution path.</p>
            </div>
            <div id="automations-canvas-actions" className="automation-inline-actions">
              <button id="automations-step-move-up-button" type="button" className="button button--secondary" disabled={!selectedStep || selectedStepIndex <= 0} onClick={() => moveSelectedStep(-1)}>
                Move up
              </button>
              <button id="automations-step-move-down-button" type="button" className="button button--secondary" disabled={!selectedStep || selectedStepIndex >= currentAutomation.steps.length - 1} onClick={() => moveSelectedStep(1)}>
                Move down
              </button>
              <button id="automations-step-remove-button" type="button" className="button button--secondary" disabled={!selectedStep} onClick={removeSelectedStep}>
                Remove step
              </button>
            </div>
          </div>
          <div id="automations-canvas-surface" className="automation-canvas-surface">
            <ReactFlow
              id="automations-canvas"
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              fitView
              deleteKeyCode={null}
              connectOnClick={false}
              nodesConnectable={false}
              edgesFocusable={false}
              elementsSelectable
              onNodeClick={(_, node) => {
                setSelectedNodeId(node.id);
                setInspectorTab("configure");
              }}
              onNodeDragStop={(_, node) => {
                if (!node.id.startsWith("step-node-")) {
                  return;
                }
                const stepId = node.id.replace("step-node-", "");
                const fromIndex = currentAutomation.steps.findIndex((step) => step.id === stepId);
                if (fromIndex < 0) {
                  return;
                }
                const targetIndex = Math.min(
                  currentAutomation.steps.length - 1,
                  Math.max(0, Math.round((node.position.y - 220) / 164))
                );
                if (targetIndex !== fromIndex) {
                  updateStepOrder(reorderSteps(currentAutomation.steps, fromIndex, targetIndex));
                }
                setSelectedNodeId(node.id);
              }}
              minZoom={0.6}
              maxZoom={1.4}
              proOptions={{ hideAttribution: true }}
            >
              <Background id="automations-canvas-background" color="#cbd5e1" gap={24} size={1.5} />
              <MiniMap
                id="automations-canvas-minimap"
                pannable
                zoomable
                nodeColor={(node) => (node.id === "trigger-node" ? "#2563eb" : "#0f766e")}
              />
              <Controls id="automations-canvas-controls" position="bottom-left" />
            </ReactFlow>
          </div>
        </section>

        <aside id="automations-inspector-panel" className="automation-panel automation-panel--inspector">
          <Tabs.Root id="automations-inspector-tabs" value={inspectorTab} onValueChange={(value) => setInspectorTab(String(value))}>
            <div id="automations-inspector-header" className="automation-panel__header">
              <div id="automations-inspector-copy" className="automation-panel__copy">
                <p id="automations-inspector-eyebrow" className="automation-panel__eyebrow">Inspector</p>
                <h3 id="automations-inspector-title" className="automation-panel__title">{selectedStep ? selectedStep.name : "Trigger settings"}</h3>
                <p id="automations-inspector-description" className="automation-panel__description">
                  {selectedStep ? "Configure the selected step and keep the linear execution path intact." : "Set the automation identity, trigger, and runtime availability."}
                </p>
              </div>
            </div>
            <Tabs.List id="automations-inspector-tab-list" className="automation-tabs-list">
              <Tabs.Tab id="automations-inspector-tab-configure" className="automation-tabs-tab" value="configure">Configure</Tabs.Tab>
              <Tabs.Tab id="automations-inspector-tab-activity" className="automation-tabs-tab" value="activity">Activity</Tabs.Tab>
              <Tabs.Indicator id="automations-inspector-tab-indicator" className="automation-tabs-indicator" />
            </Tabs.List>

            <Tabs.Panel id="automations-inspector-panel-configure" className="automation-tabs-panel" value="configure">
              {!selectedStep ? (
                <div id="automations-trigger-form" className="automation-form">
                  <label id="automations-name-field" className="automation-field automation-field--full">
                    <span id="automations-name-label" className="automation-field__label">Name</span>
                    <input
                      id="automations-name-input"
                      className="automation-input"
                      value={currentAutomation.name}
                      onChange={(event) => patchAutomation({ name: event.target.value })}
                    />
                  </label>

                  <label id="automations-description-field" className="automation-field automation-field--full">
                    <span id="automations-description-label" className="automation-field__label">Description</span>
                    <textarea
                      id="automations-description-input"
                      className="automation-textarea"
                      rows={4}
                      value={currentAutomation.description}
                      onChange={(event) => patchAutomation({ description: event.target.value })}
                    />
                  </label>

                  <div id="automations-enabled-field" className="automation-switch-field">
                    <div id="automations-enabled-copy" className="automation-switch-field__copy">
                      <span id="automations-enabled-label" className="automation-field__label">Enabled</span>
                      <span id="automations-enabled-description" className="automation-switch-field__description">
                        {currentAutomation.enabled ? "The runtime can execute this automation." : "The automation stays visible but will not execute."}
                      </span>
                    </div>
                    <Switch.Root
                      id="automations-enabled-input"
                      checked={currentAutomation.enabled}
                      onCheckedChange={(checked) => patchAutomation({ enabled: checked })}
                      className="automation-switch"
                    >
                      <Switch.Thumb className="automation-switch__thumb" />
                    </Switch.Root>
                  </div>

                  <div id="automations-trigger-type-field" className="automation-field automation-field--full">
                    <span id="automations-trigger-type-label" className="automation-field__label">Trigger type</span>
                    <FlowSelect
                      rootId="automations-trigger-type-input"
                      labelId="automations-trigger-type-label"
                      value={currentAutomation.trigger_type}
                      placeholder="Choose a trigger"
                      options={triggerTypeOptions}
                      onValueChange={(nextValue) => patchAutomation({ trigger_type: nextValue, trigger_config: {} })}
                    />
                  </div>

                  {currentAutomation.trigger_type === "schedule" ? (
                    <label id="automations-trigger-schedule-field" className="automation-field automation-field--full">
                      <span id="automations-trigger-schedule-label" className="automation-field__label">Daily run time</span>
                      <input
                        id="automations-trigger-schedule-input"
                        className="automation-input"
                        type="time"
                        value={currentAutomation.trigger_config.schedule_time || ""}
                        onChange={(event) => patchAutomation({ trigger_config: { ...currentAutomation.trigger_config, schedule_time: event.target.value } })}
                      />
                    </label>
                  ) : null}

                  {currentAutomation.trigger_type === "inbound_api" ? (
                    <label id="automations-trigger-api-field" className="automation-field automation-field--full">
                      <span id="automations-trigger-api-label" className="automation-field__label">Inbound API id</span>
                      <input
                        id="automations-trigger-api-input"
                        className="automation-input"
                        value={currentAutomation.trigger_config.inbound_api_id || ""}
                        onChange={(event) => patchAutomation({ trigger_config: { ...currentAutomation.trigger_config, inbound_api_id: event.target.value } })}
                      />
                    </label>
                  ) : null}

                  {currentAutomation.trigger_type === "smtp_email" ? (
                    <>
                      <label id="automations-trigger-smtp-subject-field" className="automation-field automation-field--full">
                        <span id="automations-trigger-smtp-subject-label" className="automation-field__label">Email subject</span>
                        <input
                          id="automations-trigger-smtp-subject-input"
                          className="automation-input"
                          value={currentAutomation.trigger_config.smtp_subject || ""}
                          onChange={(event) => patchAutomation({ trigger_config: { ...currentAutomation.trigger_config, smtp_subject: event.target.value } })}
                        />
                      </label>
                      <label id="automations-trigger-smtp-recipient-field" className="automation-field automation-field--full">
                        <span id="automations-trigger-smtp-recipient-label" className="automation-field__label">Recipient filter</span>
                        <input
                          id="automations-trigger-smtp-recipient-input"
                          className="automation-input"
                          value={currentAutomation.trigger_config.smtp_recipient_email || ""}
                          onChange={(event) => patchAutomation({ trigger_config: { ...currentAutomation.trigger_config, smtp_recipient_email: event.target.value } })}
                        />
                      </label>
                    </>
                  ) : null}
                </div>
              ) : (
                <div id="automations-step-form" className="automation-form">
                  <label id="automations-step-name-field" className="automation-field automation-field--full">
                    <span id="automations-step-name-label" className="automation-field__label">Step name</span>
                    <input
                      id="automations-step-name-input"
                      className="automation-input"
                      value={selectedStep.name}
                      onChange={(event) => updateSelectedStep((step) => ({ ...step, name: event.target.value }))}
                    />
                  </label>

                  <div id="automations-step-type-field" className="automation-field automation-field--full">
                    <span id="automations-step-type-label" className="automation-field__label">Step type</span>
                    <FlowSelect
                      rootId="automations-step-type-input"
                      labelId="automations-step-type-label"
                      value={selectedStep.type}
                      placeholder="Choose a step type"
                      options={stepTypeOptions}
                      onValueChange={(nextValue) => updateSelectedStep((step) => ({
                        ...cloneStepTemplate(nextValue),
                        id: step.id,
                        name: cloneStepTemplate(nextValue).name
                      }))}
                    />
                  </div>

                  {selectedStep.type === "log" ? (
                    <label id="automations-step-log-message-field" className="automation-field automation-field--full">
                      <span id="automations-step-log-message-label" className="automation-field__label">Message</span>
                      <textarea
                        id="automations-step-log-message-input"
                        className="automation-textarea"
                        rows={4}
                        value={selectedStep.config.message || ""}
                        onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, message: event.target.value } }))}
                      />
                    </label>
                  ) : null}

                  {selectedStep.type === "outbound_request" ? (
                    <>
                      <div id="automations-step-http-method-field" className="automation-field automation-field--full">
                        <span id="automations-step-http-method-label" className="automation-field__label">HTTP method</span>
                        <FlowSelect
                          rootId="automations-step-http-method-input"
                          labelId="automations-step-http-method-label"
                          value={(selectedStep.config.http_method || "POST") as "GET" | "POST" | "PUT" | "PATCH" | "DELETE"}
                          placeholder="Choose a method"
                          options={[
                            { value: "GET", label: "GET" },
                            { value: "POST", label: "POST" },
                            { value: "PUT", label: "PUT" },
                            { value: "PATCH", label: "PATCH" },
                            { value: "DELETE", label: "DELETE" }
                          ]}
                          onValueChange={(nextValue) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, http_method: nextValue } }))}
                        />
                      </div>
                      <label id="automations-step-http-connector-field" className="automation-field automation-field--full">
                        <span id="automations-step-http-connector-label" className="automation-field__label">Saved connector</span>
                        <select
                          id="automations-step-http-connector-input"
                          className="automation-native-select"
                          value={selectedStep.config.connector_id || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, connector_id: event.target.value } }))}
                        >
                          <option value="">None</option>
                          {connectors.map((connector) => (
                            <option key={connector.id} value={connector.id}>{connector.name}</option>
                          ))}
                        </select>
                      </label>
                      <label id="automations-step-http-url-field" className="automation-field automation-field--full">
                        <span id="automations-step-http-url-label" className="automation-field__label">Destination URL</span>
                        <input
                          id="automations-step-http-url-input"
                          className="automation-input"
                          value={selectedStep.config.destination_url || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, destination_url: event.target.value } }))}
                        />
                      </label>
                      <label id="automations-step-http-payload-field" className="automation-field automation-field--full">
                        <span id="automations-step-http-payload-label" className="automation-field__label">Payload template</span>
                        <textarea
                          id="automations-step-http-payload-input"
                          className="automation-textarea automation-textarea--code"
                          rows={6}
                          value={selectedStep.config.payload_template || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, payload_template: event.target.value } }))}
                        />
                      </label>
                    </>
                  ) : null}

                  {selectedStep.type === "script" ? (
                    <label id="automations-step-script-id-field" className="automation-field automation-field--full">
                      <span id="automations-step-script-id-label" className="automation-field__label">Script id</span>
                      <input
                        id="automations-step-script-id-input"
                        className="automation-input"
                        value={selectedStep.config.script_id || ""}
                        onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, script_id: event.target.value } }))}
                      />
                    </label>
                  ) : null}

                  {selectedStep.type === "tool" ? (
                    <>
                      <label id="automations-step-tool-id-field" className="automation-field automation-field--full">
                        <span id="automations-step-tool-id-label" className="automation-field__label">Tool id</span>
                        <input
                          id="automations-step-tool-id-input"
                          className="automation-input"
                          value={selectedStep.config.tool_id || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, tool_id: event.target.value } }))}
                        />
                      </label>

                      {selectedStep.config.tool_id === "coqui-tts" ? (
                        <>
                          <label id="automations-step-tool-text-field" className="automation-field automation-field--full">
                            <span id="automations-step-tool-text-label" className="automation-field__label">Speech text template</span>
                            <textarea
                              id="automations-step-tool-text-input"
                              className="automation-textarea"
                              rows={5}
                              value={selectedStep.config.tool_text || ""}
                              onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, tool_text: event.target.value } }))}
                            />
                          </label>
                          <label id="automations-step-tool-output-field" className="automation-field automation-field--full">
                            <span id="automations-step-tool-output-label" className="automation-field__label">Output filename</span>
                            <input
                              id="automations-step-tool-output-input"
                              className="automation-input"
                              value={selectedStep.config.tool_output_filename || ""}
                              onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, tool_output_filename: event.target.value } }))}
                            />
                          </label>
                          <label id="automations-step-tool-speaker-field" className="automation-field">
                            <span id="automations-step-tool-speaker-label" className="automation-field__label">Speaker override</span>
                            <input
                              id="automations-step-tool-speaker-input"
                              className="automation-input"
                              value={selectedStep.config.tool_speaker || ""}
                              onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, tool_speaker: event.target.value } }))}
                            />
                          </label>
                          <label id="automations-step-tool-language-field" className="automation-field">
                            <span id="automations-step-tool-language-label" className="automation-field__label">Language override</span>
                            <input
                              id="automations-step-tool-language-input"
                              className="automation-input"
                              value={selectedStep.config.tool_language || ""}
                              onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, tool_language: event.target.value } }))}
                            />
                          </label>
                        </>
                      ) : null}
                    </>
                  ) : null}

                  {selectedStep.type === "condition" ? (
                    <>
                      <label id="automations-step-condition-expression-field" className="automation-field automation-field--full">
                        <span id="automations-step-condition-expression-label" className="automation-field__label">Expression</span>
                        <textarea
                          id="automations-step-condition-expression-input"
                          className="automation-textarea automation-textarea--code"
                          rows={4}
                          value={selectedStep.config.expression || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, expression: event.target.value } }))}
                        />
                      </label>
                      <div id="automations-step-condition-stop-field" className="automation-switch-field">
                        <div id="automations-step-condition-stop-copy" className="automation-switch-field__copy">
                          <span id="automations-step-condition-stop-label" className="automation-field__label">Stop on false</span>
                          <span id="automations-step-condition-stop-description" className="automation-switch-field__description">
                            Exit the workflow when the guard evaluates to false.
                          </span>
                        </div>
                        <Switch.Root
                          id="automations-step-condition-stop-input"
                          checked={Boolean(selectedStep.config.stop_on_false)}
                          onCheckedChange={(checked) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, stop_on_false: checked } }))}
                          className="automation-switch"
                        >
                          <Switch.Thumb className="automation-switch__thumb" />
                        </Switch.Root>
                      </div>
                    </>
                  ) : null}

                  {selectedStep.type === "llm_chat" ? (
                    <>
                      <label id="automations-step-llm-model-field" className="automation-field automation-field--full">
                        <span id="automations-step-llm-model-label" className="automation-field__label">Model override</span>
                        <input
                          id="automations-step-llm-model-input"
                          className="automation-input"
                          value={selectedStep.config.model_identifier || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, model_identifier: event.target.value } }))}
                        />
                      </label>
                      <label id="automations-step-llm-system-field" className="automation-field automation-field--full">
                        <span id="automations-step-llm-system-label" className="automation-field__label">System prompt</span>
                        <textarea
                          id="automations-step-llm-system-input"
                          className="automation-textarea automation-textarea--code"
                          rows={5}
                          value={selectedStep.config.system_prompt || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, system_prompt: event.target.value } }))}
                        />
                      </label>
                      <label id="automations-step-llm-user-field" className="automation-field automation-field--full">
                        <span id="automations-step-llm-user-label" className="automation-field__label">User prompt</span>
                        <textarea
                          id="automations-step-llm-user-input"
                          className="automation-textarea automation-textarea--code"
                          rows={7}
                          value={selectedStep.config.user_prompt || ""}
                          onChange={(event) => updateSelectedStep((step) => ({ ...step, config: { ...step.config, user_prompt: event.target.value } }))}
                        />
                      </label>
                    </>
                  ) : null}
                </div>
              )}

              <div id="automations-add-step-panel" className="automation-add-step-panel">
                <span id="automations-add-step-label" className="automation-field__label">Append a step</span>
                <div id="automations-add-step-actions" className="automation-add-step-actions">
                  {stepTypeOptions.map((option) => (
                    <button
                      key={option.value}
                      id={`automations-add-step-${option.value}`}
                      type="button"
                      className="button button--secondary"
                      onClick={() => addStep(option.value)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </Tabs.Panel>

            <Tabs.Panel id="automations-inspector-panel-activity" className="automation-tabs-panel" value="activity">
              <div id="automations-activity-panel" className="automation-activity-panel">
                <article id="automations-activity-current-card" className="automation-activity-card">
                  <span id="automations-activity-current-label" className="automation-activity-card__label">Current automation</span>
                  <span id="automations-activity-current-value" className="automation-activity-card__value">{currentAutomation.name || "Unsaved draft"}</span>
                </article>
                <article id="automations-activity-next-run-card" className="automation-activity-card">
                  <span id="automations-activity-next-run-label" className="automation-activity-card__label">Next run</span>
                  <span id="automations-activity-next-run-value" className="automation-activity-card__value">{formatDateTime(currentAutomation.next_run_at)}</span>
                </article>
                <article id="automations-activity-last-tick-card" className="automation-activity-card">
                  <span id="automations-activity-last-tick-label" className="automation-activity-card__label">Last scheduler tick</span>
                  <span id="automations-activity-last-tick-value" className="automation-activity-card__value">{formatDateTime(runtimeStatus?.last_tick_finished_at)}</span>
                </article>
                <article id="automations-activity-error-card" className="automation-activity-card">
                  <span id="automations-activity-error-label" className="automation-activity-card__label">Runtime error</span>
                  <span id="automations-activity-error-value" className="automation-activity-card__value">{runtimeStatus?.last_error || "No recent runtime error."}</span>
                </article>
              </div>
            </Tabs.Panel>
          </Tabs.Root>
        </aside>
      </section>

      <section id="automations-run-history-panel" className="automation-panel automation-panel--runs">
        <div id="automations-run-history-header" className="automation-panel__header">
          <div id="automations-run-history-copy" className="automation-panel__copy">
            <p id="automations-run-history-eyebrow" className="automation-panel__eyebrow">Run history</p>
            <h3 id="automations-run-history-title" className="automation-panel__title">Execution timeline</h3>
            <p id="automations-run-history-description" className="automation-panel__description">Inspect recent runs and open a detailed trace for each step.</p>
          </div>
        </div>
        <div id="automations-run-history-layout" className="automation-run-history-layout">
          <div id="automations-run-list" className="automation-run-list">
            {runs.length > 0 ? runs.map((run) => (
              <button
                key={run.run_id}
                id={`automations-run-list-item-${run.run_id}`}
                type="button"
                className={selectedRun?.run_id === run.run_id ? "automation-run-card automation-run-card--selected" : "automation-run-card"}
                onClick={() => {
                  loadRunDetail(run.run_id).catch((error: Error) => {
                    setFeedback(error.message);
                    setFeedbackTone("error");
                  });
                }}
              >
                <span id={`automations-run-list-status-${run.run_id}`} className={`automation-run-card__status automation-run-card__status--${getRunStatusTone(run.status)}`}>
                  {run.status}
                </span>
                <span id={`automations-run-list-trigger-${run.run_id}`} className="automation-run-card__title">{run.trigger_type}</span>
                <span id={`automations-run-list-started-${run.run_id}`} className="automation-run-card__meta">{formatDateTime(run.started_at)}</span>
                <span id={`automations-run-list-duration-${run.run_id}`} className="automation-run-card__meta">{formatDuration(run.duration_ms)}</span>
              </button>
            )) : (
              <div id="automations-run-history-empty-state" className="automation-empty-state">
                No runs have been recorded for this automation yet.
              </div>
            )}
          </div>
          <div id="automations-run-detail-panel" className="automation-run-detail-panel">
            {selectedRun ? (
              <>
                <div id="automations-run-detail-header" className="automation-run-detail-header">
                  <div id="automations-run-detail-copy" className="automation-panel__copy">
                    <h4 id="automations-run-detail-title" className="automation-panel__title automation-panel__title--compact">Run {selectedRun.run_id}</h4>
                    <p id="automations-run-detail-description" className="automation-panel__description">
                      {selectedRun.status} · {formatDateTime(selectedRun.started_at)} · {formatDuration(selectedRun.duration_ms)}
                    </p>
                  </div>
                </div>
                <div id="automations-run-detail-steps" className="automation-run-step-list">
                  {selectedRun.steps.map((step, index) => (
                    <article key={step.step_id} id={`automations-run-step-${step.step_id}`} className="automation-run-step-card">
                      <div id={`automations-run-step-header-${step.step_id}`} className="automation-run-step-card__header">
                        <span id={`automations-run-step-index-${step.step_id}`} className="automation-run-step-card__index">{index + 1}</span>
                        <div id={`automations-run-step-copy-${step.step_id}`} className="automation-run-step-card__copy">
                          <span id={`automations-run-step-name-${step.step_id}`} className="automation-run-step-card__title">{step.step_name}</span>
                          <span id={`automations-run-step-status-${step.step_id}`} className={`automation-run-step-card__status automation-run-step-card__status--${getRunStatusTone(step.status)}`}>{step.status}</span>
                        </div>
                        <span id={`automations-run-step-duration-${step.step_id}`} className="automation-run-step-card__meta">{formatDuration(step.duration_ms)}</span>
                      </div>
                      <p id={`automations-run-step-request-${step.step_id}`} className="automation-run-step-card__text">{step.request_summary || "No request summary recorded."}</p>
                      <p id={`automations-run-step-response-${step.step_id}`} className="automation-run-step-card__text">{step.response_summary || "No response summary recorded."}</p>
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <div id="automations-run-detail-empty-state" className="automation-empty-state">
                Select a run to inspect the step-by-step trace.
              </div>
            )}
          </div>
        </div>
      </section>

      <Dialog.Root open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop id="automations-delete-dialog-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup id="automations-delete-dialog" className="automation-dialog">
            <Dialog.Title id="automations-delete-dialog-title" className="automation-dialog__title">Delete automation?</Dialog.Title>
            <Dialog.Description id="automations-delete-dialog-description" className="automation-dialog__description">
              This removes the automation definition and its step layout. Existing run history stays available only through the recorded runs API.
            </Dialog.Description>
            <div id="automations-delete-dialog-actions" className="automation-dialog__actions">
              <Dialog.Close id="automations-delete-dialog-cancel" className="button button--secondary">Cancel</Dialog.Close>
              <button
                id="automations-delete-dialog-confirm"
                type="button"
                className="button button--secondary"
                onClick={() => deleteAutomation().catch((error: Error) => {
                  setFeedback(error.message);
                  setFeedbackTone("error");
                })}
              >
                Confirm delete
              </button>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};
