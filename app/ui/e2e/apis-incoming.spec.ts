import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker, readClipboardTracker } from "./support/connectors-apis";

test("incoming APIs open details, rotate secrets, toggle status, and filter logs", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/apis/incoming.html");
  await expect(page.locator("#api-directory-row-incoming-orders")).toBeVisible();

  await page.locator("#api-directory-row-incoming-orders").click();
  await expect(page.locator("#api-detail-title")).toHaveText("Orders Webhook");
  await expect(page.locator("#api-logs-summary-total-value")).toHaveText("3");
  await expect(page.locator("#api-logs-summary-accepted-value")).toHaveText("1");
  await expect(page.locator("#api-logs-summary-errors-value")).toHaveText("2");

  await page.locator("#api-log-copy-payload-evt-1").click();
  await expect(await readClipboardTracker(page)).toContain('"order.created"');

  await page.locator("#api-log-copy-headers-evt-1").click();
  await expect(await readClipboardTracker(page)).toContain('"x-request-id"');

  await page.locator("#api-logs-status-filter").selectOption("unauthorized");
  await expect(page.locator("#api-logs-summary-total-value")).toHaveText("1");
  await expect(page.locator("#api-log-card-evt-2")).toBeVisible();
  await expect(page.locator("#api-log-card-evt-1")).toHaveCount(0);

  await page.locator("#api-logs-reset-button").click();
  await expect(page.locator("#api-logs-summary-total-value")).toHaveText("3");

  await page.locator("#api-detail-rotate-secret-button").click();
  await expect(page.locator("#api-secret-panel")).toBeVisible();
  await expect(page.locator("#api-secret-value")).toContainText("secret-incoming-orders-rotated");

  await page.locator("#api-detail-toggle-status-button").click();
  await expect(page.locator("#api-detail-toggle-status-button")).toHaveText("Enable endpoint");
  await expect(page.locator("#api-directory-status-badge-incoming-orders")).toContainText("Disabled");

  await page.locator("#api-detail-toggle-status-button").click();
  await expect(page.locator("#api-detail-toggle-status-button")).toHaveText("Disable endpoint");
  await expect(page.locator("#api-directory-status-badge-incoming-orders")).toContainText("Enabled");

  await page.keyboard.press("Escape");
  await expect(page.locator("#api-detail-modal")).not.toHaveClass(/modal--open/);
  await expect(page.locator("#api-directory-row-incoming-orders")).toBeFocused();
});
