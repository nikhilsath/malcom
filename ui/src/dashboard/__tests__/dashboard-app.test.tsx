import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardApp } from "../app";

const renderDashboardApp = (initialEntries: string[]) => {
  sessionStorage.clear();

  return render(<DashboardApp initialEntries={initialEntries} />);
};

const expectTextById = (id: string, text: string) => {
  expect(document.querySelector(`#${id}`)).toHaveTextContent(text);
};

const defaultDashboardLogsPayload = {
  settings: {
    max_stored_entries: 250,
    max_visible_entries: 50,
    max_detail_characters: 4000
  },
  entries: [
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
      details: {
        maxStoredEntries: 250,
        maxVisibleEntries: 50,
        maxDetailCharacters: 4000
      },
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
  ]
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/dashboard/queue")) {
        return {
          ok: true,
          json: async () => ({
            status: "running",
            is_paused: false,
            status_updated_at: "2026-03-20T09:00:00.000Z",
            total_jobs: 0,
            pending_jobs: 0,
            claimed_jobs: 0,
            jobs: []
          })
        };
      }

      if (url.includes("/api/v1/dashboard/logs")) {
        return {
          ok: true,
          json: async () => defaultDashboardLogsPayload
        };
      }

      if (url.includes("/api/v1/dashboard/resource-dashboard")) {
        return {
          ok: true,
          json: async () => ({
            collected_at: "2026-03-20T09:00:00.000Z",
            total_snapshots: 0,
            last_captured_at: null,
            latest_snapshot: null,
            storage: {
              total_used_bytes: 0,
              total_capacity_bytes: 0,
              total_usage_percent: 0,
              local_used_bytes: 0,
              local_capacity_bytes: 0,
              local_usage_percent: 0
            },
            highest_memory_processes: [],
            widgets: []
          })
        };
      }

      return {
        ok: true,
        json: async () => ({
          host: null,
          devices: []
        })
      };
    })
  );
});

describe("DashboardApp", () => {
  it("renders the home route with offline state", async () => {
    renderDashboardApp(["/home"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Home")).toBeInTheDocument();
    });

    expect(screen.getByText("Waiting for data")).toBeInTheDocument();
    expect(screen.getByText("Backend dashboard endpoints are not yet connected.")).toBeInTheDocument();
    expect(screen.getByText("Runtime status")).toBeInTheDocument();
    expect(screen.getByText("Queue status")).toBeInTheDocument();
    expectTextById("dashboard-overview-summary-queue-status-value", "Running");
  });

  it("renders loading-ready empty states for devices", async () => {
    renderDashboardApp(["/devices"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Devices")).toBeInTheDocument();
    });

    expect(screen.getByText("No host inventory loaded")).toBeInTheDocument();
    expect(screen.getByText("No endpoints loaded")).toBeInTheDocument();
    expect(document.querySelector("#dashboard-devices-summary-card")).not.toBeInTheDocument();
  });

  it("surfaces persisted resource dashboard metrics on dashboard home", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.includes("/api/v1/dashboard/summary")) {
          return {
            ok: true,
            json: async () => ({
              health: {
                id: "system-health",
                status: "healthy",
                label: "Workspace healthy",
                summary: "Summary endpoint connected.",
                updated_at: "2026-03-21T12:00:00.000Z"
              },
              services: [],
              run_counts: { success: 2, warning: 0, error: 0, idle: 0 },
              recent_runs: [],
              alerts: [],
              quick_links: [],
              runtime_overview: {
                scheduler_active: true,
                queue_status: "running",
                queue_pending_jobs: 0,
                queue_claimed_jobs: 0,
                queue_updated_at: "2026-03-21T12:00:00.000Z",
                scheduler_last_tick_started_at: "2026-03-21T12:00:00.000Z",
                scheduler_last_tick_finished_at: "2026-03-21T12:00:01.000Z"
              },
              worker_health: { total: 1, healthy: 1, offline: 0 },
              api_performance: {
                inbound_total_24h: 4,
                inbound_errors_24h: 0,
                error_rate_percent_24h: 0,
                outgoing_scheduled_enabled: 1,
                outgoing_continuous_enabled: 0
              },
              connector_health: {
                total: 1,
                connected: 1,
                needs_attention: 0,
                expired: 0,
                revoked: 0,
                draft: 0,
                pending_oauth: 0
              }
            })
          };
        }

        if (url.includes("/api/v1/dashboard/queue")) {
          return {
            ok: true,
            json: async () => ({
              status: "running",
              is_paused: false,
              status_updated_at: "2026-03-20T09:00:00.000Z",
              total_jobs: 0,
              pending_jobs: 0,
              claimed_jobs: 0,
              jobs: []
            })
          };
        }

        if (url.includes("/api/v1/dashboard/resource-dashboard")) {
          return {
            ok: true,
            json: async () => ({
              collected_at: "2026-03-21T12:00:00.000Z",
              total_snapshots: 2,
              last_captured_at: "2026-03-21T12:00:00.000Z",
              latest_snapshot: {
                captured_at: "2026-03-21T12:00:00.000Z",
                process_memory_mb: 188.25,
                process_cpu_percent: 17.4,
                queue_pending_jobs: 2,
                queue_claimed_jobs: 1,
                tracked_operations: 3,
                total_error_count: 1,
                hottest_operation: "step_tool",
                hottest_total_duration_ms: 961.2,
                max_memory_peak_mb: 12.75
              },
              storage: {
                total_used_bytes: 640000000000,
                total_capacity_bytes: 1000000000000,
                total_usage_percent: 64,
                local_used_bytes: 240000000000,
                local_capacity_bytes: 500000000000,
                local_usage_percent: 48
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
                    { captured_at: "2026-03-21T11:40:00.000Z", primary_value: 9.1 },
                    { captured_at: "2026-03-21T11:50:00.000Z", primary_value: 12.3 },
                    { captured_at: "2026-03-21T12:00:00.000Z", primary_value: 17.4 }
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
                    { captured_at: "2026-03-21T12:00:00.000Z", primary_value: 1048576, secondary_value: 524288 }
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
                    { captured_at: "2026-03-21T12:00:00.000Z", primary_value: 2097152, secondary_value: 1048576 }
                  ]
                }
              ]
            })
          };
        }

        return {
          ok: true,
          json: async () => ({ host: null, devices: [] })
        };
      })
    );

    renderDashboardApp(["/home"]);

    await waitFor(() => {
      expectTextById("dashboard-overview-resource-dashboard-toolbar-title", "Resource dashboard");
    });

    expectTextById("dashboard-overview-resource-dashboard-total-storage-value", "596 GB");
    expectTextById("dashboard-overview-resource-dashboard-local-storage-value", "224 GB");
    expectTextById("dashboard-overview-resource-dashboard-process-name-0", "python");
    expectTextById("dashboard-overview-resource-dashboard-process-memory-0", "512.40 MB");
    expectTextById("dashboard-overview-resource-dashboard-widget-primary-value", "17.4%");
    expect(document.querySelector("#dashboard-overview-summary-visible-logs")).not.toBeInTheDocument();
    expect(document.querySelector("#dashboard-overview-layout")?.firstElementChild).toHaveAttribute(
      "id",
      "dashboard-overview-resource-dashboard"
    );

    fireEvent.click(screen.getByRole("button", { name: "Disk I/O" }));
    expectTextById("dashboard-overview-resource-dashboard-widget-primary-value", "1.00 MB");
    expectTextById("dashboard-overview-resource-dashboard-widget-secondary-value", "512 KB");
  });

  it("renders live backend devices when data is available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          host: {
            id: "host-malcom-runtime",
            name: "Malcom host",
            status: "healthy",
            location: "malcom-runtime.local",
            detail: "Live host telemetry.",
            last_seen_at: "2026-03-15T10:00:00.000Z",
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
            sampled_at: "2026-03-15T10:00:00.000Z"
          },
          devices: [
            {
              id: "service-api-endpoint",
              name: "FastAPI server",
              kind: "service",
              status: "healthy",
              location: "localhost:8000",
              detail: "Serving local endpoints.",
              last_seen_at: "2026-03-15T10:00:00.000Z"
            }
          ]
        })
      })
    );

    const { container } = renderDashboardApp(["/devices"]);

    await waitFor(() => {
      expectTextById("dashboard-devices-host-toolbar-title", "Host machine");
    });

    expect(container.querySelector("#dashboard-device-row-service-api-endpoint")).toBeInTheDocument();
    expect(container.querySelector("#dashboard-devices-storage-free-card")).toBeInTheDocument();
  });

  it("preserves logs filter behavior", async () => {
    renderDashboardApp(["/logs"]);

    const sourceSelect = await screen.findByLabelText("Source");
    fireEvent.change(sourceSelect, { target: { value: "api.webhooks" } });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/dashboard/logs");
    });

    expect(document.querySelector("#dashboard-logs-results-count")?.textContent).toContain("1 matching logs");
    expect(screen.getAllByText("Webhook signature verification retried against the local secret store.").length).toBeGreaterThan(0);
  });

  it("renders the logs route when requested", async () => {
    renderDashboardApp(["/logs"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Logs")).toBeInTheDocument();
    });

    expectTextById("dashboard-logs-toolbar-title", "Detailed log filters");
    expectTextById("dashboard-logs-results-toolbar-title", "Runtime event explorer");
    expectTextById("dashboard-logs-report-builder-toolbar-title", "Log report builder");
    expect(screen.getByText("Grafana")).toBeInTheDocument();
  });

  it("updates event detail when selecting another log", async () => {
    renderDashboardApp(["/logs"]);

    await waitFor(() => {
      expectTextById("dashboard-logs-results-toolbar-title", "Runtime event explorer");
    });

    fireEvent.click(screen.getByRole("button", { name: /Default logging thresholds applied\./i }));

    expect(screen.getByRole("dialog", { name: "Event details" })).toBeInTheDocument();
    expect(screen.getAllByText("Default logging thresholds applied.").length).toBeGreaterThan(0);
    expect(screen.getByText("Event id")).toBeInTheDocument();
    expect(screen.getByText("log-settings-defaults")).toBeInTheDocument();
  });

  it("renders the queue route when requested", async () => {
    renderDashboardApp(["/queue"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Queue")).toBeInTheDocument();
    });

    await waitFor(() => {
      expectTextById("dashboard-queue-jobs-toolbar-title", "Runtime trigger jobs");
    });
    expect(screen.getByText("Queue is empty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pause queue" })).toBeInTheDocument();
  });

  it("toggles queue pause controls", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.includes("/api/v1/dashboard/queue/pause") && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            status: "paused",
            is_paused: true,
            status_updated_at: "2026-03-20T09:05:00.000Z",
            total_jobs: 0,
            pending_jobs: 0,
            claimed_jobs: 0,
            jobs: []
          })
        };
      }

      if (url.includes("/api/v1/dashboard/queue/unpause") && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            status: "running",
            is_paused: false,
            status_updated_at: "2026-03-20T09:06:00.000Z",
            total_jobs: 0,
            pending_jobs: 0,
            claimed_jobs: 0,
            jobs: []
          })
        };
      }

      if (url.includes("/api/v1/dashboard/queue")) {
        return {
          ok: true,
          json: async () => ({
            status: "running",
            is_paused: false,
            status_updated_at: "2026-03-20T09:00:00.000Z",
            total_jobs: 0,
            pending_jobs: 0,
            claimed_jobs: 0,
            jobs: []
          })
        };
      }

      return {
        ok: true,
        json: async () => ({
          host: null,
          devices: []
        })
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderDashboardApp(["/queue"]);

    const pauseButton = await screen.findByRole("button", { name: "Pause queue" });
    fireEvent.click(pauseButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Unpause queue" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Unpause queue" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Pause queue" })).toBeInTheDocument();
    });
  });
});
