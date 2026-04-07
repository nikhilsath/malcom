import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { TriggerSettingsForm } from "../trigger-settings-form";

const baseProps = {
  idPrefix: "test",
  triggerTypeOptions: [
    { label: "GitHub", value: "github", description: "GitHub events" },
    { label: "Schedule", value: "schedule", description: "Daily" }
  ],
  value: {
    name: "Test",
    description: "desc",
    enabled: true,
    trigger_type: "github",
    trigger_config: {
      github_owner: "",
      github_repo: "",
      github_events: [],
      github_secret: ""
    }
  },
  onPatch: () => {},
  showWorkflowFields: true,
  showEnabledField: true
} as any;

describe("TriggerSettingsForm - GitHub fields", () => {
  test("renders GitHub specific inputs when trigger_type is 'github'", () => {
    render(<TriggerSettingsForm {...baseProps} />);

    expect(screen.getByLabelText(/Repository owner/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Repository name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Events/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Webhook secret/i)).toBeInTheDocument();
  });
});
