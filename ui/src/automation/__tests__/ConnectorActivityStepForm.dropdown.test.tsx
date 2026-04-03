import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConnectorActivityStepForm } from "../step-modals/connector-activity-step-form";
import type { AutomationStep } from "../types";
import { buildWorkflowBuilderConnectorOptions } from "./fixtures/builder-api-fixtures";

describe("ConnectorActivityStepForm - connector dropdown", () => {
  it("renders empty state when no connectors provided", () => {
    const step: AutomationStep = {
      id: "step-1",
      type: "api",
      name: "API step",
      config: { connector_id: "", activity_id: "", activity_inputs: {} }
    } as AutomationStep;

    render(
      <ConnectorActivityStepForm
        idPrefix="test-connector"
        draft={step}
        connectors={[]}
        activityCatalog={[]}
        onChange={vi.fn()}
      />
    );

    // The select should exist and have only the empty choice
    const select = document.querySelector<HTMLSelectElement>("#test-connector-connector-input");
    expect(select).not.toBeNull();
    expect(select?.options.length).toBeGreaterThanOrEqual(1);
    expect(select?.value).toBe("");
  });

  it("renders connector options when connectors are provided", () => {
    const step: AutomationStep = {
      id: "step-2",
      type: "api",
      name: "API step",
      config: { connector_id: "", activity_id: "", activity_inputs: {} }
    } as AutomationStep;

    render(
      <ConnectorActivityStepForm
        idPrefix="test-connector"
        draft={step}
        connectors={buildWorkflowBuilderConnectorOptions([
          { id: "conn-1", provider: "google", name: "Gmail Work", status: "connected", auth_type: "oauth2", scopes: [] },
        ]) as any}
        activityCatalog={[]}
        onChange={vi.fn()}
      />
    );

    const option = document.querySelector<HTMLSelectElement>("#test-connector-connector-input option[value=\"conn-1\"]");
    expect(option).not.toBeNull();
    expect(option?.textContent).toContain("Gmail Work");
    expect(option?.textContent).toContain("google");
  });
});
