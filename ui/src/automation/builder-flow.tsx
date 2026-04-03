import {
  MarkerType,
  Position,
  Handle,
  type Edge,
  type Node,
  type NodeProps
} from "@xyflow/react";
import type { AutomationStep, ConnectorActivityDefinition, InboundApiOption, ScriptLibraryItem, ToolManifestEntry } from "./types";
import type { AutomationDetail, InsertNodeData, WorkflowNodeData } from "./builder-types";
import { getStepSummary, getStepTypeLabel, getTriggerSummary, getTriggerTypeLabel, stepAccentByType } from "./builder-utils";

export const CANVAS_X = 240;
export const TRIGGER_Y = 44;
export const INSERT_Y = 214;
export const STEP_Y = 304;
export const STEP_GAP = 228;
export const CANVAS_SURFACE_HEIGHT = 720;
export const ZOOM_STEP_COUNT_THRESHOLD = 5;

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

export const nodeTypes = {
  automationNode: FlowAutomationNode,
  insertNode: FlowInsertNode
};

type FlowNodeArgs = {
  currentAutomation: AutomationDetail;
  selectedNodeId: string;
  inboundApis: InboundApiOption[];
  scripts: ScriptLibraryItem[];
  activityCatalog: ConnectorActivityDefinition[];
  toolsManifest: ToolManifestEntry[];
  hasBranchSteps: boolean;
  openNodeMenu: (nodeId: string, anchor: DOMRect | { x: number; y: number }) => void;
  openAddStepFlow: (index: number) => void;
};

export const createFlowNodes = ({
  currentAutomation,
  selectedNodeId,
  inboundApis,
  scripts,
  activityCatalog,
  toolsManifest,
  hasBranchSteps,
  openNodeMenu,
  openAddStepFlow
}: FlowNodeArgs): Array<Node<WorkflowNodeData | InsertNodeData>> => {
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
        onInsert: openAddStepFlow
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
        summary: getStepSummary({ step, scripts, activityCatalog, toolsManifest }),
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
      onInsert: openAddStepFlow
    }
  });

  return nodes;
};

export const createFlowEdges = (steps: AutomationStep[], selectedNodeId: string): Edge[] => {
  const orderedNodeIds = [
    "trigger-node",
    ...steps.flatMap((step, index) => [`insert-node-${index}`, `step-node-${step.id}`]),
    `insert-node-${steps.length}`
  ];

  const edges: Edge[] = orderedNodeIds.slice(0, -1).map((sourceNodeId, index) => ({
    id: `automation-canvas-edge-${sourceNodeId}-${orderedNodeIds[index + 1]}`,
    source: sourceNodeId,
    target: orderedNodeIds[index + 1],
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
    animated: orderedNodeIds[index + 1] === selectedNodeId
  }));

  steps.forEach((step) => {
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
};
