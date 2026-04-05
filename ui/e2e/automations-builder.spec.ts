import { expect, test } from "@playwright/test";
import { acceptDialogs } from "./support/core.ts";
import {
  buildConnectorActivityCatalog,
  createConnectorRecord,
} from "./support/api-response-builders.ts";
import {
  buildAutomationRun,
  createAutomationSuiteState,
  installAutomationSuiteRoutes
} from "./support/automations-scripts";

test("creates a new automation draft, adds a connector activity step, edits it, and saves", async ({ page }) => {
  const state = createAutomationSuiteState({ executeResponseDelayMs: 250 });
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");

  await page.locator("#automations-validate-button").click();
  await expect(page.locator("#automations-feedback-banner")).toBeVisible();
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await expect(page.locator("#automations-validation-summary")).toBeVisible();
  await page.locator("#automations-test-results-close").click();

  await expect(page.locator("#automations-guided-item-name-action")).toHaveCount(0);
  await expect(page.locator("#automations-guided-workflow-fields")).toBeVisible();
  await page.locator("#automations-workflow-name-input").fill("Customer notification");
  await page.locator("#automations-workflow-description-input").fill("Sends an email when a customer event occurs.");
  await expect(page.locator("#automations-guided-item-name-state")).toHaveText("Done");

  await expect(page.locator("#automations-guided-item-step-action")).toBeVisible();
  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();
  await page.locator("#add-step-type-connector_activity").click();
  await page.locator("#add-step-name-input").fill("Send customer email");
  await expect(page.locator("#add-step-connector-activity-connector-input")).toContainText("Google Primary");
  await page.locator("#add-step-connector-activity-connector-input").selectOption("google-primary");
  await page.locator("#add-step-connector-activity-activity-input").selectOption("gmail-send-email");
  await expect(page.locator("#add-step-connector-activity-required-scopes")).toContainText("gmail.send");
  await page.locator("#add-step-connector-activity-input-to").fill("customer@example.com");
  await page.locator("#add-step-modal-confirm").click();

  await expect(page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]')).toHaveCount(1);
  await expect(page.locator("#automation-canvas-node-step-draft-step-1-title")).toHaveText("Send customer email");

  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText(/Automation (created|updated)\./);
  await expect(page).toHaveURL(/builder\.html\?id=/);

  await page.locator("#automations-builder-mode-guided").click();
  await expect(page.locator("#automations-guided-panel")).toBeVisible();
  await page.locator("#automations-guided-run-button").click();
  await expect(page.locator("#automations-guided-run-button")).toHaveText("Running...");
  await expect(page.locator("#automations-guided-run-button")).toBeDisabled();
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-new-button").click();
  await expect(page.locator("#automations-guided-run-button")).toHaveText("Test run");
  await expect(page.locator("#automations-guided-run-button")).toBeDisabled();
});

test("edits an existing automation, validates, runs, and deletes it", async ({ page }) => {
  const state = createAutomationSuiteState({ executeResponseDelayMs: 250, executeRefreshResponseDelayMs: 2000 });
  state.runResponses["automation-order-sync"] = buildAutomationRun(state, "automation-order-sync", "run-order-sync");
  await installAutomationSuiteRoutes(page, state);
  await acceptDialogs(page);

  await page.goto("/automations/builder.html?id=automation-order-sync");

  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Order sync");
  await expect(page.locator("#automation-canvas-node-step-step-fetch-order-title")).toHaveText("Fetch order");

  await expect(page.locator("#automation-canvas-node-step-step-fetch-order-title")).toHaveText("Fetch order");

  await page.locator("#automations-validate-button").click();
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await expect(page.locator("#automations-validation-summary")).toContainText("No validation issues detected");
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-run-button").click();
  await expect(page.locator("#automations-run-button")).toHaveText("Running...");
  await expect(page.locator("#automations-run-button")).toBeDisabled();
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await expect(page.locator("#automations-test-results-title")).toHaveText("Test run results");
  await expect(page.locator("#automations-run-results-status-value")).toHaveText("completed");
  await expect(page.locator("#automations-run-step-step-fetch-order")).toBeVisible();
  await page.locator("#automations-test-results-close").click();

  await page.locator("#automations-delete-button").click();
  await expect(page.locator("#automations-delete-dialog")).toBeVisible();
  await page.locator("#automations-delete-dialog-confirm").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation deleted.");
  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Weekly summary");
  await expect(page.locator("#automations-run-button")).toHaveText("Run now");
});

test("keeps a new draft intact when a prior run finishes later", async ({ page }) => {
  const state = createAutomationSuiteState({ executeResponseDelayMs: 1500 });
  state.runResponses["automation-order-sync"] = buildAutomationRun(state, "automation-order-sync", "run-order-sync");
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?id=automation-order-sync");

  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Order sync");

  await page.locator("#automations-run-button").click();
  await page.locator("#automations-new-button").click({ force: true });

  await expect(page.locator("#automations-run-button")).toBeEnabled();
  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("");
});

test("defaults to guided mode for new drafts and allows switching to canvas mode", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/automations/builder.html?new=true");

  await expect(page.locator("#automations-builder-mode-guided")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#automations-guided-panel")).toBeVisible();
  await expect(page).toHaveURL(/mode=guided/);
  await expect(page.locator("#automations-guided-workflow-fields")).toBeVisible();
  await expect(page.locator("#automations-guided-item-name-action")).toHaveCount(0);
  await page.locator("#automations-workflow-name-input").fill("Guided draft");
  await page.locator("#automations-workflow-description-input").fill("Inline metadata");
  await expect(page.locator("#automations-guided-item-name-state")).toHaveText("Done");

  await page.locator("#automations-builder-mode-canvas").click();

  await expect(page.locator("#automations-builder-mode-canvas")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#automations-guided-panel")).toHaveCount(0);
  await expect(page).toHaveURL(/mode=canvas/);
  await expect(page.locator("#automations-workflow-name-input")).toHaveValue("Guided draft");
  await expect(page.locator("#automations-workflow-description-input")).toHaveValue("Inline metadata");
});

test.describe("Automation Builder - Connector Dropdown", () => {
  test("shows the resolved empty state after a delayed saved-connectors fetch", async ({ page }) => {
    const state = createAutomationSuiteState();
    state.connectorsResponseOverride = {
      status: 200,
      body: [],
      delayMs: 1500,
    };
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click();

    await expect(page.locator("#add-step-connector-activity-connector-state")).toContainText("No saved connectors found");
    await expect(page.locator("#add-step-connector-activity-connector-input")).toBeEnabled();
  });

  test("filters Google connector actions behind a Google app dropdown", async ({ page }) => {
    const state = createAutomationSuiteState({
      activityCatalog: buildConnectorActivityCatalog([
        {
          provider_id: "google",
          activity_id: "gmail-send-email",
          service: "gmail",
          operation_type: "write",
          label: "Send email",
          description: "Send an email using a saved Google connector.",
          required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
          input_schema: [
            {
              key: "to",
              label: "To",
              type: "string",
              required: true,
              placeholder: "someone@example.com"
            }
          ],
          output_schema: [
            { key: "message_id", label: "Message ID", type: "string" }
          ],
          execution: { provider: "google", action: "send-email" }
        },
        {
          provider_id: "google",
          activity_id: "drive-list-files",
          service: "drive",
          operation_type: "read",
          label: "List files",
          description: "List Drive files.",
          required_scopes: ["https://www.googleapis.com/auth/drive.metadata.readonly"],
          input_schema: [],
          output_schema: [
            { key: "files", label: "Files", type: "array" }
          ],
          execution: { provider: "google", action: "list-files" }
        },
        {
          provider_id: "google",
          activity_id: "calendar-list-events",
          service: "calendar",
          operation_type: "read",
          label: "List events",
          description: "List calendar events.",
          required_scopes: ["https://www.googleapis.com/auth/calendar.readonly"],
          input_schema: [],
          output_schema: [
            { key: "events", label: "Events", type: "array" }
          ],
          execution: { provider: "google", action: "list-events" }
        },
        {
          provider_id: "google",
          activity_id: "sheets-update-range",
          service: "sheets",
          operation_type: "write",
          label: "Update range",
          description: "Write values into a Google Sheet.",
          required_scopes: ["https://www.googleapis.com/auth/spreadsheets"],
          input_schema: [],
          output_schema: [
            { key: "updated_cells", label: "Updated cells", type: "integer" }
          ],
          execution: { provider: "google", action: "update-range" }
        }
      ]) as any
    });
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click({ force: true });
    await page.locator("#add-step-connector-activity-connector-input").selectOption("google-primary");

    await expect(page.locator("#add-step-connector-activity-service-input")).toBeVisible();
    const dropdown = page.locator("#add-step-connector-activity-activity-input");
    await expect(dropdown).toHaveValue("");

    await page.locator("#add-step-connector-activity-service-input").selectOption("gmail");
    await expect(dropdown.locator("option[value='gmail-send-email']")).toHaveCount(1);

    await page.locator("#add-step-connector-activity-service-input").selectOption("sheets");
    await expect(dropdown.locator("option[value='gmail-send-email']")).toHaveCount(0);
    await expect(dropdown.locator("option[value='sheets-update-range']")).toHaveCount(1);
  });

  test("filters GitHub connector actions behind a GitHub area dropdown", async ({ page }) => {
    const state = createAutomationSuiteState({
      connectors: [
        createConnectorRecord({
          id: "github-primary",
          provider: "github",
          name: "GitHub Primary",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["repo"],
          owner: "Workspace",
          base_url: "https://api.github.com",
        }),
      ],
      activityCatalog: buildConnectorActivityCatalog([
        {
          provider_id: "github",
          activity_id: "repo-details",
          service: "repos",
          operation_type: "read",
          label: "Repository details",
          description: "Fetch repository metadata.",
          required_scopes: ["repo"],
          input_schema: [],
          output_schema: [{ key: "repository", label: "Repository", type: "string" }],
          execution: { provider: "github", action: "repo-details" }
        },
        {
          provider_id: "github",
          activity_id: "list-workflow-runs",
          service: "actions",
          operation_type: "read",
          label: "List workflow runs",
          description: "List Actions workflow runs.",
          required_scopes: ["repo"],
          input_schema: [],
          output_schema: [{ key: "workflow_runs", label: "Workflow runs", type: "array" }],
          execution: { provider: "github", action: "workflow-runs" }
        }
      ]) as any
    });
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click({ force: true });
    await page.locator("#add-step-connector-activity-connector-input").selectOption("github-primary");

    await expect(page.locator("#add-step-connector-activity-service-label")).toHaveText("GitHub area");
    await expect(page.locator("#add-step-connector-activity-service-input")).toBeVisible();
    const dropdown = page.locator("#add-step-connector-activity-activity-input");
    await expect(dropdown).toHaveValue("");
    await expect(dropdown.locator("option")).toContainText(["Choose a GitHub area first"]);

    await page.locator("#add-step-connector-activity-service-input").selectOption("actions");
    await expect(dropdown.locator("option[value='list-workflow-runs']")).toHaveCount(1);
    await expect(dropdown.locator("option[value='repo-details']")).toHaveCount(0);
  });

  test("renders the documented Gmail list query fields and outputs", async ({ page }) => {
    const state = createAutomationSuiteState({
      connectors: [
        createConnectorRecord({
          id: "google-gmail-readonly",
          provider: "google",
          name: "Google Gmail Readonly",
          status: "connected",
          auth_type: "oauth2",
          scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          owner: "Workspace",
          base_url: "https://www.googleapis.com",
        }),
      ],
      activityCatalog: buildConnectorActivityCatalog([
        {
          provider_id: "google",
          activity_id: "gmail_list_messages",
          service: "gmail",
          operation_type: "read",
          label: "List emails",
          description: "List Gmail messages with optional q, labelIds[], pageToken, and includeSpamTrash filters.",
          required_scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
          input_schema: [
            { key: "q", label: "q", type: "string", required: false },
            { key: "labels", label: "labelIds[]", type: "string", required: false },
            { key: "max_results", label: "maxResults", type: "integer", required: false, default: 100 },
            { key: "page_token", label: "pageToken", type: "string", required: false },
            { key: "include_spam_trash", label: "includeSpamTrash", type: "boolean", required: false, default: false },
          ],
          output_schema: [
            { key: "messages", label: "Messages", type: "array" },
            { key: "next_page_token", label: "Next page token", type: "string" },
            { key: "result_size_estimate", label: "Result size estimate", type: "integer" },
          ],
          execution: { provider: "google", action: "list-messages" },
        },
      ]) as any,
    });
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click({ force: true });
    await page.locator("#add-step-connector-activity-connector-input").selectOption("google-gmail-readonly");
    await page.locator("#add-step-connector-activity-service-input").selectOption("gmail");
    await page.locator("#add-step-connector-activity-activity-input").selectOption("gmail_list_messages");

    await expect(page.locator("#add-step-connector-activity-input-q-label")).toHaveText("q");
    await expect(page.locator("#add-step-connector-activity-input-labels-label")).toHaveText("labelIds[]");
    await expect(page.locator("#add-step-connector-activity-input-max_results-label")).toHaveText("maxResults");
    await expect(page.locator("#add-step-connector-activity-input-page_token-label")).toHaveText("pageToken");
    await expect(page.locator("#add-step-connector-activity-input-include_spam_trash-label")).toHaveText("includeSpamTrash");

    await expect(page.locator("#add-step-connector-activity-output-messages")).toContainText("messages");
    await expect(page.locator("#add-step-connector-activity-output-next_page_token")).toContainText("next_page_token");
    await expect(page.locator("#add-step-connector-activity-output-result_size_estimate")).toContainText("result_size_estimate");
    await expect(page.locator("#add-step-connector-activity-output-provider")).toHaveCount(0);
    await expect(page.locator("#add-step-connector-activity-output-activity")).toHaveCount(0);
    await expect(page.locator("#add-step-connector-activity-output-count")).toHaveCount(0);
  });

  test("shows empty state when no connectors are returned", async ({ page }) => {
    const state = createAutomationSuiteState();
    // simulate empty connector list
    state.connectorsResponseOverride = { status: 200, body: [] };
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click();
    await expect(page.locator("#add-step-connector-activity-connector-state")).toContainText("No saved connectors found");
    const select = page.locator("#add-step-connector-activity-connector-input");
    await expect(select).toHaveValue("");
    await expect(select.locator('option')).toHaveCount(1);
  });

  test("shows an empty step-type picker when builder support data fails to load", async ({ page }) => {
    const state = createAutomationSuiteState();
    // simulate server error for connector endpoint
    state.connectorsResponseOverride = { status: 500, body: { detail: "Simulated failure" } };
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await expect(page.locator("#add-step-type-grid").locator("button")).toHaveCount(0);
  });

  test("disables incompatible connectors with reason text and tooltip", async ({ page }) => {
    const state = createAutomationSuiteState({
      activityCatalog: buildConnectorActivityCatalog([
        {
          provider_id: "google",
          activity_id: "gmail-send-email",
          service: "gmail",
          operation_type: "write",
          label: "Send email",
          description: "Send an email using a saved Google connector.",
          required_scopes: ["https://www.googleapis.com/auth/gmail.send"],
          input_schema: [],
          output_schema: [],
          execution: { provider: "google", action: "send-email" },
        },
      ]) as any,
    });
    state.connectors = [
      createConnectorRecord({
        id: "google-missing-scope",
        provider: "google",
        name: "Google Missing Scope",
        status: "connected",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      }),
      createConnectorRecord({
        id: "google-primary",
        provider: "google",
        name: "Google Primary",
        status: "connected",
        auth_type: "oauth2",
        scopes: ["https://www.googleapis.com/auth/gmail.send"],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      }),
    ];
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-connector_activity").click();

    const incompatibleOption = page.locator('#add-step-connector-activity-connector-input option[value="google-missing-scope"]');
    await expect(incompatibleOption).toHaveAttribute("disabled", "");
    await expect(incompatibleOption).toHaveAttribute("title", /Missing required scopes/);
    await expect(page.locator("#add-step-connector-activity-connector-help")).toContainText("Disabled connectors are unavailable");
  });

  test("shows only active connectors in step modal", async ({ page }) => {
    const state = createAutomationSuiteState();
    state.connectors = [
      createConnectorRecord({
        id: "google-primary",
        provider: "google",
        name: "Google Primary",
        status: "connected",
        auth_type: "oauth2",
        scopes: ["https://www.googleapis.com/auth/gmail.send"],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      }),
      createConnectorRecord({
        id: "google-expired",
        provider: "google",
        name: "Google Expired",
        status: "expired",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      }),
      createConnectorRecord({
        id: "google-revoked",
        provider: "google",
        name: "Google Revoked",
        status: "revoked",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      }),
      createConnectorRecord({
        id: "github-draft",
        provider: "github",
        name: "GitHub Draft",
        status: "draft",
        auth_type: "bearer",
        scopes: ["repo"],
        owner: "Workspace",
        base_url: "https://api.github.com",
      }),
    ];
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-outbound_request").click({ force: true });

    const options = await page.locator("#add-step-http-connector-input option").allTextContents();
    for (const opt of options) {
      expect(opt.toLowerCase()).not.toContain("expired");
      expect(opt.toLowerCase()).not.toContain("revoked");
      expect(opt.toLowerCase()).not.toContain("draft");
    }
    await expect(page.locator("#add-step-http-connector-input")).toContainText("Google Primary");
  });
});
