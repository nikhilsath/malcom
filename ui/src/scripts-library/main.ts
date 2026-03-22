import { Compartment, EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { indentWithTab } from "@codemirror/commands";
import { bracketMatching, foldGutter, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { normalizeRequestError, requestJson } from "../lib/request";

type ScriptLanguage = "python" | "javascript";
type ValidationStatus = "valid" | "invalid" | "unknown";

type ScriptSummary = {
  id: string;
  name: string;
  description: string;
  language: ScriptLanguage;
  sample_input: string;
  validation_status: ValidationStatus;
  validation_message: string | null;
  last_validated_at: string | null;
  created_at: string;
  updated_at: string;
};

type ScriptRecord = ScriptSummary & {
  code: string;
};

type ValidationIssue = {
  message: string;
  line: number | null;
  column: number | null;
};

type ValidationResult = {
  valid: boolean;
  issues: ValidationIssue[];
};

const scriptElements = {
  alert: document.getElementById("script-library-alert"),
  createButton: document.getElementById("scripts-library-create-button") as HTMLButtonElement | null,
  searchInput: document.getElementById("scripts-library-search-input") as HTMLInputElement | null,
  list: document.getElementById("scripts-library-list"),
  empty: document.getElementById("scripts-library-empty"),
  totalValue: document.getElementById("scripts-library-summary-total-value"),
  pythonValue: document.getElementById("scripts-library-summary-python-value"),
  javascriptValue: document.getElementById("scripts-library-summary-javascript-value"),
  validValue: document.getElementById("scripts-library-summary-valid-value"),
  form: document.getElementById("scripts-library-form") as HTMLFormElement | null,
  scriptIdInput: document.getElementById("scripts-library-script-id-input") as HTMLInputElement | null,
  nameInput: document.getElementById("scripts-library-name-input") as HTMLInputElement | null,
  descriptionInput: document.getElementById("scripts-library-description-input") as HTMLTextAreaElement | null,
  languageInput: document.getElementById("scripts-library-language-input") as HTMLSelectElement | null,
  sampleInputInput: document.getElementById("scripts-library-sample-input-input") as HTMLTextAreaElement | null,
  editorHost: document.getElementById("scripts-library-editor"),
  validateButton: document.getElementById("scripts-library-validate-button") as HTMLButtonElement | null,
  validationFeedback: document.getElementById("scripts-library-validation-feedback"),
  formFeedback: document.getElementById("scripts-library-form-feedback"),
  validationChip: document.getElementById("scripts-library-validation-chip"),
  saveButton: document.getElementById("scripts-library-save-button") as HTMLButtonElement | null,
  editorModal: document.getElementById("scripts-library-editor-modal"),
  modalCloseButtons: Array.from(document.querySelectorAll("[data-modal-close='scripts-library-editor-modal']")) as HTMLElement[]
};

const scriptState = {
  scripts: [] as ScriptSummary[],
  selectedScriptId: null as string | null,
  query: "",
  lastValidation: {
    status: "unknown" as ValidationStatus,
    message: "Not validated"
  }
};

const openEditorModal = () => {
  if (!scriptElements.editorModal) {
    return;
  }
  scriptElements.editorModal.classList.add("modal--open");
  document.body.classList.add("modal-open");
};

const closeEditorModal = () => {
  if (!scriptElements.editorModal) {
    return;
  }
  scriptElements.editorModal.classList.remove("modal--open");
  document.body.classList.remove("modal-open");
};

const languageCompartment = new Compartment();

const defaultTemplates: Record<ScriptLanguage, string> = {
  python: [
    "def run(context, script_input=None):",
    "    payload = context.get('payload', {})",
    "    return script_input or payload",
    ""
  ].join("\n"),
  javascript: [
    "function run(context, scriptInput) {",
    "  const payload = context?.payload ?? {};",
    "  return scriptInput || payload;",
    "}",
    ""
  ].join("\n")
};

const languageLabels: Record<ScriptLanguage, string> = {
  python: "Python",
  javascript: "JavaScript"
};

const editorView = scriptElements.editorHost
  ? new EditorView({
      parent: scriptElements.editorHost,
      state: EditorState.create({
        doc: defaultTemplates.python,
        extensions: [
          history(),
          foldGutter(),
          indentOnInput(),
          bracketMatching(),
          syntaxHighlighting(defaultHighlightStyle),
          keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
          EditorView.lineWrapping,
          EditorView.theme({
            "&": {
              minHeight: "420px",
              backgroundColor: "#fbfdff",
              color: "#0f172a"
            },
            ".cm-content": {
              fontFamily: "SFMono-Regular, Consolas, Liberation Mono, monospace",
              padding: "16px"
            },
            ".cm-gutters": {
              backgroundColor: "#f8fafc",
              color: "#64748b",
              borderRight: "1px solid #dbe3ef"
            }
          }),
          languageCompartment.of(python())
        ]
      })
    })
  : null;

const emitScriptLog = (action: string, message: string, level = "info", details: Record<string, unknown> = {}) => {
  window.MalcomLogStore?.log?.({
    source: "ui.scripts.library",
    category: "scripts",
    action,
    level,
    message,
    details,
    context: {
      path: window.location.pathname
    }
  });
};

const setAlert = (message: string, tone = "") => {
  if (!scriptElements.alert) {
    return;
  }

  if (!message) {
    scriptElements.alert.hidden = true;
    scriptElements.alert.textContent = "";
    scriptElements.alert.className = "script-system-alert";
    return;
  }

  scriptElements.alert.hidden = false;
  scriptElements.alert.textContent = message;
  scriptElements.alert.className = tone
    ? `script-system-alert script-system-alert--${tone}`
    : "script-system-alert";
};

const setFeedback = (element: HTMLElement | null, message: string, tone = "") => {
  if (!element) {
    return;
  }

  element.textContent = message;
  element.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const setValidationChip = (status: ValidationStatus, message: string) => {
  if (!scriptElements.validationChip) {
    return;
  }

  scriptElements.validationChip.textContent = message;
  scriptElements.validationChip.className = `script-validation-chip script-validation-chip--${status}`;
  scriptState.lastValidation = { status, message };
};

const getEditorCode = () => editorView?.state.doc.toString() ?? "";

const setEditorCode = (code: string) => {
  if (!editorView) {
    return;
  }

  editorView.dispatch({
    changes: {
      from: 0,
      to: editorView.state.doc.length,
      insert: code
    }
  });
};

const setEditorLanguage = (language: ScriptLanguage) => {
  if (!editorView) {
    return;
  }

  editorView.dispatch({
    effects: languageCompartment.reconfigure(language === "javascript" ? javascript() : python())
  });
};

const formatTimestamp = (value: string | null) => {
  if (!value) {
    return "Never validated";
  }

  const timestamp = new Date(value);
  return Number.isNaN(timestamp.valueOf()) ? value : timestamp.toLocaleString();
};

const escapeHtml = (value: string) => value
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll("\"", "&quot;")
  .replaceAll("'", "&#39;");

const getFilteredScripts = () => {
  const normalizedQuery = scriptState.query.trim().toLowerCase();
  if (!normalizedQuery) {
    return scriptState.scripts;
  }

  return scriptState.scripts.filter((script) =>
    `${script.name} ${script.description}`.toLowerCase().includes(normalizedQuery)
  );
};

const updateSummary = () => {
  const pythonCount = scriptState.scripts.filter((script) => script.language === "python").length;
  const javascriptCount = scriptState.scripts.filter((script) => script.language === "javascript").length;
  const validCount = scriptState.scripts.filter((script) => script.validation_status === "valid").length;

  if (scriptElements.totalValue) {
    scriptElements.totalValue.textContent = String(scriptState.scripts.length);
  }
  if (scriptElements.pythonValue) {
    scriptElements.pythonValue.textContent = String(pythonCount);
  }
  if (scriptElements.javascriptValue) {
    scriptElements.javascriptValue.textContent = String(javascriptCount);
  }
  if (scriptElements.validValue) {
    scriptElements.validValue.textContent = String(validCount);
  }
};

const renderScriptList = () => {
  if (!scriptElements.list || !scriptElements.empty) {
    return;
  }

  const filteredScripts = getFilteredScripts();
  scriptElements.empty.hidden = filteredScripts.length > 0;
  scriptElements.list.innerHTML = filteredScripts.map((script) => {
    const selectedClass = script.id === scriptState.selectedScriptId ? " script-library-item--selected" : "";
    const validationLabel = script.validation_status === "valid"
      ? "Validated"
      : script.validation_status === "invalid"
        ? "Needs fixes"
        : "Unknown";

    return `
      <button
        type="button"
        id="scripts-library-item-${script.id}"
        class="script-library-item${selectedClass}"
        data-script-id="${escapeHtml(script.id)}"
        aria-pressed="${script.id === scriptState.selectedScriptId ? "true" : "false"}"
      >
        <div id="scripts-library-item-header-${script.id}" class="script-library-item__header">
          <div id="scripts-library-item-copy-${script.id}">
            <p id="scripts-library-item-title-${script.id}" class="script-library-item__title">${escapeHtml(script.name)}</p>
            <p id="scripts-library-item-description-${script.id}" class="script-library-item__description">${escapeHtml(script.description || "No description yet.")}</p>
          </div>
        </div>
        <div id="scripts-library-item-badges-${script.id}" class="script-library-item__badge-row">
          <span id="scripts-library-item-language-${script.id}" class="script-language-badge">${languageLabels[script.language]}</span>
          <span id="scripts-library-item-status-${script.id}" class="script-status-badge script-status-badge--${script.validation_status}">${validationLabel}</span>
        </div>
        <p id="scripts-library-item-meta-${script.id}" class="script-library-item__meta">Updated ${escapeHtml(formatTimestamp(script.updated_at))}</p>
      </button>
    `;
  }).join("");

  Array.from(scriptElements.list.querySelectorAll<HTMLButtonElement>("[data-script-id]")).forEach((button) => {
    button.addEventListener("click", () => {
      const scriptId = button.dataset.scriptId;
      if (scriptId) {
        void loadScript(scriptId);
      }
    });
  });
};

const resetForm = (language: ScriptLanguage = "python") => {
  scriptState.selectedScriptId = null;
  if (scriptElements.scriptIdInput) {
    scriptElements.scriptIdInput.value = "";
  }
  if (scriptElements.nameInput) {
    scriptElements.nameInput.value = "";
  }
  if (scriptElements.descriptionInput) {
    scriptElements.descriptionInput.value = "";
  }
  if (scriptElements.languageInput) {
    scriptElements.languageInput.value = language;
  }
  if (scriptElements.sampleInputInput) {
    scriptElements.sampleInputInput.value = "";
  }
  setEditorLanguage(language);
  setEditorCode(defaultTemplates[language]);
  setValidationChip("unknown", "Not validated");
  setFeedback(scriptElements.validationFeedback, "");
  setFeedback(scriptElements.formFeedback, "");
  renderScriptList();
};

const applyScriptToForm = (script: ScriptRecord) => {
  scriptState.selectedScriptId = script.id;
  if (scriptElements.scriptIdInput) {
    scriptElements.scriptIdInput.value = script.id;
  }
  if (scriptElements.nameInput) {
    scriptElements.nameInput.value = script.name;
  }
  if (scriptElements.descriptionInput) {
    scriptElements.descriptionInput.value = script.description;
  }
  if (scriptElements.languageInput) {
    scriptElements.languageInput.value = script.language;
  }
  if (scriptElements.sampleInputInput) {
    scriptElements.sampleInputInput.value = script.sample_input || "";
  }
  setEditorLanguage(script.language);
  setEditorCode(script.code);
  setValidationChip(
    script.validation_status,
    script.validation_status === "valid"
      ? "Validated"
      : script.validation_status === "invalid"
        ? "Needs fixes"
        : "Not validated"
  );
  setFeedback(
    scriptElements.validationFeedback,
    script.validation_message ? `Last validation: ${script.validation_message}` : `Last checked: ${formatTimestamp(script.last_validated_at)}`,
    script.validation_status === "invalid" ? "error" : script.validation_status === "valid" ? "success" : ""
  );
  setFeedback(scriptElements.formFeedback, "");
  renderScriptList();
};

const loadScripts = async () => {
  const scripts = await requestJson<ScriptSummary[]>("/api/v1/scripts");
  scriptState.scripts = scripts;
  updateSummary();
  renderScriptList();

  if (scripts.length === 0) {
    resetForm("python");
  }
};

const loadScript = async (scriptId: string) => {
  const script = await requestJson<ScriptRecord>(`/api/v1/scripts/${scriptId}`);
  applyScriptToForm(script);
  openEditorModal();
};

const validateCurrentScript = async () => {
  const language = (scriptElements.languageInput?.value || "python") as ScriptLanguage;
  const code = getEditorCode().trim();

  if (!code) {
    setValidationChip("invalid", "Code required");
    setFeedback(scriptElements.validationFeedback, "Source code is required before validation.", "error");
    return null;
  }

  setFeedback(scriptElements.validationFeedback, "Running validation...", "");
  const result = await requestJson<ValidationResult>("/api/v1/scripts/validate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      language,
      code
    })
  });

  if (result.valid) {
    setValidationChip("valid", "Validated");
    setFeedback(scriptElements.validationFeedback, `${languageLabels[language]} syntax check passed.`, "success");
  } else {
    const message = result.issues
      .map((issue) => {
        const location = issue.line ? `Line ${issue.line}${issue.column ? `, column ${issue.column}` : ""}: ` : "";
        return `${location}${issue.message}`;
      })
      .join(" ");
    setValidationChip("invalid", "Needs fixes");
    setFeedback(scriptElements.validationFeedback, message, "error");
  }

  return result;
};

const handleSave = async (event: SubmitEvent) => {
  event.preventDefault();

  const name = scriptElements.nameInput?.value.trim() || "";
  const description = scriptElements.descriptionInput?.value.trim() || "";
  const language = (scriptElements.languageInput?.value || "python") as ScriptLanguage;
  const sampleInput = scriptElements.sampleInputInput?.value || "";
  const code = getEditorCode();
  const scriptId = scriptElements.scriptIdInput?.value || "";

  if (!name) {
    setFeedback(scriptElements.formFeedback, "Script name is required.", "error");
    return;
  }

  if (!code.trim()) {
    setFeedback(scriptElements.formFeedback, "Source code is required.", "error");
    return;
  }

  setFeedback(scriptElements.formFeedback, scriptId ? "Saving script..." : "Creating script...", "");

  try {
    const savedScript = await requestJson<ScriptRecord>(scriptId ? `/api/v1/scripts/${scriptId}` : "/api/v1/scripts", {
      method: scriptId ? "PATCH" : "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name,
        description,
        language,
        sample_input: sampleInput,
        code
      })
    });

    await loadScripts();
    applyScriptToForm(savedScript);
    setFeedback(scriptElements.formFeedback, "Script saved to the library.", "success");
    emitScriptLog(scriptId ? "script_updated" : "script_created", `Saved ${languageLabels[language]} script ${savedScript.name}.`);
  } catch (error) {
    const message = normalizeRequestError(error, "Unable to save script.").message;
    setValidationChip("invalid", "Needs fixes");
    setFeedback(scriptElements.formFeedback, message, "error");
    emitScriptLog("script_save_failed", message, "error");
  }
};

scriptElements.createButton?.addEventListener("click", () => {
  resetForm("python");
  openEditorModal();
  scriptElements.nameInput?.focus();
});

scriptElements.searchInput?.addEventListener("input", () => {
  scriptState.query = scriptElements.searchInput?.value || "";
  renderScriptList();
});

scriptElements.languageInput?.addEventListener("change", () => {
  const language = (scriptElements.languageInput?.value || "python") as ScriptLanguage;
  setEditorLanguage(language);
  if (!scriptElements.scriptIdInput?.value && !getEditorCode().trim()) {
    setEditorCode(defaultTemplates[language]);
  }
  setValidationChip("unknown", "Not validated");
  setFeedback(scriptElements.validationFeedback, "");
});

scriptElements.validateButton?.addEventListener("click", () => {
  void validateCurrentScript();
});

scriptElements.form?.addEventListener("submit", (event) => {
  void handleSave(event as SubmitEvent);
});

scriptElements.modalCloseButtons.forEach((button) => {
  button.addEventListener("click", closeEditorModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && scriptElements.editorModal?.classList.contains("modal--open")) {
    closeEditorModal();
  }
});

void loadScripts().catch((error) => {
  const message = normalizeRequestError(error, "Unable to load scripts.").message;
  setAlert(message, "error");
  setFeedback(scriptElements.formFeedback, message, "error");
  emitScriptLog("script_load_failed", message, "error");
});
