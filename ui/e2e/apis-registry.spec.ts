import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker, readClipboardTracker } from "./support/connectors-apis";

test("API registry surfaces create choices and copy actions", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/apis/registry.html");
  await expect(page.locator("#apis-overview-content-title")).toHaveText("Configured API surfaces");
  await expect(page.locator("#apis-overview-total-count")).toContainText("4 configured APIs");
  await expect(page.locator("#apis-overview-incoming-list")).toBeVisible();
  await expect(page.locator("#apis-overview-outgoing-list")).toBeVisible();
  await expect(page.locator("#apis-overview-webhooks-list")).toBeVisible();

  await page.locator("#apis-overview-create-incoming").click();
  await expect(page.locator("#apis-create-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#apis-create-modal-title")).toHaveText("New Incoming API");
  await page.locator("#create-api-modal-close").click();

  await page.locator("#apis-overview-create-from-connector").click();
  await expect(page.locator("#apis-create-modal-title")).toHaveText("New Outgoing Scheduled API");
  await expect(page.locator("#create-api-connector-input")).toHaveValue("github-oauth");
  await expect(page.locator("#create-api-destination-input")).toHaveValue("https://api.github.com");
  await page.locator("#create-api-modal-close").click();

  await page.locator("#apis-overview-create-webhook").click();
  await expect(page.locator("#apis-create-modal-title")).toHaveText("New Webhook");
  await page.locator("#create-api-modal-close").click();

  await page.locator("#apis-overview-incoming-list-copy-endpoint-incoming-orders").click();
  await expect(await readClipboardTracker(page)).toContain("/api/v1/inbound/incoming-orders");
});

