import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardApp } from "../app";

const renderDashboardApp = (initialEntries: string[], developerMode = true) => {
  sessionStorage.clear();

  sessionStorage.setItem("developerMode", String(developerMode));

  return render(<DashboardApp initialEntries={initialEntries} />);
};

describe("DashboardApp", () => {
  it("renders the overview route with developer mode data", async () => {
    renderDashboardApp(["/overview"]);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Overview")).toBeInTheDocument();
    });

    expect(screen.getByText("Runtime status")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent runs" })).toBeInTheDocument();
    expect(screen.getByText("Active attention items")).toBeInTheDocument();
  });

  it("renders loading-ready empty states when developer mode is disabled", async () => {
    renderDashboardApp(["/devices"], false);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Devices")).toBeInTheDocument();
    });

    expect(screen.getByText("No host inventory loaded")).toBeInTheDocument();
    expect(screen.getByText("No endpoints loaded")).toBeInTheDocument();
  });

  it("responds to developer mode changes from the shell toggle", async () => {
    renderDashboardApp(["/overview"], true);

    // Simulate the shell toggle updating session storage and dispatching the shared event.
    sessionStorage.setItem("developerMode", "false");
    window.dispatchEvent(new CustomEvent("malcom:developerModeChanged", { detail: { enabled: false } }));

    await waitFor(() => {
      expect(sessionStorage.getItem("developerMode")).toBe("false");
      expect(screen.getByText("Enable Developer Mode or connect the backend dashboard endpoints to load operational data.")).toBeInTheDocument();
    });
  });

  it("preserves logs filter behavior", async () => {
    renderDashboardApp(["/logs"]);

    const sourceSelect = await screen.findByLabelText("Source");
    fireEvent.change(sourceSelect, { target: { value: "api.webhooks" } });

    expect(screen.getByText("1 matching logs")).toBeInTheDocument();
    expect(screen.getByText("Webhook signature verification retried against the local secret store.")).toBeInTheDocument();
  });

  it("keeps repeated row ids stable from record identifiers", async () => {
    const { container } = renderDashboardApp(["/overview"]);

    await waitFor(() => {
      expect(container.querySelector("#dashboard-run-row-run-weather-poll")).toBeInTheDocument();
    });

    expect(container.querySelector("#dashboard-alert-alert-api-retry")).toBeInTheDocument();
  });

  it("navigates between dashboard routes", async () => {
    renderDashboardApp(["/overview"]);

    const logsLink = await screen.findByRole("link", { name: "Logs" });
    fireEvent.click(logsLink);

    await waitFor(() => {
      expect(screen.getByText("Dashboard Logs")).toBeInTheDocument();
    });

    expect(screen.getByText("Detailed log filters")).toBeInTheDocument();
  });
});
