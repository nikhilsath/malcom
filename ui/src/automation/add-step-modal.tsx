import { useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import type { DataFlowToken } from "./data-flow";
import type {
  StepType,
  AutomationStep,
  ConnectorRecord,
  ConnectorActivityDefinition,
  HttpPreset,
  ToolManifestEntry,
  ScriptLibraryItem
} from "./types";
import { stepTypeOptions, cloneStepTemplate, getDefaultStepName } from "./types";
import { LogStepForm } from "./step-modals/log-step-form";
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
  connectors: ConnectorRecord[];
  httpPresets: HttpPreset[];
  activityCatalog: ConnectorActivityDefinition[];
  toolsManifest: ToolManifestEntry[];
  scripts?: ScriptLibraryItem[];
  dataFlowTokens?: DataFlowToken[];
};

const ACTIVE_CONNECTOR_STATUSES = ["connected", "pending_oauth", "needs_attention"];

export const AddStepModal = ({
  open,
  onClose,
  onAdd,
  connectors,
  httpPresets,
  activityCatalog,
  toolsManifest,
  scripts,
  dataFlowTokens = []
}: Props) => {
  // Only show connectors with active statuses
  const activeConnectors = connectors.filter(c => ACTIVE_CONNECTOR_STATUSES.includes((c.status || "").toLowerCase()));

  const [pickedType, setPickedType] = useState<StepType | null>(null);
  const [apiMode, setApiMode] = useState<"prebuilt" | "custom" | null>(null);
  const [draft, setDraft] = useState<AutomationStep | null>(null);

  const handlePickType = (type: StepType) => {
    setPickedType(type);
    if (type === "api") {
      setApiMode(null);
      setDraft({ ...cloneStepTemplate(type), name: "" });
    } else {
      setDraft({ ...cloneStepTemplate(type), name: "" });
    }
  };
  return (
    <Dialog open={open} onClose={onClose}>
      {/* ...existing code... */}
      {pickedType === "api" && apiMode === "custom" && draft && (
        <HttpStepForm
          draft={draft}
          connectors={activeConnectors}
          httpPresets={httpPresets}
          dataFlowTokens={dataFlowTokens}
          onChange={setDraft}
        />
      )}
      {pickedType === "api" && apiMode === "prebuilt" && draft && (
        <ConnectorActivityStepForm
          draft={draft}
          connectors={activeConnectors}
          activityCatalog={activityCatalog}
          dataFlowTokens={dataFlowTokens}
          onChange={setDraft}
        />
      )}
      {/* ...existing code... */}
    </Dialog>
  );
    setPickedType(null);
    setApiMode(null);
    setDraft(null);
  };

  const renderDetailForm = () => {
    if (!draft || !pickedType) return null;
    if (pickedType === "api") {
      if (apiMode === "prebuilt") {
        return <ConnectorActivityStepForm draft={draft} connectors={connectors} activityCatalog={activityCatalog} dataFlowTokens={dataFlowTokens} onChange={step => setDraft({ ...step, config: { ...step.config, api_mode: "prebuilt" } })} />;
      } else if (apiMode === "custom") {
        return <HttpStepForm draft={draft} connectors={connectors} httpPresets={httpPresets} dataFlowTokens={dataFlowTokens} onChange={step => setDraft({ ...step, config: { ...step.config, api_mode: "custom" } })} />;
      }
      return null;
    }
    switch (pickedType) {
      case "log":
        return <LogStepForm draft={draft} onChange={setDraft} />;
      case "script":
        return <ScriptStepForm draft={draft} scripts={scripts} dataFlowTokens={dataFlowTokens} onChange={setDraft} />;
      case "tool":
        return <ToolStepForm draft={draft} toolsManifest={toolsManifest} dataFlowTokens={dataFlowTokens} onChange={setDraft} />;
      case "condition":
        return <ConditionStepForm draft={draft} onChange={setDraft} />;
      case "llm_chat":
        return <LlmStepForm draft={draft} dataFlowTokens={dataFlowTokens} onChange={setDraft} />;
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

          {/* ── Page 1: type picker ── */}
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
                    style={{
                      minHeight: "200px",
                      padding: "10px",
                      alignItems: "center",
                      justifyContent: "center",
                      textAlign: "center",
                      background: "var(--neutral-surface)",
                      border: "2px solid var(--brand-main)",
                      color: "var(--brand-main)",
                      transition: "border-color 0.2s, color 0.2s"
                    }}
                    onClick={() => handlePickType(opt.value)}
                    onMouseOver={e => (e.currentTarget.style.borderColor = "var(--brand-primary)")}
                    onMouseOut={e => (e.currentTarget.style.borderColor = "var(--brand-main)")}
                  >
                    <span
                      id={`add-step-type-${opt.value}-icon-stack`}
                      className="add-step-type-card__icon-stack"
                      style={{ gap: "10px" }}
                    >
                      {opt.value === "log" ? (
                        <img id="add-step-type-log-icon" className="add-step-type-card__icon" src="/media/logs_icon.png" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      ) : opt.value === "llm_chat" ? (
                        <img id="add-step-type-llm_chat-icon" className="add-step-type-card__icon" src="/media/bot_icon" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      ) : opt.value === "tool" ? (
                        <img id="add-step-type-tool-icon" className="add-step-type-card__icon" src="/media/tools_icon.png" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      ) : opt.value === "api" ? (
                        <img id="add-step-type-api-icon" className="add-step-type-card__icon" src="/media/api_icon.png" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      ) : opt.value === "condition" ? (
                        <img id="add-step-type-condition-icon" className="add-step-type-card__icon" src="/media/conditional_icon.png" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      ) : (
                        <img id="add-step-type-script-icon" className="add-step-type-card__icon" src="/media/script_icon.png" alt="" aria-hidden="true" style={{ width: "128px", height: "128px", flex: "0 0 128px" }} />
                      )}
                      <span id={`add-step-type-${opt.value}-label`} className="add-step-type-card__label add-step-type-card__label--below">
                        {opt.value === "log" ? "Write" : opt.label}
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
                    onChange={(e) =>
                      setDraft((prev) => prev ? { ...prev, name: e.target.value } : prev)
                    }
                  />
                </label>

                {/* API step branching menu */}
                {pickedType === "api" && !apiMode && (
                  <div id="add-step-api-mode-picker" style={{ display: "flex", gap: 24, margin: "32px 0" }}>
                    <button
                      type="button"
                      id="add-step-api-mode-prebuilt"
                      style={{
                        flex: 1,
                        background: "var(--neutral-surface)",
                        border: "2px solid var(--brand-main)",
                        color: "var(--brand-main)",
                        borderRadius: 8,
                        padding: "32px 0",
                        fontWeight: 600,
                        fontSize: 18,
                        cursor: "pointer",
                        transition: "border-color 0.2s, color 0.2s"
                      }}
                      onClick={() => { setApiMode("prebuilt"); setDraft((prev) => prev ? { ...prev, config: { ...prev.config, api_mode: "prebuilt" } } : prev); }}
                      onMouseOver={e => (e.currentTarget.style.borderColor = "var(--brand-primary)")}
                      onMouseOut={e => (e.currentTarget.style.borderColor = "var(--brand-main)")}
                    >
                      <span style={{ display: "block", fontSize: 24, marginBottom: 8 }}>Prebuilt connector</span>
                      <span style={{ color: "var(--neutral-secondary-text)", fontWeight: 400 }}>Provider-aware action (recommended)</span>
                    </button>
                    <button
                      type="button"
                      id="add-step-api-mode-custom"
                      style={{
                        flex: 1,
                        background: "var(--neutral-surface)",
                        border: "2px solid var(--brand-main)",
                        color: "var(--brand-main)",
                        borderRadius: 8,
                        padding: "32px 0",
                        fontWeight: 600,
                        fontSize: 18,
                        cursor: "pointer",
                        transition: "border-color 0.2s, color 0.2s"
                      }}
                      onClick={() => { setApiMode("custom"); setDraft((prev) => prev ? { ...prev, config: { ...prev.config, api_mode: "custom" } } : prev); }}
                      onMouseOver={e => (e.currentTarget.style.borderColor = "var(--brand-primary)")}
                      onMouseOut={e => (e.currentTarget.style.borderColor = "var(--brand-main)")}
                    >
                      <span style={{ display: "block", fontSize: 24, marginBottom: 8 }}>Custom HTTP request</span>
                      <span style={{ color: "var(--neutral-secondary-text)", fontWeight: 400 }}>Raw HTTP call (advanced)</span>
                    </button>
                  </div>
                )}

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
