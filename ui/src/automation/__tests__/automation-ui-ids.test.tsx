import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AutomationLibraryApp } from "../library";
import { TriggerSettingsForm } from "../trigger-settings-form";
import { ToolStepFields } from "../tool-step-fields";
import { ConnectorActivityStepForm } from "../step-modals/connector-activity-step-form";
import type { AutomationStep, ToolManifestEntry } from "../types";

const requestJsonMock = vi.hoisted(() => vi.fn());

vi.mock("../../lib/request", () => ({
  requestJson: requestJsonMock,
  normalizeRequestError: (_error: unknown, fallbackMessage: string) => ({ message: fallbackMessage })
}));

beforeEach(() => {
  document.body.innerHTML = '<button id="automations-create-button" type="button">Create</button>';
  requestJsonMock.mockReset();
});

describe("automation UI ids", () => {
  it("renders deterministic ids for schedule and inbound trigger controls", () => {
    const onPatch = vi.fn();

    const { rerender } = render(
      <TriggerSettingsForm
        idPrefix="automation-trigger"
        value={{
          name: "Daily ingest",
          description: "Pull the current feed.",
          enabled: true,
          trigger_type: "schedule",
          trigger_config: { schedule_time: "08:30" }
        }}
        onPatch={onPatch}
      />
    );

    expect(document.querySelector("#automation-trigger-enabled-thumb")).toBeInTheDocument();

    const scheduleButton = document.querySelector<HTMLButtonElement>("#automation-trigger-trigger-schedule-input");
    expect(scheduleButton).not.toBeNull();
    fireEvent.click(scheduleButton!);

    expect(document.querySelector("#automation-trigger-trigger-schedule-picker-title")).toHaveTextContent("Schedule time picker");
    expect(document.querySelector("#automation-trigger-trigger-schedule-hour-option-8")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-schedule-minute-option-30")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-schedule-period-option-am")).toBeInTheDocument();

    rerender(
      <TriggerSettingsForm
        idPrefix="automation-trigger"
        value={{
          name: "Inbound orders",
          description: "",
          enabled: true,
          trigger_type: "inbound_api",
          trigger_config: { inbound_api_id: "orders-api" }
        }}
        onPatch={onPatch}
        inboundApiOptions={[{ id: "orders-api", name: "Orders API" }]}
      />
    );

    expect(document.querySelector("#automation-trigger-trigger-api-option-empty")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-api-option-orders-api")).toHaveTextContent("Orders API");
  });

  it("renders deterministic ids for tool input options and outputs", () => {
    const step: AutomationStep = {
      id: "step-tool",
      type: "tool",
      name: "SMTP dispatch",
      config: {
        tool_id: "smtp",
        tool_inputs: {
          priority: "High priority"
        }
      }
    };

    const toolsManifest: ToolManifestEntry[] = [
      {
        id: "smtp",
        name: "SMTP",
        description: "Send email through the SMTP tool.",
        pageHref: "/tools/smtp.html",
        inputs: [
          { key: "body", label: "Body", type: "text", required: true },
          { key: "priority", label: "Priority", type: "select", required: false, options: ["Normal", "High priority"] },
          { key: "relay_password", label: "Relay password", type: "string", required: false }
        ],
        outputs: [{ key: "message_id", label: "Message ID", type: "string" }]
      }
    ];

    render(<ToolStepFields idPrefix="tool-step" step={step} toolsManifest={toolsManifest} onChange={vi.fn()} />);

    expect(document.querySelector("#tool-step-tool-id-option-empty")).toBeInTheDocument();
    expect(document.querySelector("#tool-step-tool-id-option-smtp")).toHaveTextContent("SMTP");
    expect(document.querySelector("#tool-step-tool-input-priority-option-high-priority")).toHaveTextContent("High priority");
    expect(document.querySelector("#tool-step-tool-output-message_id-key")).toHaveTextContent("{{steps.<step_name>.message_id}}");
    expect(document.querySelector("#tool-step-tool-output-message_id-description")).toHaveTextContent("Message ID");
  });

  it("renders deterministic ids for the Google app selector in connector actions", () => {
    const step: AutomationStep = {
      id: "step-google",
      type: "api",
      name: "Google step",
      config: {
        connector_id: "google-primary",
        activity_id: "",
        activity_inputs: {}
      }
    };

    render(
      <ConnectorActivityStepForm
        idPrefix="connector-step"
        draft={step}
        connectors={[
          {
            id: "google-primary",
            provider: "google",
            name: "Google Primary",
            status: "connected",
            auth_type: "oauth2"
          }
        ]}
        activityCatalog={[
          {
            provider_id: "google",
            activity_id: "gmail_list_messages",
            service: "gmail",
            operation_type: "read",
            label: "List emails",
            description: "List Gmail messages.",
            required_scopes: [],
            input_schema: [],
            output_schema: [],
            execution: {}
          },
          {
            provider_id: "google",
            activity_id: "calendar_list_events",
            service: "calendar",
            operation_type: "read",
            label: "List events",
            description: "List calendar events.",
            required_scopes: [],
            input_schema: [],
            output_schema: [],
            execution: {}
          }
        ]}
        onChange={vi.fn()}
      />
    );

    expect(document.querySelector("#connector-step-service-field")).toBeInTheDocument();
    expect(document.querySelector("#connector-step-service-label")).toHaveTextContent("Google app");
    expect(document.querySelector("#connector-step-service-input")).toBeInTheDocument();
  });

  it("renders deterministic ids for automation library title rows and detail stats", async () => {
    requestJsonMock.mockImplementation(async (path: string) => {
      if (path === "/api/v1/automations") {
        return [
          {
            id: "automation-daily-ingest",
            name: "Daily ingest",
            description: "Pull the current feed and forward it.",
            enabled: true,
            trigger_type: "schedule",
            step_count: 2,
            created_at: "2026-03-15T08:00:00.000Z",
            updated_at: "2026-03-15T08:00:00.000Z",
            last_run_at: "2026-03-15T08:30:00.000Z",
            next_run_at: "2026-03-16T08:30:00.000Z"
          }
        ];
      }

      if (path === "/api/v1/runtime/status") {
        return {
          active: true,
          last_tick_started_at: "2026-03-15T08:30:00.000Z",
          last_tick_finished_at: "2026-03-15T08:31:00.000Z",
          last_error: null,
          job_count: 3
        };
      }

      throw new Error(`Unexpected path: ${path}`);
    });

    render(<AutomationLibraryApp />);

    await waitFor(() => {
      expect(document.querySelector("#automations-library-item-automation-daily-ingest")).toBeInTheDocument();
    });

    expect(document.querySelector("#automations-library-list-title-row")).toBeInTheDocument();
    expect(document.querySelector("#automations-library-runtime-title-row")).toBeInTheDocument();

    const automationCard = document.querySelector<HTMLButtonElement>("#automations-library-item-automation-daily-ingest");
    expect(automationCard).not.toBeNull();
    fireEvent.click(automationCard!);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    expect(document.querySelector("#automations-library-detail-stat-trigger-label")).toHaveTextContent("Trigger");
    expect(document.querySelector("#automations-library-detail-stat-trigger-value")).toHaveTextContent("Schedule");
    expect(document.querySelector("#automations-library-detail-stat-steps-value")).toHaveTextContent("2");
    expect(document.querySelector("#automations-library-detail-modal-close")).toHaveAttribute("aria-label", "Close automation details");
  });
});
