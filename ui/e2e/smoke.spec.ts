import { expect, test } from "@playwright/test";

test("loads the dashboard home route", async ({ page }) => {
  await page.goto("/dashboard/home.html");
  await expect(page.locator("#dashboard-react-root")).toBeVisible();
  await expect(page.getByText("Dashboard Home")).toBeVisible();
});

test("loads the workspace settings page", async ({ page }) => {
  await page.goto("/settings/workspace.html");
  await expect(page.locator("#settings-workspace-title")).toHaveText("Workspace defaults");
  await expect(page.locator("#settings-save-button")).toBeVisible();
});

test("loads the tools catalog page", async ({ page }) => {
  await page.goto("/tools/catalog.html");
  await expect(page.locator("#tools-selection-title")).toHaveText("Select a tool");
  await expect(page.locator("#tools-grid")).toBeVisible();
});

test("loads the API registry page", async ({ page }) => {
  await page.goto("/apis/registry.html");
  await expect(page.locator("#apis-overview-content-title")).toHaveText("Configured API surfaces");
  await expect(page.locator("#apis-overview-action-grid")).toBeVisible();
});

test("loads the automation builder page", async ({ page }) => {
  await page.goto("/automations/builder.html?new=true");
  await expect(page.locator("#automations-builder-page-title")).toHaveText("Automation Builder");
  await expect(page.locator("#automations-react-root")).toBeVisible();
  await expect(page.locator("#automations-workflow-bar")).toBeVisible();
  await expect(page.locator("#automations-canvas-panel")).toBeVisible();
});
