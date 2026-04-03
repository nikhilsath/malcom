import { useEffect, useMemo, useRef, useState, startTransition } from "react";
import { flushSync } from "react-dom";
import type { ReactFlowInstance } from "@xyflow/react";
import { buildDataFlowTokens } from "./data-flow";
import {
  deleteAutomationRequest,
  executeAutomationRequest,
  loadAutomationDetail,
  loadAutomationList,
  loadBuilderSupportData,
  saveAutomationRequest,
  validateAutomationRequest
} from "./builder-api";
import type {
  Automation,
  AutomationDetail,
  BuilderMode,
  ConnectorActivityDefinition,
  ConnectorRecord,
  EditorDrawerState,
  HttpPreset,
  InboundApiOption,
  NodeMenuState,
  ScriptLibraryItem,
  TestResultState,
  ToolManifestEntry,
  TriggerEditorScreen
} from "./builder-types";
import { createFlowEdges, createFlowNodes, CANVAS_SURFACE_HEIGHT, STEP_GAP, STEP_Y, ZOOM_STEP_COUNT_THRESHOLD } from "./builder-flow";
import { emptyDetail, getInitialBuilderMode, inferBuilderModeFromSearch, isInboundApiSelectionMissing, isTriggerConfigured, normalizeStep, reorderSteps, sanitizeAutomationDetail, validateAutomationDefinition } from "./builder-utils";
import { getDefaultStepName, type AutomationStep } from "./types";

export const useAutomationBuilderController = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [currentAutomation, setCurrentAutomation] = useState<AutomationDetail>(emptyDetail);
  const [builderMode, setBuilderMode] = useState<BuilderMode>(getInitialBuilderMode);
  const [selectedNodeId, setSelectedNodeId] = useState<string>("trigger-node");
  const [connectors, setConnectors] = useState<ConnectorRecord[]>([]);
  const [supportDataLoading, setSupportDataLoading] = useState(false);
  const [supportDataError, setSupportDataError] = useState<string | null>(null);
  const [httpPresets, setHttpPresets] = useState<HttpPreset[]>([]);
  const [inboundApis, setInboundApis] = useState<InboundApiOption[]>([]);
  const [activityCatalog, setActivityCatalog] = useState<ConnectorActivityDefinition[]>([]);
  const [scripts, setScripts] = useState<ScriptLibraryItem[]>([]);
  const [toolsManifest, setToolsManifest] = useState<ToolManifestEntry[]>([]);
  const [feedback, setFeedback] = useState("");
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error" | "">("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [addStepModalOpen, setAddStepModalOpen] = useState(false);
  const [editorDrawer, setEditorDrawer] = useState<EditorDrawerState>(null);
  const [triggerEditorScreen, setTriggerEditorScreen] = useState<TriggerEditorScreen>("picker");
  const [nodeMenu, setNodeMenu] = useState<NodeMenuState | null>(null);
  const [pendingInsertIndex, setPendingInsertIndex] = useState(0);
  const [testResults, setTestResults] = useState<TestResultState>(null);
  const [runInFlight, setRunInFlight] = useState(false);
  const [runCompletedFlash, setRunCompletedFlash] = useState(false);
  const [advancedLabelOpen, setAdvancedLabelOpen] = useState(false);
  const nodeMenuRef = useRef<HTMLDivElement | null>(null);
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);
  const runCompletedFlashTimeoutRef = useRef<number | null>(null);
  const activeAutomationIdRef = useRef(currentAutomation.id);

  const hasBranchSteps = useMemo(
    () => currentAutomation.steps.some((step) => step.type === "condition" && (step.on_true_step_id || step.on_false_step_id)),
    [currentAutomation.steps]
  );
  const contentHeight = STEP_Y + Math.max(0, currentAutomation.steps.length) * STEP_GAP + 200;
  const zoomEnabled = contentHeight > CANVAS_SURFACE_HEIGHT * 0.85 || currentAutomation.steps.length >= ZOOM_STEP_COUNT_THRESHOLD;
  const drawerStep = editorDrawer?.kind === "step"
    ? currentAutomation.steps.find((step) => step.id === editorDrawer.stepId) || null
    : null;
  const hasName = Boolean(currentAutomation.name.trim());
  const triggerReady = isTriggerConfigured(currentAutomation) && !isInboundApiSelectionMissing(currentAutomation, inboundApis);
  const hasAtLeastOneStep = currentAutomation.steps.length > 0;
  const hasPersistedDraft = Boolean(currentAutomation.id);

  const clearRunCompletedFlashTimeout = () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  };

  const resetRunCompletedFlash = () => {
    clearRunCompletedFlashTimeout();
    setRunCompletedFlash(false);
  };

  const guidedRunButtonLabel = runInFlight ? "Running..." : runCompletedFlash ? "Done" : "Test run";
  const canvasRunButtonLabel = runInFlight ? "Running..." : runCompletedFlash ? "Done" : "Run now";

  const guidedNextAction = useMemo(() => {
    if (!hasName) {
      return "Name your automation so it can be saved and found later.";
    }
    if (!triggerReady) {
      return "Configure the trigger so the workflow knows when to run.";
    }
    if (!hasAtLeastOneStep) {
      return "Add your first action step to start the workflow.";
    }
    if (!hasPersistedDraft) {
      return "Save once to create a persistent draft, then run validation.";
    }
    return "Validate and run a test execution to confirm behavior before enabling it.";
  }, [hasAtLeastOneStep, hasName, hasPersistedDraft, triggerReady]);

  const drawerDataFlowTokens = useMemo(
    () => buildDataFlowTokens(currentAutomation.steps, drawerStep?.id || null, toolsManifest, activityCatalog),
    [currentAutomation.steps, drawerStep?.id, toolsManifest, activityCatalog]
  );
  const addStepDataFlowTokens = useMemo(
    () => buildDataFlowTokens(currentAutomation.steps.slice(0, pendingInsertIndex), null, toolsManifest, activityCatalog),
    [currentAutomation.steps, pendingInsertIndex, toolsManifest, activityCatalog]
  );

  const openAddStepFlow = (index: number) => {
    setPendingInsertIndex(index);
    setAddStepModalOpen(true);
  };

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
    setTriggerEditorScreen("detail");
    setAdvancedLabelOpen(false);
  };

  const openEditorForNode = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    if (nodeId === "trigger-node") {
      setEditorDrawer({ kind: "trigger" });
      setTriggerEditorScreen("detail");
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

  const updateBuilderUrl = ({
    automationId,
    useNewDraft,
    mode
  }: {
    automationId?: string;
    useNewDraft: boolean;
    mode: BuilderMode;
  }) => {
    const params = new URLSearchParams();
    if (automationId) {
      params.set("id", automationId);
    } else if (useNewDraft) {
      params.set("new", "true");
    }
    params.set("mode", mode);
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  const syncModeOnlyInUrl = (mode: BuilderMode) => {
    const params = new URLSearchParams(window.location.search);
    params.set("mode", mode);
    if (!params.get("id") && params.get("new") !== "true") {
      params.set("new", "true");
    }
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  const switchBuilderMode = (mode: BuilderMode) => {
    setBuilderMode(mode);
    syncModeOnlyInUrl(mode);
  };

  const applyNewAutomationDraft = ({ updateUrl = true }: { updateUrl?: boolean } = {}) => {
    activeAutomationIdRef.current = "";
    resetRunCompletedFlash();
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
      updateBuilderUrl({ useNewDraft: true, mode: builderMode });
    }
    setFeedback("");
    setFeedbackTone("");
  };

  const selectAutomation = async (automationId: string) => {
    activeAutomationIdRef.current = automationId;
    const detail = await loadAutomationDetail(automationId);

    resetRunCompletedFlash();
    startTransition(() => {
      setCurrentAutomation(sanitizeAutomationDetail(detail));
      setSelectedNodeId("trigger-node");
      closeEditorDrawer();
      closeNodeMenu();
      setTestResults(null);
    });
  };

  const loadAutomations = async (nextSelectedId?: string) => {
    const list = await loadAutomationList();
    setAutomations(list);
    const matchingCurrentId = list.some((automation) => automation.id === currentAutomation.id) ? currentAutomation.id : "";
    const targetId = nextSelectedId || matchingCurrentId || list[0]?.id;
    if (!targetId) {
      applyNewAutomationDraft();
      return;
    }
    await selectAutomation(targetId);
    updateBuilderUrl({ automationId: targetId, useNewDraft: false, mode: builderMode });
  };

  const loadSupportData = async () => {
    setSupportDataLoading(true);
    setSupportDataError(null);
    try {
      const supportData = await loadBuilderSupportData();
      setConnectors(supportData.connectors);
      setInboundApis(supportData.inboundApis);
      setScripts(supportData.scripts);
      setActivityCatalog(supportData.activityCatalog);
      setHttpPresets(supportData.httpPresets);
      setToolsManifest(supportData.toolsManifest);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load automation builder support data.";
      setSupportDataError(message);
      setFeedback(message);
      setFeedbackTone("error");
    } finally {
      setSupportDataLoading(false);
    }
  };

  useEffect(() => {
    if (!zoomEnabled && reactFlowRef.current) {
      reactFlowRef.current.fitView({ padding: 0.2, duration: 300 });
    }
  }, [zoomEnabled, currentAutomation.steps.length]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get("id") ?? undefined;
    const isNewDraft = params.get("new") === "true";
    const urlMode = inferBuilderModeFromSearch(window.location.search);
    setBuilderMode(urlMode);
    if (params.get("mode") !== urlMode) {
      const normalized = new URLSearchParams(params);
      normalized.set("mode", urlMode);
      window.history.replaceState({}, "", `builder.html?${normalized.toString()}`);
    }

    Promise.all([
      loadSupportData(),
      isNewDraft
        ? loadAutomationList().then((list) => {
          setAutomations(list);
          applyNewAutomationDraft({ updateUrl: false });
        })
        : loadAutomations(urlId)
    ]).catch((error: Error) => {
      setFeedback(error.message);
      setFeedbackTone("error");
    });
  }, []);

  const reloadSupportData = () => {
    void loadSupportData();
  };

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

  useEffect(() => () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  }, []);

  const saveAutomation = async () => {
    const issues = validateAutomationDefinition(currentAutomation, inboundApis, activityCatalog, connectors, toolsManifest);
    if (issues.length > 0) {
      setFeedback(issues.join(" "));
      setFeedbackTone("error");
      return;
    }

    const response = await saveAutomationRequest(currentAutomation);
    setFeedback(currentAutomation.id ? "Automation updated." : "Automation created.");
    setFeedbackTone("success");
    updateBuilderUrl({ automationId: response.id, useNewDraft: false, mode: builderMode });
    await loadAutomations(response.id);
  };

  const validateAutomation = async () => {
    const localIssues = validateAutomationDefinition(currentAutomation, inboundApis, activityCatalog, connectors, toolsManifest);
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

    const response = await validateAutomationRequest(currentAutomation.id);
    setFeedback(response.valid ? "Automation definition is valid." : response.issues.join(" "));
    setFeedbackTone(response.valid ? "success" : "error");
    setTestResults({ kind: "validation", valid: response.valid, issues: response.issues || [] });
  };

  const executeAutomation = async () => {
    if (runInFlight) {
      return;
    }
    const automationId = currentAutomation.id;
    if (!automationId) {
      setFeedback("Save the automation before running it.");
      setFeedbackTone("error");
      return;
    }
    setRunCompletedFlash(false);
    clearRunCompletedFlashTimeout();
    setRunInFlight(true);
    let shouldFlashCompletion = false;
    try {
      const run = await executeAutomationRequest(automationId);
      if (activeAutomationIdRef.current !== automationId) {
        return;
      }
      setFeedback("Automation executed.");
      setFeedbackTone("success");
      setTestResults({ kind: "run", run });
      const refreshed = await loadAutomationDetail(automationId);
      if (activeAutomationIdRef.current !== automationId) {
        return;
      }
      setCurrentAutomation((current) => ({
        ...sanitizeAutomationDetail(refreshed),
        steps: current.steps
      }));
      shouldFlashCompletion = true;
    } finally {
      flushSync(() => {
        setRunInFlight(false);
        if (shouldFlashCompletion) {
          clearRunCompletedFlashTimeout();
          setRunCompletedFlash(true);
          runCompletedFlashTimeoutRef.current = window.setTimeout(() => {
            setRunCompletedFlash(false);
            runCompletedFlashTimeoutRef.current = null;
          }, 1500);
        }
      });
    }
  };

  const deleteAutomation = async () => {
    if (!currentAutomation.id) {
      applyNewAutomationDraft();
      return;
    }
    await deleteAutomationRequest(currentAutomation.id);
    setDeleteDialogOpen(false);
    setFeedback("Automation deleted.");
    setFeedbackTone("success");
    await loadAutomations();
  };

  const flowNodes = useMemo(
    () =>
      createFlowNodes({
        currentAutomation,
        selectedNodeId,
        inboundApis,
        scripts,
        activityCatalog,
        toolsManifest,
        hasBranchSteps,
        openNodeMenu,
        openAddStepFlow
      }),
    [currentAutomation, selectedNodeId, inboundApis, scripts, activityCatalog, toolsManifest, hasBranchSteps]
  );

  const flowEdges = useMemo(
    () => createFlowEdges(currentAutomation.steps, selectedNodeId),
    [currentAutomation.steps, selectedNodeId]
  );

  return {
    automations,
    currentAutomation,
    builderMode,
    selectedNodeId,
    connectors,
    supportDataLoading,
    supportDataError,
    httpPresets,
    inboundApis,
    activityCatalog,
    scripts,
    toolsManifest,
    feedback,
    feedbackTone,
    deleteDialogOpen,
    addStepModalOpen,
    editorDrawer,
    triggerEditorScreen,
    nodeMenu,
    pendingInsertIndex,
    testResults,
    runInFlight,
    runCompletedFlash,
    advancedLabelOpen,
    nodeMenuRef,
    reactFlowRef,
    drawerStep,
    hasBranchSteps,
    zoomEnabled,
    triggerReady,
    hasName,
    hasAtLeastOneStep,
    hasPersistedDraft,
    guidedNextAction,
    drawerDataFlowTokens,
    addStepDataFlowTokens,
    guidedRunButtonLabel,
    canvasRunButtonLabel,
    flowNodes,
    flowEdges,
    setFeedback,
    setFeedbackTone,
    setDeleteDialogOpen,
    setAddStepModalOpen,
    setTriggerEditorScreen,
    setAdvancedLabelOpen,
    setTestResults,
    setSelectedNodeId,
    switchBuilderMode,
    patchAutomation,
    updateDrawerStep,
    updateStepOrder,
    insertStep,
    removeStepById,
    openAddStepFlow,
    openNodeMenu,
    closeNodeMenu,
    closeEditorDrawer,
    openEditorForNode,
    saveAutomation,
    validateAutomation,
    executeAutomation,
    deleteAutomation,
    applyNewAutomationDraft,
    reloadSupportData,
    reorderSteps
  };
};
