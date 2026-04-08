import { expect, test } from "@playwright/test";
import { createAutomationSuiteState, installAutomationSuiteRoutes } from "./support/automations-scripts";

test("shows automation overview metrics and opens the selected detail modal", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/overview.html");

  await expect(page.locator("#overview-stat-enabled-value")).toHaveText("1/2");
  await expect(page.locator("#overview-stat-runtime-value")).toHaveText("Active");
  await expect(page.locator("#overview-stat-jobs-value")).toHaveText("4");
  await expect(page.locator("#overview-stat-tools-value")).toHaveText("4");

  await page.locator("#automations-overview-list-description-badge").click();
  await expect(page.locator("#info-badge-popover")).toContainText("Select an automation to view details or open Builder.");

  await page.locator("#overview-automation-automation-order-sync").click();
  await expect(page.locator("#automation-detail-modal")).toBeVisible();
  await expect(page.locator("#automation-detail-modal-title")).toHaveText("Order sync");
  await expect(page.locator("#automation-detail-modal-edit-link")).toHaveAttribute("href", "builder.html?id=automation-order-sync");

  await expect(page.locator("#automations-overview-create-link")).toHaveAttribute("href", "builder.html?new=true");

  await page.locator("#automation-detail-modal-close").click();
  await expect(page.locator("#automation-detail-modal")).toBeHidden();
});
