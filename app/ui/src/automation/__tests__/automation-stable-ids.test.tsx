import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AutomationLibraryApp } from "../library";
import { ToolStepFields } from "../tool-step-fields";
import { TriggerSettingsForm } from "../trigger-settings-form";
import type { AutomationStep, ToolManifestEntry } from "../types";

const triggerTypeOptions = [
  { value: "manual", label: "Manual", description: "Run the automation only when an operator starts it." },
  { value: "schedule", label: "Schedule", description: "Start automatically at a set time each day." },
  { value: "inbound_api", label: "Inbound API", description: "Start when an inbound API endpoint receives an event." },
  { value: "smtp_email", label: "SMTP email", description: "Start when incoming email matches your filters." }
];

const libraryAutomations = [
  {
    id: "automation-order-intake",
    name: "Order intake",
    description: "Review new orders before dispatch.",
    enabled: true,
    trigger_type: "inbound_api",
    step_count: 3,
    created_at: "2026-03-18T09:00:00.000Z",
    updated_at: "2026-03-19T09:00:00.000Z",
    last_run_at: "2026-03-20T11:00:00.000Z",
    next_run_at: null
  }
];

const runtimeStatus = {
  active: true,
  last_tick_started_at: "2026-03-20T10:59:00.000Z",
  last_tick_finished_at: "2026-03-20T11:00:00.000Z",
  last_error: null,
  job_count: 4
};

beforeEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = '<button id="automations-create-button" type="button">Create</button>';
  window.Malcom = {
    requestJson: vi.fn(async (path: string) => {
      if (path === "/api/v1/runtime/status") {
        return runtimeStatus;
      }
      return libraryAutomations;
    })
  };
});

describe("automation stable ids", () => {
  it("renders trigger settings ids for the enabled switch thumb", () => {
    render(
      <TriggerSettingsForm
        idPrefix="automation-trigger"
        triggerTypeOptions={triggerTypeOptions}
        value={{
          name: "Order intake",
          description: "Review new orders before dispatch.",
          enabled: true,
          trigger_type: "manual",
          trigger_config: {}
        }}
        onPatch={() => {}}
      />
    );

    expect(document.querySelector("#automation-trigger-enabled-thumb")).toBeInTheDocument();
  });

  it("renders deterministic ids for tool output keys and descriptions", () => {
    const step: AutomationStep = {
      id: "step-smtp",
      type: "tool",
      name: "SMTP step",
      config: {
        tool_id: "smtp",
        tool_inputs: {}
      }
    };

    const toolsManifest: ToolManifestEntry[] = [
      {
        id: "smtp",
        name: "SMTP",
        description: "Send email",
        pageHref: "/tools/smtp.html",
        inputs: [],
        outputs: [{ key: "message_id", label: "Message ID", type: "string" }]
      }
    ];

    render(<ToolStepFields idPrefix="builder-step" step={step} toolsManifest={toolsManifest} onChange={() => {}} />);

    expect(document.querySelector("#builder-step-tool-output-message_id-key")).toBeInTheDocument();
    expect(document.querySelector("#builder-step-tool-output-message_id-description")).toHaveTextContent("Message ID");
  });

  it("renders library ids for title rows and detail stats", async () => {
    render(<AutomationLibraryApp />);

    expect(document.querySelector("#automations-library-list-title-row")).toBeInTheDocument();
    expect(document.querySelector("#automations-library-runtime-title-row")).toBeInTheDocument();

    await waitFor(() => {
      expect(document.querySelector("#automations-library-item-automation-order-intake")).toBeInTheDocument();
    });

    const automationButton = document.querySelector<HTMLButtonElement>("#automations-library-item-automation-order-intake");
    expect(automationButton).not.toBeNull();
    fireEvent.click(automationButton!);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    expect(document.querySelector("#automations-library-detail-stat-trigger-label")).toHaveTextContent("Trigger");
    expect(document.querySelector("#automations-library-detail-stat-trigger-value")).toHaveTextContent("Inbound API");
    expect(document.querySelector("#automations-library-detail-stat-steps-label")).toHaveTextContent("Steps");
    expect(document.querySelector("#automations-library-detail-stat-steps-value")).toHaveTextContent("3");
    expect(document.querySelector("#automations-library-detail-stat-lastrun-label")).toHaveTextContent("Last run");
    expect(document.querySelector("#automations-library-detail-stat-nextrun-label")).toHaveTextContent("Next run");
  });
});
