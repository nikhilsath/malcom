import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness } from "./support/connectors-apis";

test("outgoing API create-from-connector flow populates connector defaults and saves", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/apis/outgoing.html");
  await page.locator("#apis-create-button").click();
  await expect(page.locator("#apis-create-type-modal")).toHaveClass(/modal--open/);
  await page.locator("#apis-create-type-option-from-connector").click();

  await expect(page.locator("#apis-create-modal-title")).toHaveText("New Outgoing Scheduled API");
  await expect(page.locator("#create-api-connector-input")).toHaveValue("github-oauth");
  await expect(page.locator("#create-api-destination-input")).toHaveValue("https://api.github.com");
  await expect(page.locator("#create-api-outgoing-auth-type-input")).toHaveValue("bearer");

  await page.locator("#create-api-name-input").fill("GitHub Delivery");
  await page.locator("#create-api-description-input").fill("Sends connector-backed updates.");
  await page.locator("#create-api-payload-input").fill('{ "event": "connector.delivery", "sent_at": "{{timestamp}}" }');

  await expect(page.locator("#create-api-payload-variable-timestamp-1")).toBeVisible();

  await page.locator("#create-api-test-button").click();
  await expect(page.locator("#create-api-test-feedback")).toContainText("Test delivery returned 200.");

  await page.locator("#create-api-form").getByRole("button", { name: "Create scheduled API" }).click();
  await expect(page.locator("#apis-outgoing-list-row-outgoing-github-delivery")).toBeVisible();
  await expect(page.locator("#apis-create-modal")).not.toHaveClass(/modal--open/);
});

test("outgoing registry edit modal saves changes and exercises the test delivery action", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/apis/outgoing.html");
  await page.locator("#apis-outgoing-list-row-outgoing-heartbeat").click();

  await expect(page.locator("#outgoing-api-edit-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#outgoing-api-edit-modal-title")).toHaveText("Edit continuous API");
  await page.locator("#outgoing-api-edit-name-input").fill("Heartbeat Updated");
  await page.locator("#outgoing-api-edit-destination-input").fill("https://example.com/webhooks/heartbeat-updated");
  await page.locator("#outgoing-api-edit-payload-input").fill('{ "event": "heartbeat.updated" }');

  await page.locator("#outgoing-api-edit-test-button").click();
  await expect(page.locator("#outgoing-api-edit-test-feedback")).toContainText("Test delivery returned 200.");

  await page.locator("#outgoing-api-edit-form").getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator("#apis-outgoing-list-row-outgoing-heartbeat")).toContainText("Heartbeat Updated");
  await expect(page.locator("#outgoing-api-edit-modal")).not.toHaveClass(/modal--open/);
});

