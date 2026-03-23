import { useEffect, useMemo, useRef, useState, startTransition } from "react";
import { normalizeRequestError, requestJson } from "../lib/request";
import { Dialog } from "@base-ui/react/dialog";
import { Select } from "@base-ui/react/select";
import { Switch } from "@base-ui/react/switch";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
  Position,
  Handle
} from "@xyflow/react";
import type {
  TriggerType,
  StepType,
  AutomationStep,
  ConnectorRecord,
  ConnectorActivityDefinition,
  ToolManifestEntry,
  InboundApiOption,
  ScriptLibraryItem
} from "./types";
import { stepTypeOptions, triggerTypeOptions, cloneStepTemplate, createDraftStepId, getDefaultStepName } from "./types";
import { AddStepModal } from "./add-step-modal";
import { LogStepForm } from "./step-modals/log-step-form";
import { HttpStepForm } from "./step-modals/http-step-form";
import { ConnectorActivityStepForm } from "./step-modals/connector-activity-step-form";
import { ScriptStepForm } from "./step-modals/script-step-form";
import { ToolStepFields } from "./tool-step-fields";
import { TriggerSettingsForm } from "./trigger-settings-form";
import { CollapsibleSection } from "../lib/collapsible-section";

declare global {
  interface Window {
    TOOLS_MANIFEST?: ToolManifestEntry[];
    INBOUND_APIS?: { id: string; name: string }[];
    CONNECTORS?: { id: string; name: string }[];
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<unknown>;
    };
  }
}

const requestJsonCompat = async <T = unknown>(path: string, options?: RequestInit): Promise<T> => {
  if (typeof window !== "undefined" && typeof window.Malcom?.requestJson === "function") {
    return (await window.Malcom.requestJson(path, options)) as T;
  }
  return (await requestJson(path, options)) as T;
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
    response_body_json: unknown | null;
    extracted_fields_json: Record<string, unknown> | null;
  }>;
};

type WorkflowNodeData = {
  canvasNodeId: string;
  kind: "trigger" | "step";
  label: string;
  subtitle: string;
  summary: string;
  accent: "trigger" | "log" | "http" | "connector" | "script" | "tool" | "condition" | "llm";
  selected: boolean;
  isMergeTarget?: boolean;
  hasBranchEdges?: boolean;
  onOpenMenu?: (nodeId: string, anchor: DOMRect) => void;
};

type InsertNodeData = {
  canvasNodeId: string;
  insertionIndex: number;
  empty: boolean;
  onInsert?: (index: number) => void;
};

type NodeMenuState = {
  nodeId: string;
  x: number;
  y: number;
};

type EditorDrawerState =
  | { kind: "trigger" }
  | { kind: "step"; stepId: string }
  | null;

type ValidationResultState = {
  kind: "validation";
  valid: boolean;
  issues: string[];
};

type TestRunResultState = {
  kind: "run";
  run: AutomationRunDetail;
};

type TestResultState = ValidationResultState | TestRunResultState | null;

const CANVAS_X = 240;
const TRIGGER_Y = 44;
const INSERT_Y = 214;
const STEP_Y = 304;
const STEP_GAP = 228;
// Zoom gate: height of the canvas surface element (matches CSS .automation-canvas-surface--full)
const CANVAS_SURFACE_HEIGHT = 720;
// Zoom is also enabled when step count reaches this threshold regardless of overflow
const ZOOM_STEP_COUNT_THRESHOLD = 5;

const stepAccentByType: Record<StepType, WorkflowNodeData["accent"]> = {
  log: "log",
  outbound_request: "http",
  connector_activity: "connector",
  script: "script",
  tool: "tool",
  condition: "condition",
  llm_chat: "llm"
};

const normalizeStep = (step: AutomationStep): AutomationStep => ({
  ...step,
  id: step.id || createDraftStepId(),
  name: step.name || getDefaultStepName(step.type),
  config: { ...step.config }
});

const emptyDetail = (): AutomationDetail => ({
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

const getTriggerSummary = (automation: AutomationDetail, inboundApis: InboundApiOption[]) => {
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

const isInboundApiSelectionMissing = (automation: AutomationDetail, inboundApis: InboundApiOption[]) => {
  if (automation.trigger_type !== "inbound_api") {
    return false;
  }
  const inboundApiId = automation.trigger_config.inbound_api_id;
  if (!inboundApiId) {
    return false;
  }
  return !inboundApis.some((option) => option.id === inboundApiId);
};

const getStepSummary = (step: AutomationStep, scripts: ScriptLibraryItem[], activityCatalog: ConnectorActivityDefinition[] = []) => {
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
      const manifest = (window.TOOLS_MANIFEST || []).find((tool) => tool.id === step.config.tool_id);
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

const validateAutomationDefinition = (automation: AutomationDetail, inboundApis: InboundApiOption[], activityCatalog: ConnectorActivityDefinition[], connectors: ConnectorRecord[]) => {
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
      const manifest = (window.TOOLS_MANIFEST || []).find((tool) => tool.id === step.config.tool_id);
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

const FlowAutomationNode = ({ id, data }: NodeProps<Node<WorkflowNodeData>>) => {
  const isTriggerNode = data.kind === "trigger";
  const triggerCompactTitle = `Trigger:${data.label.toLowerCase()}`;

  return (
    <div
      id={data.canvasNodeId}
      className={`automation-node nopan automation-node--${data.kind} automation-node--accent-${data.accent}${data.selected ? " automation-node--selected" : ""}${data.isMergeTarget ? " automation-node--merge-target" : ""}${isTriggerNode ? " automation-node--trigger-compact" : ""}`}
    >
      <Handle type="target" position={Position.Top} className="automation-node__handle" isConnectable={false} />
      {data.isMergeTarget ? (
        <div id={`${data.canvasNodeId}-merge-badge`} className="automation-merge-badge" aria-label="Merge target">⇢ merge</div>
      ) : null}
      <div id={`${data.canvasNodeId}-header`} className="automation-node__header">
        <div>
          {isTriggerNode ? null : (
            <div id={`${data.canvasNodeId}-eyebrow`} className="automation-node__eyebrow">
              {data.subtitle}
            </div>
          )}
          <div id={`${data.canvasNodeId}-title`} className="automation-node__title">
            {isTriggerNode ? triggerCompactTitle : data.label}
          </div>
        </div>
        {data.selected ? (
          <button
            id={`${data.canvasNodeId}-actions-button`}
            type="button"
            className="automation-node__actions-button nodrag nopan"
            aria-label="Open node actions"
            onClick={(event) => {
              event.stopPropagation();
              data.onOpenMenu?.(id, event.currentTarget.getBoundingClientRect());
            }}
          >
            ...
          </button>
        ) : null}
      </div>
      {isTriggerNode ? null : (
        <div id={`${data.canvasNodeId}-summary`} className="automation-node__summary">
          {data.summary}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="automation-node__handle" isConnectable={false} />
    </div>
  );
};

const FlowInsertNode = ({ data }: NodeProps<Node<InsertNodeData>>) => (
  <div id={data.canvasNodeId} className={`automation-insert-node nopan${data.empty ? " automation-insert-node--empty" : ""}`}>
    <Handle type="target" position={Position.Top} className="automation-insert-node__handle" isConnectable={false} />
    <button
      id={`${data.canvasNodeId}-button`}
      type="button"
      className="automation-insert-node__button"
      onClick={(event) => {
        event.stopPropagation();
        data.onInsert?.(data.insertionIndex);
      }}
    >
      {data.empty ? "Add your first step" : "Add step here"}
    </button>
    <Handle type="source" position={Position.Bottom} className="automation-insert-node__handle" isConnectable={false} />
  </div>
);

const nodeTypes = {
  automationNode: FlowAutomationNode,
  insertNode: FlowInsertNode
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
}) => {
  const popupId = `${rootId}-popup`;
  const listId = `${rootId}-list`;

  return (
    <Select.Root value={value} onValueChange={(nextValue) => onValueChange(String(nextValue) as T)}>
      <Select.Trigger id={rootId} className="automation-select-trigger" aria-labelledby={labelId} aria-controls={listId}>
        <Select.Value placeholder={placeholder} />
        <Select.Icon className="automation-select-trigger__icon">▾</Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner className="automation-select-positioner">
          <Select.Popup id={popupId} className="automation-select-popup">
            <Select.List id={listId} className="automation-select-list" aria-labelledby={labelId}>
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
};

const getNodeMenuLabel = (nodeId: string, steps: AutomationStep[]) => {
  if (nodeId === "trigger-node") {
    return "Trigger";
  }
  const step = steps.find((candidate) => `step-node-${candidate.id}` === nodeId);
  return step?.name || "Step";
};

export const AutomationApp = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [currentAutomation, setCurrentAutomation] = useState<AutomationDetail>(emptyDetail);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("trigger-node");
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [inboundApis, setInboundApis] = useState<InboundApiOption[]>([]);
  const [activityCatalog, setActivityCatalog] = useState<ConnectorActivityDefinition[]>([]);
  const [scripts, setScripts] = useState<ScriptLibraryItem[]>([]);
  const [feedback, setFeedback] = useState("");
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error" | "">("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [addStepModalOpen, setAddStepModalOpen] = useState(false);
  const [editorDrawer, setEditorDrawer] = useState<EditorDrawerState>(null);
  const [nodeMenu, setNodeMenu] = useState<NodeMenuState | null>(null);
  const [pendingInsertIndex, setPendingInsertIndex] = useState(0);
  const [testResults, setTestResults] = useState<TestResultState>(null);
  const [advancedLabelOpen, setAdvancedLabelOpen] = useState(false);
  const nodeMenuRef = useRef<HTMLDivElement | null>(null);
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);

  // Derived: any condition step with explicit branch targets locks drag-reorder and widens canvas
  const hasBranchSteps = useMemo(
    () => currentAutomation.steps.some((s) => s.type === "condition" && (s.on_true_step_id || s.on_false_step_id)),
    [currentAutomation.steps]
  );

  // Zoom gate: enable when content overflows canvas height OR step count hits threshold
  const contentHeight = STEP_Y + Math.max(0, currentAutomation.steps.length) * STEP_GAP + 200;
  const zoomEnabled = contentHeight > CANVAS_SURFACE_HEIGHT * 0.85 || currentAutomation.steps.length >= ZOOM_STEP_COUNT_THRESHOLD;

  // Lock-to-fit when zoom is not needed (small flows)
  useEffect(() => {
    if (!zoomEnabled && reactFlowRef.current) {
      reactFlowRef.current.fitView({ padding: 0.2, duration: 300 });
    }
  }, [zoomEnabled, currentAutomation.steps.length]);

  const selectedStep = currentAutomation.steps.find((step) => `step-node-${step.id}` === selectedNodeId) || null;
  const selectedStepIndex = selectedStep ? currentAutomation.steps.findIndex((step) => step.id === selectedStep.id) : -1;
  const drawerStep = editorDrawer?.kind === "step"
    ? currentAutomation.steps.find((step) => step.id === editorDrawer.stepId) || null
    : null;

  const openNodeMenu = (nodeId: string, anchor: DOMRect | { x: number; y: number }) => {
    const x = anchor instanceof DOMRect ? anchor.right + 8 : anchor.x;
    const y = anchor instanceof DOMRect ? anchor.top : anchor.y;
    setSelectedNodeId(nodeId);
    setNodeMenu({
      nodeId,
      x: Math.max(16, Math.min(window.innerWidth - 220, x)),
      y: Math.max(16, Math.min(window.innerHeight - 180, y))
    });
  };

  const closeNodeMenu = () => setNodeMenu(null);

  const closeEditorDrawer = () => {
    setEditorDrawer(null);
    setAdvancedLabelOpen(false);
  };

  const openEditorForNode = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    if (nodeId === "trigger-node") {
      setEditorDrawer({ kind: "trigger" });
      setAdvancedLabelOpen(false);
      closeNodeMenu();
      return;
    }
    const stepId = nodeId.replace("step-node-", "");
    setEditorDrawer({ kind: "step", stepId });
    setAdvancedLabelOpen(false);
    closeNodeMenu();
  };

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

  const updateDrawerStep = (updater: (step: AutomationStep) => AutomationStep) => {
    if (!drawerStep) {
      return;
    }
    setCurrentAutomation((current) => ({
      ...current,
      steps: current.steps.map((step) => (step.id === drawerStep.id ? normalizeStep(updater(step)) : step))
    }));
  };

  const updateStepOrder = (nextSteps: AutomationStep[]) => {
    setCurrentAutomation((current) => ({
      ...current,
      steps: nextSteps.map(normalizeStep),
      step_count: nextSteps.length
    }));
  };

  const insertStep = (step: AutomationStep, index: number) => {
    const normalizedStep = normalizeStep({
      ...step,
      name: step.name.trim() || getDefaultStepName(step.type)
    });
    setCurrentAutomation((current) => {
      const nextSteps = [...current.steps];
      nextSteps.splice(index, 0, normalizedStep);
      return {
        ...current,
        steps: nextSteps,
        step_count: nextSteps.length
      };
    });
    setSelectedNodeId(`step-node-${normalizedStep.id}`);
  };

  const removeStepById = (stepId: string) => {
    setCurrentAutomation((current) => {
      const nextSteps = current.steps.filter((step) => step.id !== stepId);
      return {
        ...current,
        steps: nextSteps,
        step_count: nextSteps.length
      };
    });
    setSelectedNodeId("trigger-node");
    closeEditorDrawer();
    closeNodeMenu();
  };

  const loadBuilderSupportData = async () => {
    const [settings, inbound, scriptItems, activityItems] = await Promise.all([
      requestJsonCompat<{ connectors?: { records?: ConnectorRecord[] } }>("/api/v1/settings"),
      requestJsonCompat<Array<{ id: string; name: string }>>("/api/v1/inbound"),
      requestJsonCompat<ScriptLibraryItem[]>("/api/v1/scripts"),
      requestJsonCompat<ConnectorActivityDefinition[]>("/api/v1/connectors/activity-catalog")
    ]);
    setConnectors(settings.connectors?.records || []);
    setInboundApis(inbound.map((api) => ({ id: api.id, name: api.name })));
    setScripts(scriptItems);
    setActivityCatalog(activityItems);
  };

  const applyNewAutomationDraft = ({ updateUrl = true }: { updateUrl?: boolean } = {}) => {
    startTransition(() => {
      setCurrentAutomation(emptyDetail());
      setSelectedNodeId("trigger-node");
      setDeleteDialogOpen(false);
      setAddStepModalOpen(false);
      closeEditorDrawer();
      closeNodeMenu();
      setTestResults(null);
    });
    if (updateUrl) {
      window.history.replaceState({}, "", "builder.html?new=true");
    }
    setFeedback("");
    setFeedbackTone("");
  };

  const selectAutomation = async (automationId: string) => {
    const detail = await requestJsonCompat<AutomationDetail>(`/api/v1/automations/${automationId}`);

    startTransition(() => {
      setCurrentAutomation(sanitizeAutomationDetail(detail));
      setSelectedNodeId("trigger-node");
      closeEditorDrawer();
      closeNodeMenu();
      setTestResults(null);
    });
  };

  const loadAutomations = async (nextSelectedId?: string) => {
    const list = await requestJsonCompat<Automation[]>("/api/v1/automations");
    setAutomations(list);
    const matchingCurrentId = list.some((automation) => automation.id === currentAutomation.id) ? currentAutomation.id : "";
    const targetId = nextSelectedId || matchingCurrentId || list[0]?.id;
    if (!targetId) {
      applyNewAutomationDraft();
      return;
    }
    await selectAutomation(targetId);
    window.history.replaceState({}, "", `builder.html?id=${targetId}`);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get("id") ?? undefined;
    const isNewDraft = params.get("new") === "true";

    Promise.all([
      loadBuilderSupportData(),
      isNewDraft
        ? requestJsonCompat<Automation[]>("/api/v1/automations").then((list) => {
          setAutomations(list);
          applyNewAutomationDraft({ updateUrl: false });
        })
        : loadAutomations(urlId)
    ]).catch((error: Error) => {
      setFeedback(error.message);
      setFeedbackTone("error");
    });
  }, []);

  useEffect(() => {
    const createButton = document.getElementById("automations-create-button");
    const handleCreate = () => {
      applyNewAutomationDraft();
    };
    createButton?.addEventListener("click", handleCreate);
    return () => createButton?.removeEventListener("click", handleCreate);
  }, []);

  useEffect(() => {
    if (!nodeMenu) {
      return undefined;
    }
    const handlePointerDown = (event: PointerEvent) => {
      if (nodeMenuRef.current?.contains(event.target as Node)) {
        return;
      }
      closeNodeMenu();
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [nodeMenu]);

  useEffect(() => {
    if (editorDrawer?.kind === "step" && !currentAutomation.steps.some((step) => step.id === editorDrawer.stepId)) {
      closeEditorDrawer();
    }
  }, [currentAutomation.steps, editorDrawer]);

  const saveAutomation = async () => {
    const issues = validateAutomationDefinition(currentAutomation, inboundApis, activityCatalog, connectors);
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
      ? await requestJsonCompat<AutomationDetail>(`/api/v1/automations/${currentAutomation.id}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await requestJsonCompat<AutomationDetail>("/api/v1/automations", { method: "POST", body: JSON.stringify(payload) });

    setFeedback(currentAutomation.id ? "Automation updated." : "Automation created.");
    setFeedbackTone("success");
    window.history.replaceState({}, "", `builder.html?id=${response.id}`);
    await loadAutomations(response.id);
  };

  const validateAutomation = async () => {
    const localIssues = validateAutomationDefinition(currentAutomation, inboundApis, activityCatalog, connectors);
    if (localIssues.length > 0) {
      setFeedback(localIssues.join(" "));
      setFeedbackTone("error");
      setTestResults({ kind: "validation", valid: false, issues: localIssues });
      return;
    }

    if (!currentAutomation.id) {
      setFeedback("Automation definition is valid.");
      setFeedbackTone("success");
      setTestResults({ kind: "validation", valid: true, issues: [] });
      return;
    }

    const response = await requestJsonCompat<{ valid: boolean; issues: string[] }>(`/api/v1/automations/${currentAutomation.id}/validate`, { method: "POST" });
    setFeedback(response.valid ? "Automation definition is valid." : response.issues.join(" "));
    setFeedbackTone(response.valid ? "success" : "error");
    setTestResults({ kind: "validation", valid: response.valid, issues: response.issues || [] });
  };

  const executeAutomation = async () => {
    if (!currentAutomation.id) {
      setFeedback("Save the automation before running it.");
      setFeedbackTone("error");
      return;
    }
    const run = await requestJsonCompat<AutomationRunDetail>(`/api/v1/automations/${currentAutomation.id}/execute`, { method: "POST" });
    setFeedback("Automation executed.");
    setFeedbackTone("success");
    setTestResults({ kind: "run", run });
    const refreshed = await requestJsonCompat<AutomationDetail>(`/api/v1/automations/${currentAutomation.id}`);
    setCurrentAutomation((current) => ({
      ...sanitizeAutomationDetail(refreshed),
      steps: current.steps
    }));
  };

  const deleteAutomation = async () => {
    if (!currentAutomation.id) {
      applyNewAutomationDraft();
      return;
    }
    await requestJsonCompat(`/api/v1/automations/${currentAutomation.id}`, { method: "DELETE" });
    setDeleteDialogOpen(false);
    setFeedback("Automation deleted.");
    setFeedbackTone("success");
    await loadAutomations();
  };

  const flowNodes = useMemo(() => {
    const nodes: Array<Node<WorkflowNodeData | InsertNodeData>> = [
      {
        id: "trigger-node",
        type: "automationNode",
        position: { x: CANVAS_X, y: TRIGGER_Y },
        draggable: false,
        selectable: true,
        data: {
          canvasNodeId: "automation-canvas-node-trigger",
          kind: "trigger",
          label: getTriggerTypeLabel(currentAutomation.trigger_type),
          subtitle: "Trigger",
          summary: getTriggerSummary(currentAutomation, inboundApis),
          accent: "trigger",
          selected: selectedNodeId === "trigger-node",
          onOpenMenu: openNodeMenu
        }
      }
    ];

    currentAutomation.steps.forEach((step, index) => {
      nodes.push({
        id: `insert-node-${index}`,
        type: "insertNode",
        position: { x: CANVAS_X + 32, y: INSERT_Y + (index * STEP_GAP) },
        draggable: false,
        selectable: false,
        data: {
          canvasNodeId: `automation-canvas-insert-${index}`,
          insertionIndex: index,
          empty: false,
          onInsert: (insertIndex) => {
            setPendingInsertIndex(insertIndex);
            setAddStepModalOpen(true);
          }
        }
      });
      nodes.push({
        id: `step-node-${step.id}`,
        type: "automationNode",
        position: { x: CANVAS_X, y: STEP_Y + (index * STEP_GAP) },
        draggable: !hasBranchSteps,
        selectable: true,
        data: {
          canvasNodeId: `automation-canvas-node-step-${step.id}`,
          kind: "step",
          label: step.name,
          subtitle: `${index + 1}. ${getStepTypeLabel(step.type)}`,
          summary: getStepSummary(step, scripts, activityCatalog),
          accent: stepAccentByType[step.type],
          selected: selectedNodeId === `step-node-${step.id}`,
          isMergeTarget: Boolean(step.is_merge_target),
          hasBranchEdges: step.type === "condition" && Boolean(step.on_true_step_id || step.on_false_step_id),
          onOpenMenu: openNodeMenu
        }
      });
    });

    nodes.push({
      id: `insert-node-${currentAutomation.steps.length}`,
      type: "insertNode",
      position: { x: CANVAS_X + 32, y: INSERT_Y + (currentAutomation.steps.length * STEP_GAP) },
      draggable: false,
      selectable: false,
      data: {
        canvasNodeId: `automation-canvas-insert-${currentAutomation.steps.length}`,
        insertionIndex: currentAutomation.steps.length,
        empty: currentAutomation.steps.length === 0,
        onInsert: (insertIndex) => {
          setPendingInsertIndex(insertIndex);
          setAddStepModalOpen(true);
        }
      }
    });

    return nodes;
  }, [currentAutomation, selectedNodeId, inboundApis, scripts]);

  const flowEdges = useMemo(() => {
    const orderedNodeIds = [
      "trigger-node",
      ...currentAutomation.steps.flatMap((step, index) => [`insert-node-${index}`, `step-node-${step.id}`]),
      `insert-node-${currentAutomation.steps.length}`
    ];

    const edges: Edge[] = orderedNodeIds.slice(0, -1).map((sourceNodeId, index) => ({
      id: `automation-canvas-edge-${sourceNodeId}-${orderedNodeIds[index + 1]}`,
      source: sourceNodeId,
      target: orderedNodeIds[index + 1],
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
      animated: orderedNodeIds[index + 1] === selectedNodeId
    }));

    // Add labeled branch edges for condition steps that have explicit targets
    currentAutomation.steps.forEach((step) => {
      if (step.type !== "condition") return;
      if (step.on_true_step_id) {
        edges.push({
          id: `branch-true-${step.id}-${step.on_true_step_id}`,
          source: `step-node-${step.id}`,
          target: `step-node-${step.on_true_step_id}`,
          type: "smoothstep",
          label: "TRUE",
          labelStyle: { fill: "#15803d", fontWeight: 700, fontSize: 11 },
          labelBgStyle: { fill: "rgba(220, 252, 231, 0.92)", stroke: "#86efac", strokeWidth: 1 },
          style: { stroke: "#16a34a", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#16a34a" },
          animated: false
        } as Edge);
      }
      if (step.on_false_step_id) {
        edges.push({
          id: `branch-false-${step.id}-${step.on_false_step_id}`,
          source: `step-node-${step.id}`,
          target: `step-node-${step.on_false_step_id}`,
          type: "smoothstep",
          label: "FALSE",
          labelStyle: { fill: "#b91c1c", fontWeight: 700, fontSize: 11 },
          labelBgStyle: { fill: "rgba(254, 226, 226, 0.92)", stroke: "#fca5a5", strokeWidth: 1 },
          style: { stroke: "#dc2626", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#dc2626" },
          animated: false
        } as Edge);
      }
    });

    return edges;
  }, [currentAutomation.steps, selectedNodeId]);

  const renderStepEditor = (step: AutomationStep) => {
    const customLabelValue = step.name === getDefaultStepName(step.type) ? "" : step.name;

    return (
      <div id="automations-step-drawer-form" className="automation-form">
        <div id="automations-step-type-field" className="automation-field automation-field--full">
          <span id="automations-step-type-label" className="automation-field__label">Step type</span>
          <FlowSelect
            rootId="automations-step-type-input"
            labelId="automations-step-type-label"
            value={step.type}
            placeholder="Choose a step type"
            options={stepTypeOptions}
            onValueChange={(nextValue) => updateDrawerStep(() => ({
              ...cloneStepTemplate(nextValue),
              id: step.id,
              name: getDefaultStepName(nextValue)
            }))}
          />
        </div>

        {step.type === "log" ? (
          <LogStepForm
            draft={step}
            onChange={(updated) => updateDrawerStep(() => updated)}
          />
        ) : null}

        {step.type === "outbound_request" ? (
          <HttpStepForm
            draft={step}
            connectors={connectors}
            onChange={(updated) => updateDrawerStep(() => updated)}
            idPrefix="automations-step-http"
          />
        ) : null}

        {step.type === "connector_activity" ? (
          <ConnectorActivityStepForm
            draft={step}
            connectors={connectors}
            activityCatalog={activityCatalog}
            onChange={(updated) => updateDrawerStep(() => updated)}
            idPrefix="automations-step-connector-activity"
          />
        ) : null}

        {step.type === "script" ? (
          <ScriptStepForm
            draft={step}
            scripts={scripts}
            onChange={(updated) => updateDrawerStep(() => updated)}
            idPrefix="automations-step"
          />
        ) : null}

        {step.type === "tool" ? (
          <ToolStepFields
            idPrefix="automations-step"
            step={step}
            toolsManifest={window.TOOLS_MANIFEST || []}
            onChange={(updatedStep) => updateDrawerStep(() => updatedStep)}
          />
        ) : null}

        {step.type === "condition" ? (
          <>
            <label id="automations-step-condition-expression-field" className="automation-field automation-field--full">
              <span id="automations-step-condition-expression-label" className="automation-field__label">Expression</span>
              <textarea
                id="automations-step-condition-expression-input"
                className="automation-textarea automation-textarea--code"
                rows={4}
                value={step.config.expression || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, config: { ...currentStep.config, expression: event.target.value } }))}
              />
            </label>
            <div id="automations-step-condition-stop-field" className="automation-switch-field">
              <div id="automations-step-condition-stop-copy" className="automation-switch-field__copy">
                <span id="automations-step-condition-stop-label" className="automation-field__label">Stop on false</span>
                <span id="automations-step-condition-stop-description" className="automation-switch-field__description">
                  Exit the automation when the guard evaluates to false (ignored when a FALSE branch target is set).
                </span>
              </div>
              <Switch.Root
                id="automations-step-condition-stop-input"
                checked={Boolean(step.config.stop_on_false)}
                onCheckedChange={(checked) => updateDrawerStep((currentStep) => ({ ...currentStep, config: { ...currentStep.config, stop_on_false: checked } }))}
                className="automation-switch"
              >
                <Switch.Thumb className="automation-switch__thumb" />
              </Switch.Root>
            </div>

            <label id="automations-step-condition-true-branch-field" className="automation-field automation-field--full">
              <span id="automations-step-condition-true-branch-label" className="automation-field__label">On TRUE — jump to step</span>
              <select
                id="automations-step-condition-true-branch-input"
                className="automation-native-select"
                value={step.on_true_step_id || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, on_true_step_id: event.target.value || null }))}
              >
                <option value="">Continue in sequence</option>
                {currentAutomation.steps.filter((s) => s.id !== step.id).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </label>

            <label id="automations-step-condition-false-branch-field" className="automation-field automation-field--full">
              <span id="automations-step-condition-false-branch-label" className="automation-field__label">On FALSE — jump to step</span>
              <select
                id="automations-step-condition-false-branch-input"
                className="automation-native-select"
                value={step.on_false_step_id || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, on_false_step_id: event.target.value || null }))}
              >
                <option value="">Use &ldquo;stop on false&rdquo; setting</option>
                {currentAutomation.steps.filter((s) => s.id !== step.id).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </label>
          </>
        ) : null}

        {step.type === "llm_chat" ? (
          <>
            <label id="automations-step-llm-model-field" className="automation-field automation-field--full">
              <span id="automations-step-llm-model-label" className="automation-field__label">Model override</span>
              <input
                id="automations-step-llm-model-input"
                className="automation-input"
                value={step.config.model_identifier || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, config: { ...currentStep.config, model_identifier: event.target.value } }))}
              />
            </label>
            <label id="automations-step-llm-system-field" className="automation-field automation-field--full">
              <span id="automations-step-llm-system-label" className="automation-field__label">System prompt</span>
              <textarea
                id="automations-step-llm-system-input"
                className="automation-textarea automation-textarea--code"
                rows={5}
                value={step.config.system_prompt || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, config: { ...currentStep.config, system_prompt: event.target.value } }))}
              />
            </label>
            <label id="automations-step-llm-user-field" className="automation-field automation-field--full">
              <span id="automations-step-llm-user-label" className="automation-field__label">User prompt</span>
              <textarea
                id="automations-step-llm-user-input"
                className="automation-textarea automation-textarea--code"
                rows={7}
                value={step.config.user_prompt || ""}
                onChange={(event) => updateDrawerStep((currentStep) => ({ ...currentStep, config: { ...currentStep.config, user_prompt: event.target.value } }))}
              />
            </label>
          </>
        ) : null}

        <details id="automations-step-advanced-section" className="automation-advanced-section" open={advancedLabelOpen} onToggle={(event) => setAdvancedLabelOpen((event.currentTarget as HTMLDetailsElement).open)}>
          <summary id="automations-step-advanced-summary" className="automation-advanced-section__summary">
            Advanced
          </summary>
          <div id="automations-step-advanced-content" className="automation-advanced-section__content">
            <label id="automations-step-name-field" className="automation-field automation-field--full">
              <span id="automations-step-name-label" className="automation-field__label">Custom label (optional)</span>
              <input
                id="automations-step-name-input"
                className="automation-input"
                value={customLabelValue}
                placeholder={getDefaultStepName(step.type)}
                onChange={(event) => updateDrawerStep((currentStep) => ({
                  ...currentStep,
                  name: event.target.value.trim() || getDefaultStepName(currentStep.type)
                }))}
              />
            </label>

            <div id="automations-step-merge-target-field" className="automation-switch-field">
              <div id="automations-step-merge-target-copy" className="automation-switch-field__copy">
                <span id="automations-step-merge-target-label" className="automation-field__label">Merge target</span>
                <span id="automations-step-merge-target-description" className="automation-switch-field__description">
                  Mark this step as the convergence point where conditional branches rejoin.
                </span>
              </div>
              <Switch.Root
                id="automations-step-merge-target-input"
                checked={Boolean(step.is_merge_target)}
                onCheckedChange={(checked) => updateDrawerStep((currentStep) => ({ ...currentStep, is_merge_target: checked }))}
                className="automation-switch"
              >
                <Switch.Thumb className="automation-switch__thumb" />
              </Switch.Root>
            </div>
          </div>
        </details>

        <div id="automations-step-danger-zone" className="automation-danger-zone">
          <span id="automations-step-danger-label" className="automation-field__label">Danger zone</span>
          <button
            id="automations-step-remove-button"
            type="button"
            className="button button--danger automation-danger-zone__button"
            onClick={() => {
              if (step.id) {
                removeStepById(step.id);
              }
            }}
          >
            Remove step
          </button>
        </div>
      </div>
    );
  };

  return (
    <div id="automations-app-shell" className="automations-app automations-builder-app">
      <CollapsibleSection
        id="automations-workflow-bar"
        label="Automation settings"
        classes={{
          section: "automation-workflow-bar",
          sectionCollapsed: "automation-workflow-bar--collapsed",
          toggle: "automation-workflow-bar__top-toggle",
          label: "automation-workflow-bar__top-label",
          symbol: "automation-workflow-bar__collapse-symbol",
          body: "automation-workflow-bar__body",
          bodyCollapsed: "automation-workflow-bar__body--hidden"
        }}
      >
          <div id="automations-workflow-bar-content" className="automation-workflow-bar__content">
            <div id="automations-workflow-bar-fields" className="automation-workflow-bar__fields">
              <label id="automations-workflow-name-field" className="automation-field automation-field--full automation-workflow-bar__field">
                <span id="automations-workflow-name-label" className="automation-field__label">Automation name</span>
                <input
                  id="automations-workflow-name-input"
                  className="automation-input"
                  placeholder="Name this automation"
                  value={currentAutomation.name}
                  onChange={(event) => patchAutomation({ name: event.target.value })}
                />
              </label>
              <label id="automations-workflow-description-field" className="automation-field automation-field--full automation-workflow-bar__field">
                <span id="automations-workflow-description-label" className="automation-field__label">Automation description</span>
                <textarea
                  id="automations-workflow-description-input"
                  className="automation-textarea"
                  rows={2}
                  placeholder="Describe what this automation is for"
                  value={currentAutomation.description}
                  onChange={(event) => patchAutomation({ description: event.target.value })}
                />
              </label>
            </div>

            <div id="automations-workflow-bar-meta" className="automation-workflow-bar__meta">
              <div id="automations-workflow-enabled-field" className="automation-switch-field automation-workflow-card">
                <div id="automations-workflow-enabled-copy" className="automation-switch-field__copy">
                  <span id="automations-workflow-enabled-label" className="automation-field__label">Enabled</span>
                  <span id="automations-workflow-enabled-description" className="automation-switch-field__description">
                    Edit the trigger directly from the canvas trigger node.
                  </span>
                </div>
                <Switch.Root
                  id="automations-workflow-enabled-input"
                  checked={currentAutomation.enabled}
                  onCheckedChange={(checked) => patchAutomation({ enabled: checked })}
                  className="automation-switch"
                >
                  <Switch.Thumb className="automation-switch__thumb" />
                </Switch.Root>
              </div>
            </div>

          </div>
      </CollapsibleSection>

      <div
        id="automations-feedback-banner"
        className={feedbackTone ? `automation-feedback automation-feedback--${feedbackTone}` : "automation-feedback"}
        hidden={!feedback}
      >
        {feedback}
      </div>

      <section id="automations-canvas-panel" className="automation-panel automation-panel--canvas automation-panel--canvas-full">
        <div id="automations-canvas-header" className="automation-panel__header automation-panel__header--canvas">
          <div id="automations-canvas-copy" className="automation-panel__copy">
            <p id="automations-canvas-eyebrow" className="automation-panel__eyebrow">Builder</p>
            <div className="title-row">
              <h3 id="automations-canvas-title" className="automation-panel__title">Automation canvas</h3>
              <button type="button" id="automations-canvas-description-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-canvas-description">i</button>
            </div>
            <p id="automations-canvas-description" className="automation-panel__description" hidden>Select a node, drag steps to reorder them, and use node actions to edit.</p>
          </div>
          <div id="automations-canvas-chips" className="automation-canvas-chips">
            <div id="automations-canvas-selection-chip" className="automation-selection-chip" hidden={!selectedNodeId}>
              Selected: {getNodeMenuLabel(selectedNodeId, currentAutomation.steps)}
            </div>
            {hasBranchSteps ? (
              <div id="automations-canvas-branch-chip" className="automation-selection-chip automation-selection-chip--branch" title="Drag reorder is disabled while conditional branches are configured. Remove branch targets to re-enable.">
                Branch mode
              </div>
            ) : null}
          </div>
          <div id="automations-workflow-actions" className="automation-workflow-bar__actions">
            <button id="automations-save-button" type="button" className="primary-action-button" onClick={() => saveAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
              Save
            </button>
            <button id="automations-validate-button" type="button" className="button button--secondary" onClick={() => validateAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
              Validate
            </button>
            <button id="automations-run-button" type="button" className="button button--secondary" onClick={() => executeAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
              Run now
            </button>
            <button id="automations-new-button" type="button" className="button button--secondary" onClick={() => applyNewAutomationDraft()}>
              New draft
            </button>
            <button id="automations-delete-button" type="button" className="button button--danger" onClick={() => setDeleteDialogOpen(true)}>
              Delete
            </button>
          </div>
        </div>

        <div id="automations-canvas-surface" className="automation-canvas-surface automation-canvas-surface--full">
          <ReactFlow
            id="automations-canvas"
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            deleteKeyCode={null}
            connectOnClick={false}
            nodesConnectable={false}
            edgesFocusable={false}
            elementsSelectable
            snapToGrid
            snapGrid={[16, 16]}
            onPaneClick={() => {
              setSelectedNodeId("");
              closeNodeMenu();
            }}
            onNodeClick={(_, node) => {
              if (String(node.id).startsWith("insert-node-")) {
                return;
              }
              setSelectedNodeId(node.id);
              closeNodeMenu();
            }}
            onNodeDoubleClick={(_, node) => {
              if (String(node.id).startsWith("insert-node-")) {
                return;
              }
              openEditorForNode(node.id);
            }}
            onNodeContextMenu={(event, node) => {
              if (String(node.id).startsWith("insert-node-")) {
                return;
              }
              event.preventDefault();
              openNodeMenu(node.id, { x: event.clientX, y: event.clientY });
            }}
            onNodeDragStop={(_, node) => {
              if (!String(node.id).startsWith("step-node-")) {
                return;
              }
              const stepId = String(node.id).replace("step-node-", "");
              const fromIndex = currentAutomation.steps.findIndex((step) => step.id === stepId);
              if (fromIndex < 0) {
                return;
              }
              const targetIndex = Math.min(
                currentAutomation.steps.length - 1,
                Math.max(0, Math.round((node.position.y - STEP_Y) / STEP_GAP))
              );
              if (targetIndex !== fromIndex) {
                updateStepOrder(reorderSteps(currentAutomation.steps, fromIndex, targetIndex));
              }
              setSelectedNodeId(String(node.id));
            }}
            onInit={(instance) => { reactFlowRef.current = instance; }}
            zoomOnScroll={zoomEnabled}
            zoomOnPinch={zoomEnabled}
            zoomOnDoubleClick={false}
            panOnScroll={zoomEnabled}
            minZoom={zoomEnabled ? 0.6 : 1}
            maxZoom={zoomEnabled ? 1.25 : 1}
            proOptions={{ hideAttribution: true }}
          >
            <Background id="automations-canvas-background" color="#dbe3f1" gap={24} size={1.2} />
            {zoomEnabled ? <Controls id="automations-canvas-controls" position="bottom-left" /> : null}
          </ReactFlow>
        </div>
      </section>

      {nodeMenu ? (
        <div
          id="automations-node-menu"
          ref={nodeMenuRef}
          className="automation-node-menu"
          style={{ left: nodeMenu.x, top: nodeMenu.y }}
          role="menu"
          aria-label="Node actions"
        >
          <div id="automations-node-menu-heading" className="automation-node-menu__heading">
            {getNodeMenuLabel(nodeMenu.nodeId, currentAutomation.steps)}
          </div>
          <button
            id="automations-node-menu-edit"
            type="button"
            className="automation-node-menu__item"
            onClick={() => openEditorForNode(nodeMenu.nodeId)}
          >
            Edit
          </button>
          <button
            id="automations-node-menu-add-after"
            type="button"
            className="automation-node-menu__item automation-node-menu__item--success"
            onClick={() => {
              const insertionIndex = nodeMenu.nodeId === "trigger-node"
                ? 0
                : currentAutomation.steps.findIndex((step) => `step-node-${step.id}` === nodeMenu.nodeId) + 1;
              setPendingInsertIndex(Math.max(0, insertionIndex));
              setAddStepModalOpen(true);
              closeNodeMenu();
            }}
          >
            Add step after
          </button>
          {nodeMenu.nodeId !== "trigger-node" ? (
            <button
              id="automations-node-menu-remove"
              type="button"
              className="automation-node-menu__item automation-node-menu__item--danger"
              onClick={() => {
                const stepId = nodeMenu.nodeId.replace("step-node-", "");
                removeStepById(stepId);
              }}
            >
              Remove step
            </button>
          ) : null}
        </div>
      ) : null}

      <Dialog.Root open={editorDrawer !== null} onOpenChange={(open) => { if (!open) closeEditorDrawer(); }}>
        <Dialog.Portal>
          <Dialog.Backdrop id="automations-editor-drawer-backdrop" className="automation-dialog-backdrop automation-dialog-backdrop--drawer" />
          <Dialog.Popup
            id="automations-editor-drawer"
            className="automation-side-drawer automation-side-drawer--editor"
            aria-labelledby="automations-editor-drawer-title"
            aria-describedby="automations-editor-drawer-description"
          >
            <div id="automations-editor-drawer-header" className="automation-side-drawer__header">
              <div id="automations-editor-drawer-copy" className="automation-panel__copy">
                <Dialog.Title id="automations-editor-drawer-title" className="automation-dialog__title">
                  {editorDrawer?.kind === "trigger" ? "Edit trigger" : drawerStep?.name || "Edit step"}
                </Dialog.Title>
                <Dialog.Description id="automations-editor-drawer-description" className="automation-dialog__description">
                  {editorDrawer?.kind === "trigger"
                    ? "Configure when the automation runs. Automation naming stays separate in the builder header."
                    : "Adjust the selected step. Essential fields come first, with optional custom labeling under Advanced."}
                </Dialog.Description>
              </div>
              <Dialog.Close
                id="automations-editor-drawer-close"
                className="modal__close-icon-button automation-side-drawer__close"
                aria-label="Close editor drawer"
              >
                ×
              </Dialog.Close>
            </div>

            <div id="automations-editor-drawer-body" className="automation-side-drawer__body">
              {editorDrawer?.kind === "trigger" ? (
                <TriggerSettingsForm
                  idPrefix="automations-trigger-drawer"
                  value={currentAutomation}
                  onPatch={patchAutomation}
                  showWorkflowFields={false}
                  showEnabledField={false}
                  inboundApiOptions={inboundApis}
                  inboundApiMissingSelection={isInboundApiSelectionMissing(currentAutomation, inboundApis)}
                />
              ) : drawerStep ? renderStepEditor(drawerStep) : null}
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={testResults !== null} onOpenChange={(open) => { if (!open) setTestResults(null); }}>
        <Dialog.Portal>
          <Dialog.Backdrop id="automations-test-results-backdrop" className="automation-dialog-backdrop automation-dialog-backdrop--drawer" />
          <Dialog.Popup
            id="automations-test-results-drawer"
            className="automation-side-drawer automation-side-drawer--results"
            aria-labelledby="automations-test-results-title"
            aria-describedby="automations-test-results-description"
          >
            <div id="automations-test-results-header" className="automation-side-drawer__header">
              <div id="automations-test-results-copy" className="automation-panel__copy">
                <Dialog.Title id="automations-test-results-title" className="automation-dialog__title">
                  {testResults?.kind === "validation" ? "Validation results" : "Test run results"}
                </Dialog.Title>
                <Dialog.Description id="automations-test-results-description" className="automation-dialog__description">
                  {testResults?.kind === "validation"
                    ? "Validation only appears when you test the draft."
                    : "Execution output is shown on demand so the builder can stay focused on composition."}
                </Dialog.Description>
              </div>
              <Dialog.Close
                id="automations-test-results-close"
                className="modal__close-icon-button automation-side-drawer__close"
                aria-label="Close test results drawer"
              >
                ×
              </Dialog.Close>
            </div>

            <div id="automations-test-results-body" className="automation-side-drawer__body automation-side-drawer__body--results">
              {testResults?.kind === "validation" ? (
                <div id="automations-validation-results" className="automation-results-panel">
                  <div id="automations-validation-summary" className={`automation-results-banner automation-results-banner--${testResults.valid ? "success" : "error"}`}>
                    {testResults.valid ? "No validation issues detected." : `${testResults.issues.length} validation issue${testResults.issues.length === 1 ? "" : "s"} found.`}
                  </div>
                  {testResults.issues.length > 0 ? (
                    <ul id="automations-validation-issues" className="automation-results-list">
                      {testResults.issues.map((issue, index) => (
                        <li key={`${issue}-${index}`} id={`automations-validation-issue-${index}`} className="automation-results-list__item">
                          {issue}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : testResults?.kind === "run" ? (
                <div id="automations-run-results" className="automation-results-panel automation-results-panel--run">
                  <div id="automations-run-results-summary" className="automation-results-grid">
                    <article id="automations-run-results-status-card" className="automation-runtime-stat">
                      <span id="automations-run-results-status-label" className="automation-runtime-stat__label">Status</span>
                      <span id="automations-run-results-status-value" className="automation-runtime-stat__value">{testResults.run.status}</span>
                    </article>
                    <article id="automations-run-results-trigger-card" className="automation-runtime-stat">
                      <span id="automations-run-results-trigger-label" className="automation-runtime-stat__label">Trigger</span>
                      <span id="automations-run-results-trigger-value" className="automation-runtime-stat__value">{testResults.run.trigger_type}</span>
                    </article>
                    <article id="automations-run-results-started-card" className="automation-runtime-stat">
                      <span id="automations-run-results-started-label" className="automation-runtime-stat__label">Started</span>
                      <span id="automations-run-results-started-value" className="automation-runtime-stat__value">{formatDateTime(testResults.run.started_at)}</span>
                    </article>
                    <article id="automations-run-results-duration-card" className="automation-runtime-stat">
                      <span id="automations-run-results-duration-label" className="automation-runtime-stat__label">Duration</span>
                      <span id="automations-run-results-duration-value" className="automation-runtime-stat__value">{formatDuration(testResults.run.duration_ms)}</span>
                    </article>
                  </div>

                  <div id="automations-run-results-steps" className="automation-run-step-list">
                    {testResults.run.steps.map((step, index) => (
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
                        {step.extracted_fields_json && Object.keys(step.extracted_fields_json).length > 0 ? (
                          <details id={`automations-run-step-extracted-${step.step_id}`} className="automation-run-step-card__details">
                            <summary id={`automations-run-step-extracted-summary-${step.step_id}`} className="automation-run-step-card__details-summary">
                              Extracted values
                            </summary>
                            <pre id={`automations-run-step-extracted-body-${step.step_id}`} className="automation-run-step-card__code">
                              {JSON.stringify(step.extracted_fields_json, null, 2)}
                            </pre>
                          </details>
                        ) : null}
                        {step.response_body_json ? (
                          <details id={`automations-run-step-response-body-${step.step_id}`} className="automation-run-step-card__details">
                            <summary id={`automations-run-step-response-body-summary-${step.step_id}`} className="automation-run-step-card__details-summary">
                              Full JSON response
                            </summary>
                            <pre id={`automations-run-step-response-body-code-${step.step_id}`} className="automation-run-step-card__code">
                              {JSON.stringify(step.response_body_json, null, 2)}
                            </pre>
                          </details>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>

      <AddStepModal
        open={addStepModalOpen}
        onClose={() => setAddStepModalOpen(false)}
        onAdd={(step) => {
          insertStep(step, pendingInsertIndex);
          setAddStepModalOpen(false);
        }}
        connectors={connectors}
        activityCatalog={activityCatalog}
        toolsManifest={window.TOOLS_MANIFEST || []}
        scripts={scripts}
      />

      <Dialog.Root open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop id="automations-delete-dialog-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup id="automations-delete-dialog" className="automation-dialog">
            <div id="automations-delete-dialog-dismiss-row" className="automation-dialog__dismiss-row">
              <Dialog.Close
                id="automations-delete-dialog-cancel"
                className="modal__close-icon-button automation-dialog__close-button"
                aria-label="Close delete automation dialog"
              >
                ×
              </Dialog.Close>
            </div>
            <Dialog.Title id="automations-delete-dialog-title" className="automation-dialog__title">Delete automation?</Dialog.Title>
            <Dialog.Description id="automations-delete-dialog-description" className="automation-dialog__description">
              This removes the automation definition and its step layout. Existing run history stays available through recorded runs.
            </Dialog.Description>
            <div id="automations-delete-dialog-actions" className="automation-dialog__actions">
              <button
                id="automations-delete-dialog-confirm"
                type="button"
                className="button button--danger"
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
