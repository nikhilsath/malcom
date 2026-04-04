import { useEffect, useMemo, useRef, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { requestJson } from "../../lib/request";
import type { DataFlowToken } from "../data-flow";
import { TokenPicker } from "../token-picker";
import { SCRIPT_LANGUAGE_LABELS, SCRIPT_LANGUAGE_TEMPLATES } from "../constants";
import type { AutomationStep, RepoCheckoutOption, ScriptLanguageOption, ScriptLibraryItem } from "../types";

type Props = {
  draft: AutomationStep;
  scripts?: ScriptLibraryItem[];
  scriptLanguages?: ScriptLanguageOption[];
  dataFlowTokens?: DataFlowToken[];
  repoCheckoutOptions?: RepoCheckoutOption[];
  onChange: (step: AutomationStep) => void;
  idPrefix?: string;
  allowCreate?: boolean;
};

type ScriptLanguage = "python" | "javascript";

const requestJsonCompat = async <T,>(path: string, options?: RequestInit): Promise<T> => {
  if (typeof window !== "undefined" && typeof window.Malcom?.requestJson === "function") {
    return (await window.Malcom.requestJson(path, options)) as T;
  }
  return (await requestJson(path, options)) as T;
};

const sortScripts = (items: ScriptLibraryItem[]) =>
  [...items].sort((a, b) => a.name.localeCompare(b.name));

export const ScriptStepForm = ({
  draft,
  scripts,
  scriptLanguages = [],
  dataFlowTokens = [],
  repoCheckoutOptions = [],
  onChange,
  idPrefix = "add-step",
  allowCreate = true
}: Props) => {
  const availableScriptLanguages = scriptLanguages.length > 0
    ? scriptLanguages
    : Object.entries(SCRIPT_LANGUAGE_LABELS).map(([value, label]) => ({ value: value as ScriptLanguage, label }));
  const [availableScripts, setAvailableScripts] = useState<ScriptLibraryItem[]>(() => sortScripts(scripts || []));
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newLanguage, setNewLanguage] = useState<ScriptLanguage>("python");
  const [newSampleInput, setNewSampleInput] = useState("");
  const [newCode, setNewCode] = useState(SCRIPT_LANGUAGE_TEMPLATES.python);
  const scriptInputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setAvailableScripts(sortScripts(scripts || []));
  }, [scripts]);

  const hasScripts = availableScripts.length > 0;
  const selectedScriptId = draft.config.script_id || "";
  const selectedScript = availableScripts.find((script) => script.id === selectedScriptId) || null;

  const languageHelpText = useMemo(
    () => (newLanguage === "python"
      ? "Use run(context, script_input) or assign result directly."
      : "Use run(context, scriptInput) or assign result directly."),
    [newLanguage]
  );

  const resetCreateForm = () => {
    setNewName("");
    setNewDescription("");
    setNewLanguage("python");
    setNewSampleInput("");
    setNewCode(SCRIPT_LANGUAGE_TEMPLATES.python);
    setCreateError(null);
  };

  const applyScriptSelection = (scriptId: string) => {
    const nextScript = availableScripts.find((script) => script.id === scriptId) || null;
    onChange({
      ...draft,
      config: {
        ...draft.config,
        script_id: scriptId,
        script_input_template: draft.config.script_input_template || nextScript?.sample_input || ""
      }
    });
  };

  const handleLanguageChange = (value: ScriptLanguage) => {
    setNewLanguage(value);
    if (!newCode.trim() || newCode === SCRIPT_LANGUAGE_TEMPLATES.python || newCode === SCRIPT_LANGUAGE_TEMPLATES.javascript) {
      setNewCode(SCRIPT_LANGUAGE_TEMPLATES[value]);
    }
  };

  const insertTokenIntoScriptInput = (token: string) => {
    const currentValue = draft.config.script_input_template || "";
    const textarea = scriptInputRef.current;
    if (!textarea) {
      onChange({
        ...draft,
        config: { ...draft.config, script_input_template: `${currentValue}${token}` }
      });
      return;
    }
    const selectionStart = textarea.selectionStart ?? currentValue.length;
    const selectionEnd = textarea.selectionEnd ?? selectionStart;
    const nextValue = `${currentValue.slice(0, selectionStart)}${token}${currentValue.slice(selectionEnd)}`;
    onChange({
      ...draft,
      config: { ...draft.config, script_input_template: nextValue }
    });
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
      const created = await requestJsonCompat<ScriptLibraryItem>("/api/v1/scripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          description,
          language: newLanguage,
          sample_input: newSampleInput,
          code
        })
      });
      const nextScripts = sortScripts([...availableScripts, created]);
      setAvailableScripts(nextScripts);
      onChange({
        ...draft,
        config: {
          ...draft.config,
          script_id: created.id,
          script_input_template: draft.config.script_input_template || created.sample_input || ""
        }
      });
      setCreateModalOpen(false);
      resetCreateForm();
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Unable to create script.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <label
        id={`${idPrefix}-script-id-field`}
        className="automation-field automation-field--full automation-field--inline-label"
      >
        <span id={`${idPrefix}-script-id-label`} className="automation-field__label">Script</span>
        <div id={`${idPrefix}-script-id-controls`} className="add-step-script-controls">
          <select
            id={`${idPrefix}-script-id-input`}
            className="automation-native-select"
            aria-labelledby={`${idPrefix}-script-id-label`}
            value={selectedScriptId}
            onChange={(event) => applyScriptSelection(event.target.value)}
          >
            <option value="">{hasScripts ? "Select a script..." : "No scripts available"}</option>
            {availableScripts.map((script) => (
              <option key={script.id} value={script.id}>{script.name}</option>
            ))}
          </select>
          {allowCreate ? (
            <button
              id={`${idPrefix}-script-create-button`}
              type="button"
              className="button button--success add-step-script-create-button"
              onClick={() => {
                resetCreateForm();
                setCreateModalOpen(true);
              }}
            >
              Create new script
            </button>
          ) : null}
        </div>
      </label>

      {selectedScript ? (
        <div id={`${idPrefix}-script-selected-meta`} className="automation-switch-field__description">
          {selectedScript.description || `Selected ${selectedScript.language} script.`}
        </div>
      ) : null}

      {selectedScript?.expected_output && (() => {
        try {
          const parsed = JSON.parse(selectedScript.expected_output) as Record<string, string>;
          const entries = Object.entries(parsed).filter(([key]) => Boolean(key));
          if (entries.length === 0) return null;
          return (
            <div id={`${idPrefix}-script-output-fields`} className="automation-switch-field__description">
              <strong>Output fields:</strong>{" "}
              {entries.map(([key, desc], i) => (
                <span key={key}>
                  <code>{`{{steps.…${key}}}`}</code>
                  {desc ? ` — ${desc}` : ""}
                  {i < entries.length - 1 ? ", " : ""}
                </span>
              ))}
            </div>
          );
        } catch {
          return null;
        }
      })()}

      <label id={`${idPrefix}-script-input-field`} className="automation-field automation-field--full">
        <span id={`${idPrefix}-script-input-label`} className="automation-field__label">Script input</span>
        <textarea
          id={`${idPrefix}-script-input-input`}
          ref={scriptInputRef}
          className="automation-textarea automation-textarea--code"
          aria-labelledby={`${idPrefix}-script-input-label`}
          rows={8}
          placeholder={selectedScript?.sample_input || "{\"text\":\"{{payload.text}}\"}"}
          value={draft.config.script_input_template || ""}
          onChange={(event) =>
            onChange({
              ...draft,
              config: { ...draft.config, script_input_template: event.target.value }
            })
          }
        />
        <span id={`${idPrefix}-script-input-hint`} className="automation-field__hint">
          Provide plain text or JSON. JSON is parsed before the script runs.
        </span>
        {selectedScript?.sample_input ? (
          <button
            id={`${idPrefix}-script-input-sample-button`}
            type="button"
            className="button button--secondary"
            onClick={() =>
              onChange({
                ...draft,
                config: { ...draft.config, script_input_template: selectedScript.sample_input }
              })
            }
          >
            Use sample input
          </button>
        ) : null}
      </label>

      {dataFlowTokens.length > 0 ? (
        <TokenPicker
          idPrefix={`${idPrefix}-script-input`}
          tokens={dataFlowTokens}
          description="Insert available workflow outputs directly into script input templates."
          onInsert={insertTokenIntoScriptInput}
        />
      ) : null}

      {/* Repo checkout picker (shown when repo checkouts are available) */}
      {repoCheckoutOptions.length > 0 && (
        <>
          <label id={`${idPrefix}-script-repo-checkout-field`} className="automation-field automation-field--full">
            <span id={`${idPrefix}-script-repo-checkout-label`} className="automation-field__label">Repo checkout (optional)</span>
            <select
              id={`${idPrefix}-script-repo-checkout-input`}
              className="automation-native-select"
              value={String(draft.config.repo_checkout_id || "")}
              onChange={(e) => onChange({ ...draft, config: { ...draft.config, repo_checkout_id: e.target.value || undefined } })}
            >
              <option value="">— use default working directory —</option>
              {repoCheckoutOptions.map((checkout) => (
                <option key={checkout.id} value={checkout.id}>
                  {checkout.repo_url} ({checkout.branch})
                </option>
              ))}
            </select>
          </label>
          {draft.config.repo_checkout_id && (
            <label id={`${idPrefix}-script-working-dir-field`} className="automation-field automation-field--full">
              <span id={`${idPrefix}-script-working-dir-label`} className="automation-field__label">Working directory (optional)</span>
              <input
                id={`${idPrefix}-script-working-dir-input`}
                type="text"
                className="automation-input"
                placeholder="Subdirectory within the repo (e.g. src/scripts)"
                value={String(draft.config.working_directory || "")}
                onChange={(e) => onChange({ ...draft, config: { ...draft.config, working_directory: e.target.value || undefined } })}
              />
            </label>
          )}
        </>
      )}

      <Dialog.Root open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop
            id={`${idPrefix}-script-create-backdrop`}
            className="automation-dialog-backdrop"
          />
          <Dialog.Popup id={`${idPrefix}-script-create-modal`} className="automation-dialog automation-dialog--wide">
            <div id={`${idPrefix}-script-create-dismiss-row`} className="automation-dialog__dismiss-row">
              <Dialog.Close
                id={`${idPrefix}-script-create-close-icon`}
                className="modal__close-icon-button automation-dialog__close-button"
                aria-label="Close create script dialog"
              >
                ×
              </Dialog.Close>
            </div>

            <Dialog.Title id={`${idPrefix}-script-create-title`} className="automation-dialog__title">
              Create script
            </Dialog.Title>
            <Dialog.Description id={`${idPrefix}-script-create-description`} className="automation-dialog__description">
              Save a reusable script and its sample input for later automation steps.
            </Dialog.Description>

            <div id={`${idPrefix}-script-create-form`} className="automation-form automation-form--modal">
              <label id={`${idPrefix}-script-create-name-field`} className="automation-field automation-field--full">
                <span id={`${idPrefix}-script-create-name-label`} className="automation-field__label">Name</span>
                <input
                  id={`${idPrefix}-script-create-name-input`}
                  className="automation-input"
                  value={newName}
                  placeholder="Script name"
                  onChange={(event) => setNewName(event.target.value)}
                />
              </label>

              <label id={`${idPrefix}-script-create-language-field`} className="automation-field automation-field--full">
                <span id={`${idPrefix}-script-create-language-label`} className="automation-field__label">Language</span>
                <select
                  id={`${idPrefix}-script-create-language-input`}
                  className="automation-native-select"
                  value={newLanguage}
                  onChange={(event) => handleLanguageChange(event.target.value as ScriptLanguage)}
                >
                  {availableScriptLanguages.map((languageOption) => (
                    <option key={languageOption.value} value={languageOption.value}>{languageOption.label}</option>
                  ))}
                </select>
              </label>

              <label id={`${idPrefix}-script-create-description-field`} className="automation-field automation-field--full">
                <span id={`${idPrefix}-script-create-description-label`} className="automation-field__label">Description (optional)</span>
                <input
                  id={`${idPrefix}-script-create-description-input`}
                  className="automation-input"
                  value={newDescription}
                  placeholder="What this script does"
                  onChange={(event) => setNewDescription(event.target.value)}
                />
              </label>

              <label id={`${idPrefix}-script-create-sample-input-field`} className="automation-field automation-field--full">
                <span id={`${idPrefix}-script-create-sample-input-label`} className="automation-field__label">Sample input (optional)</span>
                <textarea
                  id={`${idPrefix}-script-create-sample-input-input`}
                  className="automation-textarea automation-textarea--code"
                  value={newSampleInput}
                  rows={6}
                  placeholder={"{\"text\":\"alpha,beta,gamma\"}"}
                  onChange={(event) => setNewSampleInput(event.target.value)}
                />
              </label>

              <label id={`${idPrefix}-script-create-code-field`} className="automation-field automation-field--full">
                <span id={`${idPrefix}-script-create-code-label`} className="automation-field__label">Code</span>
                <textarea
                  id={`${idPrefix}-script-create-code-input`}
                  className="automation-textarea automation-textarea--code automation-code-input"
                  value={newCode}
                  rows={12}
                  onChange={(event) => setNewCode(event.target.value)}
                />
                <span id={`${idPrefix}-script-create-code-hint`} className="automation-field__hint">
                  {languageHelpText}
                </span>
              </label>

              {createError ? (
                <p id={`${idPrefix}-script-create-error`} className="automation-field__hint" role="alert">
                  {createError}
                </p>
              ) : null}
            </div>

            <div id={`${idPrefix}-script-create-actions`} className="automation-dialog__actions">
              <button
                id={`${idPrefix}-script-create-cancel`}
                type="button"
                className="button button--secondary"
                onClick={() => setCreateModalOpen(false)}
              >
                Cancel
              </button>
              <button
                id={`${idPrefix}-script-create-submit`}
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
