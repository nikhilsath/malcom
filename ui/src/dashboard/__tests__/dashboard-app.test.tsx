import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardApp } from "../app";

const renderDashboardApp = (initialEntries: string[]) => {
  sessionStorage.clear();

  return render(<DashboardApp initialEntries={initialEntries} />);
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        host: null,
        devices: []
      })
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
      expect(screen.getByText("Host machine")).toBeInTheDocument();
    });

    expect(container.querySelector("#dashboard-device-row-service-api-endpoint")).toBeInTheDocument();
    expect(container.querySelector("#dashboard-devices-storage-free-card")).toBeInTheDocument();
  });

  it("preserves logs filter behavior", async () => {
    renderDashboardApp(["/logs"]);

    const sourceSelect = await screen.findByLabelText("Source");
    fireEvent.change(sourceSelect, { target: { value: "api.webhooks" } });

    expect(screen.getByText("1 matching logs")).toBeInTheDocument();
    expect(screen.getByText("Webhook signature verification retried against the local secret store.")).toBeInTheDocument();
  });

  it("renders the logs route when requested", async () => {
    renderDashboardApp(["/logs"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Logs")).toBeInTheDocument();
    });

    expect(screen.getByText("Detailed log filters")).toBeInTheDocument();
    expect(screen.getByText("Log report builder")).toBeInTheDocument();
    expect(screen.getByText("Grafana")).toBeInTheDocument();
  });
});
