import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import "./add-step-modal.css";
import type { DataFlowToken } from "./data-flow";
import type {
  AutomationBuilderMetadata,
  AutomationBuilderOption,
  AutomationStep,
  ConnectorActivityDefinition,
  ConnectorRecord,
  HttpPreset,
  ScriptLanguageOption,
  ScriptLibraryItem,
  StepType,
  ToolManifestEntry
} from "./types";
import { cloneStepTemplate, getDefaultStepName } from "./types";
import StorageStepForm from "./step-modals/storage-step-form";
import { HttpStepForm } from "./step-modals/http-step-form";
import { ConnectorActivityStepForm } from "./step-modals/connector-activity-step-form";
import { ScriptStepForm } from "./step-modals/script-step-form";
import { ToolStepForm } from "./step-modals/tool-step-form";
import { ConditionStepForm } from "./step-modals/condition-step-form";
import { LlmStepForm } from "./step-modals/llm-step-form";

type Props = {
  open: boolean;
  onClose: () => void;
  onAdd: (step: AutomationStep) => void;
  stepTypeOptions: AutomationBuilderOption[];
  connectors: ConnectorRecord[];
  connectorsLoading?: boolean;
  connectorsError?: string | null;
  onRetryConnectors?: () => void;
  httpPresets: HttpPreset[];
  activityCatalog: ConnectorActivityDefinition[];
  toolsManifest: ToolManifestEntry[];
  scripts?: ScriptLibraryItem[];
  scriptLanguages?: ScriptLanguageOption[];
  builderMetadata: AutomationBuilderMetadata;
  dataFlowTokens?: DataFlowToken[];
};

export const AddStepModal = ({
  open,
  onClose,
  onAdd,
  stepTypeOptions,
  connectors,
  connectorsLoading = false,
  connectorsError = null,
  onRetryConnectors,
  httpPresets,
  activityCatalog,
  toolsManifest,
  scripts,
  scriptLanguages = [],
  builderMetadata,
  dataFlowTokens = []
}: Props) => {
  const [pickedType, setPickedType] = useState<StepType | null>(null);
  const [draft, setDraft] = useState<AutomationStep | null>(null);

  const handlePickType = (type: StepType) => {
    setPickedType(type);
    setDraft({ ...cloneStepTemplate(type), name: "" });
  };

  const handleClose = () => {
    setPickedType(null);
    setDraft(null);
    onClose();
  };

  const handleBack = () => {
    setPickedType(null);
    setDraft(null);
  };

  const handleAdd = () => {
    if (!draft) {
      return;
    }
    onAdd(draft);
    handleClose();
  };

  const renderDetailForm = () => {
    if (!draft || !pickedType) return null;

    switch (pickedType) {
      case "log":
        return (
          <StorageStepForm
            draft={draft}
            storageTypeOptions={builderMetadata.storage_types}
            logColumnTypeOptions={builderMetadata.log_column_types}
            storageLocationOptions={builderMetadata.storage_locations}
            onChange={setDraft}
          />
        );
      case "outbound_request":
        return (
          <HttpStepForm
            draft={draft}
            connectors={connectors}
            httpPresets={httpPresets}
            httpMethodOptions={builderMetadata.http_methods}
            dataFlowTokens={dataFlowTokens}
            onChange={setDraft}
          />
        );
      case "connector_activity":
        return (
          <ConnectorActivityStepForm
            draft={draft}
            connectors={connectors}
            connectorsLoading={connectorsLoading}
            connectorsError={connectorsError}
            onRetryConnectors={onRetryConnectors}
            activityCatalog={activityCatalog}
            dataFlowTokens={dataFlowTokens}
            onChange={setDraft}
          />
        );
      case "script":
        return (
          <ScriptStepForm
            draft={draft}
            scripts={scripts}
            scriptLanguages={scriptLanguages}
            dataFlowTokens={dataFlowTokens}
            onChange={setDraft}
          />
        );
      case "tool":
        return <ToolStepForm draft={draft} toolsManifest={toolsManifest} dataFlowTokens={dataFlowTokens} onChange={setDraft} />;
      case "condition":
        return <ConditionStepForm draft={draft} onChange={setDraft} />;
      case "llm_chat":
        return <LlmStepForm draft={draft} dataFlowTokens={dataFlowTokens} onChange={setDraft} />;
      default:
        return null;
    }
  };

  const popupTitleId = pickedType ? "add-step-modal-detail-title" : "add-step-modal-type-title";
  const popupDescriptionId = pickedType ? "add-step-modal-detail-description" : "add-step-modal-type-description";

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => { if (!nextOpen) handleClose(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop id="add-step-modal-backdrop" className="automation-dialog-backdrop" />
        <Dialog.Popup
          id="add-step-modal"
          className="automation-dialog automation-dialog--wide"
          aria-labelledby={popupTitleId}
          aria-describedby={popupDescriptionId}
          data-modal-id="add-step-modal"
          data-source="ui/src/automation/add-step-modal.tsx"
        >
          <div id="add-step-modal-dismiss-row" className="automation-dialog__dismiss-row">
            <Dialog.Close
              id="add-step-modal-close-icon"
              className="modal__close-icon-button automation-dialog__close-button"
              aria-label="Close add step modal"
            >
              ×
            </Dialog.Close>
          </div>

          {!pickedType ? (
            <>
              <Dialog.Title id="add-step-modal-type-title" className="sr-only">
                Add an automation step
              </Dialog.Title>
              <Dialog.Description id="add-step-modal-type-description" className="sr-only">
                Pick a step type to continue.
              </Dialog.Description>
              <div id="add-step-type-grid" className="add-step-type-grid">
                {stepTypeOptions.map((opt) => (
                  <button
                    key={opt.value}
                    id={`add-step-type-${opt.value}`}
                    type="button"
                    className={`add-step-type-card add-step-type-card--${opt.value}`}
                    onClick={() => handlePickType(opt.value as StepType)}
                  >
                    <span
                      id={`add-step-type-${opt.value}-icon-stack`}
                      className="add-step-type-card__icon-stack"
                    >
                      {opt.value === "log" ? (
                        <img id="add-step-type-log-icon" className="add-step-type-card__icon" src="/media/logs_icon.png" alt="" aria-hidden="true" />
                      ) : opt.value === "llm_chat" ? (
                        <img id="add-step-type-llm_chat-icon" className="add-step-type-card__icon" src="/media/bot_icon" alt="" aria-hidden="true" />
                      ) : opt.value === "tool" ? (
                        <img id="add-step-type-tool-icon" className="add-step-type-card__icon" src="/media/tools_icon.png" alt="" aria-hidden="true" />
                      ) : opt.value === "outbound_request" ? (
                        <img id="add-step-type-outbound_request-icon" className="add-step-type-card__icon" src="/media/api_icon.png" alt="" aria-hidden="true" />
                      ) : opt.value === "connector_activity" ? (
                        <img id="add-step-type-connector_activity-icon" className="add-step-type-card__icon" src="/media/api_icon.png" alt="" aria-hidden="true" />
                      ) : opt.value === "condition" ? (
                        <img id="add-step-type-condition-icon" className="add-step-type-card__icon" src="/media/conditional_icon.png" alt="" aria-hidden="true" />
                      ) : (
                        <img id="add-step-type-script-icon" className="add-step-type-card__icon" src="/media/script_icon.png" alt="" aria-hidden="true" />
                      )}
                      <span id={`add-step-type-${opt.value}-label`} className="add-step-type-card__label add-step-type-card__label--below">
                        {opt.label}
                      </span>
                    </span>
                    <span id={`add-step-type-${opt.value}-description`} className="add-step-type-card__description">
                      {opt.description}
                    </span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <Dialog.Title id="add-step-modal-detail-title" className="automation-dialog__title">
                Configure step
              </Dialog.Title>
              <Dialog.Description id="add-step-modal-detail-description" className="automation-dialog__description">
                Fill in the details for the new{" "}
                <strong>{stepTypeOptions.find((option) => option.value === pickedType)?.label}</strong> step.
              </Dialog.Description>

              <div id="add-step-detail-form" className="automation-form automation-form--modal">
                <label
                  id="add-step-name-field"
                  className={`automation-field automation-field--full${pickedType === "script" ? " automation-field--inline-label" : ""}`}
                >
                  <span id="add-step-name-label" className="automation-field__label">Custom label (optional)</span>
                  <input
                    id="add-step-name-input"
                    className="automation-input"
                    value={draft?.name || ""}
                    placeholder={draft ? getDefaultStepName(draft.type) : ""}
                    onChange={(event) => {
                      setDraft((previous) => previous ? { ...previous, name: event.target.value } : previous);
                    }}
                  />
                </label>

                {renderDetailForm()}
              </div>

              <div id="add-step-modal-detail-actions" className="automation-dialog__actions">
                <button
                  id="add-step-modal-back"
                  type="button"
                  className="button button--secondary"
                  onClick={handleBack}
                >
                  ← Back
                </button>
                <button
                  id="add-step-modal-confirm"
                  type="button"
                  className="button button--success primary-action-button"
                  onClick={handleAdd}
                >
                  Add step
                </button>
              </div>
            </>
          )}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
