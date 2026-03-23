import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AutomationDataApp } from "../data";

const tablesResponse = [
  {
    id: "table-1",
    name: "Delivery audit",
    description: "Rows captured from a log step.",
    row_count: 2,
    created_at: "2026-03-20T09:00:00.000Z",
    updated_at: "2026-03-21T10:00:00.000Z"
  }
];

const rowsResponse = {
  table_id: "table-1",
  table_name: "Delivery audit",
  columns: ["row_id", "status"],
  rows: [
    { row_id: 1, status: "ok" },
    { row_id: 2, status: "warning" }
  ],
  total: 2
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/log-tables/") && url.includes("/rows")) {
        return {
          ok: true,
          json: async () => rowsResponse
        };
      }

      return {
        ok: true,
        json: async () => tablesResponse
      };
    })
  );
});

describe("AutomationDataApp", () => {
  it("keeps details hidden by default until a table is selected", async () => {
    render(<AutomationDataApp />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Delivery audit/i })).toBeInTheDocument();
    });

    expect(screen.getByText("Select a table to view its data.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens selected table rows in a modal and returns focus on close", async () => {
    render(<AutomationDataApp />);

    const trigger = await screen.findByRole("button", { name: /Delivery audit/i });
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    expect(document.querySelector("#automations-data-total-hint")).toHaveTextContent("Showing 2 of 2 rows");
    expect(screen.getByText("warning")).toBeInTheDocument();

    const closeButton = document.querySelector<HTMLButtonElement>("#automations-data-modal-close");
    expect(closeButton).not.toBeNull();
    expect(closeButton).toHaveAttribute("aria-label", "Close log table details");
    fireEvent.click(closeButton!);

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(document.activeElement).toBe(trigger);
  });
});
