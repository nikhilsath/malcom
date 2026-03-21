import { useDeferredValue, useEffect, useState } from "react";
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

export const AutomationLibraryApp = () => {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const deferredQuery = useDeferredValue(searchQuery);

  const visibleAutomations = automations.filter((automation) => {
    const query = deferredQuery.trim().toLowerCase();
    if (!query) {
      return true;
    }
    return `${automation.name} ${automation.description}`.toLowerCase().includes(query);
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        const [automationList, status] = await Promise.all([
          requestJson("/api/v1/automations"),
          requestJson("/api/v1/runtime/status"),
        ]);
        setAutomations(automationList as Automation[]);
        setRuntimeStatus(status as RuntimeStatus);
      } catch (nextError: unknown) {
        setError(nextError instanceof Error ? nextError.message : "Failed to load automations.");
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
    <div id="automations-library-app" className="automations-overview automations-library-page">
      {error ? (
        <div id="automations-library-error" className="automation-feedback automation-feedback--error">{error}</div>
      ) : null}

      <div id="automations-library-main" className="automations-library-main">
        <section id="automations-library-list-panel" className="automation-panel automations-overview-list-panel">
          <div id="automations-library-list-header" className="automation-panel__header">
            <div id="automations-library-list-copy" className="automation-panel__copy">
              <p id="automations-library-list-eyebrow" className="automation-panel__eyebrow">Library</p>
              <div className="title-row">
                <h3 id="automations-library-list-title" className="automation-panel__title">Saved automations</h3>
                <button type="button" id="automations-library-list-description-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-library-list-description">i</button>
              </div>
              <p id="automations-library-list-description" className="automation-panel__description" hidden>Search and select an automation to open in Builder.</p>
            </div>
            <a id="automations-library-create-link" href="builder.html?new=true" className="primary-action-button">
              Create +
            </a>
          </div>

          <label id="automations-library-search-field" className="automation-field automation-field--full">
            <span id="automations-library-search-label" className="automation-field__label">Search</span>
            <input
              id="automations-library-search-input"
              className="automation-input"
              value={searchQuery}
              placeholder="Find an automation"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>

          {loading ? (
            <div id="automations-library-loading" className="automation-empty-state">Loading automations…</div>
          ) : visibleAutomations.length === 0 ? (
            <div id="automations-library-empty" className="automation-empty-state">
              {automations.length === 0 ? "No automations yet." : "No automations match the current filter."}
            </div>
          ) : (
            <div id="automations-library-list" className="automation-library-list" role="list">
              {visibleAutomations.map((automation) => (
                <button
                  key={automation.id}
                  id={`automations-library-item-${automation.id}`}
                  type="button"
                  role="listitem"
                  className="automation-library-card"
                  onClick={() => setSelectedAutomation(automation)}
                >
                  <span id={`automations-library-item-name-${automation.id}`} className="automation-library-card__title">
                    {automation.name}
                  </span>
                  <span id={`automations-library-item-description-${automation.id}`} className="automation-library-card__description">
                    {automation.description || "No description provided."}
                  </span>
                  <span id={`automations-library-item-meta-${automation.id}`} className="automation-library-card__meta">
                    {triggerLabels[automation.trigger_type] ?? "Unknown"} · {automation.step_count} {automation.step_count === 1 ? "step" : "steps"}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        <aside id="automations-library-runtime-panel" className="automation-panel automations-overview-tools-panel">
          <div id="automations-library-runtime-header" className="automation-panel__header automation-panel__header--compact">
            <div id="automations-library-runtime-copy" className="automation-panel__copy">
              <p id="automations-library-runtime-eyebrow" className="automation-panel__eyebrow">Runtime</p>
              <div className="title-row">
                <h3 id="automations-library-runtime-title" className="automation-panel__title">Scheduler status</h3>
                <button type="button" id="automations-library-runtime-description-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-library-runtime-description">i</button>
              </div>
              <p id="automations-library-runtime-description" className="automation-panel__description" hidden>Current scheduler health and queue size.</p>
            </div>
          </div>
          <div id="automations-library-runtime-stats" className="automation-runtime-stats">
            <article id="automations-library-runtime-active-card" className="automation-runtime-stat">
              <span id="automations-library-runtime-active-label" className="automation-runtime-stat__label">Scheduler</span>
              <span id="automations-library-runtime-active-value" className="automation-runtime-stat__value">{runtimeStatus?.active ? "Active" : "Inactive"}</span>
            </article>
            <article id="automations-library-runtime-jobs-card" className="automation-runtime-stat">
              <span id="automations-library-runtime-jobs-label" className="automation-runtime-stat__label">Jobs</span>
              <span id="automations-library-runtime-jobs-value" className="automation-runtime-stat__value">{runtimeStatus?.job_count ?? 0}</span>
            </article>
          </div>
          {runtimeStatus?.last_error ? (
            <div id="automations-library-runtime-error" className="overview-runtime-error">
              <span id="automations-library-runtime-error-label" className="overview-runtime-error__label">Runtime error</span>
              <span id="automations-library-runtime-error-value" className="overview-runtime-error__value">{runtimeStatus.last_error}</span>
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
          <Dialog.Backdrop id="automations-library-detail-modal-backdrop" className="automation-dialog-backdrop" />
          <Dialog.Popup id="automations-library-detail-modal" className="automation-detail-dialog">
            {selectedAutomation ? (
              <>
                <div id="automations-library-detail-modal-dismiss-row" className="automation-dialog__dismiss-row">
                  <Dialog.Close
                    id="automations-library-detail-modal-close"
                    className="modal__close-icon-button automation-detail-dialog__close-button"
                    aria-label="Close automation details"
                  >
                    ×
                  </Dialog.Close>
                </div>
                <div id="automations-library-detail-modal-header" className="automation-detail-dialog__header">
                  <div id="automations-library-detail-modal-title-row" className="automation-detail-dialog__title-row">
                    <Dialog.Title id="automations-library-detail-modal-title" className="automation-detail-dialog__title">
                      {selectedAutomation.name}
                    </Dialog.Title>
                    <span
                      id="automations-library-detail-modal-badge"
                      className={`overview-automation-badge${selectedAutomation.enabled ? " overview-automation-badge--enabled" : " overview-automation-badge--disabled"}`}
                    >
                      {selectedAutomation.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <Dialog.Description id="automations-library-detail-modal-description" className="automation-dialog__description">
                    {selectedAutomation.description || "No description provided."}
                  </Dialog.Description>
                </div>

                <div id="automations-library-detail-modal-stats" className="automation-detail-dialog__stats">
                  <div id="automations-library-detail-stat-trigger" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Trigger</span>
                    <span className="automation-detail-stat__value">{triggerLabels[selectedAutomation.trigger_type] ?? "Unknown"}</span>
                  </div>
                  <div id="automations-library-detail-stat-steps" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Steps</span>
                    <span className="automation-detail-stat__value">{selectedAutomation.step_count}</span>
                  </div>
                  <div id="automations-library-detail-stat-lastrun" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Last run</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.last_run_at)}</span>
                  </div>
                  <div id="automations-library-detail-stat-nextrun" className="automation-detail-stat">
                    <span className="automation-detail-stat__label">Next run</span>
                    <span className="automation-detail-stat__value">{formatDateTime(selectedAutomation.next_run_at)}</span>
                  </div>
                </div>

                <div id="automations-library-detail-modal-actions" className="automation-dialog__actions">
                  <a
                    id="automations-library-detail-modal-edit-link"
                    href={`builder.html?id=${selectedAutomation.id}`}
                    className="primary-action-button"
                  >
                    Open in Builder
                  </a>
                </div>
              </>
            ) : null}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};
