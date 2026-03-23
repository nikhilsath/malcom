import type { ReactNode } from "react";
import { CollapsibleSection } from "../lib/collapsible-section";
import type {
  AlertSeverity,
  DashboardAlert,
  DashboardDevice,
  DashboardHost,
  DashboardLogEntry,
  DashboardQuickLink,
  HealthStatus,
  QueueStatus,
  RuntimeServiceStatus,
  RunStatus
} from "./types";
import { formatBytes, formatDateTime, formatDuration, stringifyValue } from "./data";

export { CollapsibleSection };

const badgeToneMap: Record<string, string> = {
  healthy: "status-badge--success",
  success: "status-badge--success",
  degraded: "status-badge--warning",
  warning: "status-badge--warning",
  offline: "status-badge--danger",
  error: "status-badge--danger",
  idle: "status-badge--muted",
  pending: "status-badge--warning",
  claimed: "status-badge--muted",
  info: "status-badge--muted",
  debug: "status-badge--muted"
};

export const StatusBadge = ({
  id,
  value
}: {
  id: string;
  value: HealthStatus | RunStatus | AlertSeverity | DashboardLogEntry["level"] | QueueStatus;
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
      <div className="title-row">
        <h3 id={`${id}-title`} className="section-header__title dashboard-toolbar__title">
          {title}
        </h3>
        <button type="button" id={`${id}-description-badge`} className="info-badge" aria-label="More information" aria-expanded="false" aria-controls={`${id}-description`}>i</button>
      </div>
      <p id={`${id}-description`} className="section-header__description dashboard-toolbar__description" hidden>
        {description}
      </p>
    </div>
    {action}
  </div>
);

export const ServiceStatusStrip = ({ services }: { services: RuntimeServiceStatus[] }) => (
  <CollapsibleSection id="dashboard-overview-services" label="Runtime status" description="Current service health checks.">
    {services.length === 0 ? (
      <EmptyState
        id="dashboard-overview-services-empty"
        title="No service data loaded"
        description="Connect the summary endpoint to load checks."
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
    </CollapsibleSection>
);

export const AlertsPanel = ({ alerts }: { alerts: DashboardAlert[] }) => (
  <CollapsibleSection id="dashboard-overview-alerts" label="Active attention items" description="Items that need operator action.">
    {alerts.length === 0 ? (
      <EmptyState
        id="dashboard-overview-alerts-empty"
        title="No active alerts"
        description="Alerts appear here when warnings or errors are detected."
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
    </CollapsibleSection>
);

export const QuickLinksPanel = ({ quickLinks }: { quickLinks: DashboardQuickLink[] }) => (
  <CollapsibleSection id="dashboard-overview-links" label="Quick links" description="Shortcuts to related pages.">
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
    </CollapsibleSection>
);

export const RecentLogsPreview = ({ entries }: { entries: DashboardLogEntry[] }) => (
    <CollapsibleSection id="dashboard-overview-log-preview" label="Recent log preview">
      <SectionToolbar
      id="dashboard-overview-log-preview-toolbar"
      title="Recent log preview"
      description="Newest retained log entries."
      action={
        <a id="dashboard-overview-log-preview-link" className="button button--secondary secondary-action-button" href="logs.html">
          Open full logs
        </a>
      }
    />
    {entries.length === 0 ? (
      <EmptyState
        id="dashboard-overview-log-preview-empty"
        title="No recent logs loaded"
        description="Connect the backend to load logs."
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
    </CollapsibleSection>
);

export const ReportBuilderPanel = () => (
  <CollapsibleSection id="dashboard-logs-report-builder-card" label="Log report builder">
    <SectionToolbar
      id="dashboard-logs-report-builder-toolbar"
      title="Log report builder"
      description="Build reports from retained runtime logs."
      action={
        <a
          id="dashboard-logs-report-builder-link"
          className="button button--secondary secondary-action-button"
          href="../tools/catalog.html"
        >
          Open tools catalog
        </a>
      }
    />
    <article id="dashboard-logs-report-builder-tool" className="dashboard-report-builder-card">
      <div id="dashboard-logs-report-builder-copy" className="dashboard-report-builder-card__copy">
        <p id="dashboard-logs-report-builder-label" className="summary-card__label">
          Recommended tool
        </p>
        <h3 id="dashboard-logs-report-builder-title" className="dashboard-host-card__title">
          Grafana
        </h3>
        <p id="dashboard-logs-report-builder-description" className="dashboard-host-card__detail">
          Open-source dashboards and reports for log analysis.
        </p>
      </div>
      <dl id="dashboard-logs-report-builder-metadata" className="dashboard-report-builder-card__metadata">
        <div id="dashboard-logs-report-builder-source-group">
          <dt className="summary-card__label">Catalog entry</dt>
          <dd id="dashboard-logs-report-builder-source-value">tools/grafana</dd>
        </div>
        <div id="dashboard-logs-report-builder-focus-group">
          <dt className="summary-card__label">Best fit</dt>
          <dd id="dashboard-logs-report-builder-focus-value">Reports from retained logs</dd>
        </div>
      </dl>
    </article>
  </CollapsibleSection>
);

export const DevicesTable = ({
  host,
  devices
}: {
  host: DashboardHost | null;
  devices: DashboardDevice[];
}) => (
  <div id="dashboard-devices-layout" className="stacked-card-layout">
    <CollapsibleSection id="dashboard-devices-host-card" label="Host machine">
      <SectionToolbar
        id="dashboard-devices-host-toolbar"
        title="Host machine"
        description="Primary runtime host details."
      />
      {!host ? (
        <EmptyState
          id="dashboard-devices-host-empty"
          title="No host inventory loaded"
          description="Connect the devices endpoint to load host data."
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
              <dt className="summary-card__label">Hostname</dt>
              <dd id={`dashboard-device-host-hostname-${host.id}`}>{host.hostname}</dd>
            </div>
            <div>
              <dt className="summary-card__label">OS</dt>
              <dd id={`dashboard-device-host-os-${host.id}`}>{host.operatingSystem}</dd>
            </div>
            <div>
              <dt className="summary-card__label">Architecture</dt>
              <dd id={`dashboard-device-host-architecture-${host.id}`}>{host.architecture}</dd>
            </div>
            <div>
              <dt className="summary-card__label">Sampled</dt>
              <dd id={`dashboard-device-host-sampled-${host.id}`}>{formatDateTime(host.sampledAt)}</dd>
            </div>
          </dl>
          <div id="dashboard-devices-summary-grid" className="summary-grid">
            <article id="dashboard-devices-ram-total-card" className="stat-card summary-card">
              <p id="dashboard-devices-ram-total-card-label" className="summary-card__label">
                Total RAM
              </p>
              <p id="dashboard-devices-ram-total-card-value" className="summary-card__value">
                {formatBytes(host.memoryTotalBytes)}
              </p>
              <p id="dashboard-devices-ram-total-card-detail" className="api-directory-description">
                Available {formatBytes(host.memoryAvailableBytes)}
              </p>
            </article>
            <article id="dashboard-devices-ram-used-card" className="stat-card summary-card">
              <p id="dashboard-devices-ram-used-card-label" className="summary-card__label">
                RAM used
              </p>
              <p id="dashboard-devices-ram-used-card-value" className="summary-card__value">
                {formatBytes(host.memoryUsedBytes)}
              </p>
              <p id="dashboard-devices-ram-used-card-detail" className="api-directory-description">
                {host.memoryUsagePercent.toFixed(1)}% of total RAM
              </p>
            </article>
            <article id="dashboard-devices-storage-total-card" className="stat-card summary-card">
              <p id="dashboard-devices-storage-total-card-label" className="summary-card__label">
                Total storage
              </p>
              <p id="dashboard-devices-storage-total-card-value" className="summary-card__value">
                {formatBytes(host.storageTotalBytes)}
              </p>
              <p id="dashboard-devices-storage-total-card-detail" className="api-directory-description">
                Used {formatBytes(host.storageUsedBytes)}
              </p>
            </article>
            <article id="dashboard-devices-storage-free-card" className="stat-card summary-card">
              <p id="dashboard-devices-storage-free-card-label" className="summary-card__label">
                Storage free
              </p>
              <p id="dashboard-devices-storage-free-card-value" className="summary-card__value">
                {formatBytes(host.storageFreeBytes)}
              </p>
              <p id="dashboard-devices-storage-free-card-detail" className="api-directory-description">
                {host.storageUsagePercent.toFixed(1)}% of disk in use
              </p>
            </article>
          </div>
        </div>
      )}
    </CollapsibleSection>

    <CollapsibleSection id="dashboard-devices-inventory-card" label="Runtime endpoints">
      <SectionToolbar
        id="dashboard-devices-inventory-toolbar"
        title="Runtime endpoints"
        description="Malcom-managed services and attached endpoints, separate from the host machine telemetry above."
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
    </CollapsibleSection>
  </div>
);

export const LogEntryList = ({
  entries,
  selectedEntryId,
  onSelectEntry
}: {
  entries: DashboardLogEntry[];
  selectedEntryId: string | null;
  onSelectEntry: (entryId: string) => void;
}) => (
  <div id="dashboard-logs-list" className="dashboard-log-list">
    {entries.map((entry) => (
      <button
        type="button"
        id={`dashboard-log-item-${entry.id}`}
        key={entry.id}
        className={`dashboard-log-item ${selectedEntryId === entry.id ? "dashboard-log-item--active" : ""}`}
        onClick={() => onSelectEntry(entry.id)}
        aria-pressed={selectedEntryId === entry.id}
      >
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
      </button>
    ))}
  </div>
);

export const LogEntryDetailsPanel = ({
  entry,
  maxDetailCharacters
}: {
  entry: DashboardLogEntry;
  maxDetailCharacters: number;
}) => (
  <article id={`dashboard-log-details-${entry.id}`} className="dashboard-log-details">
    <div id={`dashboard-log-details-header-${entry.id}`} className="dashboard-log-details__header">
      <div id={`dashboard-log-details-title-row-${entry.id}`} className="dashboard-log-details__title-row">
        <h4 id={`dashboard-log-details-title-${entry.id}`} className="dashboard-log-details__title">
          {entry.message}
        </h4>
        <StatusBadge id={`dashboard-log-details-level-${entry.id}`} value={entry.level} />
      </div>
      <p id={`dashboard-log-details-meta-${entry.id}`} className="dashboard-log-details__meta">
        {formatDateTime(entry.timestamp)} • {entry.source} • {entry.action}
      </p>
    </div>
    <dl id={`dashboard-log-details-overview-${entry.id}`} className="dashboard-log-details__overview">
      <div id={`dashboard-log-details-id-group-${entry.id}`}>
        <dt className="summary-card__label">Event id</dt>
        <dd id={`dashboard-log-details-id-value-${entry.id}`}>{entry.id}</dd>
      </div>
      <div id={`dashboard-log-details-category-group-${entry.id}`}>
        <dt className="summary-card__label">Category</dt>
        <dd id={`dashboard-log-details-category-value-${entry.id}`}>{entry.category}</dd>
      </div>
    </dl>
    <div id={`dashboard-log-details-grid-${entry.id}`} className="dashboard-log-details__grid">
      <section id={`dashboard-log-context-panel-${entry.id}`} className="dashboard-log-details__panel">
        <p id={`dashboard-log-context-label-${entry.id}`} className="dashboard-log-details__label">
          Context
        </p>
        <pre id={`dashboard-log-context-value-${entry.id}`} className="api-code-block">
          {stringifyValue(entry.context, maxDetailCharacters)}
        </pre>
      </section>
      <section id={`dashboard-log-details-panel-${entry.id}`} className="dashboard-log-details__panel">
        <p id={`dashboard-log-details-label-${entry.id}`} className="dashboard-log-details__label">
          Details
        </p>
        <pre id={`dashboard-log-details-value-${entry.id}`} className="api-code-block">
          {stringifyValue(entry.details, maxDetailCharacters)}
        </pre>
      </section>
    </div>
  </article>
);

export const LogEntryDetailsModal = ({
  entry,
  maxDetailCharacters,
  onClose
}: {
  entry: DashboardLogEntry;
  maxDetailCharacters: number;
  onClose: () => void;
}) => (
  <>
    <button
      type="button"
      id="dashboard-log-details-modal-backdrop"
      className="dashboard-log-details-modal-backdrop"
      aria-label="Close event details"
      onClick={onClose}
    />
    <div
      id="dashboard-log-details-modal"
      className="dashboard-log-details-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dashboard-log-details-modal-title"
    >
      <div id="dashboard-log-details-modal-header" className="dashboard-log-details-modal__header">
        <h4 id="dashboard-log-details-modal-title" className="dashboard-log-details-modal__title">
          Event details
        </h4>
        <button
          type="button"
          id="dashboard-log-details-modal-close"
          className="modal__close-icon-button dashboard-log-details-modal__close"
          aria-label="Close event details"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <LogEntryDetailsPanel entry={entry} maxDetailCharacters={maxDetailCharacters} />
    </div>
  </>
);
