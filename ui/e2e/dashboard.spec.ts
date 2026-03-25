import { expect, test } from "@playwright/test";
import { installDashboardSettingsFixtures } from "./support/dashboard-settings";

test("renders the dashboard home summary and collapsible sections", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/dashboard/home.html");

  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Home");
  await expect(page.locator("#dashboard-overview-health-title")).toHaveText("Workspace healthy");
  await expect(page.locator("#dashboard-overview-summary-total-runs-value")).toHaveText("2");
  await expect(page.locator("#dashboard-overview-summary-queue-status-value")).toHaveText("Running");
  await expect(page.locator("#dashboard-overview-summary-queue-pending-value")).toHaveText("1");
  await expect(page.locator("#dashboard-overview-log-preview-item-log-api-retry")).toBeVisible();
  await expect(page.locator("#dashboard-overview-resource-total-metrics-value")).toHaveText("3");
  await expect(page.locator("#dashboard-overview-resource-operation-0")).toContainText("step_tool");
  await expect(page.locator("#dashboard-overview-resource-errors-0")).toHaveText("12.5% (1)");
  await expect(page.locator("#dashboard-overview-resource-profile-reset-button")).toBeVisible();

  await page.locator("#dashboard-overview-resource-profile-reset-button").click();
  await expect(page.locator("#dashboard-overview-resource-total-metrics-value")).toHaveText("0");

  await expect(page.locator("#dashboard-overview-services-body")).toBeVisible();
  await page.locator("#dashboard-overview-services-collapse-toggle").click();
  await expect(page.locator("#dashboard-overview-services-body")).toBeHidden();
  await page.locator("#dashboard-overview-services-collapse-toggle").click();
  await expect(page.locator("#dashboard-overview-services-body")).toBeVisible();
});

test("renders dashboard devices with host telemetry and runtime endpoints", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/dashboard/devices.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/devices$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Devices");
  await expect(page.locator("#dashboard-devices-host-toolbar-title")).toHaveText("Host machine");
  await expect(page.locator("#dashboard-devices-storage-free-card-detail")).toContainText("25.0% of disk in use");
  await expect(page.locator("#dashboard-device-row-service-api-endpoint")).toBeVisible();
  await expect(page.locator("#dashboard-device-row-service-smtp-relay")).toBeVisible();
  await expect(page.locator("#dashboard-device-status-service-smtp-relay")).toHaveText("warning");
});

test("filters dashboard logs and opens the log detail modal", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/dashboard/logs.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/logs$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Logs");
  await expect(page.locator("#dashboard-logs-summary-body")).toBeHidden();

  await page.locator("#dashboard-logs-summary-collapse-toggle").click();
  await expect(page.locator("#dashboard-logs-summary-body")).toBeVisible();

  await page.locator("#dashboard-logs-search-input").fill("verification");
  await page.locator("#dashboard-logs-level-select").selectOption("warning");
  await page.locator("#dashboard-logs-source-select").selectOption("api.webhooks");
  await page.locator("#dashboard-logs-category-select").selectOption("delivery");
  await page.locator("#dashboard-logs-time-select").selectOption("24h");

  await expect(page.locator("#dashboard-logs-results-count")).toContainText("1 matching logs");
  await expect(page.locator("#dashboard-log-item-log-api-retry")).toBeVisible();

  await page.locator("#dashboard-log-item-log-api-retry").click();
  await expect(page.locator("#dashboard-log-details-modal")).toBeVisible();
  await expect(page.locator("#dashboard-log-details-id-value-log-api-retry")).toHaveText("log-api-retry");
  await expect(page.locator("#dashboard-log-details-value-log-api-retry")).toContainText("/webhooks/inbound/weather");

  await page.keyboard.press("Escape");
  await expect(page.locator("#dashboard-log-details-modal")).toBeHidden();
});

test("renders the queue route and toggles pause controls", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/dashboard/queue.html");

  await expect(page).toHaveURL(/\/dashboard\/home\.html#\/queue$/);
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Queue");
  await expect(page.locator("#dashboard-queue-jobs-toolbar-title")).toHaveText("Runtime trigger jobs");
  await expect(page.locator("#dashboard-queue-row-job-trigger-1")).toBeVisible();
  await expect(page.locator("#dashboard-queue-status-job-trigger-1")).toHaveText("pending");
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Pause queue");

  await page.locator("#dashboard-queue-toggle-button").click();
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Unpause queue");
  await expect(page.locator("#dashboard-queue-status-card-value")).toHaveText("Paused");

  await page.locator("#dashboard-queue-toggle-button").click();
  await expect(page.locator("#dashboard-queue-toggle-button")).toHaveText("Pause queue");
  await expect(page.locator("#dashboard-queue-status-card-value")).toHaveText("Running");
});
