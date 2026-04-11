import { expect, test } from "@playwright/test";

test("renders the dashboard home summary and collapsible sections", async ({ page }) => {
  await page.goto("/dashboard/home.html");

  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Home");
  await expect(page.locator("#dashboard-overview-health-title")).toBeVisible();
  await expect(page.locator("#dashboard-overview-services-body")).toBeVisible();
  await page.locator("#dashboard-overview-services-collapse-toggle").click();
  await expect(page.locator("#dashboard-overview-services-body")).toBeHidden();
  await page.locator("#dashboard-overview-services-collapse-toggle").click();
  await expect(page.locator("#dashboard-overview-services-body")).toBeVisible();
});

test("renders dashboard devices page", async ({ page }) => {
  await page.goto("/dashboard/devices.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/devices$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Devices");
});

test("renders dashboard logs page and clears logs", async ({ page }) => {
  await page.goto("/dashboard/logs.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/logs$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Logs");

  await expect(page.locator("#dashboard-logs-summary-body")).toBeHidden();
  await page.locator("#dashboard-logs-summary-collapse-toggle").click();
  await expect(page.locator("#dashboard-logs-summary-body")).toBeVisible();

  await expect(page.locator("#dashboard-logs-search-input")).toBeVisible();
  await expect(page.locator("#dashboard-logs-level-select")).toBeVisible();
  await expect(page.locator("#dashboard-logs-source-select")).toBeVisible();
  await expect(page.locator("#dashboard-logs-category-select")).toBeVisible();

  await page.locator("#dashboard-logs-search-input").fill("verification");
  await page.locator("#dashboard-logs-level-select").selectOption("warning");

  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#dashboard-logs-clear-button").click();
  await expect(page.locator("#dashboard-logs-clear-status")).toHaveText("Logs cleared.");
});

test("renders the queue route and toggles pause controls", async ({ page }) => {
  await page.goto("/dashboard/queue.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/queue$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Queue");
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Pause queue");

  await page.locator("#dashboard-queue-toggle-button").click();
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Unpause queue");
  await expect(page.locator("#dashboard-queue-status-card-value")).toHaveText("Paused");

  await page.locator("#dashboard-queue-toggle-button").click();
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Pause queue");
  await expect(page.locator("#dashboard-queue-status-card-value")).toHaveText("Running");
});
