import React, { useEffect, useState } from 'react';
import { Dialog } from "@base-ui/react/dialog";

type TriggerType = "manual" | "schedule" | "inbound_api" | "smtp_email";

type Automation = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: TriggerType;
  step_count: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
};

type RuntimeStatus = {
  active: boolean;
  last_tick_started_at: string | null;
  last_tick_finished_at: string | null;
  last_error: string | null;
  job_count: number;
};

type ToolEntry = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  page_href: string;
};

declare global {
  interface Window {
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<any>;
    };
  }
}

const requestJson = (path: string, options?: RequestInit) => {
  if (!window.Malcom?.requestJson) {
    throw new Error("Malcom request helper is unavailable.");
  }
  return window.Malcom.requestJson(path, options);
};

const triggerLabels: Record<TriggerType, string> = {
  manual: "Manual",
  schedule: "Schedule",
  inbound_api: "Inbound API",
  smtp_email: "SMTP Email",
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

export const AutomationOverviewApp = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [tools, setTools] = useState<ToolEntry[]>([]);
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const enabledCount = automations.filter((a) => a.enabled).length;
  const enabledToolsCount = tools.filter((t) => t.enabled).length;

  useEffect(() => {
    const loadData = async () => {
      try {
        const [automationList, status, toolList] = await Promise.all([
          requestJson("/api/v1/automations"),
          requestJson("/api/v1/runtime/status"),
          requestJson("/api/v1/tools"),
        ]);
        setAutomations(automationList as Automation[]);
        setRuntimeStatus(status as RuntimeStatus);
        setTools(toolList as ToolEntry[]);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load data.");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    const createButton = document.getElementById("automations-create-button");
    const handleCreate = () => {
      window.location.href = "builder.html?new=true";
    };
    createButton?.addEventListener("click", handleCreate);
    return () => createButton?.removeEventListener("click", handleCreate);
  }, []);

  return (
    <div id="automations-overview-app" className="automations-overview">

      <div id="automations-overview-stats" className="automations-overview-stats">
        <article id="overview-stat-enabled" className="overview-stat overview-stat--success">
          <span id="overview-stat-enabled-value" className="overview-stat__value">{enabledCount}/{automations.length}</span>
          <span id="overview-stat-enabled-label" className="overview-stat__label">Automations</span>
        </article>
        <article
          id="overview-stat-runtime"
          className={`overview-stat${runtimeStatus?.active ? " overview-stat--success" : " overview-stat--warning"}`}
        >
          <span id="overview-stat-runtime-value" className="overview-stat__value">
            {runtimeStatus ? (runtimeStatus.active ? "Active" : "Inactive") : "—"}
          </span>
          <span id="overview-stat-runtime-label" className="overview-stat__label">Scheduler</span>
        </article>
        <article id="overview-stat-jobs" className="overview-stat">
          <span id="overview-stat-jobs-value" className="overview-stat__value">{runtimeStatus?.job_count ?? 0}</span>
          <span id="overview-stat-jobs-label" className="overview-stat__label">Scheduled Jobs</span>
        </article>
        <article id="overview-stat-tools" className="overview-stat overview-stat--success">
          <span id="overview-stat-tools-value" className="overview-stat__value">{enabledToolsCount}</span>
          <span id="overview-stat-tools-label" className="overview-stat__label">Tools Ready</span>
        </article>
      </div>

      {error ? (
        <div id="automations-overview-error" className="automation-feedback automation-feedback--error">{error}</div>
      ) : null}

      <div id="automations-overview-main" className="automations-overview-main">

        <section id="automations-overview-list-panel" className="automation-panel automations-overview-list-panel">
          <div id="automations-overview-list-header" className="automation-panel__header">
            <div id="automations-overview-list-copy" className="automation-panel__copy">
              <p id="automations-overview-list-eyebrow" className="automation-panel__eyebrow">Workflows</p>
              <h3 id="automations-overview-list-title" className="automation-panel__title">All automations</h3>
              <p id="automations-overview-list-description" className="automation-panel__description">
                Click any automation to view its details and open it in the builder.
              </p>
            </div>
            <a
              id="automations-overview-create-link"
              href="builder.html?new=true"
              className="primary-action-button"
            >
              Create +
            </a>
          </div>

          {loading ? (
            <div id="automations-overview-loading" className="automation-empty-state">Loading automations…</div>
          ) : automations.length === 0 ? (
            <div id="automations-overview-empty" className="automation-empty-state">
              No automations yet.{" "}
              <a href="builder.html?new=true" className="overview-inline-link">Create your first workflow.</a>
            </div>
          ) : (
            <div id="automations-overview-list" className="automations-overview-list" role="list">
              {automations.map((automation) => (
                <button
                  key={automation.id}
                  id={`overview-automation-${automation.id}`}
                  type="button"
                  role="listitem"
                  className="overview-automation-row"
                  onClick={() => setSelectedAutomation(automation)}
                >
                  <span
                    id={`overview-automation-badge-${automation.id}`}
                    className={`overview-automation-badge${automation.enabled ? " overview-automation-badge--enabled" : " overview-automation-badge--disabled"}`}
                  >
                    {automation.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <span id={`overview-automation-name-${automation.id}`} className="overview-automation-row__name">
                    {automation.name}
                  </span>
                  <span id={`overview-automation-desc-${automation.id}`} className="overview-automation-row__description">
                    {automation.description || "No description."}
                  </span>
                  <span id={`overview-automation-trigger-${automation.id}`} className="overview-automation-row__tag">
                    {triggerLabels[automation.trigger_type] ?? "Unknown"}
                  </span>
                  <span id={`overview-automation-steps-${automation.id}`} className="overview-automation-row__tag">
                    {automation.step_count} {automation.step_count === 1 ? "step" : "steps"}
                  </span>
                  <span id={`overview-automation-lastrun-${automation.id}`} className="overview-automation-row__lastrun">
                    {formatDateTime(automation.last_run_at)}
                  </span>
                  <span id={`overview-automation-chevron-${automation.id}`} className="overview-automation-row__chevron" aria-hidden="true">›</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <aside id="automations-overview-tools-panel" className="automation-panel automations-overview-tools-panel">
          <div id="automations-overview-tools-header" className="automation-panel__header">
            <div id="automations-overview-tools-copy" className="automation-panel__copy">
              <p id="automations-overview-tools-eyebrow" className="automation-panel__eyebrow">Tools</p>
              <h3 id="automations-overview-tools-title" className="automation-panel__title">Tool availability</h3>
              <p id="automations-overview-tools-description" className="automation-panel__description">
                Enabled tools are available as steps in your automations.
              </p>
            </div>
          </div>
          <div id="automations-overview-tools-list" className="automations-overview-tools-list">
            {loading ? (
              <div className="automation-empty-state">Loading tools…</div>
            ) : tools.length === 0 ? (
              <div id="automations-overview-tools-empty" className="automation-empty-state">No tools configured.</div>
            ) : (
              tools.map((tool) => (
                <article key={tool.id} id={`overview-tool-${tool.id}`} className="overview-tool-card">
                  <div id={`overview-tool-info-${tool.id}`} className="overview-tool-card__info">
                    <span id={`overview-tool-name-${tool.id}`} className="overview-tool-card__name">{tool.name}</span>
                    <span id={`overview-tool-desc-${tool.id}`} className="overview-tool-card__description">{tool.description}</span>
                  </div>
                  <span
                    id={`overview-tool-badge-${tool.id}`}
                    className={`overview-automation-badge${tool.enabled ? " overview-automation-badge--enabled" : " overview-automation-badge--disabled"}`}
                  >
                    {tool.enabled ? "Ready" : "Off"}
                  </span>
                </article>
              ))
            )}
          </div>

          {runtimeStatus?.last_error ? (
            <div id="automations-overview-runtime-error" className="overview-runtime-error">
              <span id="automations-overview-runtime-error-label" className="overview-runtime-error__label">Runtime error</span>
              <span id="automations-overview-runtime-error-value" className="overview-runtime-error__value">{runtimeStatus.last_error}</span>
            </div>
          ) : null}
        </aside>

      </div>

      <Dialog.Root
        open={selectedAutomation !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedAutomation(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Backdrop id="automation-detail-modal-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup id="automation-detail-modal" className="automation-detail-dialog">
            {selectedAutomation && (
              <>
                <div id="automation-detail-modal-header" className="automation-detail-dialog__header">
                  <div id="automation-detail-modal-title-row" className="automation-detail-dialog__title-row">
                    <Dialog.Title
                      id="automation-detail-modal-title"
                      className="automation-detail-dialog__title"
                    >
                      {selectedAutomation.name}
                    </Dialog.Title>
                    <span
                      id="automation-detail-modal-badge"
                      className={`overview-automation-badge${selectedAutomation.enabled ? " overview-automation-badge--enabled" : " overview-automation-badge--disabled"}`}
                    >
                      {selectedAutomation.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <Dialog.Description
                    id="automation-detail-modal-description"
                    className="automation-dialog__description"
                  >
                    {selectedAutomation.description || "No description provided."}
                  </Dialog.Description>
                </div>

                <div id="automation-detail-modal-stats" className="automation-detail-dialog__stats">
                  <div id="automation-detail-stat-trigger" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Trigger</span>
                    <span className="automation-detail-stat__value">
                      {triggerLabels[selectedAutomation.trigger_type] ?? "Unknown"}
                    </span>
                  </div>
                  <div id="automation-detail-stat-steps" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Steps</span>
                    <span className="automation-detail-stat__value">{selectedAutomation.step_count}</span>
                  </div>
                  <div id="automation-detail-stat-lastrun" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Last run</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.last_run_at)}</span>
                  </div>
                  <div id="automation-detail-stat-nextrun" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Next run</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.next_run_at)}</span>
                  </div>
                  <div id="automation-detail-stat-created" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Created</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.created_at)}</span>
                  </div>
                  <div id="automation-detail-stat-updated" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Updated</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.updated_at)}</span>
                  </div>
                </div>

                <div id="automation-detail-modal-actions" className="automation-dialog__actions">
                  <a
                    id="automation-detail-modal-edit-link"
                    href={`builder.html?id=${selectedAutomation.id}`}
                    className="primary-action-button"
                  >
                    Open in Builder
                  </a>
                  <Dialog.Close
                    id="automation-detail-modal-close"
                    className="button button--secondary"
                  >
                    Close
                  </Dialog.Close>
                </div>
              </>
            )}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};

