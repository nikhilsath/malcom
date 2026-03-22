import { useMemo, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import type { AutomationStep } from "../types";

type ScriptOption = { id: string; name: string };

type Props = {
  draft: AutomationStep;
  scripts?: ScriptOption[];
  onChange: (step: AutomationStep) => void;
};

type ScriptLanguage = "python" | "javascript";

const defaultTemplates: Record<ScriptLanguage, string> = {
  python: [
    "def run(context):",
    "    payload = context.get('payload', {})",
    "    return payload",
    ""
  ].join("\n"),
  javascript: [
    "export function run(context) {",
    "  const payload = context?.payload ?? {};",
    "  return payload;",
    "}",
    ""
  ].join("\n")
};

type ScriptRecord = {
  id: string;
  name: string;
};

const sortScripts = (items: ScriptRecord[]) =>
  [...items].sort((a, b) => a.name.localeCompare(b.name));

export const ScriptStepForm = ({ draft, scripts, onChange }: Props) => {
  const [availableScripts, setAvailableScripts] = useState<ScriptRecord[]>(() => sortScripts(scripts || []));
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newLanguage, setNewLanguage] = useState<ScriptLanguage>("python");
  const [newCode, setNewCode] = useState(defaultTemplates.python);

  const hasScripts = availableScripts.length > 0;
  const selectedScriptId = draft.config.script_id || "";

  const languageHelpText = useMemo(
    () => (newLanguage === "python" ? "Use a run(context) function." : "Use an exported run(context) function."),
    [newLanguage]
  );

  const resetCreateForm = () => {
    setNewName("");
    setNewDescription("");
    setNewLanguage("python");
    setNewCode(defaultTemplates.python);
    setCreateError(null);
  };

  const handleLanguageChange = (value: ScriptLanguage) => {
    setNewLanguage(value);
    if (!newCode.trim() || newCode === defaultTemplates.python || newCode === defaultTemplates.javascript) {
      setNewCode(defaultTemplates[value]);
    }
  };

  const handleCreateScript = async () => {
    const name = newName.trim();
    const description = newDescription.trim();
    const code = newCode.trim();

    if (!name) {
      setCreateError("Script name is required.");
      return;
    }
    if (!code) {
      setCreateError("Script code is required.");
      return;
    }

    setCreateError(null);
    setSaving(true);
    try {
      const response = await fetch("/api/v1/scripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          description,
          language: newLanguage,
          code
        })
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setCreateError(data.detail || "Unable to create script.");
        setSaving(false);
        return;
      }

      const created = await response.json();
      const nextScripts = sortScripts([...availableScripts, { id: created.id, name: created.name }]);
      setAvailableScripts(nextScripts);
      onChange({ ...draft, config: { ...draft.config, script_id: created.id } });
      setCreateModalOpen(false);
      resetCreateForm();
    } catch {
      setCreateError("Unexpected error creating script.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <label
        id="add-step-script-id-field"
        className="automation-field automation-field--full automation-field--inline-label"
      >
        <span id="add-step-script-id-label" className="automation-field__label">Script</span>
        <div id="add-step-script-id-controls" className="add-step-script-controls">
          <select
            id="add-step-script-id-input"
            className="automation-native-select"
            value={selectedScriptId}
            onChange={(e) =>
              onChange({ ...draft, config: { ...draft.config, script_id: e.target.value } })
            }
          >
            <option value="">{hasScripts ? "Select a script…" : "No scripts available"}</option>
            {availableScripts.map((script) => (
              <option key={script.id} value={script.id}>{script.name}</option>
            ))}
          </select>
          <button
            id="add-step-script-create-button"
            type="button"
            className="button button--secondary add-step-script-create-button"
            onClick={() => {
              resetCreateForm();
              setCreateModalOpen(true);
            }}
          >
            Create new script
          </button>
        </div>
      </label>

      <Dialog.Root open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop
            id="add-step-script-create-backdrop"
            className="automation-dialog-backdrop"
          />
          <Dialog.Popup id="add-step-script-create-modal" className="automation-dialog automation-dialog--wide">
            <div id="add-step-script-create-dismiss-row" className="automation-dialog__dismiss-row">
              <Dialog.Close
                id="add-step-script-create-close-icon"
                className="modal__close-icon-button automation-dialog__close-button"
                aria-label="Close create script dialog"
              >
                ×
              </Dialog.Close>
            </div>

            <Dialog.Title id="add-step-script-create-title" className="automation-dialog__title">
              Create script
            </Dialog.Title>
            <Dialog.Description id="add-step-script-create-description" className="automation-dialog__description">
              Write a script and save it to the library for this step.
            </Dialog.Description>

            <div id="add-step-script-create-form" className="automation-form automation-form--modal">
              <label id="add-step-script-create-name-field" className="automation-field automation-field--full">
                <span id="add-step-script-create-name-label" className="automation-field__label">Name</span>
                <input
                  id="add-step-script-create-name-input"
                  className="automation-input"
                  value={newName}
                  placeholder="Script name"
                  onChange={(e) => setNewName(e.target.value)}
                />
              </label>

              <label id="add-step-script-create-language-field" className="automation-field automation-field--full">
                <span id="add-step-script-create-language-label" className="automation-field__label">Language</span>
                <select
                  id="add-step-script-create-language-input"
                  className="automation-native-select"
                  value={newLanguage}
                  onChange={(e) => handleLanguageChange(e.target.value as ScriptLanguage)}
                >
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                </select>
              </label>

              <label id="add-step-script-create-description-field" className="automation-field automation-field--full">
                <span id="add-step-script-create-description-label" className="automation-field__label">Description (optional)</span>
                <input
                  id="add-step-script-create-description-input"
                  className="automation-input"
                  value={newDescription}
                  placeholder="What this script does"
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </label>

              <label id="add-step-script-create-code-field" className="automation-field automation-field--full">
                <span id="add-step-script-create-code-label" className="automation-field__label">Code</span>
                <textarea
                  id="add-step-script-create-code-input"
                  className="automation-textarea automation-textarea--code automation-code-input"
                  value={newCode}
                  rows={12}
                  onChange={(e) => setNewCode(e.target.value)}
                />
                <span id="add-step-script-create-code-hint" className="automation-field__hint">
                  {languageHelpText}
                </span>
              </label>

              {createError ? (
                <p id="add-step-script-create-error" className="automation-field__hint" role="alert">
                  {createError}
                </p>
              ) : null}
            </div>

            <div id="add-step-script-create-actions" className="automation-dialog__actions">
              <button
                id="add-step-script-create-cancel"
                type="button"
                className="button button--secondary"
                onClick={() => setCreateModalOpen(false)}
              >
                Cancel
              </button>
              <button
                id="add-step-script-create-submit"
                type="button"
                className="primary-action-button"
                disabled={saving}
                onClick={() => {
                  void handleCreateScript();
                }}
              >
                {saving ? "Saving..." : "Save script"}
              </button>
            </div>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
};
