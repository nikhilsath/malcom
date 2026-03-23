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

const scriptLibraryItems = [
  {
    id: "script-change-delimiter",
    name: "Change Delimiter",
    description: "Split text on one delimiter and join it with another.",
    language: "python",
    sample_input: "{\n  \"text\": \"alpha,beta,gamma\",\n  \"from\": \",\",\n  \"to\": \"|\"\n}"
  },
  {
    id: "script-extract-regex",
    name: "Extract With Regex",
    description: "Search text with a regex and return matches.",
    language: "python",
    sample_input: "{\n  \"text\": \"Invoice INV-1042\",\n  \"pattern\": \"INV-(\\\\d+)\",\n  \"group\": 1\n}"
  }
];

const renderAutomationApp = (options?: {
  initialAutomation?: Partial<typeof dailyIngest> & {
    trigger_config?: Record<string, unknown>;
    steps?: Array<Record<string, unknown>>;
  };
  inboundApis?: Array<{ id: string; name: string }>;
  connectors?: Array<Record<string, unknown>>;
  httpPresets?: Array<Record<string, unknown>>;
}) => {
  document.body.innerHTML = '<button id="automations-create-button" type="button">Create</button>';
  window.history.replaceState({}, "", "/automations/builder.html?id=automation-daily-ingest");

  const initialAutomation = {
    ...structuredClone(dailyIngest),
    ...structuredClone(options?.initialAutomation || {}),
    trigger_config: {
      ...structuredClone(dailyIngest.trigger_config),
      ...(options?.initialAutomation?.trigger_config || {})
    },
    steps: (options?.initialAutomation?.steps as any[]) || structuredClone(dailyIngest.steps)
  };

  const inboundApis = options?.inboundApis || [
    { id: "inbound-orders", name: "Orders API" },
    { id: "inbound-invoices", name: "Invoices API" }
  ];

  const automationDetails: Record<string, any> = {
    [dailyIngest.id]: structuredClone(initialAutomation)
  };

  const requestLog: RequestLogEntry[] = [];
  const requestJson = vi.fn(async (path: string, requestOptions?: RequestInit) => {
    const method = requestOptions?.method || "GET";
    const body = requestOptions?.body ? JSON.parse(String(requestOptions.body)) : null;
    requestLog.push({ path, method, body });

    if (path === "/api/v1/settings") {
      return {
        connectors: {
          records: options?.connectors || [
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

    if (path === "/api/v1/inbound") {
      return inboundApis;
    }

    if (path === "/api/v1/scripts") {
      return scriptLibraryItems;
    }

    if (path === "/api/v1/connectors/activity-catalog") {
      return [
        {
          provider_id: "http",
          activity_id: "custom_http",
          service: "http",
          operation_type: "read",
          label: "Custom HTTP",
          description: "Not used in this test harness.",
          required_scopes: [],
          input_schema: [],
          output_schema: [],
          execution: {}
        },
        {
          provider_id: "google",
          activity_id: "gmail_list_messages",
          service: "gmail",
          operation_type: "read",
          label: "List emails",
          description: "List Gmail messages.",
          required_scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          input_schema: [
            { key: "max_results", label: "Max results", type: "integer", required: false, default: 25 }
          ],
          output_schema: [{ key: "messages", label: "Messages", type: "array" }],
          execution: {}
        },
        {
          provider_id: "google",
          activity_id: "gmail_send_email",
          service: "gmail",
          operation_type: "write",
          label: "Send email",
          description: "Send Gmail message.",
          required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
          input_schema: [
            { key: "recipients", label: "Recipients", type: "string", required: true },
            { key: "subject", label: "Subject", type: "string", required: true },
            { key: "body", label: "Body", type: "textarea", required: true }
          ],
          output_schema: [{ key: "message_id", label: "Message ID", type: "string" }],
          execution: {}
        },
        {
          provider_id: "google",
          activity_id: "sheets_update_range",
          service: "sheets",
          operation_type: "write",
          label: "Update range",
          description: "Write values into a sheet.",
          required_scopes: ["https://www.googleapis.com/auth/spreadsheets"],
          input_schema: [
            { key: "spreadsheet_id", label: "Spreadsheet ID", type: "string", required: true },
            { key: "range", label: "A1 range", type: "string", required: true },
            { key: "values_payload", label: "Values payload", type: "json", required: true }
          ],
          output_schema: [{ key: "updated_cells", label: "Updated cells", type: "integer" }],
          execution: {}
        }
      ];
    }

    if (path === "/api/v1/connectors/http-presets") {
      return options?.httpPresets || [];
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
            detail_json: null,
            response_body_json: null,
            extracted_fields_json: null
          }
        ]
      };
    }

    if (path === "/api/v1/apis/test-delivery") {
      return {
        ok: true,
        status_code: 200,
        response_body: JSON.stringify({
          data: {
            guides: {
              count: 4,
              items: [{ title: "Welcome" }]
            }
          }
        }),
        sent_headers: { "Content-Type": "application/json" },
        destination_url: "https://example.com/ingest"
      };
    }

    if (path.startsWith("/api/v1/automations/")) {
      const automationId = path.replace("/api/v1/automations/", "");
      return structuredClone(automationDetails[automationId]);
    }

    throw new Error(`Unhandled request ${method} ${path}`);
  });

  window.TOOLS_MANIFEST = [
    {
      id: "smtp",
      name: "SMTP",
      description: "Send email",
      pageHref: "tools/smtp.html",
      inputs: [
        { key: "relay_host", label: "Relay Host", type: "string", required: true },
        { key: "relay_port", label: "Relay Port", type: "number", required: true },
        { key: "relay_security", label: "Security", type: "select", required: false, options: ["none", "starttls", "tls"] },
        { key: "relay_username", label: "Username", type: "string", required: false },
        { key: "relay_password", label: "Password", type: "string", required: false },
        { key: "from_address", label: "From Address", type: "string", required: true },
        { key: "to", label: "To", type: "string", required: true },
        { key: "subject", label: "Subject", type: "string", required: true },
        { key: "body", label: "Body", type: "text", required: true }
      ],
      outputs: [
        { key: "status", label: "Status", type: "string" },
        { key: "message", label: "Message", type: "string" }
      ]
    }
  ];
  window.Malcom = { requestJson };
  const renderResult = render(<AutomationApp />);

  return { ...renderResult, requestJson, requestLog };
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("AutomationApp", () => {

  it("uses connector-scoped HTTP presets and hides manual fields in preset mode", async () => {
    renderAutomationApp({
      connectors: [
        {
          id: "google-primary",
          provider: "google",
          name: "Google Workspace",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          base_url: "https://www.googleapis.com"
        }
      ],
      httpPresets: [
        {
          preset_id: "gmail_list_messages_http",
          provider_id: "google",
          service: "gmail",
          operation: "list messages",
          label: "List emails",
          description: "List Gmail messages",
          http_method: "GET",
          endpoint_path_template: "/gmail/v1/users/me/messages",
          payload_template: "{}",
          query_params: {},
          required_scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          input_schema: []
        }
      ]
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automation-canvas-insert-0-button") as HTMLElement);
    fireEvent.click(document.querySelector("#add-step-type-outbound_request") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#add-step-http-connector-input")).toBeInTheDocument();
    });

    expect(document.querySelector("#add-step-http-connector-label")).toHaveTextContent("Connectors");
    expect(screen.getByLabelText("Destination URL")).toBeInTheDocument();
    expect(screen.getByLabelText("Payload template")).toBeInTheDocument();

    const connectorSelect = document.querySelector("#add-step-http-connector-input") as HTMLSelectElement;
    fireEvent.change(connectorSelect, { target: { value: "google-primary" } });

    const presetSelect = (await waitFor(() => {
      const element = document.querySelector("#add-step-http-action-input") as HTMLSelectElement | null;
      expect(element).not.toBeNull();
      return element as HTMLSelectElement;
    })) as HTMLSelectElement;
    expect(within(presetSelect).getByRole("option", { name: "gmail - list messages" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByLabelText("Destination URL")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Payload template")).not.toBeInTheDocument();
    });
  });

  it("shows grouped Google connector actions and dynamic inputs in the add-step modal", async () => {
    renderAutomationApp({
      connectors: [
        {
          id: "google-primary",
          provider: "google",
          name: "Google Workspace",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/spreadsheets"],
          base_url: "https://www.googleapis.com"
        }
      ]
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automation-canvas-insert-0-button") as HTMLElement);
    fireEvent.click(screen.getByRole("button", { name: /Connector activity/i }));
    fireEvent.change(screen.getByLabelText("Saved connector"), { target: { value: "google-primary" } });

    expect((await screen.findAllByText("GMAIL")).length).toBeGreaterThan(0);
    expect(screen.getByText("READ")).toBeInTheDocument();
    expect(screen.getAllByText("WRITE").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /send email/i }));

    expect(await screen.findByLabelText("Recipients")).toBeInTheDocument();
    expect(screen.getByLabelText("Subject")).toBeInTheDocument();
    expect(screen.getByLabelText("Body")).toBeInTheDocument();
    expect(screen.getByText(/message_id/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /update range/i }));
    expect(await screen.findByLabelText("Spreadsheet ID")).toBeInTheDocument();
    expect(screen.getByLabelText("A1 range")).toBeInTheDocument();
    expect(screen.getByLabelText("Values payload")).toBeInTheDocument();
  });

  it("validates required connector action inputs before save", async () => {
    renderAutomationApp({
      connectors: [
        {
          id: "google-primary",
          provider: "google",
          name: "Google Workspace",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["https://www.googleapis.com/auth/gmail.send"],
          base_url: "https://www.googleapis.com"
        }
      ]
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automation-canvas-insert-0-button") as HTMLElement);
    fireEvent.click(screen.getByRole("button", { name: /Connector activity/i }));
    fireEvent.change(screen.getByLabelText("Saved connector"), { target: { value: "google-primary" } });
    fireEvent.click(screen.getByRole("button", { name: /send email/i }));
    fireEvent.click(document.querySelector("#add-step-modal-confirm") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    expect(await screen.findByText(/requires 'Recipients' for Send email/i)).toBeInTheDocument();
  });

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

  it("collapses and expands the workflow settings bar", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    const toggle = container.querySelector("#automations-workflow-bar-collapse-toggle") as HTMLButtonElement;
    const symbol = container.querySelector("#automations-workflow-bar-collapse-symbol") as HTMLElement;
    const workflowBarBody = container.querySelector("#automations-workflow-bar-body") as HTMLElement;

    expect(workflowBarBody.hidden).toBe(false);
    expect(workflowBarBody).not.toHaveClass("automation-workflow-bar__body--hidden");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(symbol).toHaveTextContent("-");

    fireEvent.click(toggle);
    expect(workflowBarBody.hidden).toBe(true);
    expect(workflowBarBody).toHaveClass("automation-workflow-bar__body--hidden");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(symbol).toHaveTextContent("+");

    fireEvent.click(toggle);
    expect(workflowBarBody.hidden).toBe(false);
    expect(workflowBarBody).not.toHaveClass("automation-workflow-bar__body--hidden");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(symbol).toHaveTextContent("-");
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
      expect(document.querySelector("#log-step-form-root")).toBeInTheDocument();
    });
  });

  it("adds HTTP response mappings from a sample JSON response", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#mock-select-step-node-step-http") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-step-step-http-actions-button") as HTMLElement);
    await waitFor(() => {
      expect(document.querySelector("#automations-node-menu")).toBeInTheDocument();
    });
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    const loadSampleButton = await screen.findByRole("button", { name: "Load sample response" });
    fireEvent.click(loadSampleButton);

    await waitFor(() => {
      expect(requestLog.some((entry) => entry.path === "/api/v1/apis/test-delivery")).toBe(true);
    });

    const countNodeButton = await screen.findByRole("button", { name: /count/i });
    fireEvent.click(countNodeButton);

    expect(await screen.findByDisplayValue("count")).toBeInTheDocument();
    expect(screen.getByText("data.guides.count")).toBeInTheDocument();
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
    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      const patchRequest = requestLog.find((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequest).toBeDefined();
      expect((patchRequest?.body?.steps as Array<{ id: string }>).map((step) => step.id)).toEqual(["step-http", "step-log"]);
    });
  });

  it("keeps workflow identity outside trigger settings and shows test output only on demand", async () => {
    const { container } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByLabelText("Automation name")).toBeInTheDocument();
    });

    expect(container.querySelector("#automations-test-results-drawer")).not.toBeInTheDocument();

    fireEvent.click(document.querySelector("#mock-select-trigger-node") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-trigger-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    const drawer = document.querySelector("#automations-editor-drawer") as HTMLElement;
    expect(within(drawer).queryByLabelText("Automation name")).not.toBeInTheDocument();
    expect(within(drawer).getByText("Manual")).toBeInTheDocument();
    expect(within(drawer).getByText("Schedule")).toBeInTheDocument();
    fireEvent.click(within(drawer).getByRole("radio", { name: /schedule/i }));
    expect(within(drawer).getByRole("button", { name: "Select time" })).toBeInTheDocument();
    fireEvent.click(within(drawer).getByRole("button", { name: "Close editor drawer" }));

    fireEvent.click(screen.getByRole("button", { name: "Run now" }));

    await waitFor(() => {
      expect(document.querySelector("#automations-test-results-drawer")).toBeInTheDocument();
      expect(
        document.querySelector("#automations-validation-results") ||
        document.querySelector("#automations-run-results")
      ).toBeInTheDocument();
    });
  });

  it("loads inbound API options and blocks stale inbound trigger selections", async () => {
    const { requestLog } = renderAutomationApp({
      initialAutomation: {
        trigger_type: "inbound_api",
        trigger_config: { inbound_api_id: "missing-api" }
      }
    });

    await waitFor(() => {
      expect(requestLog.some((entry) => entry.path === "/api/v1/inbound" && entry.method === "GET")).toBe(true);
    });

    fireEvent.click(document.querySelector("#mock-select-trigger-node") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-trigger-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    const drawer = document.querySelector("#automations-editor-drawer") as HTMLElement;
    expect(within(drawer).getByText("The selected inbound API is no longer available. Choose another API to continue.")).toBeInTheDocument();

    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText("Selected inbound API is unavailable. Choose a currently configured inbound API.")).toBeInTheDocument();
    });
  });

  it("stores schedule time from custom picker controls", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#mock-select-trigger-node") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-trigger-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automations-trigger-drawer-trigger-type-option-schedule") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-trigger-drawer-trigger-schedule-input") as HTMLElement);
    fireEvent.change(document.querySelector("#automations-trigger-drawer-trigger-schedule-hour-input") as HTMLElement, { target: { value: "1" } });
    fireEvent.change(document.querySelector("#automations-trigger-drawer-trigger-schedule-minute-input") as HTMLElement, { target: { value: "07" } });
    fireEvent.change(document.querySelector("#automations-trigger-drawer-trigger-schedule-period-input") as HTMLElement, { target: { value: "PM" } });

    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      const patchRequest = requestLog.find((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequest).toBeDefined();
      expect(patchRequest?.body?.trigger_config).toEqual({ schedule_time: "13:07" });
    });
  });

  it("loads script options and applies sample input in the step drawer", async () => {
    const { container } = renderAutomationApp({
      initialAutomation: {
        steps: [
          {
            id: "step-script",
            type: "script",
            name: "Transform feed",
            config: {
              script_id: "script-change-delimiter",
              script_input_template: ""
            }
          }
        ]
      }
    });

    await waitFor(() => {
      expect(container.querySelector("#automation-canvas-node-step-step-script-title")).toHaveTextContent("Transform feed");
    });

    fireEvent.click(document.querySelector("#mock-select-step-node-step-script") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-step-step-script-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    const scriptSelect = await screen.findByLabelText("Script");
    expect(scriptSelect).toHaveValue("script-change-delimiter");

    fireEvent.click(screen.getByRole("button", { name: "Use sample input" }));

    const scriptInput = screen.getByLabelText("Script input") as HTMLTextAreaElement;
    expect(scriptInput.value).toContain("\"from\": \",\"");
    expect(scriptInput.value).toContain("\"to\": \"|\"");
  });

  it("allows SMTP triggers without filters and persists recipient-only filters", async () => {
    const { requestLog } = renderAutomationApp();

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#mock-select-trigger-node") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-trigger-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#automations-trigger-drawer-trigger-type-option-smtp_email") as HTMLElement);
    expect(screen.getByText("Leave both filters blank to trigger on any inbound email. Matching is exact for now.")).toBeInTheDocument();

    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      const patchRequest = requestLog.find((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequest?.body?.trigger_type).toBe("smtp_email");
      expect(patchRequest?.body?.trigger_config).toEqual({});
    });

    fireEvent.change(document.querySelector("#automations-trigger-drawer-trigger-smtp-recipient-input") as HTMLElement, {
      target: { value: "alerts@example.com" }
    });
    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      const patchRequests = requestLog.filter((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH");
      expect(patchRequests.at(-1)?.body?.trigger_config).toEqual({ smtp_recipient_email: "alerts@example.com" });
    });
  });

  it("renders SMTP tool step fields and blocks invalid relay ports before save", async () => {
    const { requestLog } = renderAutomationApp({
      initialAutomation: {
        steps: [
          {
            id: "step-smtp",
            type: "tool",
            name: "Send email",
            config: {
              tool_id: "smtp",
              tool_inputs: {
                relay_host: "smtp.example.com",
                relay_port: "abc",
                relay_security: "starttls",
                relay_username: "mailer",
                relay_password: "secret",
                from_address: "{{payload.mail_from}}",
                to: "alerts@example.com",
                subject: "{{payload.subject}}",
                body: "{{payload.body}}"
              }
            }
          }
        ]
      }
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Daily ingest")).toBeInTheDocument();
    });

    fireEvent.click(document.querySelector("#mock-select-step-node-step-smtp") as HTMLElement);
    fireEvent.click(document.querySelector("#automation-canvas-node-step-step-smtp-actions-button") as HTMLElement);
    fireEvent.click(document.querySelector("#automations-node-menu-edit") as HTMLElement);

    await waitFor(() => {
      expect(document.querySelector("#automations-editor-drawer")).toBeInTheDocument();
    });

    expect(document.querySelector("#automations-step-tool-input-relay_host-input")).toHaveValue("smtp.example.com");
    expect(document.querySelector("#automations-step-tool-input-relay_password-input")).toHaveAttribute("type", "password");
    expect(screen.getByText(/Supports template variables in From, To, Subject, and Body/)).toBeInTheDocument();

    fireEvent.click(document.querySelector("#automations-save-button") as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText("Step 1 requires a numeric 'Relay Port' for SMTP.")).toBeInTheDocument();
    });
    expect(requestLog.some((entry) => entry.path === `/api/v1/automations/${dailyIngest.id}` && entry.method === "PATCH")).toBe(false);
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

  it("keeps the legacy APIs automation route redirecting through the page registry", () => {
    const pageRegistry = JSON.parse(readFileSync(resolve(process.cwd(), "page-registry.json"), "utf8"));
    const automationRedirect = pageRegistry.pages.find((entry: { routePath: string }) => entry.routePath === "/apis/automation.html");

    expect(automationRedirect).toMatchObject({
      routePath: "/apis/automation.html",
      serveMode: "redirect",
      canonicalRoutePath: "/automations/library.html",
      redirectTarget: "/automations/library.html"
    });
  });


});
