import type {
  AutomationStep,
  AutomationBuilderMetadata,
  ConnectorActivityDefinition,
  ConnectorRecord,
  HttpPreset,
  InboundApiOption,
  ScriptLanguageOption,
  ScriptLibraryItem,
  StepType,
  ToolManifestEntry,
  TriggerType,
  WorkflowBuilderConnectorOption
} from "./types";

export type {
  AutomationBuilderMetadata,
  ConnectorActivityDefinition,
  ConnectorRecord,
  HttpPreset,
  InboundApiOption,
  ScriptLanguageOption,
  ScriptLibraryItem,
  ToolManifestEntry,
  TriggerType,
  WorkflowBuilderConnectorOption
};

export type Automation = {
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

export type AutomationDetail = Automation & {
  steps: AutomationStep[];
};

export type AutomationRun = {
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

export type AutomationRunDetail = AutomationRun & {
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

export type WorkflowNodeData = {
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

export type InsertNodeData = {
  canvasNodeId: string;
  insertionIndex: number;
  empty: boolean;
  onInsert?: (index: number) => void;
};

export type NodeMenuState = {
  nodeId: string;
  x: number;
  y: number;
};

export type EditorDrawerState =
  | { kind: "trigger" }
  | { kind: "step"; stepId: string }
  | null;

export type ValidationResultState = {
  kind: "validation";
  valid: boolean;
  issues: string[];
};

export type TestRunResultState = {
  kind: "run";
  run: AutomationRunDetail;
};

export type TestResultState = ValidationResultState | TestRunResultState | null;
export type BuilderMode = "guided" | "canvas";
export type TriggerEditorScreen = "picker" | "detail";

export type ToolDirectoryEntryApi = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  page_href: string;
  inputs: ToolManifestEntry["inputs"];
  outputs: ToolManifestEntry["outputs"];
};

export type BuilderSupportData = {
  builderMetadata: AutomationBuilderMetadata;
  connectors: ConnectorRecord[];
  httpPresets: HttpPreset[];
  inboundApis: InboundApiOption[];
  activityCatalog: ConnectorActivityDefinition[];
  scripts: ScriptLibraryItem[];
  scriptLanguages: ScriptLanguageOption[];
  toolsManifest: ToolManifestEntry[];
};

export type StepSummaryArgs = {
  step: AutomationStep;
  scripts: ScriptLibraryItem[];
  activityCatalog?: ConnectorActivityDefinition[];
  toolsManifest?: ToolManifestEntry[];
};

export type StepAccentMap = Record<StepType, WorkflowNodeData["accent"]>;
