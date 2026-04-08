import { expect, test } from "@playwright/test";
import { acceptDialogs } from "./support/core.ts";
import { createAutomationSuiteState, installAutomationSuiteRoutes } from "./support/automations-scripts";

const buildRows = (count: number) => Array.from({ length: count }, (_, index) => ({
  row_id: index + 1,
  order_id: `ORD-${String(1000 + index)}`,
  status: index % 3 === 0 ? "queued" : index % 3 === 1 ? "paid" : "warning"
}));

test("selects a log table, changes limits, clears rows, and deletes the table", async ({ page }) => {
  const state = createAutomationSuiteState();
  state.rowsByTableId["order-events"] = buildRows(101);
  await installAutomationSuiteRoutes(page, state);
  await acceptDialogs(page);

  await page.goto("/automations/data.html");

  await expect(page.locator("#automations-data-directory-title")).toHaveText("Log tables");
  await expect(page.locator("#automations-data-select-hint")).toBeVisible();

  await page.locator("#automations-data-table-order-events").click();
  await expect(page.locator("#automations-data-modal")).toBeVisible();
  await expect(page.locator("#automations-data-total-hint")).toContainText("Showing 100 of 101 rows");
  await expect(page.locator("#automations-data-row-1")).toBeVisible();

  await page.locator("#automations-data-limit-select").selectOption("250");
  await expect(page.locator("#automations-data-total-hint")).toContainText("Showing 101 of 101 rows");
  await expect(page.locator("#automations-data-row-101")).toBeVisible();

  await page.locator("#automations-data-clear-button").click();
  await expect(page.locator("#automations-data-no-rows")).toBeVisible();

  await page.locator("#automations-data-delete-button").click();
  await expect(page.locator("#automations-data-modal")).toBeHidden();
  await expect(page.locator("#automations-data-table-order-events")).toHaveCount(0);
  await expect(page.locator("#automations-data-table-customer-events")).toBeVisible();
});

test("returns focus to the selected table after closing the modal", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/data.html");
  await page.locator("#automations-data-table-customer-events").click();
  await expect(page.locator("#automations-data-modal")).toBeVisible();

  await page.locator("#automations-data-modal-close").click();
  await expect(page.locator("#automations-data-modal")).toBeHidden();
  await expect(page.locator("#automations-data-table-customer-events")).toBeFocused();
});

test("shows the empty state when no log tables exist", async ({ page }) => {
  const state = createAutomationSuiteState({ logTables: [], rowsByTableId: {} });
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/data.html");

  await expect(page.locator("#automations-data-empty")).toBeVisible();
  await expect(page.locator("#automations-data-empty-text")).toHaveText("No log tables yet.");
});
