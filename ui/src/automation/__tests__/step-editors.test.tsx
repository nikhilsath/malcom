import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StepEditor from "../step-editors";

const baseProps: any = {
  currentAutomation: { steps: [] },
  builderMetadata: { storage_types: [], log_column_types: [], storage_locations: [], http_methods: [], repo_checkouts: [] },
  connectors: [],
  supportDataLoading: false,
  supportDataError: null,
  reloadSupportData: () => {},
  httpPresets: [],
  scripts: [],
  scriptLanguages: [],
  toolsManifest: [],
  drawerDataFlowTokens: [],
  updateDrawerStep: () => {},
  removeStepById: () => {},
  advancedLabelOpen: false,
  setAdvancedLabelOpen: () => {}
};

describe("StepEditor dispatcher", () => {
  it("renders log/storage editor ids for log step", () => {
    const step = { id: "step-log", type: "log", name: "Log", config: { message: "ok" } };
    render(<StepEditor step={step} {...baseProps} />);
    expect(document.getElementById("automations-step-modal-form")).not.toBeNull();
  });

  it("renders condition editor inputs for condition step", () => {
    const step = { id: "step-cond", type: "condition", name: "Cond", config: { expression: "true" } };
    const currentAutomation = { steps: [step, { id: "other", type: "log", name: "Other" }] };
    render(<StepEditor step={step} currentAutomation={currentAutomation} {...baseProps} />);
    expect(document.getElementById("automations-step-condition-expression-input")).not.toBeNull();
  });
});
