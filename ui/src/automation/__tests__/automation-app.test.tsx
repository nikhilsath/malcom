import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", async () => {
  const React = await import("react");

  const MockReactFlow = ({ nodes = [], nodeTypes = {}, onNodeClick, onNodeDragStop, children }: any) => (
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
              onClick={() => onNodeDragStop?.({}, { ...node, position: { ...node.position, y: node.position.y + 164 } })}
            >
              Drag {node.id}
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
    MiniMap: ({ id }: { id?: string }) => <div id={id || "mock-minimap"} />,
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

const emailTriage = {
  id: "automation-email-triage",
  name: "Email triage",
  description: "Screen inbound support email.",
  enabled: false,
  trigger_type: "smtp_email",
  trigger_config: {
    smtp_subject: "Support",
    smtp_recipient_email: "ops@example.com"
  },
  step_count: 2,
  created_at: "2026-03-15T08:00:00.000Z",
  updated_at: "2026-03-15T08:00:00.000Z",
  last_run_at: null,
  next_run_at: null,
  steps: [
    {
      id: "step-email-guard",
      type: "condition",
      name: "Priority filter",
      config: {
        expression: "payload.priority == 'high'",
        stop_on_false: true
      }
    },
    {
      id: "step-email-llm",
      type: "llm_chat",
      name: "Summarize thread",
      config: {
        system_prompt: "Summarize the issue.",
        user_prompt: "Review the email body.",
        model_identifier: "gpt-4.1-mini"
      }
    }
  ]
} as const;

const renderAutomationApp = () => {
  document.body.innerHTML = '<button id="automations-create-button" type="button">Create</button>';

  const automationDetails: Record<string, any> = {
    [dailyIngest.id]: structuredClone(dailyIngest),
    [emailTriage.id]: structuredClone(emailTriage)
  };

  const requestLog: RequestLogEntry[] = [];
  const requestJson = vi.fn(async (path: string, options?: RequestInit) => {
    const method = options?.method || "GET";
    const body = options?.body ? JSON.parse(String(options.body)) : null;
    requestLog.push({ path, method, body });

    if (path === "/api/v1/runtime/status") {
      return {
        active: true,
        last_tick_started_at: "2026-03-15T08:29:00.000Z",
        last_tick_finished_at: "2026-03-15T08:29:30.000Z",
        last_error: null,
        job_count: 1
      };
    }

    if (path === "/api/v1/scheduler/jobs") {
      return [
        {
          id: dailyIngest.id,
          kind: "automation",
          name: dailyIngest.name,
          next_run_at: dailyIngest.next_run_at
        }
      ];
    }

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

    if (path.startsWith("/api/v1/automations/") && path.endsWith("/runs")) {
      return [
        {
          run_id: "run-1",
          automation_id: dailyIngest.id,
          trigger_type: "schedule",
          status: "success",
          started_at: "2026-03-15T08:30:00.000Z",
          finished_at: "2026-03-15T08:30:01.000Z",
          duration_ms: 1000,
          error_summary: null
        }
      ];
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

    if (path === "/api/v1/runs/run-1" || path === "/api/v1/runs/run-execute") {
      return {
        run_id: path.endsWith("run-1") ? "run-1" : "run-execute",
        automation_id: dailyIngest.id,
        trigger_type: "schedule",
        status: "success",
        started_at: "2026-03-15T08:30:00.000Z",
        finished_at: "2026-03-15T08:30:01.000Z",
        duration_ms: 1000,
        error_summary: null,
        steps: [
          {
            step_id: "run-step-1",
            run_id: path.endsWith("run-1") ? "run-1" : "run-execute",
            step_name: "Log ingest",
            status: "success",
            request_summary: "Built request",
            response_summary: "Completed",
            started_at: "2026-03-15T08:30:00.000Z",
            finished_at: "2026-03-15T08:30:01.000Z",
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
  it("renders the control room surfaces", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(document.querySelector("#automations-summary-title")).toHaveTextContent("Daily ingest");
    });

    expect(container.querySelector("#automations-canvas-panel")).toBeInTheDocument();
    expect(container.querySelector("#automations-inspector-panel")).toBeInTheDocument();
    expect(container.querySelector("#automations-run-history-panel")).toBeInTheDocument();
  });

  it("hydrates canvas nodes for the selected automation", async () => {
    renderAutomationApp();

    await waitFor(() => {
      expect(document.querySelector("#automations-summary-title")).toHaveTextContent("Daily ingest");
    });

    fireEvent.click(screen.getByRole("button", { name: /email triage/i }));

    await waitFor(() => {
      expect(document.querySelector("#automation-canvas-node-step-step-email-guard-title")).toHaveTextContent("Priority filter");
    });

    expect(document.querySelector("#automation-canvas-node-trigger-title")).toHaveTextContent("SMTP email");
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

  it("persists trigger and step edits through the existing automation payload", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByLabelText("Name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Daily ingest revised" } });
    fireEvent.click(document.querySelector("#mock-select-step-node-step-log") as HTMLElement);
    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Updated log payload." } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      const patchRequest = requestLog.find((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequest?.body?.name).toBe("Daily ingest revised");
      expect((patchRequest?.body?.steps as Array<any>)[0].config.message).toBe("Updated log payload.");
    });
  });

  it("keeps validate, run, and delete bound to the same backend endpoints", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(document.querySelector("#automations-summary-title")).toHaveTextContent("Daily ingest");
    });

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    fireEvent.click(screen.getByRole("button", { name: "Run now" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Confirm delete" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));

    await waitFor(() => {
      expect(requestLog.some((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}/validate` && entry.method === "POST")).toBe(true);
      expect(requestLog.some((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}/execute` && entry.method === "POST")).toBe(true);
      expect(requestLog.some((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "DELETE")).toBe(true);
    });
  });

  it("keeps the legacy APIs automation page redirecting to the new route", () => {
    const redirectHtml = readFileSync(resolve(process.cwd(), "apis/automation.html"), "utf8");
    expect(redirectHtml).toContain("../automations/library.html");
    expect(redirectHtml).toContain("window.location.replace");
  });
});
