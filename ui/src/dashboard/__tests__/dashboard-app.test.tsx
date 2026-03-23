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
    expect(screen.getByText("Running")).toBeInTheDocument();
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
