import { expect, test } from "@playwright/test";

const logTablesResponse = [
  {
    id: "log-table-1",
    name: "Delivery audit",
    description: "Rows captured from a log step.",
    row_count: 2,
    created_at: "2026-03-20T09:00:00.000Z",
    updated_at: "2026-03-21T10:00:00.000Z"
  }
];

const logTableRowsResponse = {
  table_id: "log-table-1",
  table_name: "Delivery audit",
  columns: ["row_id", "status"],
  rows: [
    { row_id: 1, status: "ok" },
    { row_id: 2, status: "warning" }
  ],
  total: 2
};

const scriptsListResponse = [
  {
    id: "script-change-delimiter",
    name: "Change Delimiter",
    description: "Split text on one delimiter and join it with another.",
    language: "python",
    sample_input: "{\n  \"text\": \"alpha,beta,gamma\"\n}",
    validation_status: "valid",
    validation_message: null,
    last_validated_at: "2026-03-20T09:00:00.000Z",
    created_at: "2026-03-19T09:00:00.000Z",
    updated_at: "2026-03-21T10:00:00.000Z"
  }
];

const scriptRecordResponse = {
  ...scriptsListResponse[0],
  code: [
    "def run(context, script_input=None):",
    "    payload = context.get('payload', {})",
    "    return script_input or payload",
    ""
  ].join("\n")
};

test("loads the dashboard home route", async ({ page }) => {
  await page.goto("/dashboard/home.html");
  await expect(page.locator("#dashboard-react-root")).toBeVisible();
  await expect(page.getByText("Dashboard Home")).toBeVisible();
});

test("loads the workspace settings page", async ({ page }) => {
  await page.goto("/settings/workspace.html");
  await expect(page.locator("#settings-workspace-title")).toHaveText("Workspace defaults");
  await expect(page.locator("#settings-save-button")).toBeVisible();
});

test("loads the data settings page and expands log storage", async ({ page }) => {
  await page.route("**/api/v1/log-tables", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(logTablesResponse)
    });
  });

  await page.goto("/settings/data.html");
  await expect(page.locator("#settings-data-title")).toHaveText("Data handling");
  await expect(page.locator("#settings-storage-max-mb-input")).toBeVisible();
  await page.waitForSelector("#settings-storage-local-database");
  await expect(page.locator("#settings-storage-local-database")).toBeVisible();
  await expect(page.locator("#settings-storage-local-logs")).toBeVisible();

  await page.locator("#settings-log-storage-collapse-toggle").click();
  await expect(page.locator("#settings-log-storage-body")).toBeVisible();
  await expect(page.locator("#settings-log-storage-hint")).toHaveText("View or clear log tables.");
  await expect(page.locator("#settings-log-storage-view-link")).toBeVisible();
  await expect(page.locator("#settings-log-table-row-log-table-1")).toBeVisible();
  await expect(page.locator("#settings-log-table-name-log-table-1")).toHaveText("Delivery audit");
});

test("connect provider opens Google connector draft", async ({ page }) => {
  await page.goto("/settings/connectors.html");
  await expect(page.locator("#settings-connectors-create-button")).toBeVisible();

  await page.locator("#settings-connectors-create-button").click();
  await expect(page.locator("#settings-connectors-modal")).toHaveClass(/modal--open/);

  await page.locator("#settings-connectors-provider-option-google").click();
  await expect(page.locator("#settings-connectors-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#settings-connectors-detail-title")).toHaveText("Google OAuth setup");
  await expect(page.locator("#settings-connectors-name-input")).not.toHaveValue("");
  await expect(page.locator("#settings-connectors-redirect-uri-input")).toBeEditable();
  await expect(page.locator("#settings-connectors-redirect-uri-input")).toHaveValue(/\/api\/v1\/connectors\/google\/oauth\/callback$/);
  await expect(page.locator("#settings-connectors-feedback")).not.toContainText("422");
});

test("loads the tools catalog page", async ({ page }) => {
  await page.goto("/tools/catalog.html");
  await expect(page.locator("#tools-selection-title")).toHaveText("Select a tool");
  await expect(page.locator("#tools-grid")).toBeVisible();
});

test("loads the API registry page", async ({ page }) => {
  await page.goto("/apis/registry.html");
  await expect(page.locator("#apis-overview-content-title")).toHaveText("Configured API surfaces");
  await expect(page.locator("#apis-overview-action-grid")).toBeVisible();
});

test("loads the automation builder page", async ({ page }) => {
  await page.goto("/automations/builder.html?new=true");
  await expect(page.locator("#automations-builder-page-title")).toHaveText("Automation Builder");
  await expect(page.locator("#automations-react-root")).toBeVisible();
  await expect(page.locator("#automations-workflow-bar")).toBeVisible();
  await expect(page.locator("#automations-canvas-panel")).toBeVisible();
});

test("loads the automations log data page", async ({ page }) => {
  await page.route("**/api/v1/log-tables/log-table-1/rows?*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(logTableRowsResponse)
    });
  });
  await page.route("**/api/v1/log-tables", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(logTablesResponse)
    });
  });

  await page.goto("/automations/data.html");
  await expect(page.locator("#automations-data-page-title")).toHaveText("Log Data");
  await expect(page.locator("#automations-data-root")).toBeVisible();
  await expect(page.locator("#automations-data-directory")).toBeVisible();
  await expect(page.locator("#automations-data-select-hint")).toBeVisible();
  await expect(page.locator("#automations-data-table-log-table-1")).toBeVisible();

  await page.locator("#automations-data-table-log-table-1").click();
  await expect(page.locator("#automations-data-modal")).toBeVisible();
  await expect(page.locator("#automations-data-total-hint")).toContainText("Showing 2 of 2 rows");
  await expect(page.locator("#automations-data-cell-2-status")).toHaveText("warning");
  await page.locator("#automations-data-modal-close").click();
  await expect(page.locator("#automations-data-modal")).toBeHidden();
});

test("loads the script library page and opens the editor modal", async ({ page }) => {
  await page.route("**/api/v1/scripts/script-change-delimiter", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(scriptRecordResponse)
    });
  });
  await page.route("**/api/v1/scripts", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(scriptsListResponse)
    });
  });

  await page.goto("/scripts/library.html");
  await expect(page.locator("#scripts-library-content-title")).toHaveText("Reusable scripts");
  await expect(page.locator("#scripts-library-summary-grid")).toBeVisible();
  await expect(page.locator("#scripts-library-summary-total-value")).toHaveText("1");
  await expect(page.locator("#scripts-library-item-script-change-delimiter")).toBeVisible();

  await page.locator("#scripts-library-item-script-change-delimiter").click();
  await expect(page.locator("#scripts-library-editor-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#scripts-library-name-input")).toHaveValue("Change Delimiter");
  await expect(page.locator("#scripts-library-language-input")).toHaveValue("python");
  await page.locator("#scripts-library-editor-modal-close").click();
  await expect(page.locator("#scripts-library-editor-modal")).not.toHaveClass(/modal--open/);

  await page.locator("#scripts-library-create-button").click();
  await expect(page.locator("#scripts-library-editor-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#scripts-library-name-input")).toHaveValue("");
  await expect(page.locator("#scripts-library-editor")).toBeVisible();
  await expect(page.locator("#scripts-library-script-id-input")).toHaveValue("");
});
