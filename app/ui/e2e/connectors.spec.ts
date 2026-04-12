import { expect, test, type APIRequestContext } from "@playwright/test";

const deleteConnectorIfPresent = async (request: APIRequestContext, connectorId: string) => {
  const response = await request.delete(`/api/v1/connectors/${connectorId}`);
  expect([200, 404]).toContain(response.status());
};

const createGithubConnector = async (request: APIRequestContext, connectorId: string) => {
  const response = await request.post("/api/v1/connectors", {
    data: {
      id: connectorId,
      provider: "github",
      name: "GitHub Primary",
      status: "draft",
      auth_type: "bearer",
      scopes: ["repo"],
      base_url: "https://api.github.com",
      owner: "Workspace",
      auth_config: {
        access_token_input: "token_secret_test_value"
      }
    }
  });

  expect(response.status()).toBe(201);
};

test("google OAuth draft can be created and returned through the callback UX", async ({ page, request }) => {
  await deleteConnectorIfPresent(request, "google");

  await page.route("https://accounts.google.com/**", async (route) => {
    const authorizationUrl = new URL(route.request().url());
    const redirectUri = authorizationUrl.searchParams.get("redirect_uri");
    const state = authorizationUrl.searchParams.get("state");

    if (!redirectUri || !state) {
      throw new Error("Missing Google OAuth redirect parameters.");
    }

    await route.fulfill({
      status: 200,
      contentType: "text/html",
      body: `<html><body><script>window.location.href = ${JSON.stringify(`${redirectUri}?state=${state}&code=demo-code`)};</script></body></html>`
    });
  });

  await page.goto("/settings/connectors.html");
  await page.locator("#settings-connectors-create-button").click();
  await page.locator("#settings-connectors-provider-option-google").click();

  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Google OAuth setup");
  await expect(page.locator("#settings-connectors-google-redirect-uri-input")).toHaveValue(/\/api\/v1\/connectors\/google\/oauth\/callback$/);
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

  await deleteConnectorIfPresent(request, "google");
});

test("non-Google connector lifecycle actions update the registry through the live connectors API", async ({ page, request }) => {
  const connectorId = `github-ui-${Date.now()}`;
  await createGithubConnector(request, connectorId);

  await page.goto("/settings/connectors.html");
  await expect(page.locator(`#settings-connectors-row-${connectorId}`)).toBeVisible();
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("0");

  await page.locator(`#settings-connectors-row-${connectorId}`).click();
  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("GitHub PAT setup");

  await page.locator("#settings-connectors-github-name-input").fill("GitHub Primary Updated");
  await page.locator("#settings-connectors-github-access-token-input").fill("token_secret_test_value");
  await page.locator("#settings-connectors-save-button").click();

  await expect(page.locator("#settings-connectors-feedback")).toContainText("Connector saved.");
  await expect(page.locator(`#settings-connectors-row-name-value-${connectorId}`)).toHaveText("GitHub Primary Updated");

  await page.locator("#settings-connectors-test-button").click();
  await expect(page.locator("#settings-connectors-feedback")).toContainText("GitHub connection verified.");
  await expect(page.locator(`#settings-connectors-row-status-${connectorId}`)).toContainText("Connected");
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("1");

  await page.locator("#settings-connectors-revoke-button").click();
  await expect(page.locator(`#settings-connectors-row-status-${connectorId}`)).toContainText("Revoked");
  await expect(page.locator("#settings-connectors-feedback")).toContainText("credentials cleared locally");

  page.once("dialog", async (dialog) => {
    await dialog.accept();
  });
  await page.locator("#settings-connectors-remove-button").click();

  await expect(page.locator(`#settings-connectors-row-${connectorId}`)).toHaveCount(0);
  await expect(page.locator("#settings-connectors-summary-connected-value")).toHaveText("0");
});

test("invalid OAuth return surfaces an error without mutating the registry", async ({ page, request }) => {
  await deleteConnectorIfPresent(request, "google");

  await page.goto("/api/v1/connectors/google/oauth/callback?state=bad-state&code=demo-code&connector_id=google");

  await expect(page).toHaveURL(/\/settings\/connectors\.html$/);
  await expect(page.locator("#settings-connectors-feedback")).toContainText("Invalid OAuth state.");
  await expect(page.locator("#settings-connectors-row-google")).toHaveCount(0);
});
