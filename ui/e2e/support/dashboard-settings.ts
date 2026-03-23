import type { Page } from "@playwright/test";

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

export const defaultSettingsResponse = {
  general: {
    environment: "live",
    timezone: "local"
  },
  logging: {
    max_stored_entries: 250,
    max_visible_entries: 50,
    max_detail_characters: 4000,
    max_file_size_mb: 5
  },
  notifications: {
    channel: "slack",
    digest: "hourly",
    escalate_oncall: true
  },
  security: {
    session_timeout_minutes: 30,
    dual_approval_required: true,
    token_rotation_days: 90
  },
  data: {
    payload_redaction: true,
    export_window_utc: "02:00",
    audit_retention_days: 365
  },
  automation: {
    default_tool_retries: 2
  },
  connectors: {
    catalog: [
      {
        id: "google",
        name: "Google",
        description: "Google APIs",
        category: "productivity",
        auth_types: ["oauth2"],
        default_scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
        docs_url: "https://developers.google.com",
        base_url: "https://www.googleapis.com"
      },
      {
        id: "github",
        name: "GitHub",
        description: "GitHub APIs",
        category: "engineering",
        auth_types: ["bearer"],
        default_scopes: ["repo"],
        docs_url: "https://docs.github.com",
        base_url: "https://api.github.com"
      }
    ],
    records: [],
    auth_policy: {
      rotation_interval_days: 90,
      reconnect_requires_approval: true,
      credential_visibility: "masked"
    }
  }
} satisfies RouteObject;

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
  summary?: RouteObject;
  devices?: RouteObject;
  queue?: RouteObject;
  logTables?: Array<RouteObject>;
  logs?: Array<RouteObject>;
  freezeTimeIso?: string;
  collapsedSidebar?: boolean;
};

export async function installDashboardSettingsFixtures(page: Page, options: DashboardSettingsFixtureOptions = {}) {
  const state = {
    settings: clone(deepMerge(defaultSettingsResponse, options.settings || {})),
    summary: clone(deepMerge(defaultDashboardSummaryResponse, options.summary || {})),
    devices: clone(deepMerge(defaultDashboardDevicesResponse, options.devices || {})),
    queue: clone(deepMerge(defaultDashboardQueueResponse, options.queue || {})),
    logTables: clone(options.logTables || defaultLogTablesResponse),
    freezeTimeIso: options.freezeTimeIso || fixedNowIso
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

  return state;
}
