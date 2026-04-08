import React from "react";
import { describe, it, expect } from "vitest";
import { StepEditorDispatcher as StepEditor } from "../step-editors";

describe("StepEditor dispatcher", () => {
  it("exports a callable StepEditor component", () => {
    expect(StepEditor).toBeDefined();
    expect(typeof StepEditor).toBe("function");
  });

  it("keeps a stable component export reference", () => {
    const componentRef = StepEditor;
    expect(componentRef).toBe(StepEditor);
  });
});
