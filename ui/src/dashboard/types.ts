export type HealthStatus = "healthy" | "degraded" | "offline";
export type RunStatus = "success" | "warning" | "error" | "idle";
export type AlertSeverity = "info" | "warning" | "error";
export type DeviceKind = "host" | "service" | "endpoint";
export type TriggerType = "schedule" | "manual" | "api";
export type LogLevel = "debug" | "info" | "warning" | "error";
export type QueueStatus = "pending" | "claimed";
export type QueueRuntimeStatus = "running" | "paused";

export interface SystemHealthSummary {
  id: string;
  status: HealthStatus;
  label: string;
  summary: string;
  updatedAt: string;
}

export interface RuntimeServiceStatus {
  id: string;
  name: string;
  status: HealthStatus;
  detail: string;
  lastCheckAt: string;
}

export interface DashboardRunSummary {
  id: string;
  automationName: string;
  triggerType: TriggerType;
  status: RunStatus;
  startedAt: string;
  finishedAt: string | null;
  durationMs: number | null;
}

export interface DashboardAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  source: string;
  createdAt: string;
}

export interface DashboardQuickLink {
  id: string;
  label: string;
  href: string;
  count: number;
}

export interface DashboardDevice {
  id: string;
  name: string;
  kind: DeviceKind;
  status: HealthStatus;
  location: string;
  detail: string;
  lastSeenAt: string;
}

export interface DashboardHost extends DashboardDevice {
  hostname: string;
  operatingSystem: string;
  architecture: string;
  memoryTotalBytes: number;
  memoryUsedBytes: number;
  memoryAvailableBytes: number;
  memoryUsagePercent: number;
  storageTotalBytes: number;
  storageUsedBytes: number;
  storageFreeBytes: number;
  storageUsagePercent: number;
  sampledAt: string;
}

export interface DashboardLogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  source: string;
  category: string;
  action: string;
  message: string;
  details: Record<string, unknown>;
  context: Record<string, unknown>;
}

export interface DashboardLogSettings {
  maxStoredEntries: number;
  maxVisibleEntries: number;
  maxDetailCharacters: number;
}

export interface DashboardSummaryResponse {
  health: SystemHealthSummary;
  services: RuntimeServiceStatus[];
  runCounts: Record<RunStatus, number>;
  recentRuns: DashboardRunSummary[];
  alerts: DashboardAlert[];
  quickLinks: DashboardQuickLink[];
  runtimeOverview: {
    schedulerActive: boolean;
    queueStatus: QueueRuntimeStatus;
    queuePendingJobs: number;
    queueClaimedJobs: number;
    queueUpdatedAt: string;
    schedulerLastTickStartedAt: string | null;
    schedulerLastTickFinishedAt: string | null;
  };
  workerHealth: {
    total: number;
    healthy: number;
    offline: number;
  };
  apiPerformance: {
    inboundTotal24h: number;
    inboundErrors24h: number;
    errorRatePercent24h: number;
    outgoingScheduledEnabled: number;
    outgoingContinuousEnabled: number;
  };
  connectorHealth: {
    total: number;
    connected: number;
    needsAttention: number;
    expired: number;
    revoked: number;
    draft: number;
    pendingOauth: number;
  };
}

export interface DashboardDevicesResponse {
  host: DashboardHost | null;
  devices: DashboardDevice[];
}

export interface DashboardLogsResponse {
  settings: DashboardLogSettings;
  entries: DashboardLogEntry[];
}

export interface DashboardQueueJob {
  jobId: string;
  runId: string;
  stepId: string;
  status: QueueStatus;
  workerId: string | null;
  workerName: string | null;
  claimedAt: string | null;
  completedAt: string | null;
  triggerType: string;
  apiId: string;
  eventId: string;
  receivedAt: string;
}

export interface DashboardQueueResponse {
  status: QueueRuntimeStatus;
  isPaused: boolean;
  statusUpdatedAt: string;
  totalJobs: number;
  pendingJobs: number;
  claimedJobs: number;
  jobs: DashboardQueueJob[];
}

export interface MalcomLogStore {
  defaults: DashboardLogSettings;
  getSettings: () => DashboardLogSettings;
  updateSettings: (settings: Partial<DashboardLogSettings>) => DashboardLogSettings;
  resetSettings: () => DashboardLogSettings;
  getLogs: () => DashboardLogEntry[];
  log: (entry: Partial<DashboardLogEntry>) => DashboardLogEntry;
  clearLogs: () => void;
}

declare global {
  interface Window {
    MalcomLogStore?: MalcomLogStore;
  }
}
