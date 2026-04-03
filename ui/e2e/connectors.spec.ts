import { expect, test } from "@playwright/test";

import { createConnectorsApisHarness, installClipboardTracker } from "./support/connectors-apis";

test("google OAuth draft can be created and returned through the callback UX", async ({ page }) => {
  // Start with no stored connectors so creating a Google OAuth draft yields a single connected entry
  const harness = createConnectorsApisHarness({ connectors: [] });
  await harness.install(page);
  await installClipboardTracker(page);

  await page.goto("/settings/connectors.html");
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("0");
  await expect(page.locator("#settings-connectors-row-github-oauth")).toHaveCount(0);

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
  await expect(page.locator("#settings-connectors-detail-modal")).not.toHaveClass(/modal--open/);
});

test("non-Google connector lifecycle actions update the registry", async ({ page }) => {
  // Default harness includes a GitHub connector fixture
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
  // Keep default fixtures so GitHub is present while invalid Google OAuth attempts do not add Google
  const harness = createConnectorsApisHarness();
  await harness.install(page);

  await page.goto("/api/v1/connectors/google/oauth/callback?state=bad-state&code=demo-code&connector_id=google");

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Invalid OAuth state.");
  await expect(page.locator("#settings-connectors-row-google")).toHaveCount(0);
  await expect(page.locator("#settings-connectors-row-github-oauth")).toBeVisible();
});

test("populates connectors from GET /api/v1/connectors and ignores cached settings", async ({ page }) => {
  // Provide a harness seeded with the API-backed connector so the connectors route returns it
  const apiConnector = {
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
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_tested_at: new Date().toISOString(),
    auth_config: {}
  };
  const harness = createConnectorsApisHarness({ connectors: [apiConnector] });
  await harness.install(page);

  // After harness.install, seed a cached app-settings payload in localStorage (should NOT be used)
  await page.addInitScript(() => {
    try {
      const stateKey = "malcom.playwright.connectors-apis";
      const seed = { settings: { connectors: { catalog: [], records: [ { id: "cached-connector", provider: "cached", name: "Cached Connector", status: "connected", auth_type: "oauth2", scopes: [], base_url: "", owner: "Workspace", auth_config: {}, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), last_tested_at: null } ], auth_policy: {} } } };
      window.localStorage.setItem(stateKey, JSON.stringify(seed));
    } catch {}
  });
  await page.goto("/settings/connectors.html");

  // The page should render the API-provided connector and not the cached one.
  await expect(page.locator("#settings-connectors-row-api-connector")).toBeVisible();
  await expect(page.locator("#settings-connectors-row-cached-connector")).toHaveCount(0);
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");
});
