import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  Outlet,
  RouterProvider,
  createHashRouter,
  createMemoryRouter,
  useMatches
} from "react-router-dom";
import {
  dashboardApi,
  formatDateTime,
  getAlertSeveritySummary,
  getPreviewLogs,
  getRunStatusSummary,
  isSidebarCollapsed,
  writeSidebarCollapsed
} from "./data";
import { getSectionConfig } from "../../scripts/shell-config.js";
import {
  AlertsPanel,
  CollapsibleSection,
  DevicesTable,
  EmptyState,
  LogEntryDetailsModal,
  LogEntryList,
  RecentLogsPreview,
  ReportBuilderPanel,
  ResourceDashboardPanel,
  SectionToolbar,
  ServiceStatusStrip,
  StatusBadge,
  SummaryCard
} from "./components";
import type {
  DashboardDevicesResponse,
  DashboardLogsResponse,
  DashboardQueueResponse,
  DashboardResourceDashboardResponse,
  DashboardSummaryResponse
} from "./types";

type RouteHandle = {
  title: string;
  description: string;
};

const dashboardSectionConfig = getSectionConfig("dashboard");
const dashboardSectionItems = dashboardSectionConfig?.items || [];
const dashboardHomeItem = dashboardSectionItems.find((item) => item.id === "sidenav-dashboard-home");
const dashboardDevicesItem = dashboardSectionItems.find((item) => item.id === "sidenav-dashboard-devices");
const dashboardLogsItem = dashboardSectionItems.find((item) => item.id === "sidenav-dashboard-logs");
const dashboardQueueItem = dashboardSectionItems.find((item) => item.id === "sidenav-dashboard-queue");

const DashboardUiContext = createContext({});

const useDashboardUi = () => useContext(DashboardUiContext);

const useRouteHandle = () => {
  const matches = useMatches();
  const currentMatch = [...matches].reverse().find((match) => match.handle) as { handle?: RouteHandle } | undefined;
  return currentMatch?.handle;
};

const useSummaryData = () => {
  const [state, setState] = useState<DashboardSummaryResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    let intervalId: number | null = null;

    const loadSummary = () => {
      dashboardApi.getSummary().then((response) => {
        if (isActive) {
          setState(response);
        }
      });
    };

    setState(null);
    loadSummary();
    intervalId = window.setInterval(loadSummary, 10_000);

    return () => {
      isActive = false;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, []);

  return state;
};

const useDevicesData = () => {
  const [state, setState] = useState<DashboardDevicesResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    setState(null);

    dashboardApi.getDevices().then((response) => {
      if (isActive) {
        setState(response);
      }
    });

    return () => {
      isActive = false;
    };
  }, []);

  return state;
};

const useLogsData = () => {
  const [state, setState] = useState<DashboardLogsResponse | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadLogs = () => {
      setState(null);

      dashboardApi.getLogs().then((response) => {
        if (isActive) {
          setState(response);
        }
      });
    };

    loadLogs();
    window.addEventListener("malcom:logs-updated", loadLogs);
    window.addEventListener("malcom:log-settings-updated", loadLogs);

    return () => {
      isActive = false;
      window.removeEventListener("malcom:logs-updated", loadLogs);
      window.removeEventListener("malcom:log-settings-updated", loadLogs);
    };
  }, []);

  return state;
};

const useQueueData = () => {
  const [state, setState] = useState<DashboardQueueResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    setState(null);

    dashboardApi.getQueue().then((response) => {
      if (isActive) {
        setState(response);
      }
    });

    return () => {
      isActive = false;
    };
  }, []);

  return state;
};

const useResourceDashboardData = () => {
  const [state, setState] = useState<DashboardResourceDashboardResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    let intervalId: number | null = null;

    const loadResourceDashboard = () => {
      dashboardApi.getResourceDashboard().then((response) => {
        if (isActive) {
          setState(response);
        }
      });
    };

    loadResourceDashboard();
    intervalId = window.setInterval(loadResourceDashboard, 10_000);

    return () => {
      isActive = false;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, []);

  return state;
};

const DashboardLayout = () => {
  const routeHandle = useRouteHandle();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(isSidebarCollapsed);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", sidebarCollapsed);

    return () => {
      document.body.classList.remove("sidebar-collapsed");
    };
  }, [sidebarCollapsed]);

  const handleSidebarToggle = useCallback(() => {
    const nextValue = !sidebarCollapsed;
    writeSidebarCollapsed(nextValue);
    setSidebarCollapsed(nextValue);
  }, [sidebarCollapsed]);

  useEffect(() => {
    const toggleButton = document.getElementById("sidebar-collapse-toggle");
    if (toggleButton) {
      toggleButton.addEventListener("click", handleSidebarToggle);
      return () => {
        toggleButton.removeEventListener("click", handleSidebarToggle);
      };
    }
  }, [handleSidebarToggle]);

  useEffect(() => {
    document.title = `Malcom - ${routeHandle?.title || "Dashboard"}`;
  }, [routeHandle]);

  return (
    <DashboardUiContext.Provider value={{}}>
      <main className="main" id="main-layout">
        <div className="content-shell">
          <div className="page-header section-header--page" id="dashboard-page-header">
            <div className="page-header__inner">
              <div className="page-header__content">
                <div className="title-row">
                  <h2 className="page-title section-header__title--page" id="dashboard-page-title">
                    {routeHandle?.title || "Dashboard"}
                  </h2>
                  <button type="button" id="dashboard-page-info-badge" className="info-badge" aria-label="Page information" aria-expanded="false" aria-controls="dashboard-page-description">i</button>
                </div>
                <p className="page-description section-header__description--page" id="dashboard-page-description" hidden>
                  {routeHandle?.description || "Operational dashboard"}
                </p>
              </div>
            </div>
          </div>
          <Outlet />
        </div>
      </main>
    </DashboardUiContext.Provider>
  );
};

const HomePage = () => {
  useDashboardUi();
  const summary = useSummaryData();
  const logs = useLogsData();
  const queue = useQueueData();
  const resourceDashboard = useResourceDashboardData();

  if (!summary || !logs || !queue || !resourceDashboard) {
    return null;
  }

  const runSummary = getRunStatusSummary(summary.recentRuns);
  const alertSummary = getAlertSeveritySummary(summary.alerts);

  return (
    <div id="dashboard-overview-layout" className="stacked-card-layout">
      <ResourceDashboardPanel resourceDashboard={resourceDashboard} />

      <CollapsibleSection id="dashboard-overview-health-card" label="Overall health">
        <div id="dashboard-overview-health-header" className="dashboard-health-strip">
          <div id="dashboard-overview-health-copy" className="dashboard-health-strip__copy">
            <p id="dashboard-overview-health-label" className="summary-card__label">
              Overall health
            </p>
            <h3 id="dashboard-overview-health-title" className="dashboard-health-strip__title">
              {summary.health.label}
            </h3>
            <p id="dashboard-overview-health-description" className="dashboard-health-strip__description">
              {summary.health.summary}
            </p>
          </div>
          <div id="dashboard-overview-health-meta" className="dashboard-health-strip__meta">
            <p id="dashboard-overview-health-updated" className="dashboard-health-strip__updated">
              Updated {formatDateTime(summary.health.updatedAt)}
            </p>
          </div>
        </div>
        <div id="dashboard-overview-summary-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-summary-total-runs" label="Recent runs" value={runSummary.total} />
          <SummaryCard id="dashboard-overview-summary-errors" label="Run errors" value={summary.runCounts.error} />
          <SummaryCard id="dashboard-overview-summary-warnings" label="Alerts" value={alertSummary.warning + alertSummary.error} />
          <SummaryCard id="dashboard-overview-summary-queue-status" label="Queue status" value={queue.isPaused ? "Paused" : "Running"} />
          <SummaryCard id="dashboard-overview-summary-queue-pending" label="Queue pending" value={queue.pendingJobs} />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-overview-runtime-performance" label="Runtime and queue performance">
        <div id="dashboard-overview-runtime-performance-grid" className="summary-grid">
          <SummaryCard
            id="dashboard-overview-runtime-scheduler-status"
            label="Scheduler"
            value={summary.runtimeOverview.schedulerActive ? "Active" : "Offline"}
          />
          <SummaryCard
            id="dashboard-overview-runtime-queue-status"
            label="Queue state"
            value={summary.runtimeOverview.queueStatus === "paused" ? "Paused" : "Running"}
          />
          <SummaryCard
            id="dashboard-overview-runtime-queue-pending"
            label="Queue pending"
            value={summary.runtimeOverview.queuePendingJobs}
          />
          <SummaryCard
            id="dashboard-overview-runtime-queue-claimed"
            label="Queue claimed"
            value={summary.runtimeOverview.queueClaimedJobs}
          />
          <SummaryCard
            id="dashboard-overview-runtime-last-tick"
            label="Last scheduler tick"
            value={formatDateTime(summary.runtimeOverview.schedulerLastTickFinishedAt)}
          />
          <SummaryCard
            id="dashboard-overview-runtime-queue-updated"
            label="Queue updated"
            value={formatDateTime(summary.runtimeOverview.queueUpdatedAt)}
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-overview-run-performance" label="Automation run performance">
        <div id="dashboard-overview-run-performance-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-run-success" label="Run success" value={summary.runCounts.success} />
          <SummaryCard id="dashboard-overview-run-warning" label="Run warning" value={summary.runCounts.warning} />
          <SummaryCard id="dashboard-overview-run-error" label="Run error" value={summary.runCounts.error} />
          <SummaryCard id="dashboard-overview-run-idle" label="Run idle" value={summary.runCounts.idle} />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-overview-worker-performance" label="Worker health">
        <div id="dashboard-overview-worker-performance-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-worker-total" label="Workers total" value={summary.workerHealth.total} />
          <SummaryCard id="dashboard-overview-worker-healthy" label="Workers healthy" value={summary.workerHealth.healthy} />
          <SummaryCard id="dashboard-overview-worker-offline" label="Workers offline" value={summary.workerHealth.offline} />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-overview-api-performance" label="API performance">
        <div id="dashboard-overview-api-performance-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-api-inbound-total" label="Inbound events 24h" value={summary.apiPerformance.inboundTotal24h} />
          <SummaryCard id="dashboard-overview-api-inbound-errors" label="Inbound errors 24h" value={summary.apiPerformance.inboundErrors24h} />
          <SummaryCard
            id="dashboard-overview-api-error-rate"
            label="Inbound error rate"
            value={`${summary.apiPerformance.errorRatePercent24h.toFixed(1)}%`}
          />
          <SummaryCard
            id="dashboard-overview-api-scheduled-enabled"
            label="Scheduled outbound APIs"
            value={summary.apiPerformance.outgoingScheduledEnabled}
          />
          <SummaryCard
            id="dashboard-overview-api-continuous-enabled"
            label="Continuous outbound APIs"
            value={summary.apiPerformance.outgoingContinuousEnabled}
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-overview-connector-performance" label="Connector health">
        <div id="dashboard-overview-connector-performance-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-connectors-total" label="Connectors total" value={summary.connectorHealth.total} />
          <SummaryCard id="dashboard-overview-connectors-connected" label="Connected" value={summary.connectorHealth.connected} />
          <SummaryCard
            id="dashboard-overview-connectors-needs-attention"
            label="Needs attention"
            value={summary.connectorHealth.needsAttention}
          />
          <SummaryCard id="dashboard-overview-connectors-expired" label="Expired" value={summary.connectorHealth.expired} />
          <SummaryCard id="dashboard-overview-connectors-revoked" label="Revoked" value={summary.connectorHealth.revoked} />
          <SummaryCard id="dashboard-overview-connectors-draft" label="Draft" value={summary.connectorHealth.draft} />
          <SummaryCard id="dashboard-overview-connectors-pending" label="Pending OAuth" value={summary.connectorHealth.pendingOauth} />
        </div>
      </CollapsibleSection>

      <ServiceStatusStrip services={summary.services} />
      <AlertsPanel alerts={summary.alerts} />
      <RecentLogsPreview entries={getPreviewLogs(logs.entries)} />
    </div>
  );
};

const DevicesPage = () => {
  useDashboardUi();
  const devicesResponse = useDevicesData();

  if (!devicesResponse) {
    return null;
  }

  return (
    <div id="dashboard-devices-page-layout">
      <DevicesTable host={devicesResponse.host} devices={devicesResponse.devices} />
    </div>
  );
};

const filterLogs = (
  entries: DashboardLogsResponse["entries"],
  filters: {
    query: string;
    level: string;
    source: string;
    category: string;
    timeframe: string;
  }
) => entries.filter((entry) => {
  if (filters.level !== "all" && entry.level !== filters.level) {
    return false;
  }

  if (filters.source !== "all" && entry.source !== filters.source) {
    return false;
  }

  if (filters.category !== "all" && entry.category !== filters.category) {
    return false;
  }

  if (filters.timeframe !== "all") {
    const hoursMap: Record<string, number> = {
      "1h": 1,
      "24h": 24,
      "7d": 24 * 7,
      "30d": 24 * 30
    };
    const hours = hoursMap[filters.timeframe];
    const entryTime = new Date(entry.timestamp).getTime();

    if (Number.isFinite(entryTime) && entryTime < Date.now() - hours * 60 * 60 * 1000) {
      return false;
    }
  }

  if (!filters.query) {
    return true;
  }

  return JSON.stringify(entry).toLowerCase().includes(filters.query);
});

const LogsPage = () => {
  useDashboardUi();
  const logsResponse = useLogsData();
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("all");
  const [source, setSource] = useState("all");
  const [category, setCategory] = useState("all");
  const [timeframe, setTimeframe] = useState("all");
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);

  const visibleEntries = logsResponse
    ? logsResponse.entries.slice(0, logsResponse.settings.maxVisibleEntries)
    : [];
  const filteredEntries = filterLogs(visibleEntries, {
    query: query.trim().toLowerCase(),
    level,
    source,
    category,
    timeframe
  });
  const sources = logsResponse ? [...new Set(logsResponse.entries.map((entry) => entry.source))].sort() : [];
  const categories = logsResponse ? [...new Set(logsResponse.entries.map((entry) => entry.category))].sort() : [];
  const selectedEntry = filteredEntries.find((entry) => entry.id === selectedEntryId) || null;

  useEffect(() => {
    if (selectedEntryId && !filteredEntries.some((entry) => entry.id === selectedEntryId)) {
      setSelectedEntryId(null);
    }
  }, [filteredEntries, selectedEntryId]);

  useEffect(() => {
    if (!selectedEntryId) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedEntryId(null);
      }
    };

    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [selectedEntryId]);

  const handleSelectEntry = (entryId: string) => {
    if (selectedEntryId === entryId) {
      setSelectedEntryId(null);
      return;
    }

    setSelectedEntryId(entryId);
  };

  if (!logsResponse) {
    return null;
  }

  const openDetailsCount = selectedEntry ? 1 : 0;

  return (
    <div id="dashboard-logs-layout" className="stacked-card-layout">
      <CollapsibleSection id="dashboard-logs-summary" label="Logs summary" defaultCollapsed>
        <div id="dashboard-logs-summary-grid" className="summary-grid">
          <SummaryCard id="dashboard-logs-total-card" label="Stored logs" value={logsResponse.entries.length} />
          <SummaryCard id="dashboard-logs-filtered-card" label="Filtered results" value={filteredEntries.length} />
          <SummaryCard
            id="dashboard-logs-latest-card"
            label="Latest event"
            value={logsResponse.entries[0] ? formatDateTime(logsResponse.entries[0].timestamp) : "No logs yet"}
          />
          <SummaryCard
            id="dashboard-logs-retention-card"
            label="Retention"
            value={`${logsResponse.settings.maxStoredEntries} stored / ${logsResponse.settings.maxVisibleEntries} shown`}
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-logs-filters-card" label="Detailed log filters">
        <SectionToolbar
          id="dashboard-logs-toolbar"
          title="Detailed log filters"
          description="Filter by severity, source, category, time window, and free-text matches across message, context, and details."
          action={
            <button
              type="button"
              id="dashboard-logs-reset-button"
              className="button button--secondary secondary-action-button"
              onClick={() => {
                setQuery("");
                setLevel("all");
                setSource("all");
                setCategory("all");
                setTimeframe("all");
                setSelectedEntryId(null);
              }}
            >
              Reset filters
            </button>
          }
        />
        <form id="dashboard-logs-filters" className="dashboard-log-filters">
          <label id="dashboard-logs-search-field" className="api-form-field">
            <span id="dashboard-logs-search-label" className="api-form-label">
              Search
            </span>
            <input
              id="dashboard-logs-search-input"
              className="api-form-input"
              placeholder="Search message, details, or context"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label id="dashboard-logs-level-field" className="api-form-field">
            <span id="dashboard-logs-level-label" className="api-form-label">
              Level
            </span>
            <select id="dashboard-logs-level-select" className="api-form-input" value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="all">All</option>
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </label>
          <label id="dashboard-logs-source-field" className="api-form-field">
            <span id="dashboard-logs-source-label" className="api-form-label">
              Source
            </span>
            <select id="dashboard-logs-source-select" className="api-form-input" value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="all">All</option>
              {sources.map((sourceValue) => (
                <option key={sourceValue} value={sourceValue}>
                  {sourceValue}
                </option>
              ))}
            </select>
          </label>
          <label id="dashboard-logs-category-field" className="api-form-field">
            <span id="dashboard-logs-category-label" className="api-form-label">
              Category
            </span>
            <select
              id="dashboard-logs-category-select"
              className="api-form-input"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="all">All</option>
              {categories.map((categoryValue) => (
                <option key={categoryValue} value={categoryValue}>
                  {categoryValue}
                </option>
              ))}
            </select>
          </label>
          <label id="dashboard-logs-time-field" className="api-form-field">
            <span id="dashboard-logs-time-label" className="api-form-label">
              Time window
            </span>
            <select id="dashboard-logs-time-select" className="api-form-input" value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
              <option value="all">All time</option>
              <option value="1h">Last hour</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </select>
          </label>
        </form>
      </CollapsibleSection>

      <ReportBuilderPanel />

      <CollapsibleSection id="dashboard-logs-results-card" label="Runtime event explorer">
        <SectionToolbar
          id="dashboard-logs-results-toolbar"
          title="Runtime event explorer"
          description="Click an event to open a full detail popup with context and metadata."
          action={
            <p id="dashboard-logs-results-count" className="dashboard-toolbar__description">
              {filteredEntries.length} matching logs • {openDetailsCount} detail popup open
            </p>
          }
        />
        {filteredEntries.length === 0 ? (
          <EmptyState
            id="dashboard-logs-empty"
            title="No logs match the current filters"
            description="Adjust the filters or generate new activity from the dashboard, APIs, tools, or settings pages."
          />
        ) : (
          <LogEntryList entries={filteredEntries} selectedEntryId={selectedEntryId} onSelectEntry={handleSelectEntry} />
        )}
      </CollapsibleSection>

      {selectedEntry ? (
        <LogEntryDetailsModal
          entry={selectedEntry}
          maxDetailCharacters={logsResponse.settings.maxDetailCharacters}
          onClose={() => setSelectedEntryId(null)}
        />
      ) : null}
    </div>
  );
};

const QueuePage = () => {
  useDashboardUi();
  const queueData = useQueueData();
  const [queueResponse, setQueueResponse] = useState<DashboardQueueResponse | null>(null);

  useEffect(() => {
    setQueueResponse(queueData);
  }, [queueData]);

  if (!queueResponse) {
    return null;
  }

  const queueStatusLabel = queueResponse.isPaused ? "Paused" : "Running";

  return (
    <div id="dashboard-queue-layout" className="stacked-card-layout">
      <CollapsibleSection id="dashboard-queue-summary-card" label="Queue summary" defaultCollapsed>
        <div id="dashboard-queue-summary-grid" className="summary-grid">
          <SummaryCard id="dashboard-queue-status-card" label="Queue status" value={queueStatusLabel} />
          <SummaryCard id="dashboard-queue-total-card" label="Queue jobs" value={queueResponse.totalJobs} />
          <SummaryCard id="dashboard-queue-pending-card" label="Pending" value={queueResponse.pendingJobs} />
          <SummaryCard id="dashboard-queue-claimed-card" label="Claimed" value={queueResponse.claimedJobs} />
        </div>
      </CollapsibleSection>

      <CollapsibleSection id="dashboard-queue-jobs-card" label="Runtime trigger jobs">
        <SectionToolbar
          id="dashboard-queue-jobs-toolbar"
          title="Runtime trigger jobs"
          description="Pending and claimed trigger jobs currently waiting in the runtime worker queue."
          action={
            <div id="dashboard-queue-controls" className="dashboard-queue-controls">
              <p id="dashboard-queue-jobs-count" className="dashboard-toolbar__description">
                {queueResponse.jobs.length} active jobs • {queueStatusLabel}
              </p>
              <button
                type="button"
                id="dashboard-queue-toggle-button"
                className="button button--secondary secondary-action-button"
                onClick={async () => {
                  const nextState = queueResponse.isPaused ? await dashboardApi.unpauseQueue() : await dashboardApi.pauseQueue();
                  setQueueResponse(nextState);
                }}
              >
                {queueResponse.isPaused ? "Unpause queue" : "Pause queue"}
              </button>
            </div>
          }
        />
        {queueResponse.jobs.length === 0 ? (
          <EmptyState
            id="dashboard-queue-empty"
            title="Queue is empty"
            description="New runtime trigger jobs will appear here when automations enqueue work."
          />
        ) : (
          <div id="dashboard-queue-table-shell" className="api-table-shell">
            <table id="dashboard-queue-table" className="api-directory-table dashboard-table">
              <thead>
                <tr>
                  <th id="dashboard-queue-header-job">Job</th>
                  <th id="dashboard-queue-header-status">Status</th>
                  <th id="dashboard-queue-header-trigger">Trigger</th>
                  <th id="dashboard-queue-header-api">API</th>
                  <th id="dashboard-queue-header-worker">Worker</th>
                  <th id="dashboard-queue-header-received">Received</th>
                </tr>
              </thead>
              <tbody>
                {queueResponse.jobs.map((job) => (
                  <tr id={`dashboard-queue-row-${job.jobId}`} key={job.jobId}>
                    <td id={`dashboard-queue-job-${job.jobId}`}>
                      <span className="api-directory-name">{job.jobId}</span>
                    </td>
                    <td id={`dashboard-queue-status-cell-${job.jobId}`}>
                      <StatusBadge id={`dashboard-queue-status-${job.jobId}`} value={job.status} />
                    </td>
                    <td id={`dashboard-queue-trigger-${job.jobId}`}>{job.triggerType}</td>
                    <td id={`dashboard-queue-api-${job.jobId}`}>{job.apiId}</td>
                    <td id={`dashboard-queue-worker-${job.jobId}`}>{job.workerName || job.workerId || "Unclaimed"}</td>
                    <td id={`dashboard-queue-received-${job.jobId}`}>{formatDateTime(job.receivedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsibleSection>
    </div>
  );
};

const routeDefinitions = [
  {
    path: "/",
    element: <DashboardLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
        handle: {
          title: dashboardHomeItem?.pageTitle || "Dashboard Home",
          description: dashboardHomeItem?.description || "View workspace status at a glance."
        } satisfies RouteHandle
      },
      {
        path: "home",
        element: <HomePage />,
        handle: {
          title: dashboardHomeItem?.pageTitle || "Dashboard Home",
          description: dashboardHomeItem?.description || "View workspace status at a glance."
        } satisfies RouteHandle
      },
      {
        path: "overview",
        element: <HomePage />,
        handle: {
          title: dashboardHomeItem?.pageTitle || "Dashboard Home",
          description: dashboardHomeItem?.description || "Monitor the middleware at a glance and review the current workspace state."
        } satisfies RouteHandle
      },
      {
        path: "devices",
        element: <DevicesPage />,
        handle: {
          title: dashboardDevicesItem?.pageTitle || "Dashboard Devices",
          description: dashboardDevicesItem?.description || "View connected devices and runtime endpoints."
        } satisfies RouteHandle
      },
      {
        path: "logs",
        element: <LogsPage />,
        handle: {
          title: dashboardLogsItem?.pageTitle || "Dashboard Logs",
          description: dashboardLogsItem?.description || "Review recent runtime logs and events."
        } satisfies RouteHandle
      },
      {
        path: "queue",
        element: <QueuePage />,
        handle: {
          title: dashboardQueueItem?.pageTitle || "Dashboard Queue",
          description: dashboardQueueItem?.description || "Track pending and claimed queue jobs."
        } satisfies RouteHandle
      }
    ]
  }
];

export const createDashboardRouter = (initialEntries?: string[]) => {
  return createMemoryRouter(routeDefinitions, {
    initialEntries: initialEntries?.length ? initialEntries : ["/home"],
    future: {
      v7_startTransition: true
    }
  });
};

export const createDashboardHashRouter = () => createHashRouter(routeDefinitions, {
  future: {
    v7_startTransition: true
  }
});

export const DashboardApp = ({ initialEntries }: { initialEntries?: string[] }) => (
  <RouterProvider router={createDashboardRouter(initialEntries)} />
);
