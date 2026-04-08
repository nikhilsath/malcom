import { Switch } from "@base-ui/react/switch";
import StorageStepForm from "../step-modals/storage-step-form";
import { HttpStepForm } from "../step-modals/http-step-form";
import { ConnectorActivityStepForm } from "../step-modals/connector-activity-step-form";
import { ScriptStepForm } from "../step-modals/script-step-form";
import { ToolStepFields } from "../tool-step-fields";
import { ConditionStepEditor } from "./ConditionStepEditor";
import { LlmChatStepEditor } from "./LlmChatStepEditor";
import type { DataFlowToken } from "../data-flow";
import type {
  ConnectorRecord,
  ConnectorActivityDefinition,
  HttpPreset,
  ScriptLanguageOption,
  ScriptLibraryItem,
  ToolManifestEntry
} from "../builder-types";
import type { AutomationStep, AutomationBuilderMetadata } from "../types";
import { getDefaultStepName } from "../types";

type Props = {
  step: AutomationStep;
  allSteps: AutomationStep[];
  storageTypeOptions: AutomationBuilderMetadata["storage_types"];
  logColumnTypeOptions: AutomationBuilderMetadata["log_column_types"];
  connectors: ConnectorRecord[];
  httpPresets: HttpPreset[];
  httpMethodOptions: AutomationBuilderMetadata["http_methods"];
  supportDataLoading: boolean;
  supportDataError: string | null;
  onRetryConnectors: () => void;
  activityCatalog: ConnectorActivityDefinition[];
  scripts: ScriptLibraryItem[];
  scriptLanguages: ScriptLanguageOption[];
  toolsManifest: ToolManifestEntry[];
  drawerDataFlowTokens: DataFlowToken[];
  advancedLabelOpen: boolean;
  setAdvancedLabelOpen: (open: boolean) => void;
  updateDrawerStep: (updater: (step: AutomationStep) => AutomationStep) => void;
  removeStepById: (stepId: string) => void;
};

export const StepEditorDispatcher = ({
  step,
  allSteps,
  storageTypeOptions,
  logColumnTypeOptions,
  connectors,
  httpPresets,
  httpMethodOptions,
  supportDataLoading,
  supportDataError,
  onRetryConnectors,
  activityCatalog,
  scripts,
  scriptLanguages,
  toolsManifest,
  drawerDataFlowTokens,
  advancedLabelOpen,
  setAdvancedLabelOpen,
  updateDrawerStep,
  removeStepById
}: Props) => {
  const customLabelValue = step.name === getDefaultStepName(step.type) ? "" : step.name;
  const usesCustomHttpMode = step.type === "outbound_request" || (step.type === "api" && step.config.api_mode === "custom");
  const usesConnectorActivityMode = step.type === "connector_activity" || (step.type === "api" && step.config.api_mode !== "custom");

  return (
    <div id="automations-step-modal-form" className="automation-form">
      {step.type === "log" ? (
        <StorageStepForm
          draft={step}
          storageTypeOptions={storageTypeOptions}
          logColumnTypeOptions={logColumnTypeOptions}
          onChange={(updated) => updateDrawerStep(() => updated)}
        />
      ) : null}

      {usesCustomHttpMode ? (
        <HttpStepForm
          draft={step}
          connectors={connectors}
          httpPresets={httpPresets}
          httpMethodOptions={httpMethodOptions}
          dataFlowTokens={drawerDataFlowTokens}
          onChange={(updated) => updateDrawerStep(() => updated)}
          idPrefix="automations-step-http"
        />
      ) : null}

      {usesConnectorActivityMode ? (
        <ConnectorActivityStepForm
          draft={step}
          connectors={connectors}
          connectorsLoading={supportDataLoading}
          connectorsError={supportDataError}
          onRetryConnectors={onRetryConnectors}
          activityCatalog={activityCatalog}
          onChange={(updated) => updateDrawerStep(() => updated)}
          idPrefix="automations-step-connector-activity"
        />
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
        <ConditionStepEditor
          draft={step}
          allSteps={allSteps}
          dataFlowTokens={drawerDataFlowTokens}
          onChange={updateDrawerStep}
        />
      ) : null}

      {step.type === "llm_chat" ? (
        <LlmChatStepEditor
          draft={step}
          dataFlowTokens={drawerDataFlowTokens}
          onChange={updateDrawerStep}
        />
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
