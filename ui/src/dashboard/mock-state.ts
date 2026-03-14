import type {
  DashboardAlertsResponse,
  DashboardDevice,
  DashboardDevicesResponse,
  DashboardQuickLink,
  DashboardRunsResponse,
  DashboardSummaryResponse,
  DeveloperModeDashboardState,
  RuntimeServiceStatus,
  SystemHealthSummary
} from "./types";

const now = Date.parse("2026-03-14T09:30:00.000Z");

const isoMinutesAgo = (minutes: number) => new Date(now - minutes * 60 * 1000).toISOString();

const health: SystemHealthSummary = {
  id: "system-health",
  status: "healthy",
  label: "Healthy",
  summary: "Runtime, scheduler, API, and storage are responding within expected local thresholds.",
  updatedAt: isoMinutesAgo(3)
};

const services: RuntimeServiceStatus[] = [
  {
    id: "runtime",
    name: "Automation runtime",
    status: "healthy",
    detail: "13 workflows loaded and idle with no queued retries.",
    lastCheckAt: isoMinutesAgo(4)
  },
  {
    id: "scheduler",
    name: "Scheduler",
    status: "healthy",
    detail: "4 scheduled jobs due in the next hour.",
    lastCheckAt: isoMinutesAgo(4)
  },
  {
    id: "api",
    name: "Local API",
    status: "degraded",
    detail: "Webhook verification retries increased for one inbound endpoint.",
    lastCheckAt: isoMinutesAgo(2)
  },
  {
    id: "storage",
    name: "SQLite storage",
    status: "healthy",
    detail: "Database compaction completed successfully overnight.",
    lastCheckAt: isoMinutesAgo(5)
  }
];

const runs: DashboardRunsResponse["runs"] = [
  {
    id: "run-weather-poll",
    automationName: "Weather Poll",
    triggerType: "schedule",
    status: "success",
    startedAt: isoMinutesAgo(12),
    finishedAt: isoMinutesAgo(11),
    durationMs: 8100
  },
  {
    id: "run-disk-health",
    automationName: "Disk Health Watch",
    triggerType: "schedule",
    status: "warning",
    startedAt: isoMinutesAgo(35),
    finishedAt: isoMinutesAgo(34),
    durationMs: 5400
  },
  {
    id: "run-webhook-sync",
    automationName: "Webhook Sync",
    triggerType: "api",
    status: "error",
    startedAt: isoMinutesAgo(49),
    finishedAt: isoMinutesAgo(48),
    durationMs: 2900
  },
  {
    id: "run-tool-inventory",
    automationName: "Tool Inventory Refresh",
    triggerType: "manual",
    status: "idle",
    startedAt: isoMinutesAgo(70),
    finishedAt: null,
    durationMs: null
  }
];

const alerts: DashboardAlertsResponse["alerts"] = [
  {
    id: "alert-api-retry",
    severity: "warning",
    title: "Inbound webhook verification retrying",
    message: "One API subscription is retrying signature verification against the local secret store.",
    source: "api.webhooks",
    createdAt: isoMinutesAgo(8)
  },
  {
    id: "alert-disk-threshold",
    severity: "info",
    title: "Disk usage check drift detected",
    message: "The last storage check completed later than expected after a large media scan.",
    source: "system.storage",
    createdAt: isoMinutesAgo(38)
  }
];

const quickLinks: DashboardQuickLink[] = [
  {
    id: "automations",
    label: "Automations",
    href: "../apis/overview.html",
    count: 13
  },
  {
    id: "runs",
    label: "Runs",
    href: "#/logs",
    count: 4
  },
  {
    id: "tools",
    label: "Tools",
    href: "../tools/overview.html",
    count: 3
  },
  {
    id: "settings",
    label: "Settings",
    href: "../settings/general.html",
    count: 2
  }
];

const devices: DashboardDevice[] = [
  {
    id: "host-malcom-macbook",
    name: "Malcom host",
    kind: "host",
    status: "healthy",
    location: "Local MacBook runtime",
    detail: "Low-power host running launchd-managed scheduler, local API, and automation runtime.",
    lastSeenAt: isoMinutesAgo(1)
  },
  {
    id: "service-runtime-endpoint",
    name: "Runtime command endpoint",
    kind: "service",
    status: "healthy",
    location: "127.0.0.1",
    detail: "Command executor is available for automation step dispatch.",
    lastSeenAt: isoMinutesAgo(2)
  },
  {
    id: "service-api-endpoint",
    name: "FastAPI server",
    kind: "service",
    status: "degraded",
    location: "localhost:8000",
    detail: "Serving local endpoints with one delayed webhook verification.",
    lastSeenAt: isoMinutesAgo(2)
  },
  {
    id: "endpoint-sftp-gateway",
    name: "SFTP gateway",
    kind: "endpoint",
    status: "healthy",
    location: "lan://storage-gateway",
    detail: "Mounted target for file-based automations and backups.",
    lastSeenAt: isoMinutesAgo(18)
  }
];

const runCounts = runs.reduce<Record<(typeof runs)[number]["status"], number>>(
  (counts, run) => {
    counts[run.status] += 1;
    return counts;
  },
  {
    success: 0,
    warning: 0,
    error: 0,
    idle: 0
  }
);

export const mockSummaryResponse: DashboardSummaryResponse = {
  health,
  services,
  runCounts,
  recentRuns: runs,
  alerts,
  quickLinks
};

export const mockRunsResponse: DashboardRunsResponse = {
  runs
};

export const mockAlertsResponse: DashboardAlertsResponse = {
  alerts
};

export const mockDevicesResponse: DashboardDevicesResponse = {
  host: devices[0],
  devices: devices.slice(1)
};

export const mockDashboardState: DeveloperModeDashboardState = {
  summary: mockSummaryResponse,
  runs: mockRunsResponse,
  alerts: mockAlertsResponse,
  devices: mockDevicesResponse
};
