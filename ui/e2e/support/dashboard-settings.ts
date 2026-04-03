import type { Page } from "@playwright/test";
import { buildAppSettingsResponse, buildConnectorSettingsPayload } from "./api-response-builders.ts";

type RouteObject = Record<string, unknown>;

export const fixedNowIso = "2026-03-21T12:00:00.000Z";

export const dashboardLogEntries = [
  {
    id: "log-settings-defaults",
    timestamp: "2026-03-21T11:40:00.000Z",
    level: "info",
    source: "system.settings",
    category: "configuration",
    action: "defaults_loaded",
    message: "Default logging thresholds applied.",
    details: {
      maxStoredEntries: 250
    },
    context: {
      boot: true
    }
  },
  {
    id: "log-api-retry",
    timestamp: "2026-03-21T10:30:00.000Z",
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
  },
  {
    id: "log-ui-navigation",
    timestamp: "2026-03-20T09:30:00.000Z",
    level: "info",
    source: "ui.navigation",
    category: "navigation",
    action: "page_view",
    message: "Visited Malcom - Dashboard Home.",
    details: {
      section: "dashboard"
    },
    context: {
      path: "/dashboard/home.html"
    }
  },
  {
    id: "log-runtime-queue",
    timestamp: "2026-03-20T08:00:00.000Z",
    level: "error",
    source: "runtime.queue",
    category: "runtime",
    action: "queue_status",
    message: "Queue paused after worker maintenance.",
    details: {
      jobs: 1
    },
    context: {
      section: "dashboard"
    }
  }
] satisfies Array<RouteObject>;

export const defaultSettingsResponse = buildAppSettingsResponse({
  notifications: {
    channel: "slack",
    digest: "hourly",
  },
}) satisfies RouteObject;

export const defaultDashboardSummaryResponse = {
  health: {
    id: "system-health",
    status: "healthy",
    label: "Workspace healthy",
    summary: "All tracked surfaces are healthy in the deterministic smoke fixture.",
    updated_at: fixedNowIso
  },
  services: [
    {
      id: "runtime-api",
      name: "Runtime API",
      status: "healthy",
      detail: "Serving the dashboard and API routes.",
      last_check_at: fixedNowIso
    },
    {
      id: "connector-worker",
      name: "Connector worker",
      status: "warning",
      detail: "One connector activity is waiting for a retry.",
      last_check_at: "2026-03-21T11:55:00.000Z"
    }
  ],
  run_counts: {
    success: 18,
    warning: 3,
    error: 1,
    idle: 2
  },
  recent_runs: [
    {
      id: "run-automation-digest",
      automation_name: "Daily digest",
      trigger_type: "schedule",
      status: "success",
      started_at: "2026-03-21T11:45:00.000Z",
      finished_at: "2026-03-21T11:45:14.000Z",
      duration_ms: 14000
    },
    {
      id: "run-connector-sync",
      automation_name: "Connector sync",
      trigger_type: "manual",
      status: "warning",
      started_at: "2026-03-21T11:30:00.000Z",
      finished_at: "2026-03-21T11:31:10.000Z",
      duration_ms: 70000
    }
  ],
  alerts: [
    {
      id: "alert-queue-retry",
      severity: "warning",
      title: "Queue retry pending",
      message: "A queue worker will retry the next claim cycle.",
      source: "runtime.queue",
      created_at: "2026-03-21T11:50:00.000Z"
    }
  ],
  quick_links: [
    {
      id: "quick-link-logs",
      label: "Logs",
      href: "../dashboard/logs.html",
      count: 4
    },
    {
      id: "quick-link-queue",
      label: "Queue",
      href: "../dashboard/queue.html",
      count: 2
    }
  ],
  runtime_overview: {
    scheduler_active: true,
    queue_status: "running",
    queue_pending_jobs: 2,
    queue_claimed_jobs: 1,
    queue_updated_at: fixedNowIso,
    scheduler_last_tick_started_at: "2026-03-21T11:58:00.000Z",
    scheduler_last_tick_finished_at: "2026-03-21T11:58:04.000Z"
  },
  worker_health: {
    total: 2,
    healthy: 1,
    offline: 1
  },
  api_performance: {
    inbound_total_24h: 42,
    inbound_errors_24h: 1,
    error_rate_percent_24h: 2.4,
    outgoing_scheduled_enabled: 3,
    outgoing_continuous_enabled: 1
  },
  connector_health: {
    total: 4,
    connected: 2,
    needs_attention: 1,
    expired: 0,
    revoked: 0,
    draft: 1,
    pending_oauth: 0
  }
} satisfies RouteObject;

export const defaultDashboardDevicesResponse = {
  host: {
    id: "host-malcom-runtime",
    name: "Malcom host",
    status: "healthy",
    location: "malcom-runtime.local",
    detail: "Live host telemetry for the deterministic browser fixture.",
    last_seen_at: fixedNowIso,
    hostname: "malcom-runtime.local",
    operating_system: "macOS 15.3",
    architecture: "arm64",
    memory_total_bytes: 16000000000,
    memory_used_bytes: 8000000000,
    memory_available_bytes: 8000000000,
    memory_usage_percent: 50,
    storage_total_bytes: 100000000000,
    storage_used_bytes: 25000000000,
    storage_free_bytes: 75000000000,
    storage_usage_percent: 25,
    sampled_at: fixedNowIso
  },
  devices: [
    {
      id: "service-api-endpoint",
      name: "FastAPI server",
      kind: "service",
      status: "healthy",
      location: "localhost:8000",
      detail: "Serving local endpoints.",
      last_seen_at: fixedNowIso
    },
    {
      id: "service-smtp-relay",
      name: "SMTP relay",
      kind: "service",
      status: "warning",
      location: "localhost:2525",
      detail: "Awaiting a test message.",
      last_seen_at: "2026-03-21T11:45:00.000Z"
    }
  ]
} satisfies RouteObject;

export const defaultDashboardQueueResponse = {
  status: "running",
  is_paused: false,
  status_updated_at: fixedNowIso,
  total_jobs: 2,
  pending_jobs: 1,
  claimed_jobs: 1,
  jobs: [
    {
      job_id: "job-trigger-1",
      run_id: "run-connector-sync",
      step_id: "step-http",
      status: "pending",
      worker_id: null,
      worker_name: null,
      claimed_at: null,
      completed_at: null,
      trigger_type: "schedule",
      api_id: "outgoing-digest",
      event_id: "event-001",
      received_at: "2026-03-21T11:52:00.000Z"
    },
    {
      job_id: "job-trigger-2",
      run_id: "run-digest",
      step_id: "step-log",
      status: "claimed",
      worker_id: "worker-1",
      worker_name: "Worker 1",
      claimed_at: "2026-03-21T11:54:00.000Z",
      completed_at: null,
      trigger_type: "manual",
      api_id: "inbound-support",
      event_id: "event-002",
      received_at: "2026-03-21T11:53:45.000Z"
    }
  ]
} satisfies RouteObject;

export const defaultDashboardResourceDashboardResponse = {
  collected_at: fixedNowIso,
  total_snapshots: 3,
  last_captured_at: fixedNowIso,
  latest_snapshot: {
    captured_at: fixedNowIso,
    process_memory_mb: 188.25,
    process_cpu_percent: 17.4,
    queue_pending_jobs: 1,
    queue_claimed_jobs: 0,
    tracked_operations: 3,
    total_error_count: 1,
    hottest_operation: "step_tool",
    hottest_total_duration_ms: 1200,
    max_memory_peak_mb: 12.75
  },
  storage: {
    total_used_bytes: 640000000000,
    total_capacity_bytes: 1000000000000,
    total_usage_percent: 64,
    local_used_bytes: 250000000000,
    local_capacity_bytes: 1000000000000,
    local_usage_percent: 25
  },
  highest_memory_processes: [
    {
      pid: 331,
      name: "python",
      memory_mb: 512.4,
      memory_percent: 6.8
    },
    {
      pid: 998,
      name: "Firefox",
      memory_mb: 401.2,
      memory_percent: 5.3
    },
    {
      pid: 120,
      name: "code helper",
      memory_mb: 287.9,
      memory_percent: 4.1
    }
  ],
  widgets: [
    {
      id: "cpu",
      label: "CPU",
      primary_label: "Process CPU",
      primary_unit: "percent",
      primary_latest: 17.4,
      points: [
        { captured_at: "2026-03-21T11:40:00.000Z", primary_value: 8.1 },
        { captured_at: "2026-03-21T11:50:00.000Z", primary_value: 12.3 },
        { captured_at: fixedNowIso, primary_value: 17.4 }
      ]
    },
    {
      id: "disk-io",
      label: "Disk I/O",
      primary_label: "Read",
      primary_unit: "bytes",
      primary_latest: 1048576,
      secondary_label: "Write",
      secondary_unit: "bytes",
      secondary_latest: 524288,
      points: [
        { captured_at: "2026-03-21T11:40:00.000Z", primary_value: 131072, secondary_value: 65536 },
        { captured_at: "2026-03-21T11:50:00.000Z", primary_value: 524288, secondary_value: 262144 },
        { captured_at: fixedNowIso, primary_value: 1048576, secondary_value: 524288 }
      ]
    },
    {
      id: "network-io",
      label: "Network I/O",
      primary_label: "Sent",
      primary_unit: "bytes",
      primary_latest: 2097152,
      secondary_label: "Received",
      secondary_unit: "bytes",
      secondary_latest: 1048576,
      points: [
        { captured_at: "2026-03-21T11:40:00.000Z", primary_value: 262144, secondary_value: 131072 },
        { captured_at: "2026-03-21T11:50:00.000Z", primary_value: 1048576, secondary_value: 524288 },
        { captured_at: fixedNowIso, primary_value: 2097152, secondary_value: 1048576 }
      ]
    }
  ]
} satisfies RouteObject;

export const defaultLogTablesResponse = [
  {
    id: "log-table-1",
    name: "Delivery audit",
    description: "Rows captured from a log step.",
    row_count: 2,
    created_at: "2026-03-20T09:00:00.000Z",
    updated_at: "2026-03-21T10:00:00.000Z"
  }
] satisfies Array<RouteObject>;

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const isPlainObject = (value: unknown): value is Record<string, unknown> => (
  Boolean(value) && typeof value === "object" && !Array.isArray(value)
);

const deepMerge = <T,>(base: T, patch: unknown): T => {
  if (!isPlainObject(base) || !isPlainObject(patch)) {
    return (patch === undefined ? base : patch) as T;
  }

  const output: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(patch)) {
    output[key] = deepMerge((output as Record<string, unknown>)[key], value);
  }
  return output as T;
};

export type DashboardSettingsFixtureOptions = {
  settings?: RouteObject;
  connectors?: RouteObject;
  summary?: RouteObject;
  devices?: RouteObject;
  queue?: RouteObject;
  resourceDashboard?: RouteObject;
  logTables?: Array<RouteObject>;
  logs?: Array<RouteObject>;
  freezeTimeIso?: string;
  collapsedSidebar?: boolean;
  settingsGetDelayMs?: number;
};

export async function installDashboardSettingsFixtures(page: Page, options: DashboardSettingsFixtureOptions = {}) {
  const state = {
    settings: clone(deepMerge(defaultSettingsResponse, options.settings || {})),
    connectors: clone(deepMerge(buildConnectorSettingsPayload(), options.connectors || {})),
    summary: clone(deepMerge(defaultDashboardSummaryResponse, options.summary || {})),
    devices: clone(deepMerge(defaultDashboardDevicesResponse, options.devices || {})),
    queue: clone(deepMerge(defaultDashboardQueueResponse, options.queue || {})),
    logs: clone(options.logs || dashboardLogEntries),
    resourceDashboard: clone(deepMerge(defaultDashboardResourceDashboardResponse, options.resourceDashboard || {})),
    logTables: clone(options.logTables || defaultLogTablesResponse),
    backups: clone(options.backups || [
      { filename: 'backup-2026-03-21-120000.dump', created_at: '2026-03-21T12:00:00.000Z' }
    ]),
    backupsDirectory: options.backupsDirectory || '/tmp/malcom-backups',
    freezeTimeIso: options.freezeTimeIso || fixedNowIso,
    settingsGetDelayMs: options.settingsGetDelayMs || 0
  };

  await page.addInitScript(
    ({ logs, collapsedSidebar, freezeTimeIso }) => {
      localStorage.setItem("malcom.runtimeLogs", JSON.stringify(logs));
      if (collapsedSidebar) {
        sessionStorage.setItem("sidebarCollapsed", "true");
      }

      const fixedNow = new Date(freezeTimeIso).getTime();
      const originalNow = Date.now;
      Date.now = () => fixedNow;

      window.addEventListener("beforeunload", () => {
        Date.now = originalNow;
      });
    },
    {
      logs: options.logs || dashboardLogEntries,
      collapsedSidebar: options.collapsedSidebar || false,
      freezeTimeIso: state.freezeTimeIso
    }
  );

  await page.route("**/api/v1/settings", async (route) => {
    const method = route.request().method();

    if (method === "GET") {
      if (state.settingsGetDelayMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, state.settingsGetDelayMs));
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.settings)
      });
      return;
    }

    if (method === "PATCH") {
      const patch = route.request().postDataJSON() as RouteObject;
      state.settings = deepMerge(state.settings, patch);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.settings)
      });
      return;
    }

    await route.fallback();
  });

  await page.route("**/api/v1/connectors", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.connectors)
    });
  });

  await page.route("**/api/v1/dashboard/summary", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.summary)
    });
  });

  await page.route("**/api/v1/dashboard/devices", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.devices)
    });
  });

  await page.route("**/api/v1/dashboard/queue", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.queue)
    });
  });

  await page.route("**/api/v1/dashboard/logs", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    const loggingSettings = (state.settings as Record<string, unknown>).logging as Record<string, unknown> | undefined;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        settings: {
          max_stored_entries: Number(loggingSettings?.max_stored_entries || 250),
          max_visible_entries: Number(loggingSettings?.max_visible_entries || 50),
          max_detail_characters: Number(loggingSettings?.max_detail_characters || 4000)
        },
        entries: state.logs
      })
    });
  });

  await page.route("**/api/v1/dashboard/resource-dashboard", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.resourceDashboard)
    });
  });

  await page.route("**/api/v1/dashboard/queue/pause", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    state.queue = {
      ...state.queue,
      status: "paused",
      is_paused: true,
      status_updated_at: state.freezeTimeIso
    };

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.queue)
    });
  });

  await page.route("**/api/v1/dashboard/queue/unpause", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    state.queue = {
      ...state.queue,
      status: "running",
      is_paused: false,
      status_updated_at: state.freezeTimeIso
    };

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.queue)
    });
  });

  await page.route("**/api/v1/log-tables", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(state.logTables)
    });
  });

  await page.route("**/api/v1/log-tables/*/rows/clear", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    const tableId = new URL(route.request().url()).pathname.split("/")[4];
    state.logTables = state.logTables.map((table) => (table.id === tableId
      ? {
          ...table,
          row_count: 0,
          updated_at: state.freezeTimeIso
        }
      : table));

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true })
    });
  });

  // Backup endpoints for settings data
  await page.route("**/api/v1/settings/data/backups", async (route) => {
    const method = route.request().method();

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ directory: state.backupsDirectory, backups: state.backups })
      });
      return;
    }

    if (method === 'POST') {
      const nowIso = new Date(state.freezeTimeIso).toISOString();
      const filename = `backup-${nowIso.replace(/[:.]/g, '-').replace(/T/, '-').replace(/Z/, '')}.dump`;
      const newEntry = { id: filename, filename, created_at: nowIso };
      state.backups.unshift(newEntry);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, message: 'Backup created', backup: newEntry })
      });
      return;
    }

    await route.fallback();
  });

  await page.route("**/api/v1/settings/data/backups/restore", async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }

    try {
      const body = await route.request().postDataJSON();
      const filename = (body && body.backup_id) || null;
      if (!filename) {
        await route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ error: 'backup_id required' }) });
        return;
      }
      const exists = state.backups.some((b: any) => b.filename === filename);
      if (!exists) {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: 'backup not found' }) });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, message: 'Restore completed', restored_at: state.freezeTimeIso })
      });
    } catch (e) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'invalid request' }) });
    }
  });

  return state;
}
