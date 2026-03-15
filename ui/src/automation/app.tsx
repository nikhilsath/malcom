import { useEffect, useState } from "react";

type TriggerType = "manual" | "schedule" | "inbound_api";
type StepType = "log" | "outbound_request" | "script" | "tool" | "condition";

type AutomationStep = {
  id?: string;
  type: StepType;
  name: string;
  config: {
    message?: string;
    destination_url?: string;
    http_method?: string;
    auth_type?: string;
    payload_template?: string;
    script_id?: string;
    tool_id?: string;
    expression?: string;
    stop_on_false?: boolean;
  };
};

type Automation = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: TriggerType;
  trigger_config: {
    schedule_time?: string | null;
    inbound_api_id?: string | null;
  };
  step_count: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
};

type AutomationDetail = Automation & {
  steps: AutomationStep[];
};

type AutomationRun = {
  run_id: string;
  automation_id: string;
  trigger_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_summary: string | null;
};

type AutomationRunDetail = AutomationRun & {
  steps: Array<{
    step_id: string;
    run_id: string;
    step_name: string;
    status: string;
    request_summary: string | null;
    response_summary: string | null;
    started_at: string;
    finished_at: string | null;
    duration_ms: number | null;
    detail_json: Record<string, unknown> | null;
  }>;
};

type RuntimeStatus = {
  active: boolean;
  last_tick_started_at: string | null;
  last_tick_finished_at: string | null;
  last_error: string | null;
  job_count: number;
};

declare global {
  interface Window {
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<any>;
    };
  }
}

const emptyDetail = (): AutomationDetail => ({
  id: "",
  name: "",
  description: "",
  enabled: true,
  trigger_type: "manual",
  trigger_config: {},
  step_count: 0,
  created_at: "",
  updated_at: "",
  last_run_at: null,
  next_run_at: null,
  steps: [
    {
      type: "log",
      name: "Log step",
      config: {
        message: "Automation executed at {{timestamp}}"
      }
    }
  ]
});

const requestJson = (path: string, options?: RequestInit) => {
  if (!window.Malcom?.requestJson) {
    throw new Error("Malcom request helper is unavailable.");
  }
  return window.Malcom.requestJson(path, options);
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return "Not scheduled";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
};

const stepTemplates: Record<StepType, AutomationStep> = {
  log: { type: "log", name: "Log step", config: { message: "Reached {{timestamp}}" } },
  outbound_request: {
    type: "outbound_request",
    name: "HTTP request",
    config: {
      destination_url: "https://example.com/hooks/run",
      http_method: "POST",
      auth_type: "none",
      payload_template: "{\"automation_id\":\"{{automation.id}}\"}"
    }
  },
  script: { type: "script", name: "Script step", config: { script_id: "" } },
  tool: { type: "tool", name: "Tool step", config: { tool_id: "" } },
  condition: { type: "condition", name: "Condition step", config: { expression: "true", stop_on_false: true } }
};

const validateDraft = (draft: AutomationDetail) => {
  const issues: string[] = [];
  if (!draft.name.trim()) {
    issues.push("Name is required.");
  }
  if (draft.trigger_type === "schedule" && !draft.trigger_config.schedule_time) {
    issues.push("Schedule time is required for scheduled automations.");
  }
  if (draft.trigger_type === "inbound_api" && !draft.trigger_config.inbound_api_id) {
    issues.push("Inbound API id is required for inbound-triggered automations.");
  }
  if (draft.steps.length === 0) {
    issues.push("At least one step is required.");
  }
  return issues;
};

export const AutomationApp = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [draft, setDraft] = useState<AutomationDetail>(emptyDetail);
  const [selectedRun, setSelectedRun] = useState<AutomationRunDetail | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [schedulerJobs, setSchedulerJobs] = useState<Array<Record<string, unknown>>>([]);
  const [feedback, setFeedback] = useState("");
  const [feedbackTone, setFeedbackTone] = useState("");

  const loadRuntime = async () => {
    const [status, jobs] = await Promise.all([
      requestJson("/api/v1/runtime/status"),
      requestJson("/api/v1/scheduler/jobs")
    ]);
    setRuntimeStatus(status);
    setSchedulerJobs(jobs);
  };

  const loadAutomations = async (nextSelectedId?: string) => {
    const list = (await requestJson("/api/v1/automations")) as Automation[];
    setAutomations(list);
    const targetId = nextSelectedId || draft.id || list[0]?.id;
    if (!targetId) {
      setDraft(emptyDetail());
      setRuns([]);
      setSelectedRun(null);
      return;
    }
    await selectAutomation(targetId);
  };

  const selectAutomation = async (automationId: string) => {
    const [detail, automationRuns] = await Promise.all([
      requestJson(`/api/v1/automations/${automationId}`),
      requestJson(`/api/v1/automations/${automationId}/runs`)
    ]);
    setDraft(detail);
    setRuns(automationRuns);
    setSelectedRun(null);
  };

  useEffect(() => {
    loadAutomations().catch((error: Error) => {
      setFeedback(error.message);
      setFeedbackTone("error");
    });
    loadRuntime().catch(() => undefined);
  }, []);

  useEffect(() => {
    const createButton = document.getElementById("apis-create-button");
    const handleCreate = () => {
      setDraft(emptyDetail());
      setRuns([]);
      setSelectedRun(null);
      setFeedback("");
      setFeedbackTone("");
    };
    createButton?.addEventListener("click", handleCreate);
    return () => createButton?.removeEventListener("click", handleCreate);
  }, []);

  const patchDraft = (patch: Partial<AutomationDetail>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };

  const patchStep = (index: number, nextStep: AutomationStep) => {
    setDraft((current) => ({
      ...current,
      steps: current.steps.map((step, stepIndex) => (stepIndex === index ? nextStep : step))
    }));
  };

  const saveAutomation = async () => {
    const issues = validateDraft(draft);
    if (issues.length > 0) {
      setFeedback(issues.join(" "));
      setFeedbackTone("error");
      return;
    }

    const payload = {
      name: draft.name,
      description: draft.description,
      enabled: draft.enabled,
      trigger_type: draft.trigger_type,
      trigger_config: draft.trigger_config,
      steps: draft.steps
    };

    const response = draft.id
      ? await requestJson(`/api/v1/automations/${draft.id}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await requestJson("/api/v1/automations", { method: "POST", body: JSON.stringify(payload) });

    setFeedback(draft.id ? "Automation updated." : "Automation created.");
    setFeedbackTone("success");
    await loadAutomations(response.id);
    await loadRuntime();
  };

  const executeAutomation = async () => {
    if (!draft.id) {
      setFeedback("Save the automation before running it.");
      setFeedbackTone("error");
      return;
    }
    const run = (await requestJson(`/api/v1/automations/${draft.id}/execute`, { method: "POST" })) as AutomationRunDetail;
    setSelectedRun(run);
    setFeedback("Automation executed.");
    setFeedbackTone("success");
    await selectAutomation(draft.id);
    await loadRuntime();
  };

  const validateAutomation = async () => {
    const issues = validateDraft(draft);
    if (!draft.id) {
      setFeedback(issues.length > 0 ? issues.join(" ") : "Draft is valid.");
      setFeedbackTone(issues.length > 0 ? "error" : "success");
      return;
    }
    const response = await requestJson(`/api/v1/automations/${draft.id}/validate`, { method: "POST" });
    setFeedback(response.valid ? "Automation definition is valid." : response.issues.join(" "));
    setFeedbackTone(response.valid ? "success" : "error");
  };

  const deleteAutomation = async () => {
    if (!draft.id) {
      return;
    }
    await requestJson(`/api/v1/automations/${draft.id}`, { method: "DELETE" });
    setFeedback("Automation deleted.");
    setFeedbackTone("success");
    await loadAutomations();
    await loadRuntime();
  };

  const addStep = (stepType: StepType) => {
    setDraft((current) => ({
      ...current,
      steps: [...current.steps, { ...stepTemplates[stepType], config: { ...stepTemplates[stepType].config } }]
    }));
  };

  return (
    <div id="automation-app-shell" className="stacked-card-layout">
      <section id="automation-workspace-summary-card" className="card">
        <div id="automation-workspace-summary-header" className="section-header">
          <div id="automation-workspace-summary-copy" className="section-header__copy">
            <p id="automation-workspace-summary-eyebrow" className="section-header__eyebrow">Automation Workflows</p>
            <h3 id="automation-workspace-summary-title" className="section-header__title">Current editor state</h3>
            <p id="automation-workspace-summary-description" className="section-header__description">Keep runtime health, saved workflows, and the active draft visible from the same APIs workspace.</p>
          </div>
        </div>
        <div id="automation-workspace-summary-grid" className="summary-grid">
          <article id="automation-workspace-summary-selected-card" className="stat-card summary-card">
            <p id="automation-workspace-summary-selected-label" className="summary-card__label">Selected workflow</p>
            <p id="automation-workspace-summary-selected-value" className="summary-card__value">{draft.name || "New draft"}</p>
          </article>
          <article id="automation-workspace-summary-trigger-card" className="stat-card summary-card">
            <p id="automation-workspace-summary-trigger-label" className="summary-card__label">Trigger</p>
            <p id="automation-workspace-summary-trigger-value" className="summary-card__value">{draft.trigger_type.replace("_", " ")}</p>
          </article>
          <article id="automation-workspace-summary-runs-card" className="stat-card summary-card">
            <p id="automation-workspace-summary-runs-label" className="summary-card__label">Loaded runs</p>
            <p id="automation-workspace-summary-runs-value" className="summary-card__value">{runs.length}</p>
          </article>
        </div>
        <div id="automation-workspace-summary-actions" className="api-form-actions">
          <button
            id="automation-reset-draft-button"
            type="button"
            className="button button--secondary"
            onClick={() => {
              setDraft(emptyDetail());
              setRuns([]);
              setSelectedRun(null);
              setFeedback("");
              setFeedbackTone("");
            }}
          >
            New draft
          </button>
        </div>
        <div id="automation-feedback" className={feedbackTone ? `api-form-feedback api-form-feedback--${feedbackTone}` : "api-form-feedback"}>{feedback}</div>
      </section>

      <section id="automation-runtime-card" className="card">
        <div id="automation-runtime-header" className="section-header">
          <div id="automation-runtime-copy" className="section-header__copy">
            <h3 id="automation-runtime-title" className="section-header__title">Runtime status</h3>
            <p id="automation-runtime-description" className="section-header__description">Scheduler and automation runtime health for this workspace.</p>
          </div>
        </div>
        <div id="automation-runtime-grid" className="summary-grid">
          <article id="automation-runtime-active-card" className="stat-card summary-card">
            <p id="automation-runtime-active-label" className="summary-card__label">Scheduler</p>
            <p id="automation-runtime-active-value" className="summary-card__value">{runtimeStatus?.active ? "active" : "inactive"}</p>
          </article>
          <article id="automation-runtime-jobs-card" className="stat-card summary-card">
            <p id="automation-runtime-jobs-label" className="summary-card__label">Registered jobs</p>
            <p id="automation-runtime-jobs-value" className="summary-card__value">{runtimeStatus?.job_count ?? 0}</p>
          </article>
          <article id="automation-runtime-last-tick-card" className="stat-card summary-card">
            <p id="automation-runtime-last-tick-label" className="summary-card__label">Last tick</p>
            <p id="automation-runtime-last-tick-value" className="summary-card__value">{formatDateTime(runtimeStatus?.last_tick_finished_at)}</p>
          </article>
        </div>
        <div id="automation-jobs-table-shell" className="api-table-shell">
          <table id="automation-jobs-table" className="api-directory-table">
            <thead>
              <tr>
                <th id="automation-jobs-header-name">Name</th>
                <th id="automation-jobs-header-kind">Kind</th>
                <th id="automation-jobs-header-next-run">Next run</th>
              </tr>
            </thead>
            <tbody id="automation-jobs-body">
              {schedulerJobs.map((job, index) => (
                <tr id={`automation-job-row-${index}`} key={`${job.kind}-${job.id}`}>
                  <td id={`automation-job-name-${index}`}>{String(job.name ?? "")}</td>
                  <td id={`automation-job-kind-${index}`}>{String(job.kind ?? "")}</td>
                  <td id={`automation-job-next-run-${index}`}>{formatDateTime(String(job.next_run_at ?? ""))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div id="automation-workspace" className="section-grid">
        <section id="automation-list-card" className="card">
          <div id="automation-list-header" className="section-header">
            <div id="automation-list-copy" className="section-header__copy">
              <h3 id="automation-list-title" className="section-header__title">Saved automations</h3>
              <p id="automation-list-description" className="section-header__description">Select an automation to edit its trigger and step definitions.</p>
            </div>
          </div>
          <div id="automation-list-items" className="resource-list">
            {automations.map((automation) => (
              <button
                key={automation.id}
                id={`automation-list-item-${automation.id}`}
                type="button"
                className={draft.id === automation.id ? "tool-card tool-card--selected" : "tool-card"}
                aria-pressed={draft.id === automation.id}
                onClick={() => {
                  selectAutomation(automation.id).catch((error: Error) => {
                    setFeedback(error.message);
                    setFeedbackTone("error");
                  });
                }}
              >
                <span id={`automation-list-item-name-${automation.id}`} className="tool-card__title">{automation.name}</span>
                <span id={`automation-list-item-description-${automation.id}`} className="tool-card__description">{automation.description || "No description provided."}</span>
              </button>
            ))}
          </div>
        </section>

        <section id="automation-editor-card" className="card">
          <div id="automation-editor-header" className="section-header">
            <div id="automation-editor-copy" className="section-header__copy">
              <h3 id="automation-editor-title" className="section-header__title">{draft.id ? "Automation editor" : "New automation"}</h3>
              <p id="automation-editor-description" className="section-header__description">Edit trigger settings, maintain step order, then validate or execute the workflow.</p>
            </div>
          </div>
          <div id="automation-editor-form" className="api-form-grid">
            <label id="automation-name-field" className="api-form-field api-form-field--full">
              <span id="automation-name-label" className="api-form-label">Name</span>
              <input id="automation-name-input" className="api-form-input" value={draft.name} onChange={(event) => patchDraft({ name: event.target.value })} />
            </label>
            <label id="automation-description-field" className="api-form-field api-form-field--full">
              <span id="automation-description-label" className="api-form-label">Description</span>
              <textarea id="automation-description-input" className="api-form-textarea" rows={3} value={draft.description} onChange={(event) => patchDraft({ description: event.target.value })} />
            </label>
            <label id="automation-enabled-field" className="api-form-field api-form-field--toggle">
              <span id="automation-enabled-label" className="api-form-label">Enabled</span>
              <span id="automation-enabled-control" className="api-inline-toggle">
                <input id="automation-enabled-input" type="checkbox" checked={draft.enabled} onChange={(event) => patchDraft({ enabled: event.target.checked })} />
                <span id="automation-enabled-copy" className="api-inline-toggle__label">{draft.enabled ? "Automation can run" : "Automation paused"}</span>
              </span>
            </label>
            <label id="automation-trigger-type-field" className="api-form-field">
              <span id="automation-trigger-type-label" className="api-form-label">Trigger type</span>
              <select id="automation-trigger-type-input" className="api-form-input" value={draft.trigger_type} onChange={(event) => patchDraft({ trigger_type: event.target.value as TriggerType, trigger_config: {} })}>
                <option value="manual">Manual</option>
                <option value="schedule">Schedule</option>
                <option value="inbound_api">Inbound API</option>
              </select>
            </label>
            {draft.trigger_type === "schedule" ? (
              <label id="automation-schedule-time-field" className="api-form-field">
                <span id="automation-schedule-time-label" className="api-form-label">Daily run time</span>
                <input
                  id="automation-schedule-time-input"
                  className="api-form-input"
                  type="time"
                  value={draft.trigger_config.schedule_time || ""}
                  onChange={(event) => patchDraft({ trigger_config: { ...draft.trigger_config, schedule_time: event.target.value } })}
                />
              </label>
            ) : null}
            {draft.trigger_type === "inbound_api" ? (
              <label id="automation-inbound-api-field" className="api-form-field">
                <span id="automation-inbound-api-label" className="api-form-label">Inbound API id</span>
                <input
                  id="automation-inbound-api-input"
                  className="api-form-input"
                  value={draft.trigger_config.inbound_api_id || ""}
                  onChange={(event) => patchDraft({ trigger_config: { ...draft.trigger_config, inbound_api_id: event.target.value } })}
                />
              </label>
            ) : null}
          </div>

          <div id="automation-steps-section" className="stacked-card-layout">
            <div id="automation-steps-header" className="section-header">
              <div id="automation-steps-copy" className="section-header__copy">
                <h4 id="automation-steps-title" className="section-header__title">Steps</h4>
                <p id="automation-steps-description" className="section-header__description">Use a structured step list for logging, HTTP requests, scripts, tools, and conditions.</p>
              </div>
            </div>
            {draft.steps.map((step, index) => (
              <div id={`automation-step-card-${index}`} className="card" key={step.id || `${step.type}-${index}`}>
                <div id={`automation-step-header-${index}`} className="api-form-grid">
                  <label id={`automation-step-name-field-${index}`} className="api-form-field">
                    <span id={`automation-step-name-label-${index}`} className="api-form-label">Step name</span>
                    <input
                      id={`automation-step-name-input-${index}`}
                      className="api-form-input"
                      value={step.name}
                      onChange={(event) => patchStep(index, { ...step, name: event.target.value })}
                    />
                  </label>
                  <label id={`automation-step-type-field-${index}`} className="api-form-field">
                    <span id={`automation-step-type-label-${index}`} className="api-form-label">Step type</span>
                    <select
                      id={`automation-step-type-input-${index}`}
                      className="api-form-input"
                      value={step.type}
                      onChange={(event) => patchStep(index, { ...stepTemplates[event.target.value as StepType], config: { ...stepTemplates[event.target.value as StepType].config } })}
                    >
                      <option value="log">Log</option>
                      <option value="outbound_request">HTTP request</option>
                      <option value="script">Script</option>
                      <option value="tool">Tool</option>
                      <option value="condition">Condition</option>
                    </select>
                  </label>
                </div>
                {step.type === "log" ? (
                  <label id={`automation-step-message-field-${index}`} className="api-form-field api-form-field--full">
                    <span id={`automation-step-message-label-${index}`} className="api-form-label">Message</span>
                    <input
                      id={`automation-step-message-input-${index}`}
                      className="api-form-input"
                      value={step.config.message || ""}
                      onChange={(event) => patchStep(index, { ...step, config: { ...step.config, message: event.target.value } })}
                    />
                  </label>
                ) : null}
                {step.type === "outbound_request" ? (
                  <div id={`automation-step-http-grid-${index}`} className="api-form-grid">
                    <label id={`automation-step-destination-field-${index}`} className="api-form-field api-form-field--full">
                      <span id={`automation-step-destination-label-${index}`} className="api-form-label">Destination URL</span>
                      <input
                        id={`automation-step-destination-input-${index}`}
                        className="api-form-input"
                        value={step.config.destination_url || ""}
                        onChange={(event) => patchStep(index, { ...step, config: { ...step.config, destination_url: event.target.value } })}
                      />
                    </label>
                    <label id={`automation-step-payload-field-${index}`} className="api-form-field api-form-field--full">
                      <span id={`automation-step-payload-label-${index}`} className="api-form-label">Payload template</span>
                      <textarea
                        id={`automation-step-payload-input-${index}`}
                        className="api-form-textarea"
                        rows={4}
                        value={step.config.payload_template || ""}
                        onChange={(event) => patchStep(index, { ...step, config: { ...step.config, payload_template: event.target.value } })}
                      />
                    </label>
                  </div>
                ) : null}
                {step.type === "script" ? (
                  <label id={`automation-step-script-field-${index}`} className="api-form-field api-form-field--full">
                    <span id={`automation-step-script-label-${index}`} className="api-form-label">Script id</span>
                    <input
                      id={`automation-step-script-input-${index}`}
                      className="api-form-input"
                      value={step.config.script_id || ""}
                      onChange={(event) => patchStep(index, { ...step, config: { ...step.config, script_id: event.target.value } })}
                    />
                  </label>
                ) : null}
                {step.type === "tool" ? (
                  <label id={`automation-step-tool-field-${index}`} className="api-form-field api-form-field--full">
                    <span id={`automation-step-tool-label-${index}`} className="api-form-label">Tool id</span>
                    <input
                      id={`automation-step-tool-input-${index}`}
                      className="api-form-input"
                      value={step.config.tool_id || ""}
                      onChange={(event) => patchStep(index, { ...step, config: { ...step.config, tool_id: event.target.value } })}
                    />
                  </label>
                ) : null}
                {step.type === "condition" ? (
                  <div id={`automation-step-condition-grid-${index}`} className="api-form-grid">
                    <label id={`automation-step-expression-field-${index}`} className="api-form-field api-form-field--full">
                      <span id={`automation-step-expression-label-${index}`} className="api-form-label">Expression</span>
                      <input
                        id={`automation-step-expression-input-${index}`}
                        className="api-form-input"
                        value={step.config.expression || ""}
                        onChange={(event) => patchStep(index, { ...step, config: { ...step.config, expression: event.target.value } })}
                      />
                    </label>
                    <label id={`automation-step-stop-field-${index}`} className="api-form-field api-form-field--toggle">
                      <span id={`automation-step-stop-label-${index}`} className="api-form-label">Stop on false</span>
                      <span id={`automation-step-stop-control-${index}`} className="api-inline-toggle">
                        <input
                          id={`automation-step-stop-input-${index}`}
                          type="checkbox"
                          checked={Boolean(step.config.stop_on_false)}
                          onChange={(event) => patchStep(index, { ...step, config: { ...step.config, stop_on_false: event.target.checked } })}
                        />
                        <span id={`automation-step-stop-copy-${index}`} className="api-inline-toggle__label">Stop the workflow when the expression is false</span>
                      </span>
                    </label>
                  </div>
                ) : null}
              </div>
            ))}
            <div id="automation-step-add-actions" className="api-form-actions">
              <button id="automation-add-log-step" type="button" className="button button--secondary" onClick={() => addStep("log")}>Add log</button>
              <button id="automation-add-http-step" type="button" className="button button--secondary" onClick={() => addStep("outbound_request")}>Add HTTP</button>
              <button id="automation-add-script-step" type="button" className="button button--secondary" onClick={() => addStep("script")}>Add script</button>
              <button id="automation-add-tool-step" type="button" className="button button--secondary" onClick={() => addStep("tool")}>Add tool</button>
              <button id="automation-add-condition-step" type="button" className="button button--secondary" onClick={() => addStep("condition")}>Add condition</button>
            </div>
            <div id="automation-editor-actions" className="api-form-actions">
              <button id="automation-save-button" type="button" className="primary-action-button" onClick={() => saveAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>Save automation</button>
              <button id="automation-validate-button" type="button" className="button button--secondary" onClick={() => validateAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>Validate</button>
              <button id="automation-execute-button" type="button" className="button button--secondary" onClick={() => executeAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>Run now</button>
              <button id="automation-delete-button" type="button" className="button button--secondary" onClick={() => deleteAutomation().catch((error: Error) => { setFeedback(error.message); setFeedbackTone("error"); })}>Delete</button>
            </div>
          </div>
        </section>
      </div>

      <section id="automation-runs-card" className="card">
        <div id="automation-runs-header" className="section-header">
          <div id="automation-runs-copy" className="section-header__copy">
            <h3 id="automation-runs-title" className="section-header__title">Run history</h3>
            <p id="automation-runs-description" className="section-header__description">Open any run to inspect step-by-step request and response summaries.</p>
          </div>
        </div>
        <div id="automation-runs-table-shell" className="api-table-shell">
          <table id="automation-runs-table" className="api-directory-table">
            <thead>
              <tr>
                <th id="automation-runs-header-id">Run</th>
                <th id="automation-runs-header-trigger">Trigger</th>
                <th id="automation-runs-header-status">Status</th>
                <th id="automation-runs-header-started">Started</th>
              </tr>
            </thead>
            <tbody id="automation-runs-body">
              {runs.map((run) => (
                <tr
                  id={`automation-run-row-${run.run_id}`}
                  key={run.run_id}
                  onClick={() => {
                    requestJson(`/api/v1/runs/${run.run_id}`)
                      .then((detail) => setSelectedRun(detail))
                      .catch((error: Error) => {
                        setFeedback(error.message);
                        setFeedbackTone("error");
                      });
                  }}
                >
                  <td id={`automation-run-id-${run.run_id}`}>{run.run_id}</td>
                  <td id={`automation-run-trigger-${run.run_id}`}>{run.trigger_type}</td>
                  <td id={`automation-run-status-${run.run_id}`}>{run.status}</td>
                  <td id={`automation-run-started-${run.run_id}`}>{formatDateTime(run.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectedRun ? (
          <div id="automation-run-detail" className="stacked-card-layout">
            <h4 id="automation-run-detail-title">Run detail</h4>
            {selectedRun.steps.map((step, index) => (
              <article id={`automation-run-step-${step.step_id}`} className="card" key={step.step_id}>
                <p id={`automation-run-step-name-${step.step_id}`} className="summary-card__label">{index + 1}. {step.step_name}</p>
                <p id={`automation-run-step-status-${step.step_id}`}>{step.status}</p>
                <p id={`automation-run-step-request-${step.step_id}`}>{step.request_summary}</p>
                <p id={`automation-run-step-response-${step.step_id}`}>{step.response_summary}</p>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
};
