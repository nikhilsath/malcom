import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker, readClipboardTracker } from "./support/connectors-apis";

test("API registry stays navigation-only and supports copy actions", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/apis/registry.html");
  await expect(page.locator("#apis-overview-content-title")).toHaveText("Configured API surfaces");
  await expect(page.locator("#apis-overview-total-count")).toContainText("4 configured APIs");
  await expect(page.locator("#apis-overview-incoming-list")).toBeVisible();
  await expect(page.locator("#apis-overview-outgoing-list")).toBeVisible();
  await expect(page.locator("#apis-overview-webhooks-list")).toBeVisible();

  await expect(page.locator("#apis-overview-actions-panel")).toHaveCount(0);
  await expect(page.locator("#apis-create-button")).toHaveCount(0);
  await expect(page.locator("#apis-create-modal")).toHaveCount(0);

  await page.locator("#apis-overview-incoming-list-copy-endpoint-incoming-orders").click();
  await expect(await readClipboardTracker(page)).toContain("/api/v1/inbound/incoming-orders");
});

