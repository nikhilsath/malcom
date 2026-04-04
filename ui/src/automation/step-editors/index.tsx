import React, { Suspense } from "react";
import { Switch } from "@base-ui/react/switch";
import { StorageStepForm } from "../step-modals/storage-step-form";
import { HttpStepForm } from "../step-modals/http-step-form";
import { ConnectorActivityStepForm } from "../step-modals/connector-activity-step-form";
import { ScriptStepForm } from "../step-modals/script-step-form";
import { ToolStepFields } from "../tool-step-fields";
import { TokenPicker } from "../token-picker";
import type { AutomationStep } from "../types";
import { getDefaultStepName } from "../types";
import { appendToken } from "../builder-utils";

type Props = {
  step: AutomationStep;
  currentAutomation: any;
  builderMetadata: any;
  connectors: any[];
  supportDataLoading: boolean;
  supportDataError: any;
  reloadSupportData: () => void;
  httpPresets: any[];
  scripts: any[];
  scriptLanguages: any[];
  toolsManifest: any;
  drawerDataFlowTokens: any[];
  updateDrawerStep: (fn: (s: AutomationStep) => AutomationStep) => void;
  removeStepById: (id: string) => void;
  advancedLabelOpen: boolean;
  setAdvancedLabelOpen: (open: boolean) => void;
};

export const LogStepEditor = ({ step, builderMetadata, updateDrawerStep }: Pick<Props, "step" | "builderMetadata" | "updateDrawerStep">) => (
  <div id="automations-step-modal-form" className="automation-form">
    <Suspense fallback={null}>
      <StorageStepForm
        draft={step}
        storageTypeOptions={builderMetadata.storage_types}
        logColumnTypeOptions={builderMetadata.log_column_types}
        storageLocationOptions={builderMetadata.storage_locations}
        onChange={(updated) => updateDrawerStep(() => updated)}
      />
    </Suspense>
  </div>
);

export const HttpStepEditor = ({ step, connectors, httpPresets, builderMetadata, drawerDataFlowTokens, updateDrawerStep }: Pick<Props, "step" | "connectors" | "httpPresets" | "builderMetadata" | "drawerDataFlowTokens" | "updateDrawerStep">) => (
  <div id="automations-step-modal-form" className="automation-form">
    <HttpStepForm
      draft={step}
      connectors={connectors}
      httpPresets={httpPresets}
      httpMethodOptions={builderMetadata.http_methods}
      dataFlowTokens={drawerDataFlowTokens}
      onChange={(updated) => updateDrawerStep(() => updated)}
      idPrefix="automations-step-http"
    />
  </div>
);

export const ConnectorActivityStepEditor = ({ step, connectors, supportDataLoading, supportDataError, reloadSupportData, activityCatalog, updateDrawerStep }: any) => (
  <div id="automations-step-modal-form" className="automation-form">
    <Suspense fallback={null}>
      <ConnectorActivityStepForm
        draft={step}
        connectors={connectors}
        connectorsLoading={supportDataLoading}
        connectorsError={supportDataError}
        onRetryConnectors={reloadSupportData}
        activityCatalog={activityCatalog}
        onChange={(updated: any) => updateDrawerStep(() => updated)}
        idPrefix="automations-step-connector-activity"
      />
    </Suspense>
  </div>
);

export const ScriptStepEditor = ({ step, scripts, scriptLanguages, builderMetadata, drawerDataFlowTokens, updateDrawerStep }: any) => (
  <div id="automations-step-modal-form" className="automation-form">
    <ScriptStepForm
      draft={step}
      scripts={scripts}
      scriptLanguages={scriptLanguages}
      repoCheckoutOptions={builderMetadata.repo_checkouts}
      dataFlowTokens={drawerDataFlowTokens}
      onChange={(updated: any) => updateDrawerStep(() => updated)}
      idPrefix="automations-step"
    />
  </div>
);

export const ToolStepEditor = ({ step, toolsManifest, drawerDataFlowTokens, updateDrawerStep }: any) => (
  <div id="automations-step-modal-form" className="automation-form">
    <ToolStepFields
      idPrefix="automations-step"
      step={step}
      toolsManifest={toolsManifest}
      dataFlowTokens={drawerDataFlowTokens}
      onChange={(updatedStep: any) => updateDrawerStep(() => updatedStep)}
    />
  </div>
);

export const ConditionStepEditor = ({ step, currentAutomation, drawerDataFlowTokens, updateDrawerStep }: any) => (
  <div id="automations-step-modal-form" className="automation-form">
    <label id="automations-step-condition-expression-field" className="automation-field automation-field--full">
      <span id="automations-step-condition-expression-label" className="automation-field__label">Expression</span>
      <textarea
        id="automations-step-condition-expression-input"
        className="automation-textarea automation-textarea--code"
        rows={4}
        value={step.config.expression || ""}
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, config: { ...currentStep.config, expression: event.target.value } }))}
      />
    </label>
    {drawerDataFlowTokens.length > 0 ? (
      <TokenPicker
        idPrefix="automations-step-condition"
        tokens={drawerDataFlowTokens}
        description="Insert data references into condition expressions."
        onInsert={(token: any) => updateDrawerStep((currentStep: any) => ({
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
        onCheckedChange={(checked: boolean) => updateDrawerStep((currentStep: any) => ({ ...currentStep, config: { ...currentStep.config, stop_on_false: checked } }))}
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
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, on_true_step_id: event.target.value || null }))}
      >
        <option value="">Continue in sequence</option>
        {currentAutomation.steps.filter((candidate: any) => candidate.id !== step.id).map((candidate: any) => (
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
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, on_false_step_id: event.target.value || null }))}
      >
        <option value="">Use &ldquo;stop on false&rdquo; setting</option>
        {currentAutomation.steps.filter((candidate: any) => candidate.id !== step.id).map((candidate: any) => (
          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
        ))}
      </select>
    </label>
  </div>
);

export const LlmChatStepEditor = ({ step, drawerDataFlowTokens, updateDrawerStep }: any) => (
  <div id="automations-step-modal-form" className="automation-form">
    <label id="automations-step-llm-model-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-model-label" className="automation-field__label">Model override</span>
      <input
        id="automations-step-llm-model-input"
        className="automation-input"
        value={step.config.model_identifier || ""}
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, config: { ...currentStep.config, model_identifier: event.target.value } }))}
      />
    </label>
    <label id="automations-step-llm-system-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-system-label" className="automation-field__label">System prompt</span>
      <textarea
        id="automations-step-llm-system-input"
        className="automation-textarea automation-textarea--code"
        rows={5}
        value={step.config.system_prompt || ""}
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, config: { ...currentStep.config, system_prompt: event.target.value } }))}
      />
    </label>
    <label id="automations-step-llm-user-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-user-label" className="automation-field__label">User prompt</span>
      <textarea
        id="automations-step-llm-user-input"
        className="automation-textarea automation-textarea--code"
        rows={7}
        value={step.config.user_prompt || ""}
        onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, config: { ...currentStep.config, user_prompt: event.target.value } }))}
      />
    </label>
    {drawerDataFlowTokens.length > 0 ? (
      <TokenPicker
        idPrefix="automations-step-llm"
        tokens={drawerDataFlowTokens}
        description="Insert workflow output tokens into prompts."
        onInsert={(token: any) => updateDrawerStep((currentStep: any) => ({
          ...currentStep,
          config: { ...currentStep.config, user_prompt: appendToken(currentStep.config.user_prompt || "", token) }
        }))}
      />
    ) : null}
  </div>
);

const StepEditor = ({
  step,
  currentAutomation,
  builderMetadata,
  connectors,
  supportDataLoading,
  supportDataError,
  reloadSupportData,
  httpPresets,
  scripts,
  scriptLanguages,
  toolsManifest,
  drawerDataFlowTokens,
  updateDrawerStep,
  removeStepById,
  advancedLabelOpen,
  setAdvancedLabelOpen
}: Props) => {
  const customLabelValue = step.name === getDefaultStepName(step.type) ? "" : step.name;
  const usesCustomHttpMode = step.type === "outbound_request" || (step.type === "api" && step.config.api_mode === "custom");
  const usesConnectorActivityMode = step.type === "connector_activity" || (step.type === "api" && step.config.api_mode !== "custom");

  if (step.type === "log") {
    return <LogStepEditor step={step} builderMetadata={builderMetadata} updateDrawerStep={updateDrawerStep} />;
  }
  if (usesCustomHttpMode) {
    return <HttpStepEditor step={step} connectors={connectors} httpPresets={httpPresets} builderMetadata={builderMetadata} drawerDataFlowTokens={drawerDataFlowTokens} updateDrawerStep={updateDrawerStep} />;
  }
  if (usesConnectorActivityMode) {
    return <ConnectorActivityStepEditor step={step} connectors={connectors} supportDataLoading={supportDataLoading} supportDataError={supportDataError} reloadSupportData={reloadSupportData} activityCatalog={(null as any)} updateDrawerStep={updateDrawerStep} />;
  }
  if (step.type === "script") {
    return <ScriptStepEditor step={step} scripts={scripts} scriptLanguages={scriptLanguages} builderMetadata={builderMetadata} drawerDataFlowTokens={drawerDataFlowTokens} updateDrawerStep={updateDrawerStep} />;
  }
  if (step.type === "tool") {
    return <ToolStepEditor step={step} toolsManifest={toolsManifest} drawerDataFlowTokens={drawerDataFlowTokens} updateDrawerStep={updateDrawerStep} />;
  }
  if (step.type === "condition") {
    return <ConditionStepEditor step={step} currentAutomation={currentAutomation} drawerDataFlowTokens={drawerDataFlowTokens} updateDrawerStep={updateDrawerStep} />;
  }
  if (step.type === "llm_chat") {
    return <LlmChatStepEditor step={step} drawerDataFlowTokens={drawerDataFlowTokens} updateDrawerStep={updateDrawerStep} />;
  }

  // Advanced section and danger zone are shared across many editors; render them here so ids remain stable.
  return (
    <div id="automations-step-modal-form" className="automation-form">
      <details id="automations-step-advanced-section" className="automation-advanced-section" open={advancedLabelOpen} onToggle={(event) => setAdvancedLabelOpen((event.currentTarget as HTMLDetailsElement).open)}>
        <summary id="automations-step-advanced-summary" className="automation-advanced-section__summary">Advanced</summary>
        <div id="automations-step-advanced-content" className="automation-advanced-section__content">
          <label id="automations-step-name-field" className="automation-field automation-field--full">
            <span id="automations-step-name-label" className="automation-field__label">Custom label (optional)</span>
            <input
              id="automations-step-name-input"
              className="automation-input"
              value={customLabelValue}
              placeholder={getDefaultStepName(step.type)}
              onChange={(event) => updateDrawerStep((currentStep: any) => ({ ...currentStep, name: event.target.value.trim() || getDefaultStepName(currentStep.type) }))}
            />
          </label>

          <div id="automations-step-merge-target-field" className="automation-switch-field">
            <div id="automations-step-merge-target-copy" className="automation-switch-field__copy">
              <span id="automations-step-merge-target-label" className="automation-field__label">Merge target</span>
              <span id="automations-step-merge-target-description" className="automation-switch-field__description">Mark this step as the convergence point where conditional branches rejoin.</span>
            </div>
            <Switch.Root
              id="automations-step-merge-target-input"
              checked={Boolean(step.is_merge_target)}
              onCheckedChange={(checked: boolean) => updateDrawerStep((currentStep: any) => ({ ...currentStep, is_merge_target: checked }))}
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

export default StepEditor;
