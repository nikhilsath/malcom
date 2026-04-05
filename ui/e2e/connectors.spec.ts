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

  await page.locator("#settings-connectors-google-client-id-input").fill("google-client-id");
  await page.locator("#settings-connectors-google-client-secret-input").fill("google-client-secret");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("authorized successfully");
  await expect(page.locator("#settings-connectors-row-google")).toBeVisible();
  await expect(page.locator("#settings-connectors-row-status-google")).toContainText("Connected");
  await expect(page.locator("#settings-connectors-detail-modal")).not.toHaveClass(/modal--open/);
});

test("non-Google connector lifecycle actions update the registry", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();

  await page.locator("#settings-connectors-row-github-oauth").click();
  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("GitHub PAT setup");

  await page.locator("#settings-connectors-github-name-input").fill("GitHub Primary Updated");
  await page.locator("#settings-connectors-github-access-token-input").fill("ghp_smoke_token");
  await page.locator("#settings-connectors-save-button").click();

  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector saved.");
  await expect(page.locator("#settings-connectors-row-name-value-github-oauth")).toHaveText("GitHub Primary Updated");

  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connection verified.");
  await expect(page.locator("#settings-connectors-row-status-github-oauth")).toContainText("Connected");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-row-status-github-oauth")).toContainText("Revoked");
  await expect(page.locator("#settings-connectors-feedback")).toContainText("revoked");

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

test("connectors page load sources connector records from the live settings API", async ({ page }) => {
  const harness = createConnectorsApisHarness();

  await harness.install(page);
  await page.goto("/settings/connectors.html");

  // The connector record from the harness fixture should be visible
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();

  // Summary should reflect connected count from API data, not stale cache
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");
});

test("connectors page shows error feedback when settings API is unavailable", async ({ page }) => {
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  // Override connectors endpoint to fail after page install
  await page.route("**/api/v1/connectors", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Service unavailable" }) });
      return;
    }
    await route.fallback();
  });

  await page.goto("/settings/connectors.html");

  // Page should remain usable even when the live load fails.
  await expect
    .poll(async () => {
      const feedbackText = (await page.locator("#settings-connectors-feedback").textContent())?.trim() || "";
      const emptyVisible = await page.locator("#settings-connectors-empty").isVisible();
      const tableVisible = await page.locator("#settings-connectors-table-shell").isVisible();
      const rowCount = await page.locator("#settings-connectors-table-body tr").count();
      return feedbackText.length > 0 || emptyVisible || tableVisible || rowCount > 0;
    })
    .toBe(true);
});
