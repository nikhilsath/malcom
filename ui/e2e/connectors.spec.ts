import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker } from "./support/connectors-apis";
import { createGithubOAuthConnector, createConnectorRecord } from "./support/api-response-builders.ts";

test("google OAuth draft can be created and returned through the callback UX", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/settings/connectors.html");
  await expect(page.locator("#page-title")).toHaveText("Settings Integrations");
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("0");

  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-google").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Google OAuth setup");
  await expect(page.locator("#settings-connectors-google-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-google-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-oauth-start-button")).toHaveText("Continue with Google");

  await page.locator("#settings-connectors-google-client-id-input").fill("google-client-id");
  await page.locator("#settings-connectors-google-client-secret-input").fill("google-client-secret");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Google connector authorized successfully.");
  await expect(page.locator("#settings-connectors-row-google")).toBeVisible();
});

test("github PAT setup supports save, test, and revoke actions", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);
  let dialogSeen = false;
  page.on("dialog", async (dialog) => {
    dialogSeen = true;
    await dialog.dismiss();
  });

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-github").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("GitHub PAT setup");
  await expect(page.locator("#settings-connectors-github-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-github-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-github-access-token-input")).toBeVisible();
  await expect(page.locator("#settings-connectors-save-button")).toHaveText("Save connector");
  await expect(page.locator("#settings-connectors-oauth-start-button")).toBeHidden();
  await expect(page.locator("#settings-connectors-refresh-button")).toBeHidden();

  await page.locator("#settings-connectors-github-access-token-input").fill("ghp_demo_token_for_tests");
  await page.locator("#settings-connectors-github-scopes-input").selectOption(["repo", "read:user", "workflow"]);
  await page.locator("#settings-connectors-save-button").click();

  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector saved.");
  await expect(page.locator("[id^='settings-connectors-row-github_']")).toHaveCount(1);
  expect(dialogSeen).toBe(false);

  await expect(page.locator("#settings-connectors-test-button")).toHaveText("Check connection");
  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connection verified.");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connector revoked and credentials cleared.");
});

test("notion OAuth setup uses the provider-specific guided flow", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  const appOrigin = new URL(page.url()).origin;
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-notion").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Notion OAuth setup");
  await expect(page.locator("#settings-connectors-notion-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-notion-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-oauth-start-button")).toHaveText("Continue with Notion");

  await page.locator("#settings-connectors-notion-client-id-input").fill("notion-client-id");
  await page.locator("#settings-connectors-notion-client-secret-input").fill("notion-client-secret");
  await page.route("**api.notion.com/v1/oauth/authorize**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><html><body>Notion authorization stub</body></html>",
    });
  });
  await page.locator("#settings-connectors-oauth-start-button").click();
  await page.waitForURL(/api\.notion\.com\/v1\/oauth\/authorize/);
  const notionAuthorizeUrl = new URL(page.url());
  const stateToken = notionAuthorizeUrl.searchParams.get("state");
  expect(stateToken).toBeTruthy();

  await page.goto(`${appOrigin}/api/v1/connectors/notion/oauth/callback?state=${encodeURIComponent(stateToken || "")}&code=demo-notion`);

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion connector authorized successfully.");
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");
  const notionRow = page.locator("#settings-connectors-table-body tr").first();
  await expect(notionRow).toBeVisible();

  await notionRow.click();
  await expect(page.locator("#settings-connectors-notion-status-badge")).toHaveText("Connected");
  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion connection verified.");
  await page.locator("#settings-connectors-refresh-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion token refreshed.");
  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion connector revoked and credentials cleared.");
});

test("trello OAuth setup uses provider-specific guided authorization and lifecycle actions", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-trello").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Trello OAuth setup");
  await expect(page.locator("#settings-connectors-trello-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-trello-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-trello-client-id-input")).toBeVisible();
  await expect(page.locator("#settings-connectors-trello-client-secret-input")).toBeVisible();
  await expect(page.locator("#settings-connectors-trello-redirect-uri-input")).toBeVisible();
  await expect(page.locator("#settings-connectors-save-button")).toBeHidden();
  await expect(page.locator("#settings-connectors-oauth-start-button")).toHaveText("Continue with Trello");
  await expect(page.locator("#settings-connectors-refresh-button")).toBeHidden();

  await page.locator("#settings-connectors-trello-client-id-input").fill("trello-client-id");
  await page.locator("#settings-connectors-trello-client-secret-input").fill("trello-client-secret");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Trello connector authorized successfully.");
  await expect(page.locator("[id^='settings-connectors-row-trello_']")).toHaveCount(1);
});

test("invalid OAuth return surfaces an error without mutating the registry", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [createGithubOAuthConnector()] });
  await harness.install(page);

  await page.goto("/api/v1/connectors/google/oauth/callback?state=bad-state&code=demo-code&connector_id=google");

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Invalid OAuth state.");
  await expect(page.locator("#settings-connectors-row-google")).toHaveCount(0);
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();
});

test("populates connectors from the API-backed harness payload", async ({ page }) => {
  const apiConnector = createConnectorRecord({
    id: "api-connector",
    provider: "github",
    name: "API Connector",
    status: "connected",
    auth_type: "bearer",
    scopes: ["repo"],
    base_url: "https://api.github.com",
    owner: "Workspace",
    docs_url: "https://docs.github.com",
    credential_ref: "connector/api-connector",
    auth_config: {},
  });
  const harness = createConnectorsApisHarness({ connectors: [apiConnector] });
  await harness.install(page);
  await page.goto("/settings/connectors.html");

  await expect(page.locator("#settings-connectors-row-api-connector")).toBeVisible();
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");
});
