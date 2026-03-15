export type HealthStatus = "healthy" | "degraded" | "offline";
export type RunStatus = "success" | "warning" | "error" | "idle";
export type AlertSeverity = "info" | "warning" | "error";
export type DeviceKind = "host" | "service" | "endpoint";
export type TriggerType = "schedule" | "manual" | "api";
export type LogLevel = "debug" | "info" | "warning" | "error";

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
}

export interface DashboardRunsResponse {
  runs: DashboardRunSummary[];
}

export interface DashboardAlertsResponse {
  alerts: DashboardAlert[];
}

export interface DashboardDevicesResponse {
  host: DashboardHost | null;
  devices: DashboardDevice[];
}

export interface DashboardLogsResponse {
  settings: DashboardLogSettings;
  entries: DashboardLogEntry[];
}

export interface DeveloperModeDashboardState {
  summary: DashboardSummaryResponse;
  runs: DashboardRunsResponse;
  alerts: DashboardAlertsResponse;
  devices: DashboardDevicesResponse;
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
