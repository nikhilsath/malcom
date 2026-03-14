import {
  mockDashboardState,
  mockDevicesResponse,
  mockSummaryResponse
} from "./mock-state";
import type {
  DashboardAlert,
  DashboardDevice,
  DashboardLogEntry,
  DashboardLogSettings,
  DashboardLogsResponse,
  DashboardRunSummary,
  DashboardSummaryResponse,
  DeveloperModeDashboardState,
  MalcomLogStore
} from "./types";

const dashboardMockStorageKey = "malcom.dashboardMockState";
const developerModeStorageKey = "developerMode";
const sidebarStorageKey = "sidebarCollapsed";

const defaultLogSettings: DashboardLogSettings = {
  maxStoredEntries: 250,
  maxVisibleEntries: 50,
  maxDetailCharacters: 4000
};

const defaultLogEntries: DashboardLogEntry[] = [
  {
    id: "log-runtime-bootstrap",
    timestamp: "2026-03-14T09:20:00.000Z",
    level: "info",
    source: "system.bootstrap",
    category: "runtime",
    action: "startup",
    message: "Client-side runtime logging initialized.",
    details: {
      storage: "localStorage",
      filters: ["level", "source", "category", "time", "search"]
    },
    context: {
      environment: "browser"
    }
  },
  {
    id: "log-settings-defaults",
    timestamp: "2026-03-14T09:25:00.000Z",
    level: "info",
    source: "system.settings",
    category: "configuration",
    action: "defaults_loaded",
    message: "Default logging thresholds applied.",
    details: defaultLogSettings,
    context: {
      boot: true
    }
  },
  {
    id: "log-api-retry",
    timestamp: "2026-03-14T09:28:00.000Z",
    level: "warning",
    source: "api.webhooks",
    category: "delivery",
    action: "verification_retry",
    message: "Webhook signature verification retried against the local secret store.",
    details: {
      attempts: 2,
      endpoint: "/webhooks/inbound/weather"
    },
    context: {
      path: "/dashboard/overview"
    }
  }
];

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

const readStoredJson = <T,>(storageKey: string, fallbackValue: T): T => {
  try {
    const rawValue = sessionStorage.getItem(storageKey);

    if (!rawValue) {
      return fallbackValue;
    }

    return JSON.parse(rawValue) as T;
  } catch {
    return fallbackValue;
  }
};

const writeStoredJson = (storageKey: string, value: unknown) => {
  sessionStorage.setItem(storageKey, JSON.stringify(value));
};

const createFallbackLogStore = (): MalcomLogStore => {
  let settings = { ...defaultLogSettings };
  let logs = [...defaultLogEntries];

  return {
    defaults: { ...defaultLogSettings },
    getSettings: () => ({ ...settings }),
    updateSettings(nextSettings) {
      settings = {
        maxStoredEntries: nextSettings.maxStoredEntries ?? settings.maxStoredEntries,
        maxVisibleEntries: nextSettings.maxVisibleEntries ?? settings.maxVisibleEntries,
        maxDetailCharacters: nextSettings.maxDetailCharacters ?? settings.maxDetailCharacters
      };
      return { ...settings };
    },
    resetSettings() {
      settings = { ...defaultLogSettings };
      return { ...settings };
    },
    getLogs: () => [...logs],
    log(entry) {
      const createdEntry: DashboardLogEntry = {
        id: entry.id || `log_${Date.now()}`,
        timestamp: entry.timestamp || new Date().toISOString(),
        level: entry.level || "info",
        source: entry.source || "ui.dashboard",
        category: entry.category || "system",
        action: entry.action || "event",
        message: entry.message || "Dashboard event recorded.",
        details: (entry.details as Record<string, unknown>) || {},
        context: (entry.context as Record<string, unknown>) || {}
      };
      logs = [createdEntry, ...logs];
      return createdEntry;
    },
    clearLogs() {
      logs = [];
    }
  };
};

const getLogStore = (): MalcomLogStore => {
  if (!window.MalcomLogStore) {
    window.MalcomLogStore = createFallbackLogStore();
  }

  return window.MalcomLogStore;
};

export const isDeveloperModeEnabled = () => {
  const storedValue = sessionStorage.getItem(developerModeStorageKey);

  if (storedValue === null) {
    // Default developer mode to off for new sessions.
    sessionStorage.setItem(developerModeStorageKey, "false");
    return false;
  }

  return storedValue === "true";
};

export const writeDeveloperMode = (enabled: boolean) => {
  sessionStorage.setItem(developerModeStorageKey, String(enabled));
};

export const isSidebarCollapsed = () => sessionStorage.getItem(sidebarStorageKey) === "true";

export const writeSidebarCollapsed = (collapsed: boolean) => {
  sessionStorage.setItem(sidebarStorageKey, String(collapsed));
};

export const ensureMockDashboardState = (): DeveloperModeDashboardState => {
  const existingState = readStoredJson<DeveloperModeDashboardState | null>(dashboardMockStorageKey, null);

  if (existingState) {
    return existingState;
  }

  const seededState = clone(mockDashboardState);
  writeStoredJson(dashboardMockStorageKey, seededState);
  return seededState;
};

export const dashboardApi = {
  async getSummary(developerMode: boolean): Promise<DashboardSummaryResponse> {
    if (!developerMode) {
      return {
        health: {
          id: "system-health",
          status: "offline",
          label: "Waiting for data",
          summary: "Enable Developer Mode or connect the backend dashboard endpoints to load operational data.",
          updatedAt: new Date().toISOString()
        },
        services: [],
        runCounts: {
          success: 0,
          warning: 0,
          error: 0,
          idle: 0
        },
        recentRuns: [],
        alerts: [],
        quickLinks: clone(mockSummaryResponse.quickLinks).map((item) => ({
          ...item,
          count: 0
        }))
      };
    }

    return clone(ensureMockDashboardState().summary);
  },

  async getDevices(developerMode: boolean) {
    if (!developerMode) {
      return { host: null, devices: [] };
    }

    return clone(ensureMockDashboardState().devices || mockDevicesResponse);
  },

  async getLogs(developerMode: boolean): Promise<DashboardLogsResponse> {
    const store = getLogStore();
    const settings = store.getSettings();

    if (!developerMode) {
      return {
        settings,
        entries: []
      };
    }

    const entries = store.getLogs();

    if (entries.length === 0) {
      defaultLogEntries
        .slice()
        .reverse()
        .forEach((entry) => {
          store.log(entry);
        });
    }

    return {
      settings: store.getSettings(),
      entries: store.getLogs()
    };
  }
};

export const formatDateTime = (value: string | null) => {
  if (!value) {
    return "Pending";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

export const formatDuration = (value: number | null) => {
  if (value === null) {
    return "In progress";
  }

  if (value < 1000) {
    return `${value}ms`;
  }

  return `${(value / 1000).toFixed(1)}s`;
};

export const stringifyValue = (value: unknown, maxCharacters: number) => {
  const rawValue = JSON.stringify(value ?? {}, null, 2);

  if (rawValue.length <= maxCharacters) {
    return rawValue;
  }

  return `${rawValue.slice(0, maxCharacters)}\n… truncated`;
};

export const getPreviewLogs = (entries: DashboardLogEntry[]) => entries.slice(0, 3);

export const getRunStatusSummary = (runs: DashboardRunSummary[]) => ({
  total: runs.length,
  success: runs.filter((run) => run.status === "success").length,
  warning: runs.filter((run) => run.status === "warning").length,
  error: runs.filter((run) => run.status === "error").length,
  idle: runs.filter((run) => run.status === "idle").length
});

export const getAlertSeveritySummary = (alerts: DashboardAlert[]) => ({
  warning: alerts.filter((alert) => alert.severity === "warning").length,
  error: alerts.filter((alert) => alert.severity === "error").length,
  info: alerts.filter((alert) => alert.severity === "info").length
});

export const getDeviceStatusSummary = (devices: DashboardDevice[]) => ({
  healthy: devices.filter((device) => device.status === "healthy").length,
  degraded: devices.filter((device) => device.status === "degraded").length,
  offline: devices.filter((device) => device.status === "offline").length
});
