import { expect, test } from "@playwright/test";
import { installDashboardSettingsFixtures } from "./support/dashboard-settings";

test("saves and resets workspace defaults", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/settings/workspace.html");

  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");

  await page.locator("#settings-workspace-timezone-select").selectOption("utc");
  await page.locator("#settings-workspace-tool-retries-input").fill("4");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("utc");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("4");

  await page.locator("#settings-reset-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Default settings restored from the database.");
  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("local");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("2");
});

test("saves logging thresholds and clears stored logs", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/settings/logging.html");

  await expect(page.locator("#settings-log-total-value")).toHaveText("5");
  await expect(page.locator("#settings-log-newest-value")).not.toHaveText("No logs recorded");

  await page.locator("#settings-log-retention-input").fill("500");
  await page.locator("#settings-log-visible-input").fill("100");
  await page.locator("#settings-log-detail-input").fill("6000");
  await page.locator("#settings-log-file-size-input").fill("8");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-log-retention-input")).toHaveValue("500");
  await expect(page.locator("#settings-log-file-size-input")).toHaveValue("8");

  await page.locator("#settings-clear-logs-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Stored logs cleared.");
  await expect(page.locator("#settings-log-total-value")).toHaveText("1");
  await expect(page.locator("#settings-log-newest-value")).not.toHaveText("No logs recorded");
});

test("toggles notifications and restores the defaults", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/settings/notifications.html");

  await page.locator("#settings-notifications-channel-select").selectOption("email");
  await page.locator("#settings-notifications-digest-select").selectOption("daily");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-notifications-channel-select")).toHaveValue("email");
  await expect(page.locator("#settings-notifications-digest-select")).toHaveValue("daily");

  await page.locator("#settings-reset-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Default settings restored from the database.");
  await expect(page.locator("#settings-notifications-channel-select")).toHaveValue("email");
  await expect(page.locator("#settings-notifications-digest-select")).toHaveValue("hourly");
});

test("renders connector-backed storage and clears log table rows", async ({ page }) => {
  await installDashboardSettingsFixtures(page, {
    settings: {
      data: {
        payload_redaction: false,
        export_window_utc: "02:00"
      },
      connectors: {
        records: [
          {
            id: "google-drive-primary",
            provider: "google",
            name: "Google Drive",
            status: "connected",
            auth_type: "oauth2",
            scopes: ["https://www.googleapis.com/auth/drive"],
            base_url: "https://www.googleapis.com/drive/v3",
            owner: "Workspace",
            auth_config: {
              client_id: "google-client-id",
              client_secret_masked: "••••••••",
              access_token_masked: "••••••••"
            }
          }
        ]
      }
    }
  });

  await page.goto("/settings/data.html");

  await expect(page.locator("#settings-storage-local-database")).toBeVisible();
  await expect(page.locator("#settings-storage-connector-google-drive")).toBeVisible();
  await expect(page.locator("#settings-data-redaction-label")).toHaveText("Disabled");

  await page.locator("#settings-data-redaction-toggle").click();
  await expect(page.locator("#settings-data-redaction-label")).toHaveText("Enabled");

  await page.locator("#settings-storage-max-mb-input").fill("7");
  await page.locator("#settings-data-export-select").selectOption("04:00");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-storage-max-mb-input")).toHaveValue("7");
  await expect(page.locator("#settings-data-export-select")).toHaveValue("04:00");

  await expect(page.locator("#settings-log-storage-body")).toBeHidden();
  await page.locator("#settings-log-storage-collapse-toggle").click();
  await expect(page.locator("#settings-log-storage-body")).toBeVisible();
  await expect(page.locator("#settings-log-table-row-log-table-1")).toBeVisible();
  await expect(page.locator("#settings-log-table-count-log-table-1")).toHaveText("2 rows");
  await expect(page.locator("#settings-log-storage-view-link")).toHaveAttribute("href", "../automations/data.html");

  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });
  await page.locator("#settings-log-table-clear-log-table-1").click();

  await expect(page.locator("#settings-log-table-count-log-table-1")).toHaveText("0 rows");
});
