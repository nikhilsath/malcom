import { createContext, useContext, useEffect, useState } from "react";
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
  isDeveloperModeEnabled,
  isSidebarCollapsed,
  writeSidebarCollapsed
} from "./data";
import { getSectionConfig } from "../../scripts/shell-config.js";
import {
  AlertsPanel,
  DevicesTable,
  EmptyState,
  LogEntryList,
  QuickLinksPanel,
  RecentLogsPreview,
  ReportBuilderPanel,
  SectionToolbar,
  ServiceStatusStrip,
  StatusBadge,
  SummaryCard
} from "./components";
import type {
  DashboardDevicesResponse,
  DashboardLogsResponse,
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

const DashboardUiContext = createContext({
  developerMode: false
});

const useDashboardUi = () => useContext(DashboardUiContext);

const useRouteHandle = () => {
  const matches = useMatches();
  const currentMatch = [...matches].reverse().find((match) => match.handle) as { handle?: RouteHandle } | undefined;
  return currentMatch?.handle;
};

const useSummaryData = (developerMode: boolean) => {
  const [state, setState] = useState<DashboardSummaryResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    setState(null);

    dashboardApi.getSummary(developerMode).then((response) => {
      if (isActive) {
        setState(response);
      }
    });

    return () => {
      isActive = false;
    };
  }, [developerMode]);

  return state;
};

const useDevicesData = (developerMode: boolean) => {
  const [state, setState] = useState<DashboardDevicesResponse | null>(null);

  useEffect(() => {
    let isActive = true;
    setState(null);

    dashboardApi.getDevices(developerMode).then((response) => {
      if (isActive) {
        setState(response);
      }
    });

    return () => {
      isActive = false;
    };
  }, [developerMode]);

  return state;
};

const useLogsData = (developerMode: boolean) => {
  const [state, setState] = useState<DashboardLogsResponse | null>(null);

  useEffect(() => {
    let isActive = true;

    const loadLogs = () => {
      setState(null);

      dashboardApi.getLogs(developerMode).then((response) => {
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
  }, [developerMode]);

  return state;
};

const DashboardLayout = () => {
  const routeHandle = useRouteHandle();
  const [developerMode, setDeveloperMode] = useState(isDeveloperModeEnabled);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(isSidebarCollapsed);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", sidebarCollapsed);

    return () => {
      document.body.classList.remove("sidebar-collapsed");
    };
  }, [sidebarCollapsed]);

  const handleSidebarToggle = () => {
    const nextValue = !sidebarCollapsed;
    writeSidebarCollapsed(nextValue);
    setSidebarCollapsed(nextValue);
  };

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
    const handleDeveloperModeEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{ enabled: boolean }>;
      setDeveloperMode(customEvent?.detail?.enabled ?? isDeveloperModeEnabled());
    };

    window.addEventListener("malcom:developerModeChanged", handleDeveloperModeEvent);
    return () => window.removeEventListener("malcom:developerModeChanged", handleDeveloperModeEvent);
  }, []);

  useEffect(() => {
    document.title = `Malcom - ${routeHandle?.title || "Dashboard"}`;
  }, [routeHandle]);

  return (
    <DashboardUiContext.Provider value={{ developerMode }}>
      <main className="main" id="main-layout">
        <div className="content-shell">
          <div className="page-header section-header--page" id="dashboard-page-header">
            <div className="page-header__inner">
              <div className="page-header__content">
                <h2 className="page-title section-header__title--page" id="page-title">
                  {routeHandle?.title || "Dashboard"}
                </h2>
                <p className="page-description section-header__description--page" id="page-description">
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
  const { developerMode } = useDashboardUi();
  const summary = useSummaryData(developerMode);
  const logs = useLogsData(developerMode);

  if (!summary || !logs) {
    return null;
  }

  const runSummary = getRunStatusSummary(summary.recentRuns);
  const alertSummary = getAlertSeveritySummary(summary.alerts);

  return (
    <div id="dashboard-overview-layout" className="stacked-card-layout">
      <section id="dashboard-overview-health-card" className="card">
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
            <StatusBadge id="dashboard-overview-health-badge" value={summary.health.status} />
            <p id="dashboard-overview-health-updated" className="dashboard-health-strip__updated">
              Updated {formatDateTime(summary.health.updatedAt)}
            </p>
          </div>
        </div>
        <div id="dashboard-overview-summary-grid" className="summary-grid">
          <SummaryCard id="dashboard-overview-summary-total-runs" label="Recent runs" value={runSummary.total} />
          <SummaryCard id="dashboard-overview-summary-errors" label="Run errors" value={runSummary.error} />
          <SummaryCard id="dashboard-overview-summary-warnings" label="Alerts" value={alertSummary.warning + alertSummary.error} />
          <SummaryCard id="dashboard-overview-summary-visible-logs" label="Stored logs" value={logs.entries.length} />
        </div>
      </section>

      <ServiceStatusStrip services={summary.services} />
      <AlertsPanel alerts={summary.alerts} />
      <QuickLinksPanel quickLinks={summary.quickLinks} />
      <RecentLogsPreview entries={getPreviewLogs(logs.entries)} />
    </div>
  );
};

const DevicesPage = () => {
  const { developerMode } = useDashboardUi();
  const devicesResponse = useDevicesData(developerMode);

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
  const { developerMode } = useDashboardUi();
  const logsResponse = useLogsData(developerMode);
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("all");
  const [source, setSource] = useState("all");
  const [category, setCategory] = useState("all");
  const [timeframe, setTimeframe] = useState("all");

  if (!logsResponse) {
    return null;
  }

  const visibleEntries = logsResponse.entries.slice(0, logsResponse.settings.maxVisibleEntries);
  const filteredEntries = filterLogs(visibleEntries, {
    query: query.trim().toLowerCase(),
    level,
    source,
    category,
    timeframe
  });
  const sources = [...new Set(logsResponse.entries.map((entry) => entry.source))].sort();
  const categories = [...new Set(logsResponse.entries.map((entry) => entry.category))].sort();

  return (
    <div id="dashboard-logs-layout" className="stacked-card-layout">
      <section id="dashboard-logs-summary" className="card">
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
      </section>

      <section id="dashboard-logs-filters-card" className="card">
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
      </section>

      <ReportBuilderPanel />

      <section id="dashboard-logs-results-card" className="card">
        <SectionToolbar
          id="dashboard-logs-results-toolbar"
          title="Runtime entries"
          description="The dashboard surfaces the newest retained entries up to the max configured in Settings."
          action={
            <p id="dashboard-logs-results-count" className="dashboard-toolbar__description">
              {filteredEntries.length} matching logs
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
          <LogEntryList entries={filteredEntries} maxDetailCharacters={logsResponse.settings.maxDetailCharacters} />
        )}
      </section>
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
          description: dashboardHomeItem?.description || "Monitor the middleware at a glance and review the current workspace state."
        } satisfies RouteHandle
      },
      {
        path: "home",
        element: <HomePage />,
        handle: {
          title: dashboardHomeItem?.pageTitle || "Dashboard Home",
          description: dashboardHomeItem?.description || "Monitor the middleware at a glance and review the current workspace state."
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
          description: dashboardDevicesItem?.description || "Review connected devices, runtime endpoints, and related middleware assets."
        } satisfies RouteHandle
      },
      {
        path: "logs",
        element: <LogsPage />,
        handle: {
          title: dashboardLogsItem?.pageTitle || "Dashboard Logs",
          description: dashboardLogsItem?.description || "Inspect recent runtime activity, operator events, and system history."
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
