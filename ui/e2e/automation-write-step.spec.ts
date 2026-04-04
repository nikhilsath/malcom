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

test("write step file mode surfaces storage_type, target, and new_file fields", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("Write test automation");

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();

  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Write CSV output");

  // Default write mode should be "Database table" (db)
  await expect(page.locator("#log-step-write-mode-db")).toBeChecked();
  await expect(page.locator("#log-step-write-mode-file")).not.toBeChecked();

  // File storage fields should not be visible in db mode
  await expect(page.locator("#log-step-file-options")).not.toBeVisible();

  // Switch to File mode
  await page.locator("#log-step-write-mode-file").click();
  await expect(page.locator("#log-step-file-options")).toBeVisible();

  // storage_type dropdown should be present and default to csv
  await expect(page.locator("#log-step-storage-type-select")).toBeVisible();
  await expect(page.locator("#log-step-storage-type-select")).toHaveValue("csv");

  // target input should be present and empty
  await expect(page.locator("#log-step-storage-target-input")).toBeVisible();

  // new_file toggle is not shown for csv (only for json)
  await expect(page.locator("#log-step-storage-new-file-toggle")).not.toBeVisible();

  // Switch to JSON type — new_file toggle should appear
  await page.locator("#log-step-storage-type-select").selectOption("json");
  await expect(page.locator("#log-step-storage-new-file-toggle")).toBeVisible();
  // Default: checked (create new file per run)
  await expect(page.locator("#log-step-storage-new-file-toggle")).toBeChecked();

  // Can toggle off (append mode)
  await page.locator("#log-step-storage-new-file-toggle").click();
  await expect(page.locator("#log-step-storage-new-file-toggle")).not.toBeChecked();
});

test("write step file mode saves step with correct config payload", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  // Capture the automation save request body
  let savedSteps: Array<Record<string, unknown>> = [];
  await page.route("**/api/v1/automations", async (route) => {
    if (route.request().method() === "POST") {
      const body = (route.request().postDataJSON?.() ?? {}) as Record<string, unknown>;
      savedSteps = (body?.steps as Array<Record<string, unknown>>) || [];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "new-auto-1", ...body }) });
    } else {
      await route.fallback();
    }
  });

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("File write automation");

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();

  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Export CSV");

  // Switch to file mode
  await page.locator("#log-step-write-mode-file").click();

  // Select csv storage type and set target
  await page.locator("#log-step-storage-type-select").selectOption("csv");
  await page.locator("#log-step-storage-target-input").fill("run_events");

  await page.locator("#add-step-modal-confirm").click();

  // A canvas node should appear with the step name
  await expect(page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]')).toHaveCount(1);

  // Save the automation
  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation created.");

  // Verify the saved payload includes the storage fields
  expect(savedSteps.length).toBeGreaterThan(0);
  const writeStep = savedSteps.find((s) => s.type === "log") as Record<string, unknown> | undefined;
  expect(writeStep).toBeDefined();
  const cfg = writeStep?.config as Record<string, unknown> | undefined;
  expect(cfg?.storage_type).toBe("csv");
  expect(cfg?.storage_target).toBe("run_events");
});

test("write step db mode does not include file storage fields", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  let savedSteps: Array<Record<string, unknown>> = [];
  await page.route("**/api/v1/automations", async (route) => {
    if (route.request().method() === "POST") {
      const body = (route.request().postDataJSON?.() ?? {}) as Record<string, unknown>;
      savedSteps = (body?.steps as Array<Record<string, unknown>>) || [];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "new-auto-2", ...body }) });
    } else {
      await route.fallback();
    }
  });

  await page.goto("/automations/builder.html?new=true");
  await page.locator("#automations-workflow-name-input").fill("DB write automation");

  await page.locator("#automations-guided-item-step-action").click();
  await page.locator("#add-step-type-log").click();
  await page.locator("#add-step-name-input").fill("Write to DB");

  // Default mode is DB — file options should not appear
  await expect(page.locator("#log-step-write-mode-db")).toBeChecked();
  await expect(page.locator("#log-step-file-options")).not.toBeVisible();

  await page.locator("#add-step-modal-confirm").click();

  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation created.");

  const writeStep = savedSteps.find((s) => s.type === "log") as Record<string, unknown> | undefined;
  expect(writeStep).toBeDefined();
  const cfg = writeStep?.config as Record<string, unknown> | undefined;
  expect(cfg?.storage_type).toBeFalsy();
});
