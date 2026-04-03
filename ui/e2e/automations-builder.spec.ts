import { expect, test } from "@playwright/test";
import { acceptDialogs } from "./support/core.ts";
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
  await expect(page.locator("#automations-feedback-banner")).toContainText("Name is required.");
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await expect(page.locator("#automations-validation-summary")).toContainText("validation issue");
  await page.locator("#automations-test-results-close").click();

  await expect(page.locator("#automations-guided-item-name-action")).toHaveCount(0);
  await expect(page.locator("#automations-guided-workflow-fields")).toBeVisible();
  await page.locator("#automations-workflow-name-input").fill("Customer notification");
  await page.locator("#automations-workflow-description-input").fill("Sends an email when a customer event occurs.");
  await expect(page.locator("#automations-guided-item-name-state")).toHaveText("Done");

  await expect(page.locator("#automations-guided-item-step-action")).toBeVisible();
  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();
  await page.locator("#add-step-type-api").click();
  await page.locator("#add-step-api-mode-prebuilt").click();
  await page.locator("#add-step-name-input").fill("Send customer email");
  await expect(page.locator("#add-step-connector-activity-connector-input")).toContainText("Google Primary");
  await page.locator("#add-step-connector-activity-connector-input").selectOption("google-primary");
  await page.locator("#add-step-connector-activity-activity-card-gmail-send-email").click();
  await expect(page.locator("#add-step-connector-activity-required-scopes")).toContainText("gmail.send");
  await page.locator("#add-step-connector-activity-input-to").fill("customer@example.com");
  await page.locator("#add-step-connector-activity-input-subject").fill("Your order shipped");
  await page.locator("#add-step-connector-activity-input-body").fill("Hello from Malcom");
  await page.locator("#add-step-modal-confirm").click();

  await expect(page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]')).toHaveCount(1);
  await page.locator('.automation-node[id^="automation-canvas-node-step-draft-step-"]').dblclick();
  await expect(page.locator("#automations-editor-modal")).toBeVisible();
  await page.locator("#automations-step-connector-activity-input-subject").fill("Your order is now in transit");
  await expect(page.locator("#automation-canvas-node-step-draft-step-1-title")).toHaveText("Send customer email");
  await page.locator("#automations-editor-modal-close").click();

  await page.locator("#automations-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText("Automation created.");
  await expect(page).toHaveURL(/builder\.html\?id=/);

  await page.locator("#automations-builder-mode-guided").click();
  await expect(page.locator("#automations-guided-panel")).toBeVisible();
  await page.locator("#automations-guided-run-button").click();
  await expect(page.locator("#automations-guided-run-button")).toHaveText("Running...");
  await expect(page.locator("#automations-guided-run-button")).toBeDisabled();
  await expect(page.locator("#automations-test-results-modal")).toBeVisible();
  await expect(page.locator("#automations-guided-run-button")).toHaveText("Done");
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

  await page.locator("#automation-canvas-node-trigger").click({ button: "right" });
  await expect(page.locator("#automations-node-menu-edit")).toBeVisible();
  await page.locator("#automations-node-menu-edit").click();
  await expect(page.locator("#automations-editor-modal")).toBeVisible();
  await expect(page.locator("#automations-editor-modal-trigger-back")).toBeVisible();
  await page.locator("#automations-editor-modal-trigger-back").click();
  await expect(page.locator("#automations-trigger-modal-trigger-type-options")).toBeVisible();
  await page.locator("#automations-trigger-modal-trigger-type-option-schedule").click();
  await page.locator("#automations-trigger-modal-trigger-schedule-input").click();
  await expect(page.locator("#automations-trigger-modal-trigger-schedule-picker")).toBeVisible();
  const scheduleTriggerBox = await page.locator("#automations-trigger-modal-trigger-schedule-input").boundingBox();
  const schedulePickerBox = await page.locator("#automations-trigger-modal-trigger-schedule-picker").boundingBox();
  expect(scheduleTriggerBox).not.toBeNull();
  expect(schedulePickerBox).not.toBeNull();
  expect((schedulePickerBox?.y ?? 0) + (schedulePickerBox?.height ?? 0)).toBeLessThanOrEqual((scheduleTriggerBox?.y ?? 0) + 2);
  await page.locator("#automations-trigger-modal-trigger-schedule-hour-input").selectOption("10");
  await page.locator("#automations-trigger-modal-trigger-schedule-minute-input").selectOption("45");
  await page.locator("#automations-trigger-modal-trigger-schedule-period-input").selectOption("AM");
  await expect(page.locator("#automations-trigger-modal-trigger-schedule-input")).toHaveText("10:45 AM");
  await page.locator("#automations-editor-modal-close").click();

  await page.locator("#automation-canvas-node-step-step-fetch-order").click({ button: "right" });
  await page.locator("#automations-node-menu-edit").click();
  await expect(page.locator("#automations-editor-modal")).toBeVisible();
  await page.locator("#automations-step-http-url-input").fill("https://api.example.com/orders/99");
  await page.locator("#automations-step-http-response-mapping-summary").click();
  await page.locator("#automations-step-http-sample-response-button").click();
  await expect(page.locator("#automations-step-http-json-tree-panel")).toBeVisible();
  await page.locator('#automations-step-http-select-data').click();
  await page.locator('[id="automations-step-http-select-data.customer"]').click();
  await expect(page.locator("#automations-step-http-mapping-row-1")).toBeVisible();
  await expect(page.locator("#automations-step-http-mapping-path-1")).toHaveText("data.customer");
  await page.locator("#automations-editor-modal-close").click();

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
  await expect(page.locator("#automations-run-button")).toHaveText("Done");
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
  test("shows loading state while saved connectors are fetched", async ({ page }) => {
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
    await page.locator("#add-step-type-api").click();
    await page.locator("#add-step-api-mode-prebuilt").click();

    await expect(page.locator("#add-step-connector-activity-connector-input")).toBeDisabled();
    await expect(page.locator("#add-step-connector-activity-connector-state")).toContainText("Loading saved connectors");
    await expect(page.locator("#add-step-connector-activity-connector-input")).toBeEnabled();
  });

  test("filters Google connector actions behind a Google app dropdown", async ({ page }) => {
    const state = createAutomationSuiteState({
      activityCatalog: [
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
      ]
    });
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-api").click({ force: true });
    await page.locator("#add-step-api-mode-prebuilt").click();
    await page.locator("#add-step-connector-activity-connector-input").selectOption("google-primary");

    await expect(page.locator("#add-step-connector-activity-service-input")).toBeVisible();
    await expect(page.locator("#add-step-connector-activity-activity-picker-empty")).toContainText("Choose a Google app");
    await expect(page.locator("#add-step-connector-activity-activity-card-gmail-send-email")).toHaveCount(0);

    await page.locator("#add-step-connector-activity-service-input").selectOption("gmail");
    await expect(page.locator("#add-step-connector-activity-group-gmail-write")).toBeVisible();
    await expect(page.locator("#add-step-connector-activity-activity-card-gmail-send-email")).toBeVisible();

    await page.locator("#add-step-connector-activity-service-input").selectOption("sheets");
    await expect(page.locator("#add-step-connector-activity-activity-card-gmail-send-email")).toHaveCount(0);
    await expect(page.locator("#add-step-connector-activity-activity-card-sheets-update-range")).toBeVisible();
  });

  test("shows empty state when no connectors are returned", async ({ page }) => {
    const state = createAutomationSuiteState();
    // simulate empty connector list
    state.connectorsResponseOverride = { status: 200, body: [] };
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-api").click();
    await page.locator("#add-step-api-mode-prebuilt").click();
    await expect(page.locator("#add-step-connector-activity-connector-state")).toContainText("No saved connectors found");
    const select = page.locator("#add-step-connector-activity-connector-input");
    await expect(select).toHaveValue("");
    await expect(select.locator('option')).toHaveCount(1);
  });

  test("shows error state when connector service fails", async ({ page }) => {
    const state = createAutomationSuiteState();
    // simulate server error for connector endpoint
    state.connectorsResponseOverride = { status: 500, body: { detail: "Simulated failure" } };
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-api").click();
    await page.locator("#add-step-api-mode-prebuilt").click();
    await expect(page.locator("#add-step-connector-activity-connector-error")).toContainText("Unable to load saved connectors");
    await expect(page.locator("#add-step-connector-activity-connector-retry")).toBeVisible();
  });

  test("disables incompatible connectors with reason text and tooltip", async ({ page }) => {
    const state = createAutomationSuiteState({
      activityCatalog: [
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
      ],
    });
    ((state.settings as Record<string, unknown>).connectors as { records: Array<Record<string, unknown>> }).records = [
      {
        id: "google-missing-scope",
        provider: "google",
        name: "Google Missing Scope",
        status: "connected",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      },
      {
        id: "google-primary",
        provider: "google",
        name: "Google Primary",
        status: "connected",
        auth_type: "oauth2",
        scopes: ["https://www.googleapis.com/auth/gmail.send"],
        owner: "Workspace",
        base_url: "https://www.googleapis.com",
      },
    ];
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-api").click();
    await page.locator("#add-step-api-mode-prebuilt").click();

    const incompatibleOption = page.locator('#add-step-connector-activity-connector-input option[value="google-missing-scope"]');
    await expect(incompatibleOption).toHaveAttribute("disabled", "");
    await expect(incompatibleOption).toHaveAttribute("title", /Missing required scopes/);
    await expect(page.locator("#add-step-connector-activity-connector-help")).toContainText("Disabled connectors are unavailable");
  });

  test("shows only active connectors in step modal", async ({ page }) => {
    const state = createAutomationSuiteState();
    ((state.settings as Record<string, unknown>).connectors as { records: Array<Record<string, unknown>> }).records = [
      {
        id: "google-primary",
        provider: "google",
        name: "Google Primary",
        status: "",
        auth_type: "oauth2",
        scopes: ["https://www.googleapis.com/auth/gmail.send"],
        owner: "Workspace",
        base_url: "https://www.googleapis.com"
      },
      {
        id: "google-expired",
        provider: "google",
        name: "Google Expired",
        status: "expired",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com"
      },
      {
        id: "google-revoked",
        provider: "google",
        name: "Google Revoked",
        status: "revoked",
        auth_type: "oauth2",
        scopes: [],
        owner: "Workspace",
        base_url: "https://www.googleapis.com"
      },
      {
        id: "github-draft",
        provider: "github",
        name: "GitHub Draft",
        status: "draft",
        auth_type: "bearer",
        scopes: ["repo"],
        owner: "Workspace",
        base_url: "https://api.github.com"
      }
    ];
    await installAutomationSuiteRoutes(page, state);

    await page.goto("/automations/builder.html?new=true");
    await page.locator("#automations-guided-item-step-action").click();
    await expect(page.locator("#add-step-modal")).toBeVisible();
    await page.locator("#add-step-type-api").click({ force: true });
    await page.locator("#add-step-api-mode-custom").click();

    const options = await page.locator("#add-step-http-connector-input option").allTextContents();
    for (const opt of options) {
      expect(opt.toLowerCase()).not.toContain("expired");
      expect(opt.toLowerCase()).not.toContain("revoked");
      expect(opt.toLowerCase()).not.toContain("draft");
    }
    await expect(page.locator("#add-step-http-connector-input")).toContainText("Google Primary");
  });
});
