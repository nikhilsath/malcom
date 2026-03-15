import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardApp } from "../app";

const renderDashboardApp = (initialEntries: string[], developerMode?: boolean) => {
  sessionStorage.clear();

  if (developerMode !== undefined) {
    sessionStorage.setItem("developerMode", String(developerMode));
  }

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
  it("renders the home route with developer mode data", async () => {
    renderDashboardApp(["/home"], true);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Home")).toBeInTheDocument();
    });

    expect(screen.getByText("Runtime status")).toBeInTheDocument();
    expect(screen.getByText("Active attention items")).toBeInTheDocument();
  });

  it("renders loading-ready empty states when developer mode is disabled", async () => {
    renderDashboardApp(["/devices"], false);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Devices")).toBeInTheDocument();
    });

    expect(screen.getByText("No host inventory loaded")).toBeInTheDocument();
    expect(screen.getByText("No endpoints loaded")).toBeInTheDocument();
    expect(document.querySelector("#dashboard-devices-summary-card")).not.toBeInTheDocument();
  });

  it("renders host telemetry summary in developer mode", async () => {
    renderDashboardApp(["/devices"], true);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Devices")).toBeInTheDocument();
    });

    expect(screen.getByText("Host machine")).toBeInTheDocument();
    expect(screen.getByText("Hostname")).toBeInTheDocument();
    expect(screen.getByText("OS")).toBeInTheDocument();
    expect(screen.getByText("Architecture")).toBeInTheDocument();
    expect(screen.getByText("Total RAM")).toBeInTheDocument();
    expect(screen.getByText("RAM used")).toBeInTheDocument();
    expect(screen.getByText("Total storage")).toBeInTheDocument();
    expect(screen.getByText("Storage free")).toBeInTheDocument();
    expect(document.querySelector("#dashboard-device-host-hostname-host-malcom-macbook")).toBeInTheDocument();
    expect(document.querySelector("#dashboard-devices-ram-total-card")).toBeInTheDocument();
  });

  it("defaults to developer mode off when unset", async () => {
    renderDashboardApp(["/devices"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Devices")).toBeInTheDocument();
    });

    expect(sessionStorage.getItem("developerMode")).toBe("false");
    expect(screen.getByText("No host inventory loaded")).toBeInTheDocument();
  });

  it("renders live backend devices when developer mode is off and data is available", async () => {
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

    const { container } = renderDashboardApp(["/devices"], false);

    await waitFor(() => {
      expect(screen.getByText("Host machine")).toBeInTheDocument();
    });

    expect(container.querySelector("#dashboard-device-row-service-api-endpoint")).toBeInTheDocument();
    expect(container.querySelector("#dashboard-devices-storage-free-card")).toBeInTheDocument();
  });

  it("responds to developer mode changes from the shell toggle", async () => {
    renderDashboardApp(["/home"], true);

    // Simulate the shell toggle updating session storage and dispatching the shared event.
    act(() => {
      sessionStorage.setItem("developerMode", "false");
      window.dispatchEvent(new CustomEvent("malcom:developerModeChanged", { detail: { enabled: false } }));
    });

    await waitFor(() => {
      expect(sessionStorage.getItem("developerMode")).toBe("false");
      expect(screen.getByText("Enable Developer Mode or connect the backend dashboard endpoints to load operational data.")).toBeInTheDocument();
    });
  });

  it("preserves logs filter behavior", async () => {
    renderDashboardApp(["/logs"], true);

    const sourceSelect = await screen.findByLabelText("Source");
    fireEvent.change(sourceSelect, { target: { value: "api.webhooks" } });

    expect(screen.getByText("1 matching logs")).toBeInTheDocument();
    expect(screen.getByText("Webhook signature verification retried against the local secret store.")).toBeInTheDocument();
  });

  it("keeps repeated row ids stable from record identifiers", async () => {
    const { container } = renderDashboardApp(["/home"], true);

    await waitFor(() => {
      expect(container.querySelector("#dashboard-service-runtime")).toBeInTheDocument();
    });

    expect(container.querySelector("#dashboard-alert-alert-api-retry")).toBeInTheDocument();
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
