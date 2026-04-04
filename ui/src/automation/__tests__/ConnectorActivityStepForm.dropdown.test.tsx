import { render, screen, waitFor } from "@testing-library/react";
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

  it("loads GitHub repositories and shows owner/repository dropdowns", async () => {
    window.Malcom = {
      requestJson: vi.fn().mockResolvedValue({
        repositories: [
          {
            id: 1,
            name: "malcom",
            full_name: "openai/malcom",
            owner: "openai",
            private: true,
            default_branch: "main",
          },
        ],
      }),
    };

    const step: AutomationStep = {
      id: "step-3",
      type: "connector_activity",
      name: "GitHub archive",
      config: {
        connector_id: "github-1",
        activity_id: "download_repo_archive",
        activity_inputs: {},
      },
    };

    render(
      <ConnectorActivityStepForm
        idPrefix="test-connector"
        draft={step}
        connectors={buildWorkflowBuilderConnectorOptions([
          { id: "github-1", provider: "github", name: "GitHub Primary", status: "connected", auth_type: "bearer", scopes: ["repo"] },
        ]) as any}
        activityCatalog={[
          {
            provider_id: "github",
            activity_id: "download_repo_archive",
            service: "repos",
            operation_type: "read",
            label: "Download repository archive",
            description: "Download a repository archive.",
            required_scopes: ["repo"],
            input_schema: [
              { key: "owner", label: "Repository owner", type: "string", required: true },
              { key: "repo", label: "Repository name", type: "string", required: true },
            ],
            output_schema: [],
            execution: {},
          },
        ]}
        onChange={vi.fn()}
      />
    );

    await waitFor(() => {
      const ownerOption = document.querySelector("#test-connector-input-owner option[value='openai']");
      const repoOption = document.querySelector("#test-connector-input-repo option[value='openai/malcom']");
      expect(ownerOption).not.toBeNull();
      expect(repoOption).not.toBeNull();
    });
  });
});
