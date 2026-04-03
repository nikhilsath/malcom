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

test("github OAuth setup supports guided authorization and lifecycle actions", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-github").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("GitHub OAuth setup");
  await expect(page.locator("#settings-connectors-github-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-github-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-save-button")).toBeHidden();
  await expect(page.locator("#settings-connectors-oauth-start-button")).toHaveText("Continue with GitHub");

  await page.locator("#settings-connectors-github-client-id-input").fill("github-client-id");
  await page.locator("#settings-connectors-github-client-secret-input").fill("github-client-secret");
  await page.locator("#settings-connectors-github-scopes-input").fill("repo, read:user");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connector authorized successfully.");
  await expect(page.locator("[id^='settings-connectors-row-github_']")).toHaveCount(1);

  const githubRow = page.locator("[id^='settings-connectors-row-github_']").first();
  await githubRow.click();
  await expect(page.locator("#settings-connectors-test-button")).toHaveText("Check connection");
  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connection verified.");

  await page.locator("#settings-connectors-refresh-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub token refreshed.");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connector revoked and credentials cleared.");
});

test("notion OAuth setup uses the provider-specific guided flow", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-notion").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Notion OAuth setup");
  await expect(page.locator("#settings-connectors-notion-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-notion-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-oauth-start-button")).toHaveText("Continue with Notion");

  await page.locator("#settings-connectors-notion-client-id-input").fill("notion-client-id");
  await page.locator("#settings-connectors-notion-client-secret-input").fill("notion-client-secret");
  await page.locator("#settings-connectors-oauth-start-button").click();

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion connector authorized successfully.");
  await expect(page.locator("[id^='settings-connectors-row-notion_']")).toHaveCount(1);

  await page.locator("[id^='settings-connectors-row-notion_']").first().click();
  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Notion connection verified.");
});

test("trello credential setup uses provider-specific save, test, and revoke actions", async ({ page }) => {
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-trello").click();

  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Trello credential setup");
  await expect(page.locator("#settings-connectors-trello-setup-panel")).toBeVisible();
  await expect(page.locator("#settings-connectors-trello-form-grid")).toBeVisible();
  await expect(page.locator("#settings-connectors-save-button")).toHaveText("Save Trello connector");
  await expect(page.locator("#settings-connectors-oauth-start-button")).toBeHidden();

  await page.locator("#settings-connectors-trello-api-key-input").fill("trello-key-demo");
  await page.locator("#settings-connectors-trello-access-token-input").fill("trello-token-demo");
  await page.locator("#settings-connectors-save-button").click();

  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector saved.");
  await expect(page.locator("[id^='settings-connectors-row-trello_']")).toHaveCount(1);

  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Trello connection verified.");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Trello credentials cleared from this workspace.");
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
    auth_type: "oauth2",
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
