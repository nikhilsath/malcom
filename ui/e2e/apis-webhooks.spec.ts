import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker, readClipboardTracker } from "./support/connectors-apis";

test("webhook registry creates records and copies callback metadata", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/apis/webhooks.html");
  await expect(page.locator("#apis-webhooks-list-card-webhook-orders")).toBeVisible();

  await page.locator("#apis-webhooks-list-copy-callback-webhook-orders").click();
  await expect(await readClipboardTracker(page)).toContain("/publisher/orders");

  await page.locator("#apis-create-button").click();
  await expect(page.locator("#apis-create-type-modal")).toHaveClass(/modal--open/);
  await page.locator("#apis-create-type-option-webhook").click();
  await expect(page.locator("#apis-create-modal-title")).toHaveText("New Webhook");

  await page.locator("#create-api-name-input").fill("Shipment Webhook");
  await page.locator("#create-api-description-input").fill("Publishes shipment updates.");
  await page.locator("#create-api-slug-input").fill("shipment-webhook");
  await page.locator("#create-api-webhook-callback-input").fill("/publisher/shipments");
  await page.locator("#create-api-webhook-verification-input").fill("verify-shipment");
  await page.locator("#create-api-webhook-signing-input").fill("signing-shipment");
  await page.locator("#create-api-webhook-header-input").fill("X-Shipment-Signature");
  await page.locator("#create-api-webhook-event-input").fill("shipment.created");
  await page.locator("#create-api-form").getByRole("button", { name: "Create webhook" }).click();

  await expect(page.locator("#apis-webhooks-list-card-webhook-shipment-webhook")).toBeVisible();
  await expect(page.locator("#apis-create-modal")).not.toHaveClass(/modal--open/);
});

