import { lazy, Suspense } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Switch } from "@base-ui/react/switch";
import { Background, Controls, ReactFlow } from "@xyflow/react";
import { AutomationSettingsFields } from "./automation-settings-fields";
import { nodeTypes, STEP_GAP, STEP_Y } from "./builder-flow";
import { appendToken, formatDateTime, formatDuration, getNodeMenuLabel, getRunStatusTone, getTriggerTypeLabel, reorderSteps } from "./builder-utils";
import { useAutomationBuilderController } from "./useAutomationBuilderController";
import { HttpStepForm } from "./step-modals/http-step-form";
import { ScriptStepForm } from "./step-modals/script-step-form";
import { TokenPicker } from "./token-picker";
import { ToolStepFields } from "./tool-step-fields";
import { TriggerSettingsForm } from "./trigger-settings-form";
import { CollapsibleSection } from "../lib/collapsible-section";
import type { AutomationStep } from "./types";
import { getDefaultStepName } from "./types";

const AddStepModal = lazy(() => import("./add-step-modal").then((m) => ({ default: m.AddStepModal })));
const StorageStepForm = lazy(() => import("./step-modals/storage-step-form"));
const ConnectorActivityStepForm = lazy(() =>
  import("./step-modals/connector-activity-step-form").then((m) => ({ default: m.ConnectorActivityStepForm }))
);

export const AutomationApp = () => {
  const controller = useAutomationBuilderController();
  const {
    currentAutomation,
    builderMode,
    builderMetadata,
    selectedNodeId,
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
    connectors,
    supportDataLoading,
    supportDataError,
    httpPresets,
    inboundApis,
    activityCatalog,
    scripts,
    scriptLanguages,
    toolsManifest,
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
    reloadSupportData
  } = controller;

  const renderStepEditor = (step: AutomationStep) => {
    const customLabelValue = step.name === getDefaultStepName(step.type) ? "" : step.name;
    const usesCustomHttpMode = step.type === "outbound_request" || (step.type === "api" && step.config.api_mode === "custom");
    const usesConnectorActivityMode = step.type === "connector_activity" || (step.type === "api" && step.config.api_mode !== "custom");

    return (
      <div id="automations-step-modal-form" className="automation-form">
        {step.type === "log" ? (
          <Suspense fallback={null}>
            <StorageStepForm
              draft={step}
              storageTypeOptions={builderMetadata.storage_types}
              logColumnTypeOptions={builderMetadata.log_column_types}
              onChange={(updated) => updateDrawerStep(() => updated)}
            />
          </Suspense>
        ) : null}

        {usesCustomHttpMode ? (
          <HttpStepForm
            draft={step}
            connectors={connectors}
            httpPresets={httpPresets}
            httpMethodOptions={builderMetadata.http_methods}
            dataFlowTokens={drawerDataFlowTokens}
            onChange={(updated) => updateDrawerStep(() => updated)}
            idPrefix="automations-step-http"
          />
        ) : null}

        {usesConnectorActivityMode ? (
          <Suspense fallback={null}>
            <ConnectorActivityStepForm
              draft={step}
              connectors={connectors}
              connectorsLoading={supportDataLoading}
              connectorsError={supportDataError}
              onRetryConnectors={reloadSupportData}
              activityCatalog={activityCatalog}
              onChange={(updated) => updateDrawerStep(() => updated)}
              idPrefix="automations-step-connector-activity"
            />
          </Suspense>
        ) : null}

        {step.type === "script" ? (
          <ScriptStepForm
            draft={step}
            scripts={scripts}
            scriptLanguages={scriptLanguages}
            dataFlowTokens={drawerDataFlowTokens}
            onChange={(updated) => updateDrawerStep(() => updated)}
            idPrefix="automations-step"
          />
        ) : null}

        {step.type === "tool" ? (
          <ToolStepFields
            idPrefix="automations-step"
            step={step}
            toolsManifest={toolsManifest}
            dataFlowTokens={drawerDataFlowTokens}
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
            {drawerDataFlowTokens.length > 0 ? (
              <TokenPicker
                idPrefix="automations-step-condition"
                tokens={drawerDataFlowTokens}
                description="Insert data references into condition expressions."
                onInsert={(token) => updateDrawerStep((currentStep) => ({
                  ...currentStep,
                  config: { ...currentStep.config, expression: appendToken(currentStep.config.expression || "", token) }
                }))}
              />
            ) : null}
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
                {currentAutomation.steps.filter((candidate) => candidate.id !== step.id).map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
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
                {currentAutomation.steps.filter((candidate) => candidate.id !== step.id).map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
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
            {drawerDataFlowTokens.length > 0 ? (
              <TokenPicker
                idPrefix="automations-step-llm"
                tokens={drawerDataFlowTokens}
                description="Insert workflow output tokens into prompts."
                onInsert={(token) => updateDrawerStep((currentStep) => ({
                  ...currentStep,
                  config: { ...currentStep.config, user_prompt: appendToken(currentStep.config.user_prompt || "", token) }
                }))}
              />
            ) : null}
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
      {builderMode === "canvas" ? (
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
            <AutomationSettingsFields currentAutomation={currentAutomation} patchAutomation={patchAutomation} />
          </div>
        </CollapsibleSection>
      ) : null}

      <div
        id="automations-feedback-banner"
        className={feedbackTone ? `automation-feedback automation-feedback--${feedbackTone}` : "automation-feedback"}
        hidden={!feedback}
      >
        {feedback}
      </div>

      <section id="automations-builder-mode-bar" className="automation-builder-mode-bar" aria-label="Builder mode selector">
        <div id="automations-builder-mode-copy" className="automation-panel__copy">
          <p id="automations-builder-mode-eyebrow" className="automation-panel__eyebrow">Build mode</p>
          <h3 id="automations-builder-mode-title" className="automation-panel__title">
            {builderMode === "guided" ? "Guided Mode" : "Canvas Mode"}
          </h3>
          <p id="automations-builder-mode-description" className="automation-panel__description">
            {builderMode === "guided"
              ? "Follow a focused sequence for trigger setup, first actions, and validation."
              : "Use freeform canvas editing with direct node operations and branch controls."}
          </p>
        </div>
        <div id="automations-builder-mode-actions" className="automation-mode-toggle" role="group" aria-label="Builder mode">
          <button
            id="automations-builder-mode-guided"
            type="button"
            className={`automation-mode-toggle__button${builderMode === "guided" ? " automation-mode-toggle__button--active" : ""}`}
            aria-pressed={builderMode === "guided"}
            onClick={() => switchBuilderMode("guided")}
          >
            Guided
          </button>
          <button
            id="automations-builder-mode-canvas"
            type="button"
            className={`automation-mode-toggle__button${builderMode === "canvas" ? " automation-mode-toggle__button--active" : ""}`}
            aria-pressed={builderMode === "canvas"}
            onClick={() => switchBuilderMode("canvas")}
          >
            Canvas
          </button>
        </div>
      </section>

      {builderMode === "guided" ? (
        <section id="automations-guided-panel" className="automation-panel automation-guided-panel" aria-label="Guided workflow setup">
          <div id="automations-guided-panel-header" className="automation-panel__header automation-panel__header--compact">
            <div id="automations-guided-panel-copy" className="automation-panel__copy">
              <p id="automations-guided-panel-eyebrow" className="automation-panel__eyebrow">Guided checklist</p>
              <h3 id="automations-guided-panel-title" className="automation-panel__title">Build your first successful run</h3>
              <p id="automations-guided-panel-description" className="automation-panel__description">{guidedNextAction}</p>
            </div>
          </div>

          <div id="automations-guided-checklist" className="automation-guided-checklist">
            <article id="automations-guided-item-name" className="automation-guided-item automation-guided-item--metadata">
              <span id="automations-guided-item-name-state" className={`automation-guided-item__state${hasName ? " automation-guided-item__state--done" : ""}`}>
                {hasName ? "Done" : "Pending"}
              </span>
              <div id="automations-guided-item-name-copy" className="automation-guided-item__copy">
                <h4 id="automations-guided-item-name-title" className="automation-guided-item__title">Name and describe automation</h4>
              </div>
              <AutomationSettingsFields currentAutomation={currentAutomation} patchAutomation={patchAutomation} variant="guided-inline" />
            </article>

            <article id="automations-guided-item-trigger" className="automation-guided-item">
              <span id="automations-guided-item-trigger-state" className={`automation-guided-item__state${triggerReady ? " automation-guided-item__state--done" : ""}`}>
                {triggerReady ? "Done" : "Pending"}
              </span>
              <div id="automations-guided-item-trigger-copy" className="automation-guided-item__copy">
                <h4 id="automations-guided-item-trigger-title" className="automation-guided-item__title">Configure trigger</h4>
                <p id="automations-guided-item-trigger-description" className="automation-guided-item__description">Open trigger settings and define when this automation starts.</p>
              </div>
              <button
                id="automations-guided-item-trigger-action"
                type="button"
                className="button button--secondary"
                onClick={() => openEditorForNode("trigger-node")}
              >
                Edit trigger
              </button>
            </article>

            <article id="automations-guided-item-step" className="automation-guided-item">
              <span id="automations-guided-item-step-state" className={`automation-guided-item__state${hasAtLeastOneStep ? " automation-guided-item__state--done" : ""}`}>
                {hasAtLeastOneStep ? "Done" : "Pending"}
              </span>
              <div id="automations-guided-item-step-copy" className="automation-guided-item__copy">
                <h4 id="automations-guided-item-step-title" className="automation-guided-item__title">Add workflow actions</h4>
                <p id="automations-guided-item-step-description" className="automation-guided-item__description">Start with one action, then expand and branch in Canvas Mode when needed.</p>
              </div>
              <button
                id="automations-guided-item-step-action"
                type="button"
                className="button button--secondary"
                onClick={() => openAddStepFlow(currentAutomation.steps.length)}
              >
                Add step
              </button>
            </article>

            <article id="automations-guided-item-save" className="automation-guided-item">
              <span id="automations-guided-item-save-state" className={`automation-guided-item__state${hasPersistedDraft ? " automation-guided-item__state--done" : ""}`}>
                {hasPersistedDraft ? "Done" : "Pending"}
              </span>
              <div id="automations-guided-item-save-copy" className="automation-guided-item__copy">
                <h4 id="automations-guided-item-save-title" className="automation-guided-item__title">Save, validate, and test</h4>
                <p id="automations-guided-item-save-description" className="automation-guided-item__description">Persist your draft, check validation, then run a test execution.</p>
              </div>
              <div id="automations-guided-item-save-actions" className="automation-inline-actions">
                <button id="automations-guided-save-button" type="button" className="button button--secondary" onClick={() => saveAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
                  Save draft
                </button>
                <button id="automations-guided-validate-button" type="button" className="button button--secondary" onClick={() => validateAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>
                  Validate
                </button>
                <button
                  id="automations-guided-run-button"
                  type="button"
                  className={`button button--secondary automation-run-button${runInFlight ? " automation-run-button--running" : ""}${runCompletedFlash ? " automation-run-button--done" : ""}`}
                  aria-busy={runInFlight}
                  disabled={!currentAutomation.id || runInFlight}
                  onClick={() => executeAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}
                >
                  {guidedRunButtonLabel}
                </button>
              </div>
            </article>
          </div>
        </section>
      ) : null}

      <section id="automations-canvas-panel" className="automation-panel automation-panel--canvas automation-panel--canvas-full">
        <div id="automations-canvas-header" className="automation-panel__header automation-panel__header--canvas">
          <div id="automations-canvas-copy" className="automation-panel__copy">
            <p id="automations-canvas-eyebrow" className="automation-panel__eyebrow">Builder</p>
            <div className="title-row">
              <h3 id="automations-canvas-title" className="automation-panel__title">Automation canvas</h3>
              <button type="button" id="automations-canvas-description-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-canvas-description">i</button>
            </div>
            <p id="automations-canvas-description" className="automation-panel__description" hidden>
              {builderMode === "guided"
                ? "Use the guided checklist above and switch here for direct visual editing."
                : "Select a node, drag steps to reorder them, and use node actions to edit."}
            </p>
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
            <button
              id="automations-run-button"
              type="button"
              className={`button button--secondary automation-run-button${runInFlight ? " automation-run-button--running" : ""}${runCompletedFlash ? " automation-run-button--done" : ""}`}
              aria-busy={runInFlight}
              disabled={runInFlight}
              onClick={() => executeAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}
            >
              {canvasRunButtonLabel}
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
              openAddStepFlow(Math.max(0, insertionIndex));
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
          <Dialog.Backdrop id="automations-editor-modal-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup
            id="automations-editor-modal"
            className="automation-dialog automation-dialog--edit"
            aria-labelledby="automations-editor-modal-title"
            aria-describedby="automations-editor-modal-description"
          >
            <div
              id="automations-editor-modal-dismiss-row"
              className={`automation-dialog__dismiss-row${editorDrawer?.kind === "trigger" && triggerEditorScreen === "detail" ? " automation-dialog__dismiss-row--split" : ""}`}
            >
              {editorDrawer?.kind === "trigger" && triggerEditorScreen === "detail" ? (
                <button
                  id="automations-editor-modal-trigger-back"
                  type="button"
                  className="modal__close-icon-button automation-dialog__close-button automation-dialog__back-button"
                  aria-label="Back to trigger types"
                  onClick={() => setTriggerEditorScreen("picker")}
                >
                  ←
                </button>
              ) : null}
              <Dialog.Close
                id="automations-editor-modal-close"
                className="modal__close-icon-button automation-dialog__close-button"
                aria-label="Close editor"
              >
                ×
              </Dialog.Close>
            </div>
            <Dialog.Title id="automations-editor-modal-title" className="automation-dialog__title">
              {editorDrawer?.kind === "trigger"
                ? triggerEditorScreen === "picker"
                  ? "Choose trigger type"
                  : `Edit ${getTriggerTypeLabel(currentAutomation.trigger_type)}`
                : drawerStep?.name || "Edit step"}
            </Dialog.Title>
            <Dialog.Description id="automations-editor-modal-description" className="automation-dialog__description">
              {editorDrawer?.kind === "trigger"
                ? triggerEditorScreen === "picker"
                  ? "Pick how this automation starts, then continue into that trigger's settings."
                  : "Configure only the settings for this trigger type. Use the back arrow to pick a different trigger."
                : "Adjust the step configuration. To change the step type, remove this step and add a new one."}
            </Dialog.Description>
            <div id="automations-editor-modal-body" className="automation-dialog--edit__body">
              {editorDrawer?.kind === "trigger" ? (
                <TriggerSettingsForm
                  idPrefix="automations-trigger-modal"
                  triggerTypeOptions={builderMetadata.trigger_types}
                  value={currentAutomation}
                  onPatch={patchAutomation}
                  showWorkflowFields={false}
                  showEnabledField={false}
                  inboundApiOptions={inboundApis}
                  inboundApiMissingSelection={controller.triggerReady ? false : currentAutomation.trigger_type === "inbound_api" && Boolean(currentAutomation.trigger_config.inbound_api_id) && !inboundApis.some((api) => api.id === currentAutomation.trigger_config.inbound_api_id)}
                  modalFlow
                  modalScreen={triggerEditorScreen}
                  onModalScreenChange={setTriggerEditorScreen}
                />
              ) : drawerStep ? renderStepEditor(drawerStep) : null}
            </div>
            <div id="automations-editor-modal-actions" className="automation-dialog__actions">
              <Dialog.Close
                id="automations-editor-modal-done"
                className="button button--primary"
              >
                Done
              </Dialog.Close>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={testResults !== null} onOpenChange={(open) => { if (!open) setTestResults(null); }}>
        <Dialog.Portal>
          <Dialog.Backdrop id="automations-test-results-modal-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup
            id="automations-test-results-modal"
            className="automation-dialog automation-dialog--results"
            aria-labelledby="automations-test-results-title"
            aria-describedby="automations-test-results-description"
          >
            <div id="automations-test-results-dismiss-row" className="automation-dialog__dismiss-row">
              <Dialog.Close
                id="automations-test-results-close"
                className="modal__close-icon-button automation-dialog__close-button"
                aria-label="Close test results"
              >
                ×
              </Dialog.Close>
            </div>
            <Dialog.Title id="automations-test-results-title" className="automation-dialog__title">
              {testResults?.kind === "validation" ? "Validation results" : "Test run results"}
            </Dialog.Title>
            <Dialog.Description id="automations-test-results-description" className="automation-dialog__description">
              {testResults?.kind === "validation"
                ? "Validation only appears when you test the draft."
                : "Execution output is shown on demand so the builder can stay focused on composition."}
            </Dialog.Description>
            <div id="automations-test-results-body" className="automation-dialog--results__body">
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

      <Suspense fallback={null}>
        <AddStepModal
          open={addStepModalOpen}
          onClose={() => setAddStepModalOpen(false)}
          stepTypeOptions={builderMetadata.step_types}
          onAdd={(step) => {
            insertStep(step, pendingInsertIndex);
            setAddStepModalOpen(false);
          }}
          connectors={connectors}
          connectorsLoading={supportDataLoading}
          connectorsError={supportDataError}
          onRetryConnectors={reloadSupportData}
          httpPresets={httpPresets}
          activityCatalog={activityCatalog}
          toolsManifest={toolsManifest}
          scripts={scripts}
          scriptLanguages={scriptLanguages}
          builderMetadata={builderMetadata}
          dataFlowTokens={addStepDataFlowTokens}
        />
      </Suspense>

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
