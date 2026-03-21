import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", async () => {
  const React = await import("react");

  const MockReactFlow = ({ nodes = [], nodeTypes = {}, onNodeClick, onNodeDragStop, onNodeContextMenu, children }: any) => (
    <div id="mock-react-flow">
      {nodes.map((node: any) => {
        const NodeComponent = nodeTypes[node.type];
        return (
          <div key={node.id} id={`mock-node-wrapper-${node.id}`}>
            <button id={`mock-select-${node.id}`} type="button" onClick={() => onNodeClick?.({}, node)}>
              Select {node.id}
            </button>
            <button
              id={`mock-drag-${node.id}`}
              type="button"
              onClick={() => onNodeDragStop?.({}, { ...node, position: { ...node.position, y: node.position.y + 228 } })}
            >
              Drag {node.id}
            </button>
            <button
              id={`mock-context-${node.id}`}
              type="button"
              onClick={() => onNodeContextMenu?.({ preventDefault() {}, clientX: 320, clientY: 240 }, node)}
            >
              Context {node.id}
            </button>
            {NodeComponent ? <NodeComponent id={node.id} data={node.data} selected={Boolean(node.data?.selected)} /> : null}
          </div>
        );
      })}
      {children}
    </div>
  );

  return {
    __esModule: true,
    ReactFlow: MockReactFlow,
    Background: ({ id }: { id?: string }) => <div id={id || "mock-background"} />,
    Controls: ({ id }: { id?: string }) => <div id={id || "mock-controls"} />,
    Handle: ({ className }: { className?: string }) => <span className={className} />,
    MarkerType: { ArrowClosed: "ArrowClosed" },
    Position: { Top: "top", Bottom: "bottom" }
  };
});

import { AutomationApp } from "../app";

type RequestLogEntry = {
  path: string;
  method: string;
  body: Record<string, unknown> | null;
};

const dailyIngest = {
  id: "automation-daily-ingest",
  name: "Daily ingest",
  description: "Pull the current feed and forward it.",
  enabled: true,
  trigger_type: "schedule",
  trigger_config: {
    schedule_time: "08:30"
  },
  step_count: 2,
  created_at: "2026-03-15T08:00:00.000Z",
  updated_at: "2026-03-15T08:00:00.000Z",
  last_run_at: "2026-03-15T08:30:00.000Z",
  next_run_at: "2026-03-16T08:30:00.000Z",
  steps: [
    {
      id: "step-log",
      type: "log",
      name: "Log ingest",
      config: {
        message: "Feed arrived."
      }
    },
    {
      id: "step-http",
      type: "outbound_request",
      name: "Dispatch webhook",
      config: {
        destination_url: "https://example.com/ingest",
        http_method: "POST",
        connector_id: "",
        payload_template: "{\"ok\":true}"
      }
    }
  ]
} as const;

const renderAutomationApp = () => {
  document.body.innerHTML = '<button id="automations-create-button" type="button">Create</button>';
  window.history.replaceState({}, "", "/automations/builder.html?id=automation-daily-ingest");

  const automationDetails: Record<string, any> = {
    [dailyIngest.id]: structuredClone(dailyIngest)
  };

  const requestLog: RequestLogEntry[] = [];
  const requestJson = vi.fn(async (path: string, options?: RequestInit) => {
    const method = options?.method || "GET";
    const body = options?.body ? JSON.parse(String(options.body)) : null;
    requestLog.push({ path, method, body });

    if (path === "/api/v1/settings") {
      return {
        connectors: {
          records: [
            {
              id: "connector-main",
              provider: "http",
              name: "Main webhook",
              auth_type: "none",
              base_url: "https://example.com"
            }
          ]
        }
      };
    }

    if (path === "/api/v1/automations") {
      if (method === "GET") {
        return Object.values(automationDetails).map((automation: any) => ({
          ...automation,
          steps: undefined,
          step_count: automation.steps.length
        }));
      }

      const created = {
        ...structuredClone(dailyIngest),
        ...body,
        id: "automation-created"
      };
      automationDetails[created.id] = created;
      return created;
    }

    if (path === `/api/v1/automations/${dailyIngest.id}` && method === "PATCH") {
      automationDetails[dailyIngest.id] = {
        ...automationDetails[dailyIngest.id],
        ...body,
        steps: body?.steps
      };
      return automationDetails[dailyIngest.id];
    }

    if (path === `/api/v1/automations/${dailyIngest.id}` && method === "DELETE") {
      delete automationDetails[dailyIngest.id];
      return null;
    }

    if (path === `/api/v1/automations/${dailyIngest.id}/validate`) {
      return { valid: true, issues: [] };
    }

    if (path === `/api/v1/automations/${dailyIngest.id}/execute`) {
      return {
        run_id: "run-execute",
        automation_id: dailyIngest.id,
        trigger_type: "manual",
        status: "success",
        started_at: "2026-03-15T09:00:00.000Z",
        finished_at: "2026-03-15T09:00:01.000Z",
        duration_ms: 1000,
        error_summary: null,
        steps: [
          {
            step_id: "run-step-1",
            run_id: "run-execute",
            step_name: "Log ingest",
            status: "success",
            request_summary: "Built request",
            response_summary: "Completed",
            started_at: "2026-03-15T09:00:00.000Z",
            finished_at: "2026-03-15T09:00:01.000Z",
            duration_ms: 1000,
            detail_json: null
          }
        ]
      };
    }

    if (path.startsWith("/api/v1/automations/")) {
      const automationId = path.replace("/api/v1/automations/", "");
      return structuredClone(automationDetails[automationId]);
    }

    throw new Error(`Unhandled request ${method} ${path}`);
  });

  window.Malcom = { requestJson };
  const renderResult = render(<AutomationApp />);

  return { ...renderResult, requestJson, requestLog };
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("AutomationApp", () => {
  it("renders the workflow bar and focused canvas without the legacy inspector surfaces", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    expect(container.querySelector("#automations-workflow-bar")).toBeInTheDocument();
    expect(container.querySelector("#automations-canvas-panel")).toBeInTheDocument();
    expect(container.querySelector("#automations-inspector-panel")).not.toBeInTheDocument();
    expect(container.querySelector("#automations-run-history-panel")).not.toBeInTheDocument();
    expect(container.querySelector("#automations-test-results-drawer")).not.toBeInTheDocument();
  });

  it("opens node actions and the step drawer from the selected canvas node", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(container.querySelector("#automation-canvas-node-step-step-log-title")).toHaveTextContent("Log ingest");
    });

    fireEvent.click(document.querySelector("#mock-select-step-node-step-log") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-step-step-log-actions-button") as HTMLElement);

    await waitFor(() => {
      expect(container.querySelector("#automations-node-menu")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
      expect(screen.getByLabelText("Message")).toBeInTheDocument();
    });
  });

  it("supports the node context menu shortcut on desktop", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(container.querySelector("#automation-canvas-node-step-step-http-title")).toHaveTextContent("Dispatch webhook");
    });

    fireEvent.click(document.querySelector("#mock-context-step-node-step-http") as HTMLElement);

    await waitFor(() => {
      expect(container.querySelector("#automations-node-menu")).toBeInTheDocument();
      expect(container.querySelector("#automations-node-menu-remove")).toBeInTheDocument();
    });
  });

  it("serializes reordered steps when the canvas order changes", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(document.querySelector("#mock-drag-step-node-step-log")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#mock-drag-step-node-step-log") as HTMLElement);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      const patchRequest = requestLog.find((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequest).toBeDefined();
      expect((patchRequest?.body?.steps as Array<{ id: string }>).map((step) => step.id)).toEqual(["step-http", "step-log"]);
    });
  });

  it("keeps workflow identity outside trigger settings and shows test output only on demand", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByLabelText("Workflow name")).toBeInTheDocument();
    });

    expect(container.querySelector("#automations-test-results-drawer")).not.toBeInTheDocument();

    fireEvent.click(document.querySelector("#mock-select-trigger-node") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-trigger-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    const drawer = document.querySelector("#automations-editor-drawer") as HTMLElement;
    expect(within(drawer).queryByLabelText("Workflow name")).not.toBeInTheDocument();
    expect(within(drawer).getByText("Manual")).toBeInTheDocument();
    expect(within(drawer).getByText("Schedule")).toBeInTheDocument();
    fireEvent.click(within(drawer).getByRole("radio", { name: /schedule/i }));
    expect(within(drawer).getByLabelText("Daily run time")).toBeInTheDocument();
    fireEvent.click(within(drawer).getByRole("button", { name: "Close" }));

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() => {
      expect(document.querySelector("#automations-test-results-drawer")).toBeInTheDocument();
      expect(document.querySelector("#automations-validation-results")).toBeInTheDocument();
    });
  });

  it("shows run results in the on-demand test drawer", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));

    await waitFor(() => {
      expect(requestLog.some((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}/execute` && entry.method === "POST")).toBe(true);
    });

    expect(await screen.findByText("Test run results")).toBeInTheDocument();
    expect(await screen.findByText("Built request")).toBeInTheDocument();
  });

  it("keeps the legacy APIs automation page redirecting to the new route", () => {
    const redirectHtml = readFileSync(resolve(process.cwd(), "apis/automation.html"), "utf8");
    expect(redirectHtml).toContain("../automations/library.html");
    expect(redirectHtml).toContain("window.location.replace");
  });
});
