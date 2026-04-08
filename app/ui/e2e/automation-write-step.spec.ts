import { expect, test } from "@playwright/test";
import {
  createAutomationSuiteState,
  installAutomationSuiteRoutes,
} from "./support/automations-scripts";

test("add-step modal shows Write (not Log) in the step type grid", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("Write test automation");

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();

  // The card for the log/write step type must show the label "Write"
  await expect(page.locator("#add-step-type-log")).toContainText("Write");
  // It must not show the old "Log" label as the card title
  const cardText = await page.locator("#add-step-type-log").textContent();
  expect(cardText).not.toMatch(/^Log$/);
});

test("write step non-table mode surfaces storage_type, target, and new_file fields", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("Write test automation");

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();

  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Write CSV output");

  // Storage type defaults to table (DB table)
  await expect(page.locator("#log-step-storage-type-input")).toBeVisible();
  await expect(page.locator("#log-step-storage-type-input")).toHaveValue("table");

  // File-oriented inputs are hidden for table mode
  await expect(page.locator("#log-step-target-input")).toHaveCount(0);
  await expect(page.locator("#log-step-new-file-input")).toHaveCount(0);

  // Switch to JSON type — target and new_file fields should appear
  await page.locator("#log-step-storage-type-input").selectOption("json");
  await expect(page.locator("#log-step-target-input")).toBeVisible();
  await expect(page.locator("#log-step-new-file-input")).toBeVisible();
  await expect(page.locator("#log-step-new-file-input")).not.toBeChecked();

  // Can toggle on
  await page.locator("#log-step-new-file-input").click();
  await expect(page.locator("#log-step-new-file-input")).toBeChecked();
});

test("write step file mode saves step with correct config payload", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  // Capture the automation save request body
  let savedSteps: Array<Record<string, unknown>> = [];
  await page.route("**/api/v1/automations**", async (route) => {
    if (["POST", "PATCH"].includes(route.request().method())) {
      const body = (route.request().postDataJSON?.() ?? {}) as Record<string, unknown>;
      savedSteps = (body?.steps as Array<Record<string, unknown>>) || [];
    }
    await route.fallback();
  });

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("File write automation");

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();

  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Export CSV");

  // Select csv storage type and set target
  await page.locator("#log-step-storage-type-input").selectOption("csv");
  await page.locator("#log-step-target-input").fill("run_events");

  await page.locator("#add-step-modal-confirm").click();

  // A canvas node should appear with the step name
  await expect(page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]')).toHaveCount(1);

  // Save the automation
  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText(/Automation (created|updated)\./);

  // Verify the saved payload includes the storage fields
  expect(savedSteps.length).toBeGreaterThan(0);
  const writeStep = savedSteps.find((s) => s.type === "log") as Record<string, unknown> | undefined;
  expect(writeStep).toBeDefined();
});

test("write step db mode does not include file storage fields", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  let savedSteps: Array<Record<string, unknown>> = [];
  await page.route("**/api/v1/automations**", async (route) => {
    if (["POST", "PATCH"].includes(route.request().method())) {
      const body = (route.request().postDataJSON?.() ?? {}) as Record<string, unknown>;
      savedSteps = (body?.steps as Array<Record<string, unknown>>) || [];
    }
    await route.fallback();
  });

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("DB write automation");

  await page.locator("#automations-guided-item-step-action").click();
  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Write to DB");

  // Default mode is DB/table — file-oriented fields should not appear
  await expect(page.locator("#log-step-storage-type-input")).toHaveValue("table");
  await expect(page.locator("#log-step-target-input")).toHaveCount(0);
  await expect(page.locator("#log-step-new-file-input")).toHaveCount(0);

  await page.locator("#add-step-modal-confirm").click();

  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText(/Automation (created|updated)\./);

  const writeStep = savedSteps.find((s) => s.type === "log") as Record<string, unknown> | undefined;
  expect(writeStep).toBeDefined();
});
