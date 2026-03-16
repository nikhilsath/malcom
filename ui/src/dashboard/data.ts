import type {
  DashboardDevice,
  DashboardDevicesResponse,
  DashboardHost,
  DashboardLogEntry,
  DashboardLogSettings,
  DashboardLogsResponse,
  DashboardSummaryResponse,
  MalcomLogStore
} from "./types";

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
      path: "/dashboard/home"
    }
  }
];

type DashboardDevicesApiHost = {
  id: string;
  name: string;
  status: DashboardHost["status"];
  location: string;
  detail: string;
  last_seen_at: string;
  hostname: string;
  operating_system: string;
  architecture: string;
  memory_total_bytes: number;
  memory_used_bytes: number;
  memory_available_bytes: number;
  memory_usage_percent: number;
  storage_total_bytes: number;
  storage_used_bytes: number;
  storage_free_bytes: number;
  storage_usage_percent: number;
  sampled_at: string;
};

type DashboardDevicesApiDevice = {
  id: string;
  name: string;
  kind: DashboardDevice["kind"];
  status: DashboardDevice["status"];
  location: string;
  detail: string;
  last_seen_at: string;
};

type DashboardDevicesApiResponse = {
  host: DashboardDevicesApiHost | null;
  devices: DashboardDevicesApiDevice[];
};

const mapApiHost = (host: DashboardDevicesApiHost): DashboardHost => ({
  id: host.id,
  name: host.name,
  kind: "host",
  status: host.status,
  location: host.location,
  detail: host.detail,
  lastSeenAt: host.last_seen_at,
  hostname: host.hostname,
  operatingSystem: host.operating_system,
  architecture: host.architecture,
  memoryTotalBytes: host.memory_total_bytes,
  memoryUsedBytes: host.memory_used_bytes,
  memoryAvailableBytes: host.memory_available_bytes,
  memoryUsagePercent: host.memory_usage_percent,
  storageTotalBytes: host.storage_total_bytes,
  storageUsedBytes: host.storage_used_bytes,
  storageFreeBytes: host.storage_free_bytes,
  storageUsagePercent: host.storage_usage_percent,
  sampledAt: host.sampled_at
});

const mapApiDevice = (device: DashboardDevicesApiDevice): DashboardDevice => ({
  id: device.id,
  name: device.name,
  kind: device.kind,
  status: device.status,
  location: device.location,
  detail: device.detail,
  lastSeenAt: device.last_seen_at
});

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

export const isSidebarCollapsed = () => sessionStorage.getItem(sidebarStorageKey) === "true";

export const writeSidebarCollapsed = (collapsed: boolean) => {
  sessionStorage.setItem(sidebarStorageKey, String(collapsed));
};

export const dashboardApi = {
  async getSummary(): Promise<DashboardSummaryResponse> {
    return {
      health: {
        id: "system-health",
        status: "offline",
        label: "Waiting for data",
        summary: "Backend dashboard endpoints are not yet connected.",
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
      quickLinks: []
    };
  },

  async getDevices(): Promise<DashboardDevicesResponse> {
    try {
      const response = await fetch("/api/v1/dashboard/devices");

      if (!response.ok) {
        return { host: null, devices: [] };
      }

      const payload = (await response.json()) as DashboardDevicesApiResponse;
      return {
        host: payload.host ? mapApiHost(payload.host) : null,
        devices: payload.devices.map(mapApiDevice)
      };
    } catch {
      return { host: null, devices: [] };
    }
  },

  async getLogs(): Promise<DashboardLogsResponse> {
    const store = getLogStore();
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

export const formatBytes = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let scaledValue = value;
  let unitIndex = 0;

  while (scaledValue >= 1024 && unitIndex < units.length - 1) {
    scaledValue /= 1024;
    unitIndex += 1;
  }

  const digits = scaledValue >= 100 ? 0 : scaledValue >= 10 ? 1 : 2;
  return `${scaledValue.toFixed(digits)} ${units[unitIndex]}`;
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
