import { expect, test } from "@playwright/test";
import { createAutomationSuiteState, installAutomationSuiteRoutes } from "./support/automations-scripts";

test("adds a Write step and persists storage options", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");

  // Fill required workflow name
  await page.locator("#automations-workflow-name-input").fill("Write step test");

  // Open add step modal and pick the Write (log) step
  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();
  await page.locator("#add-step-type-log").click();

  // Configure storage: choose CSV, set target and enable new-file
  await page.locator("#log-step-storage-type-input").selectOption("csv");
  await page.locator("#log-step-target-input").fill("/tmp/orders.csv");
  await page.locator("#log-step-new-file-input").check();

  // Optional custom step name
  await page.locator("#add-step-name-input").fill("Write orders to CSV");

  // Confirm add
  await page.locator("#add-step-modal-confirm").click();

  // There should be a draft node on the canvas
  await expect(page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]')).toHaveCount(1);

  // Save the automation (POST creates it in the test state)
  await page.locator("#automations-save-button").click();

  // Ensure the automation was created in the mocked state and the step config contains our storage keys
  const created = state.automations[0];
  expect(created).toBeDefined();
  expect(created.steps.length).toBeGreaterThan(0);
  const step = created.steps.find((s) => s.type === "log");
  expect(step).toBeDefined();
  expect((step as any).config.storage_type).toBe("csv");
  expect((step as any).config.storage_target).toBe("/tmp/orders.csv");
  expect(Boolean((step as any).config.storage_new_file)).toBe(true);
});
