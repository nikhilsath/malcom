import { expect, test } from "@playwright/test";
import { createAutomationSuiteState, installAutomationSuiteRoutes } from "./support/automations-scripts";

test("filters saved automations and opens the builder deep link", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/library.html");

  await expect(page.locator("#automations-library-runtime-active-value")).toHaveText("Active");
  await expect(page.locator("#automations-library-runtime-jobs-value")).toHaveText("4");

  await page.locator("#automations-library-list-description-badge").click();
  await expect(page.locator("#automations-library-list-description")).toBeVisible();

  await page.locator("#automations-library-search-input").fill("weekly");
  await expect(page.locator("#automations-library-item-automation-weekly-summary")).toBeVisible();
  await expect(page.locator("#automations-library-item-automation-order-sync")).toHaveCount(0);

  await page.locator("#automations-library-search-input").fill("");
  await page.locator("#automations-library-item-automation-order-sync").click();
  await expect(page.locator("#automations-library-detail-modal")).toBeVisible();
  await expect(page.locator("#automations-library-detail-modal-title")).toHaveText("Order sync");
  await expect(page.locator("#automations-library-detail-modal-edit-link")).toHaveAttribute("href", "builder.html?id=automation-order-sync");
  await expect(page.locator("#automations-library-create-link")).toHaveAttribute("href", "builder.html?new=true");

  await page.locator("#automations-library-detail-modal-close").click();
  await expect(page.locator("#automations-library-detail-modal")).toBeHidden();
});

test("shows the empty state when no automations exist", async ({ page }) => {
  const state = createAutomationSuiteState({ automations: [] });
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/library.html");

  await expect(page.locator("#automations-library-empty")).toHaveText("No automations yet.");
  await expect(page.locator("#automations-library-list")).toHaveCount(0);
});
