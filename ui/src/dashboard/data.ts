import type {
  DashboardAlert,
  DashboardDevice,
  DashboardDevicesResponse,
  DashboardHost,
  DashboardLogEntry,
  DashboardLogSettings,
  DashboardLogsResponse,
  DashboardQueueJob,
  DashboardQueueResponse,
  DashboardResourceHistoryEntry,
  DashboardResourceHistoryResponse,
  DashboardResourceMetric,
  DashboardResourceProfileResponse,
  DashboardRunSummary,
  DashboardSummaryResponse
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

type DashboardQueueApiJob = {
  job_id: string;
  run_id: string;
  step_id: string;
  status: DashboardQueueJob["status"];
  worker_id: string | null;
  worker_name: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  trigger_type: string;
  api_id: string;
  event_id: string;
  received_at: string;
};

type DashboardQueueApiResponse = {
  status: DashboardQueueResponse["status"];
  is_paused: boolean;
  status_updated_at: string;
  total_jobs: number;
  pending_jobs: number;
  claimed_jobs: number;
  jobs: DashboardQueueApiJob[];
};

type DashboardResourceMetricApi = {
  component: string;
  operation: string;
  executions: number;
  avg_duration_ms: number;
  max_duration_ms: number;
  min_duration_ms: number;
  total_duration_ms: number;
  memory_peak_mb: number;
  error_count: number;
  error_rate_percent: number;
  last_executed_at: string;
};

type DashboardResourceProfileApiResponse = {
  collected_at: string;
  total_metrics: number;
  metrics: DashboardResourceMetricApi[];
};

type DashboardResourceHistoryApiEntry = {
  snapshot_id: string;
  captured_at: string;
  process_memory_mb: number;
  process_cpu_percent: number;
  queue_pending_jobs: number;
  queue_claimed_jobs: number;
  tracked_operations: number;
  total_error_count: number;
  hottest_operation: string | null;
  hottest_total_duration_ms: number;
  max_memory_peak_mb: number;
};

type DashboardResourceHistoryApiResponse = {
  collected_at: string;
  total_snapshots: number;
  entries: DashboardResourceHistoryApiEntry[];
};

type DashboardLogsApiSettings = {
  max_stored_entries: number;
  max_visible_entries: number;
  max_detail_characters: number;
};

type DashboardLogsApiEntry = {
  id: string;
  timestamp: string;
  level: DashboardLogEntry["level"];
  source: string;
  category: string;
  action: string;
  message: string;
  details: Record<string, unknown>;
  context: Record<string, unknown>;
};

type DashboardLogsApiResponse = {
  settings: DashboardLogsApiSettings;
  entries: DashboardLogsApiEntry[];
};

type DashboardSummaryApiHealth = {
  id: string;
  status: DashboardSummaryResponse["health"]["status"];
  label: string;
  summary: string;
  updated_at: string;
};

type DashboardSummaryApiService = {
  id: string;
  name: string;
  status: DashboardSummaryResponse["services"][number]["status"];
  detail: string;
  last_check_at: string;
};

type DashboardSummaryApiRunCounts = {
  success: number;
  warning: number;
  error: number;
  idle: number;
};

type DashboardSummaryApiRun = {
  id: string;
  automation_name: string;
  trigger_type: DashboardRunSummary["triggerType"];
  status: DashboardRunSummary["status"];
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
};

type DashboardSummaryApiAlert = {
  id: string;
  severity: DashboardAlert["severity"];
  title: string;
  message: string;
  source: string;
  created_at: string;
};

type DashboardSummaryApiRuntimeOverview = {
  scheduler_active: boolean;
  queue_status: DashboardQueueResponse["status"];
  queue_pending_jobs: number;
  queue_claimed_jobs: number;
  queue_updated_at: string;
  scheduler_last_tick_started_at: string | null;
  scheduler_last_tick_finished_at: string | null;
};

type DashboardSummaryApiWorkerHealth = {
  total: number;
  healthy: number;
  offline: number;
};

type DashboardSummaryApiApiPerformance = {
  inbound_total_24h: number;
  inbound_errors_24h: number;
  error_rate_percent_24h: number;
  outgoing_scheduled_enabled: number;
  outgoing_continuous_enabled: number;
};

type DashboardSummaryApiConnectorHealth = {
  total: number;
  connected: number;
  needs_attention: number;
  expired: number;
  revoked: number;
  draft: number;
  pending_oauth: number;
};

type DashboardSummaryApiResponse = {
  health: DashboardSummaryApiHealth;
  services: DashboardSummaryApiService[];
  run_counts: DashboardSummaryApiRunCounts;
  recent_runs: DashboardSummaryApiRun[];
  alerts: DashboardSummaryApiAlert[];
  runtime_overview: DashboardSummaryApiRuntimeOverview;
  worker_health: DashboardSummaryApiWorkerHealth;
  api_performance: DashboardSummaryApiApiPerformance;
  connector_health: DashboardSummaryApiConnectorHealth;
};

const emptyQueueResponse: DashboardQueueResponse = {
  status: "running",
  isPaused: false,
  statusUpdatedAt: new Date().toISOString(),
  totalJobs: 0,
  pendingJobs: 0,
  claimedJobs: 0,
  jobs: []
};

const emptyResourceProfileResponse: DashboardResourceProfileResponse = {
  collectedAt: new Date().toISOString(),
  totalMetrics: 0,
  metrics: []
};

const emptyResourceHistoryResponse: DashboardResourceHistoryResponse = {
  collectedAt: new Date().toISOString(),
  totalSnapshots: 0,
  entries: []
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

const mapApiQueueJob = (job: DashboardQueueApiJob): DashboardQueueJob => ({
  jobId: job.job_id,
  runId: job.run_id,
  stepId: job.step_id,
  status: job.status,
  workerId: job.worker_id,
  workerName: job.worker_name,
  claimedAt: job.claimed_at,
  completedAt: job.completed_at,
  triggerType: job.trigger_type,
  apiId: job.api_id,
  eventId: job.event_id,
  receivedAt: job.received_at
});

const mapApiQueueResponse = (payload: DashboardQueueApiResponse): DashboardQueueResponse => ({
  status: payload.status,
  isPaused: payload.is_paused,
  statusUpdatedAt: payload.status_updated_at,
  totalJobs: payload.total_jobs,
  pendingJobs: payload.pending_jobs,
  claimedJobs: payload.claimed_jobs,
  jobs: payload.jobs.map(mapApiQueueJob)
});

const mapApiResourceMetric = (metric: DashboardResourceMetricApi): DashboardResourceMetric => ({
  component: metric.component,
  operation: metric.operation,
  executions: metric.executions,
  avgDurationMs: metric.avg_duration_ms,
  maxDurationMs: metric.max_duration_ms,
  minDurationMs: metric.min_duration_ms,
  totalDurationMs: metric.total_duration_ms,
  memoryPeakMb: metric.memory_peak_mb,
  errorCount: metric.error_count,
  errorRatePercent: metric.error_rate_percent,
  lastExecutedAt: metric.last_executed_at
});

const mapApiResourceProfileResponse = (
  payload: DashboardResourceProfileApiResponse
): DashboardResourceProfileResponse => ({
  collectedAt: payload.collected_at,
  totalMetrics: payload.total_metrics,
  metrics: Array.isArray(payload.metrics) ? payload.metrics.map(mapApiResourceMetric) : []
});

const mapApiResourceHistoryEntry = (entry: DashboardResourceHistoryApiEntry): DashboardResourceHistoryEntry => ({
  snapshotId: entry.snapshot_id,
  capturedAt: entry.captured_at,
  processMemoryMb: entry.process_memory_mb,
  processCpuPercent: entry.process_cpu_percent,
  queuePendingJobs: entry.queue_pending_jobs,
  queueClaimedJobs: entry.queue_claimed_jobs,
  trackedOperations: entry.tracked_operations,
  totalErrorCount: entry.total_error_count,
  hottestOperation: entry.hottest_operation,
  hottestTotalDurationMs: entry.hottest_total_duration_ms,
  maxMemoryPeakMb: entry.max_memory_peak_mb
});

const mapApiResourceHistoryResponse = (
  payload: DashboardResourceHistoryApiResponse
): DashboardResourceHistoryResponse => ({
  collectedAt: payload.collected_at,
  totalSnapshots: payload.total_snapshots,
  entries: Array.isArray(payload.entries) ? payload.entries.map(mapApiResourceHistoryEntry) : []
});

const mapApiLogsResponse = (payload: DashboardLogsApiResponse): DashboardLogsResponse => ({
  settings: {
    maxStoredEntries: payload.settings.max_stored_entries,
    maxVisibleEntries: payload.settings.max_visible_entries,
    maxDetailCharacters: payload.settings.max_detail_characters
  },
  entries: Array.isArray(payload.entries)
    ? payload.entries.map((entry) => ({
      id: entry.id,
      timestamp: entry.timestamp,
      level: entry.level,
      source: entry.source,
      category: entry.category,
      action: entry.action,
      message: entry.message,
      details: entry.details,
      context: entry.context
    }))
    : []
});

const mapApiSummaryResponse = (payload: DashboardSummaryApiResponse): DashboardSummaryResponse => ({
  health: {
    id: payload.health.id,
    status: payload.health.status,
    label: payload.health.label,
    summary: payload.health.summary,
    updatedAt: payload.health.updated_at
  },
  services: payload.services.map((service) => ({
    id: service.id,
    name: service.name,
    status: service.status,
    detail: service.detail,
    lastCheckAt: service.last_check_at
  })),
  runCounts: {
    success: payload.run_counts.success,
    warning: payload.run_counts.warning,
    error: payload.run_counts.error,
    idle: payload.run_counts.idle
  },
  recentRuns: payload.recent_runs.map((run) => ({
    id: run.id,
    automationName: run.automation_name,
    triggerType: run.trigger_type,
    status: run.status,
    startedAt: run.started_at,
    finishedAt: run.finished_at,
    durationMs: run.duration_ms
  })),
  alerts: payload.alerts.map((alert) => ({
    id: alert.id,
    severity: alert.severity,
    title: alert.title,
    message: alert.message,
    source: alert.source,
    createdAt: alert.created_at
  })),
  runtimeOverview: {
    schedulerActive: payload.runtime_overview.scheduler_active,
    queueStatus: payload.runtime_overview.queue_status,
    queuePendingJobs: payload.runtime_overview.queue_pending_jobs,
    queueClaimedJobs: payload.runtime_overview.queue_claimed_jobs,
    queueUpdatedAt: payload.runtime_overview.queue_updated_at,
    schedulerLastTickStartedAt: payload.runtime_overview.scheduler_last_tick_started_at,
    schedulerLastTickFinishedAt: payload.runtime_overview.scheduler_last_tick_finished_at
  },
  workerHealth: {
    total: payload.worker_health.total,
    healthy: payload.worker_health.healthy,
    offline: payload.worker_health.offline
  },
  apiPerformance: {
    inboundTotal24h: payload.api_performance.inbound_total_24h,
    inboundErrors24h: payload.api_performance.inbound_errors_24h,
    errorRatePercent24h: payload.api_performance.error_rate_percent_24h,
    outgoingScheduledEnabled: payload.api_performance.outgoing_scheduled_enabled,
    outgoingContinuousEnabled: payload.api_performance.outgoing_continuous_enabled
  },
  connectorHealth: {
    total: payload.connector_health.total,
    connected: payload.connector_health.connected,
    needsAttention: payload.connector_health.needs_attention,
    expired: payload.connector_health.expired,
    revoked: payload.connector_health.revoked,
    draft: payload.connector_health.draft,
    pendingOauth: payload.connector_health.pending_oauth
  }
});

export const isSidebarCollapsed = () => sessionStorage.getItem(sidebarStorageKey) === "true";

export const writeSidebarCollapsed = (collapsed: boolean) => {
  sessionStorage.setItem(sidebarStorageKey, String(collapsed));
};

export const dashboardApi = {
  async getSummary(): Promise<DashboardSummaryResponse> {
    const fallbackSummary: DashboardSummaryResponse = {
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
      runtimeOverview: {
        schedulerActive: false,
        queueStatus: "running",
        queuePendingJobs: 0,
        queueClaimedJobs: 0,
        queueUpdatedAt: new Date().toISOString(),
        schedulerLastTickStartedAt: null,
        schedulerLastTickFinishedAt: null
      },
      workerHealth: {
        total: 0,
        healthy: 0,
        offline: 0
      },
      apiPerformance: {
        inboundTotal24h: 0,
        inboundErrors24h: 0,
        errorRatePercent24h: 0,
        outgoingScheduledEnabled: 0,
        outgoingContinuousEnabled: 0
      },
      connectorHealth: {
        total: 0,
        connected: 0,
        needsAttention: 0,
        expired: 0,
        revoked: 0,
        draft: 0,
        pendingOauth: 0
      }
    };

    try {
      const response = await fetch("/api/v1/dashboard/summary");

      if (!response.ok) {
        return fallbackSummary;
      }

      const payload = (await response.json()) as DashboardSummaryApiResponse;
      return mapApiSummaryResponse(payload);
    } catch {
      return fallbackSummary;
    }
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
    try {
      const response = await fetch("/api/v1/dashboard/logs");

      if (!response.ok) {
        return {
          settings: { ...defaultLogSettings },
          entries: [...defaultLogEntries]
        };
      }

      const payload = (await response.json()) as Partial<DashboardLogsApiResponse>;
      if (!payload.settings || !Array.isArray(payload.entries)) {
        return {
          settings: { ...defaultLogSettings },
          entries: [...defaultLogEntries]
        };
      }

      return mapApiLogsResponse(payload as DashboardLogsApiResponse);
    } catch {
      return {
        settings: { ...defaultLogSettings },
        entries: [...defaultLogEntries]
      };
    }
  },

  async getQueue(): Promise<DashboardQueueResponse> {
    try {
      const response = await fetch("/api/v1/dashboard/queue");

      if (!response.ok) {
        return { ...emptyQueueResponse };
      }

      const payload = (await response.json()) as DashboardQueueApiResponse;
      return mapApiQueueResponse(payload);
    } catch {
      return { ...emptyQueueResponse };
    }
  },

  async getResourceProfile(): Promise<DashboardResourceProfileResponse> {
    try {
      const response = await fetch("/api/v1/debug/resource-profile");

      if (!response.ok) {
        return { ...emptyResourceProfileResponse };
      }

      const payload = (await response.json()) as DashboardResourceProfileApiResponse;
      return mapApiResourceProfileResponse(payload);
    } catch {
      return { ...emptyResourceProfileResponse };
    }
  },

  async getResourceHistory(): Promise<DashboardResourceHistoryResponse> {
    try {
      const response = await fetch("/api/v1/dashboard/resource-history");

      if (!response.ok) {
        return { ...emptyResourceHistoryResponse };
      }

      const payload = (await response.json()) as Partial<DashboardResourceHistoryApiResponse>;
      if (!Array.isArray(payload.entries)) {
        return { ...emptyResourceHistoryResponse };
      }

      return mapApiResourceHistoryResponse(payload as DashboardResourceHistoryApiResponse);
    } catch {
      return { ...emptyResourceHistoryResponse };
    }
  },

  async resetResourceProfile(): Promise<void> {
    try {
      await fetch("/api/v1/debug/resource-profile/reset", { method: "POST" });
    } catch {
      // best effort — do not block UI on reset failure
    }
  },

  async pauseQueue(): Promise<DashboardQueueResponse> {
    try {
      const response = await fetch("/api/v1/dashboard/queue/pause", { method: "POST" });
      if (!response.ok) {
        return { ...emptyQueueResponse, status: "paused", isPaused: true };
      }

      const payload = (await response.json()) as DashboardQueueApiResponse;
      return mapApiQueueResponse(payload);
    } catch {
      return { ...emptyQueueResponse, status: "paused", isPaused: true };
    }
  },

  async unpauseQueue(): Promise<DashboardQueueResponse> {
    try {
      const response = await fetch("/api/v1/dashboard/queue/unpause", { method: "POST" });
      if (!response.ok) {
        return { ...emptyQueueResponse };
      }

      const payload = (await response.json()) as DashboardQueueApiResponse;
      return mapApiQueueResponse(payload);
    } catch {
      return { ...emptyQueueResponse };
    }
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
