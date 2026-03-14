import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type {
  AlertSeverity,
  DashboardAlert,
  DashboardDevice,
  DashboardLogEntry,
  DashboardQuickLink,
  DashboardRunSummary,
  HealthStatus,
  RuntimeServiceStatus,
  RunStatus
} from "./types";
import { formatDateTime, formatDuration, stringifyValue } from "./data";

const badgeToneMap: Record<string, string> = {
  healthy: "status-badge--success",
  success: "status-badge--success",
  degraded: "status-badge--warning",
  warning: "status-badge--warning",
  offline: "status-badge--danger",
  error: "status-badge--danger",
  idle: "status-badge--muted",
  info: "status-badge--muted",
  debug: "status-badge--muted"
};

export const StatusBadge = ({
  id,
  value
}: {
  id: string;
  value: HealthStatus | RunStatus | AlertSeverity | DashboardLogEntry["level"];
}) => (
  <span id={id} className={`status-badge ${badgeToneMap[value] || "status-badge--muted"}`}>
    {value}
  </span>
);

export const EmptyState = ({
  id,
  title,
  description
}: {
  id: string;
  title: string;
  description: string;
}) => (
  <div id={id} className="empty-state dashboard-empty-state">
    <h3 id={`${id}-title`} className="dashboard-empty-state__title">
      {title}
    </h3>
    <p id={`${id}-description`} className="dashboard-empty-state__description">
      {description}
    </p>
  </div>
);

export const SummaryCard = ({
  id,
  label,
  value
}: {
  id: string;
  label: string;
  value: string | number;
}) => (
  <article id={id} className="stat-card summary-card">
    <p id={`${id}-label`} className="summary-card__label">
      {label}
    </p>
    <p id={`${id}-value`} className="summary-card__value">
      {value}
    </p>
  </article>
);

export const SectionToolbar = ({
  id,
  title,
  description,
  action
}: {
  id: string;
  title: string;
  description: string;
  action?: ReactNode;
}) => (
  <div id={id} className="section-header dashboard-toolbar">
    <div id={`${id}-copy`} className="section-header__copy dashboard-toolbar__copy">
      <h3 id={`${id}-title`} className="section-header__title dashboard-toolbar__title">
        {title}
      </h3>
      <p id={`${id}-description`} className="section-header__description dashboard-toolbar__description">
        {description}
      </p>
    </div>
    {action}
  </div>
);

export const ServiceStatusStrip = ({ services }: { services: RuntimeServiceStatus[] }) => (
  <section id="dashboard-overview-services" className="card">
    <SectionToolbar
      id="dashboard-overview-services-toolbar"
      title="Runtime status"
      description="Current health checks across the local middleware stack."
    />
    {services.length === 0 ? (
      <EmptyState
        id="dashboard-overview-services-empty"
        title="No service data loaded"
        description="Enable Developer Mode or connect the summary endpoint to populate runtime checks."
      />
    ) : (
      <div id="dashboard-overview-services-grid" className="dashboard-service-grid">
        {services.map((service) => (
          <article id={`dashboard-service-${service.id}`} key={service.id} className="dashboard-service-card">
            <div id={`dashboard-service-header-${service.id}`} className="dashboard-service-card__header">
              <div id={`dashboard-service-copy-${service.id}`} className="dashboard-service-card__copy">
                <h4 id={`dashboard-service-title-${service.id}`} className="dashboard-service-card__title">
                  {service.name}
                </h4>
                <p id={`dashboard-service-detail-${service.id}`} className="dashboard-service-card__detail">
                  {service.detail}
                </p>
              </div>
              <StatusBadge id={`dashboard-service-status-${service.id}`} value={service.status} />
            </div>
            <p id={`dashboard-service-updated-${service.id}`} className="dashboard-service-card__meta">
              Last check {formatDateTime(service.lastCheckAt)}
            </p>
          </article>
        ))}
      </div>
    )}
  </section>
);

export const RecentRunsTable = ({ runs }: { runs: DashboardRunSummary[] }) => (
  <section id="dashboard-overview-runs" className="card">
    <SectionToolbar
      id="dashboard-overview-runs-toolbar"
      title="Recent runs"
      description="Most recent workflow executions across scheduled, manual, and API-triggered work."
    />
    {runs.length === 0 ? (
      <EmptyState
        id="dashboard-overview-runs-empty"
        title="No run history loaded"
        description="The dashboard is ready for backend run history once the execution APIs are connected."
      />
    ) : (
      <div id="dashboard-overview-runs-table-shell" className="api-table-shell">
        <table id="dashboard-overview-runs-table" className="api-directory-table dashboard-table">
          <thead>
            <tr>
              <th id="dashboard-overview-runs-header-automation">Automation</th>
              <th id="dashboard-overview-runs-header-trigger">Trigger</th>
              <th id="dashboard-overview-runs-header-status">Status</th>
              <th id="dashboard-overview-runs-header-duration">Duration</th>
              <th id="dashboard-overview-runs-header-updated">Last updated</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr id={`dashboard-run-row-${run.id}`} key={run.id}>
                <td id={`dashboard-run-name-${run.id}`}>
                  <span className="api-directory-name">{run.automationName}</span>
                </td>
                <td id={`dashboard-run-trigger-${run.id}`}>{run.triggerType}</td>
                <td id={`dashboard-run-status-cell-${run.id}`}>
                  <StatusBadge id={`dashboard-run-status-${run.id}`} value={run.status} />
                </td>
                <td id={`dashboard-run-duration-${run.id}`}>{formatDuration(run.durationMs)}</td>
                <td id={`dashboard-run-updated-${run.id}`}>{formatDateTime(run.finishedAt || run.startedAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </section>
);

export const AlertsPanel = ({ alerts }: { alerts: DashboardAlert[] }) => (
  <section id="dashboard-overview-alerts" className="card">
    <SectionToolbar
      id="dashboard-overview-alerts-toolbar"
      title="Active attention items"
      description="Signals that should direct the next operator action."
    />
    {alerts.length === 0 ? (
      <EmptyState
        id="dashboard-overview-alerts-empty"
        title="No active alerts"
        description="Alert rows will appear here when the dashboard receives runtime warnings or errors."
      />
    ) : (
      <div id="dashboard-overview-alert-list" className="dashboard-alert-list">
        {alerts.map((alert) => (
          <article id={`dashboard-alert-${alert.id}`} key={alert.id} className="dashboard-alert-card">
            <div id={`dashboard-alert-header-${alert.id}`} className="dashboard-alert-card__header">
              <div id={`dashboard-alert-copy-${alert.id}`} className="dashboard-alert-card__copy">
                <h4 id={`dashboard-alert-title-${alert.id}`} className="dashboard-alert-card__title">
                  {alert.title}
                </h4>
                <p id={`dashboard-alert-message-${alert.id}`} className="dashboard-alert-card__message">
                  {alert.message}
                </p>
              </div>
              <StatusBadge id={`dashboard-alert-severity-${alert.id}`} value={alert.severity} />
            </div>
            <p id={`dashboard-alert-meta-${alert.id}`} className="dashboard-alert-card__meta">
              {alert.source} • {formatDateTime(alert.createdAt)}
            </p>
          </article>
        ))}
      </div>
    )}
  </section>
);

export const QuickLinksPanel = ({ quickLinks }: { quickLinks: DashboardQuickLink[] }) => (
  <section id="dashboard-overview-links" className="card">
    <SectionToolbar
      id="dashboard-overview-links-toolbar"
      title="Quick links"
      description="Jump to the next operational surface without losing context."
    />
    <div id="dashboard-overview-links-grid" className="dashboard-quick-links-grid">
      {quickLinks.map((link) => (
        <a
          id={`dashboard-quick-link-${link.id}`}
          key={link.id}
          className="dashboard-quick-link-card"
          href={link.href}
        >
          <span id={`dashboard-quick-link-label-${link.id}`} className="dashboard-quick-link-card__label">
            {link.label}
          </span>
          <span id={`dashboard-quick-link-count-${link.id}`} className="dashboard-quick-link-card__count">
            {link.count}
          </span>
        </a>
      ))}
    </div>
  </section>
);

export const RecentLogsPreview = ({ entries }: { entries: DashboardLogEntry[] }) => (
  <section id="dashboard-overview-log-preview" className="card">
    <SectionToolbar
      id="dashboard-overview-log-preview-toolbar"
      title="Recent log preview"
      description="A compact preview of the newest retained runtime entries."
      action={
        <NavLink id="dashboard-overview-log-preview-link" className="button button--secondary secondary-action-button" to="/logs">
          Open full logs
        </NavLink>
      }
    />
    {entries.length === 0 ? (
      <EmptyState
        id="dashboard-overview-log-preview-empty"
        title="No recent logs loaded"
        description="Developer Mode uses browser-seeded data; backend wiring can replace this preview later."
      />
    ) : (
      <div id="dashboard-overview-log-preview-list" className="dashboard-log-preview-list">
        {entries.map((entry) => (
          <article id={`dashboard-overview-log-preview-item-${entry.id}`} key={entry.id} className="dashboard-log-preview-card">
            <div id={`dashboard-overview-log-preview-header-${entry.id}`} className="dashboard-log-preview-card__header">
              <p id={`dashboard-overview-log-preview-meta-${entry.id}`} className="dashboard-log-preview-card__meta">
                {formatDateTime(entry.timestamp)} • {entry.source}
              </p>
              <StatusBadge id={`dashboard-overview-log-preview-level-${entry.id}`} value={entry.level} />
            </div>
            <p id={`dashboard-overview-log-preview-message-${entry.id}`} className="dashboard-log-preview-card__message">
              {entry.message}
            </p>
          </article>
        ))}
      </div>
    )}
  </section>
);

export const DevicesTable = ({
  host,
  devices
}: {
  host: DashboardDevice | null;
  devices: DashboardDevice[];
}) => (
  <div id="dashboard-devices-layout" className="stacked-card-layout">
    <section id="dashboard-devices-host-card" className="card">
      <SectionToolbar
        id="dashboard-devices-host-toolbar"
        title="Host machine"
        description="Primary runtime host and its immediate operating context."
      />
      {!host ? (
        <EmptyState
          id="dashboard-devices-host-empty"
          title="No host inventory loaded"
          description="This panel will populate once the devices endpoint is connected or Developer Mode is enabled."
        />
      ) : (
        <div id={`dashboard-device-host-${host.id}`} className="dashboard-host-card">
          <div id={`dashboard-device-host-header-${host.id}`} className="dashboard-host-card__header">
            <div id={`dashboard-device-host-copy-${host.id}`}>
              <h3 id={`dashboard-device-host-title-${host.id}`} className="dashboard-host-card__title">
                {host.name}
              </h3>
              <p id={`dashboard-device-host-detail-${host.id}`} className="dashboard-host-card__detail">
                {host.detail}
              </p>
            </div>
            <StatusBadge id={`dashboard-device-host-status-${host.id}`} value={host.status} />
          </div>
          <dl id={`dashboard-device-host-metadata-${host.id}`} className="dashboard-host-card__metadata">
            <div>
              <dt className="summary-card__label">Location</dt>
              <dd id={`dashboard-device-host-location-${host.id}`}>{host.location}</dd>
            </div>
            <div>
              <dt className="summary-card__label">Last seen</dt>
              <dd id={`dashboard-device-host-last-seen-${host.id}`}>{formatDateTime(host.lastSeenAt)}</dd>
            </div>
          </dl>
        </div>
      )}
    </section>

    <section id="dashboard-devices-inventory-card" className="card">
      <SectionToolbar
        id="dashboard-devices-inventory-toolbar"
        title="Runtime endpoints"
        description="Middleware-managed services and attached endpoints, kept separate from the tool catalog."
      />
      {devices.length === 0 ? (
        <EmptyState
          id="dashboard-devices-inventory-empty"
          title="No endpoints loaded"
          description="The dashboard is ready to render runtime inventory once device records become available."
        />
      ) : (
        <div id="dashboard-devices-table-shell" className="api-table-shell">
          <table id="dashboard-devices-table" className="api-directory-table dashboard-table">
            <thead>
              <tr>
                <th id="dashboard-devices-header-name">Name</th>
                <th id="dashboard-devices-header-kind">Kind</th>
                <th id="dashboard-devices-header-status">Status</th>
                <th id="dashboard-devices-header-location">Location</th>
                <th id="dashboard-devices-header-last-seen">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => (
                <tr id={`dashboard-device-row-${device.id}`} key={device.id}>
                  <td id={`dashboard-device-name-${device.id}`}>
                    <span className="api-directory-name">{device.name}</span>
                    <span className="api-directory-description">{device.detail}</span>
                  </td>
                  <td id={`dashboard-device-kind-${device.id}`}>{device.kind}</td>
                  <td id={`dashboard-device-status-cell-${device.id}`}>
                    <StatusBadge id={`dashboard-device-status-${device.id}`} value={device.status} />
                  </td>
                  <td id={`dashboard-device-location-${device.id}`}>{device.location}</td>
                  <td id={`dashboard-device-last-seen-${device.id}`}>{formatDateTime(device.lastSeenAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  </div>
);

export const LogEntryList = ({
  entries,
  maxDetailCharacters
}: {
  entries: DashboardLogEntry[];
  maxDetailCharacters: number;
}) => (
  <div id="dashboard-logs-list" className="dashboard-log-list">
    {entries.map((entry) => (
      <article id={`dashboard-log-item-${entry.id}`} key={entry.id} className="dashboard-log-item">
        <div id={`dashboard-log-header-${entry.id}`} className="dashboard-log-item__header">
          <div id={`dashboard-log-header-copy-${entry.id}`} className="dashboard-log-item__header-copy">
            <p id={`dashboard-log-meta-${entry.id}`} className="dashboard-log-item__meta">
              {formatDateTime(entry.timestamp)} • {entry.source} • {entry.action}
            </p>
            <h4 id={`dashboard-log-title-${entry.id}`} className="dashboard-log-item__title">
              {entry.message}
            </h4>
          </div>
          <div id={`dashboard-log-badges-${entry.id}`} className="dashboard-log-item__badges">
            <StatusBadge id={`dashboard-log-level-${entry.id}`} value={entry.level} />
            <span id={`dashboard-log-category-${entry.id}`} className="status-badge status-badge--muted">
              {entry.category}
            </span>
          </div>
        </div>
        <div id={`dashboard-log-grid-${entry.id}`} className="dashboard-log-item__grid">
          <section id={`dashboard-log-context-panel-${entry.id}`} className="dashboard-log-item__panel">
            <p id={`dashboard-log-context-label-${entry.id}`} className="dashboard-log-item__label">
              Context
            </p>
            <pre id={`dashboard-log-context-value-${entry.id}`} className="api-code-block">
              {stringifyValue(entry.context, maxDetailCharacters)}
            </pre>
          </section>
          <section id={`dashboard-log-details-panel-${entry.id}`} className="dashboard-log-item__panel">
            <p id={`dashboard-log-details-label-${entry.id}`} className="dashboard-log-item__label">
              Details
            </p>
            <pre id={`dashboard-log-details-value-${entry.id}`} className="api-code-block">
              {stringifyValue(entry.details, maxDetailCharacters)}
            </pre>
          </section>
        </div>
      </article>
    ))}
  </div>
);
