import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker } from "./support/connectors-apis";

test("google OAuth draft can be created and returned through the callback UX", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/settings/connectors.html");
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();

  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-google").click();

  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Google OAuth setup");
  await expect(page.locator("#settings-connectors-redirect-uri-input")).toHaveValue(/\/api\/v1\/connectors\/google\/oauth\/callback$/);
  await expect(page.locator("#settings-connectors-oauth-start-button")).toBeVisible();
  await expect(page.locator("#settings-connectors-save-button")).toBeHidden();

  await page.locator("#settings-connectors-client-id-input").fill("google-client-id");
  await page.locator("#settings-connectors-client-secret-input").fill("google-client-secret");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector authorized successfully.");
  await expect(page.locator("#settings-connectors-row-google")).toBeVisible();
  await expect(page.locator("#settings-connectors-row-status-google")).toContainText("Connected");
  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);

  await page.keyboard.press("Escape");
  await expect(page.locator("#settings-connectors-detail-modal")).not.toHaveClass(/modal--open/);
});

test("non-Google connector lifecycle actions update the registry", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();

  await page.locator("#settings-connectors-row-github-oauth").click();
  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("GitHub Primary");

  await page.locator("#settings-connectors-name-input").fill("GitHub Primary Updated");
  await page.locator("#settings-connectors-base-url-input").fill("https://api.github.com/rest");
  await page.locator("#settings-connectors-scopes-input").fill("repo, workflow");
  await page.locator("#settings-connectors-save-button").click();

  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector saved.");
  await expect(page.locator("#settings-connectors-row-name-value-github-oauth")).toHaveText("GitHub Primary Updated");

  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector credentials look complete.");
  await expect(page.locator("#settings-connectors-row-status-github-oauth")).toContainText("Connected");

  await page.locator("#settings-connectors-refresh-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector token refreshed.");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-row-status-github-oauth")).toContainText("Revoked");
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector revoked and stored credentials cleared.");

  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });
  await page.locator("#settings-connectors-remove-button").click();

  await expect(page.locator("#settings-connectors-empty")).toBeVisible();
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("0");
});

test("invalid OAuth return surfaces an error without mutating the registry", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/api/v1/connectors/google/oauth/callback?state=bad-state&code=demo-code&connector_id=google");

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Invalid OAuth state.");
  await expect(page.locator("#settings-connectors-row-google")).toHaveCount(0);
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();
});
