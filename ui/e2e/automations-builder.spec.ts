import { expect, test } from "@playwright/test";
import { acceptDialogs } from "./support/core.ts";
import {
  buildAutomationRun,
  createAutomationSuiteState,
  installAutomationSuiteRoutes
} from "./support/automations-scripts";

test("creates a new automation draft, adds a connector activity step, edits it, and saves", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");

  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("");
  await page.locator("#automations-validate-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Name is required.");
  await expect(page.locator("#automations-test-results-drawer")).toBeVisible();
  await expect(page.locator("#automations-validation-summary")).toContainText("validation issue");
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-workflow-name-input").fill("Customer notification");
  await page.locator("#automations-workflow-description-input").fill("Sends an email when a customer event occurs.");

  await page.locator("#automations-canvas-insert-0-button").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();
  await page.locator("#add-step-type-connector_activity").click();
  await page.locator("#add-step-name-input").fill("Send customer email");
  await page.locator("#add-step-connector-activity-connector-input").selectOption("google-primary");
  await expect(page.locator("#add-step-connector-activity-required-scopes")).toContainText("gmail.send");
  await page.locator("#add-step-connector-activity-activity-card-gmail-send-email").click();
  await page.locator("#add-step-connector-activity-input-to").fill("customer@example.com");
  await page.locator("#add-step-connector-activity-input-subject").fill("Your order shipped");
  await page.locator("#add-step-connector-activity-input-body").fill("Hello from Malcom");
  await page.locator("#add-step-modal-confirm").click();

  await expect(page.locator('[id^="step-node-draft-step-"]')).toHaveCount(1);
  await page.locator('[id^="step-node-draft-step-"]').dblclick();
  await expect(page.locator("#automations-editor-drawer")).toBeVisible();
  await page.locator("#automations-step-name-input").fill("Notify customer");
  await expect(page.locator("#automation-canvas-node-step-draft-step-1-title")).toHaveText("Notify customer");

  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation created.");
  await expect(page).toHaveURL(/builder\.html\?id=/);
});

test("edits an existing automation, validates, runs, and deletes it", async ({ page }) => {
  const state = createAutomationSuiteState();
  state.runResponses["automation-order-sync"] = buildAutomationRun(state, "automation-order-sync", "run-order-sync");
  await installAutomationSuiteRoutes(page, state);
  await acceptDialogs(page);

  await page.goto("/automations/builder.html?id=automation-order-sync");

  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Order sync");
  await expect(page.locator("#automation-canvas-node-step-step-fetch-order-title")).toHaveText("Fetch order");

  await page.locator("#automation-canvas-node-trigger").dblclick();
  await expect(page.locator("#automations-editor-drawer")).toBeVisible();
  await page.locator("#automations-trigger-drawer-trigger-schedule-input").click();
  await page.locator("#automations-trigger-drawer-trigger-schedule-hour-input").selectOption("10");
  await page.locator("#automations-trigger-drawer-trigger-schedule-minute-input").selectOption("45");
  await page.locator("#automations-trigger-drawer-trigger-schedule-period-input").selectOption("AM");
  await expect(page.locator("#automations-trigger-drawer-trigger-schedule-input")).toHaveText("10:45 AM");
  await page.locator("#automations-editor-drawer-close").click();

  await page.locator("#automation-canvas-node-step-step-fetch-order").dblclick();
  await expect(page.locator("#automations-editor-drawer")).toBeVisible();
  await page.locator("#automations-step-http-url-input").fill("https://api.example.com/orders/99");
  await page.locator("#automations-step-http-sample-response-button").click();
  await expect(page.locator("#automations-step-http-json-tree-panel")).toBeVisible();
  await page.locator('#automations-step-http-select-data').click();
  await page.locator('[id="automations-step-http-select-data.customer"]').click();
  await expect(page.locator("#automations-step-http-mapping-row-1")).toBeVisible();
  await expect(page.locator("#automations-step-http-mapping-path-1")).toHaveText("data.customer");
  await page.locator("#automations-editor-drawer-close").click();

  await page.locator("#automations-validate-button").click();
  await expect(page.locator("#automations-test-results-drawer")).toBeVisible();
  await expect(page.locator("#automations-validation-summary")).toContainText("No validation issues detected");
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-run-button").click();
  await expect(page.locator("#automations-test-results-drawer")).toBeVisible();
  await expect(page.locator("#automations-test-results-title")).toHaveText("Test run results");
  await expect(page.locator("#automations-run-results-status-value")).toHaveText("completed");
  await expect(page.locator("#automations-run-step-step-fetch-order")).toBeVisible();
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-delete-button").click();
  await expect(page.locator("#automations-delete-dialog")).toBeVisible();
  await page.locator("#automations-delete-dialog-confirm").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation deleted.");
  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Weekly summary");
});
