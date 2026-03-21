import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import type {
  StepType,
  AutomationStep,
  ConnectorRecord,
  ToolManifestEntry
} from "./types";
import { stepTypeOptions, cloneStepTemplate, getDefaultStepName } from "./types";
import { LogStepForm } from "./step-modals/log-step-form";
import { HttpStepForm } from "./step-modals/http-step-form";
import { ScriptStepForm } from "./step-modals/script-step-form";
import { ToolStepForm } from "./step-modals/tool-step-form";
import { ConditionStepForm } from "./step-modals/condition-step-form";
import { LlmStepForm } from "./step-modals/llm-step-form";

type Props = {
  open: boolean;
  onClose: () => void;
  onAdd: (step: AutomationStep) => void;
  connectors: ConnectorRecord[];
  toolsManifest: ToolManifestEntry[];
  scripts?: Array<{ id: string; name: string }>;
};

export const AddStepModal = ({
  open,
  onClose,
  onAdd,
  connectors,
  toolsManifest,
  scripts
}: Props) => {
  const [pickedType, setPickedType] = useState<StepType | null>(null);
  const [draft, setDraft] = useState<AutomationStep | null>(null);

  const handlePickType = (type: StepType) => {
    setPickedType(type);
    setDraft({ ...cloneStepTemplate(type), name: "" });
  };

  const handleBack = () => {
    setPickedType(null);
    setDraft(null);
  };

  const handleClose = () => {
    setPickedType(null);
    setDraft(null);
    onClose();
  };

  const handleAdd = () => {
    if (!draft) return;
    onAdd({
      ...draft,
      name: draft.name.trim() || getDefaultStepName(draft.type)
    });
    setPickedType(null);
    setDraft(null);
  };

  const renderDetailForm = () => {
    if (!draft || !pickedType) return null;
    switch (pickedType) {
      case "log":
        return <LogStepForm draft={draft} onChange={setDraft} />;
      case "outbound_request":
        return <HttpStepForm draft={draft} connectors={connectors} onChange={setDraft} />;
      case "script":
        return <ScriptStepForm draft={draft} scripts={scripts} onChange={setDraft} />;
      case "tool":
        return <ToolStepForm draft={draft} toolsManifest={toolsManifest} onChange={setDraft} />;
      case "condition":
        return <ConditionStepForm draft={draft} onChange={setDraft} />;
      case "llm_chat":
        return <LlmStepForm draft={draft} onChange={setDraft} />;
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => { if (!nextOpen) handleClose(); }}>
      <Dialog.Portal>
        <Dialog.Backdrop id="add-step-modal-backdrop" className="automation-dialog-backdrop" />
        <Dialog.Popup id="add-step-modal" className="automation-dialog automation-dialog--wide">

          {/* ── Page 1: type picker ── */}
          {!pickedType ? (
            <>
              <Dialog.Title id="add-step-modal-title" className="automation-dialog__title">
                Add a step
              </Dialog.Title>
              <Dialog.Description id="add-step-modal-description" className="automation-dialog__description">
                Choose the kind of step to append to the workflow.
              </Dialog.Description>

              <div id="add-step-type-grid" className="add-step-type-grid">
                {stepTypeOptions.map((opt) => (
                  <button
                    key={opt.value}
                    id={`add-step-type-${opt.value}`}
                    type="button"
                    className={`add-step-type-card add-step-type-card--${opt.value}`}
                    style={opt.value === "log" || opt.value === "llm_chat" || opt.value === "tool"
                      ? {
                        minHeight: "200px",
                        padding: "10px",
                        alignItems: "center",
                        justifyContent: "center",
                        textAlign: "center"
                      }
                      : undefined}
                    onClick={() => handlePickType(opt.value)}
                  >
                    {opt.value === "log" || opt.value === "llm_chat" || opt.value === "tool" ? (
                      <span
                        id={`add-step-type-${opt.value}-icon-stack`}
                        className="add-step-type-card__icon-stack"
                        style={{ gap: "10px" }}
                      >
                        {opt.value === "log" ? (
                          <img
                            id="add-step-type-log-icon"
                            className="add-step-type-card__icon"
                            src="/media/logs_icon.png"
                            alt=""
                            aria-hidden="true"
                            style={{ width: "128px", height: "128px", flex: "0 0 128px" }}
                          />
                        ) : opt.value === "llm_chat" ? (
                          <img
                            id="add-step-type-llm_chat-icon"
                            className="add-step-type-card__icon"
                            src="/media/bot_icon"
                            alt=""
                            aria-hidden="true"
                            style={{ width: "128px", height: "128px", flex: "0 0 128px" }}
                          />
                        ) : (
                          <img
                            id="add-step-type-tool-icon"
                            className="add-step-type-card__icon"
                            src="/media/tools_icon.png"
                            alt=""
                            aria-hidden="true"
                            style={{ width: "128px", height: "128px", flex: "0 0 128px" }}
                          />
                        )}
                        <span id={`add-step-type-${opt.value}-label`} className="add-step-type-card__label add-step-type-card__label--below">
                          {opt.label}
                        </span>
                      </span>
                    ) : (
                      <>
                        <span id={`add-step-type-${opt.value}-label`} className="add-step-type-card__label">
                          {opt.label}
                        </span>
                        <span id={`add-step-type-${opt.value}-description`} className="add-step-type-card__description">
                          {opt.description}
                        </span>
                      </>
                    )}
                  </button>
                ))}
              </div>

              <div id="add-step-modal-picker-actions" className="automation-dialog__actions">
                <Dialog.Close
                  id="add-step-modal-cancel"
                  className="button button--secondary"
                >
                  Cancel
                </Dialog.Close>
              </div>
            </>
          ) : (
            /* ── Page 2: step detail ── */
            <>
              <Dialog.Title id="add-step-modal-detail-title" className="automation-dialog__title">
                Configure step
              </Dialog.Title>
              <Dialog.Description id="add-step-modal-detail-description" className="automation-dialog__description">
                Fill in the details for the new{" "}
                <strong>{stepTypeOptions.find((o) => o.value === pickedType)?.label}</strong> step.
              </Dialog.Description>

              <div id="add-step-detail-form" className="automation-form automation-form--modal">
                {/* shared name field */}
                <label id="add-step-name-field" className="automation-field automation-field--full">
                  <span id="add-step-name-label" className="automation-field__label">Custom label (optional)</span>
                  <input
                    id="add-step-name-input"
                    className="automation-input"
                    value={draft?.name || ""}
                    placeholder={draft ? getDefaultStepName(draft.type) : ""}
                    onChange={(e) =>
                      setDraft((prev) => prev ? { ...prev, name: e.target.value } : prev)
                    }
                  />
                </label>

                {/* per-type config fields */}
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
                  className="primary-action-button"
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
