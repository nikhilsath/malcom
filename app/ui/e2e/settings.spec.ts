import { expect, test } from "@playwright/test";

test("saves and resets workspace defaults", async ({ page }) => {
  await page.goto("/settings/workspace.html");

  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");

  await page.locator("#settings-workspace-timezone-select").selectOption("utc");
  await page.locator("#settings-workspace-tool-retries-input").fill("4");
  await page.locator("#settings-workspace-proxy-domain-input").fill("tools.example.com");
  await page.locator("#settings-workspace-proxy-http-port-input").fill("8080");
  await page.locator("#settings-workspace-proxy-https-port-input").fill("8443");
  await page.locator("#settings-workspace-proxy-enabled-toggle").click();
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("utc");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("4");
  await expect(page.locator("#settings-workspace-proxy-domain-input")).toHaveValue("tools.example.com");
  await expect(page.locator("#settings-workspace-proxy-http-port-input")).toHaveValue("8080");
  await expect(page.locator("#settings-workspace-proxy-https-port-input")).toHaveValue("8443");
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Enabled");

  await page.locator("#settings-reset-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Default settings restored from the database.");
  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("local");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("2");
  await expect(page.locator("#settings-workspace-proxy-domain-input")).toHaveValue("");
  await expect(page.locator("#settings-workspace-proxy-http-port-input")).toHaveValue("80");
  await expect(page.locator("#settings-workspace-proxy-https-port-input")).toHaveValue("443");
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).not.toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Disabled");
});

test("autosaves proxy enabled toggle on change", async ({ page }) => {
  await page.goto("/settings/workspace.html");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");

  const initialChecked = await page.locator("#settings-workspace-proxy-enabled-checkbox").isChecked();

  if (initialChecked) {
    await page.locator("#settings-workspace-proxy-enabled-toggle").click();
    await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).not.toBeChecked();
    await page.locator("#settings-workspace-proxy-enabled-toggle").click();
  } else {
    await page.locator("#settings-workspace-proxy-enabled-toggle").click();
  }

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Enabled");

  await page.reload();

  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Enabled");
});

test("tests workspace proxy connection and shows feedback", async ({ page }) => {
  await page.goto("/settings/workspace.html");

  await page.locator("#settings-workspace-proxy-domain-input").fill("malcom.artuin.io");
  await page.locator("#settings-workspace-proxy-enabled-toggle").click();
  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");

  await page.locator("#settings-workspace-proxy-test-button").click();

  await expect(page.locator("#settings-workspace-proxy-test-feedback")).toBeVisible();
  await expect(page.locator("#settings-workspace-proxy-test-feedback")).toHaveAttribute("data-state", /(success|error)/);
});

test("saves logging thresholds and clears stored logs", async ({ page }) => {
  await page.goto("/settings/logging.html");

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
  await expect(page.locator("#settings-log-total-value")).toBeVisible();
  await expect(page.locator("#settings-log-newest-value")).toBeVisible();
});

test("toggles notifications and restores the defaults", async ({ page }) => {
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

test("saves and resets access security settings", async ({ page }) => {
  await page.goto("/settings/access.html");

  await expect(page.locator("#page-title")).toHaveText("Settings Access");

  await page.locator("#settings-access-session-select").selectOption("120");
  await page.locator("#settings-access-approval-checkbox").check();
  await page.locator("#settings-access-token-select").selectOption("90");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-access-session-select")).toHaveValue("120");
  await expect(page.locator("#settings-access-approval-checkbox")).toBeChecked();
  await expect(page.locator("#settings-access-token-select")).toHaveValue("90");

  await page.locator("#settings-reset-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Default settings restored from the database.");
  await expect(page.locator("#settings-access-session-select")).toHaveValue("60");
  await expect(page.locator("#settings-access-approval-checkbox")).not.toBeChecked();
  await expect(page.locator("#settings-access-token-select")).toHaveValue("30");
});

test("renders data settings page and toggles redaction", async ({ page }) => {
  await page.goto("/settings/data.html");

  await expect(page.locator("#settings-storage-locations")).toBeVisible();
  await expect(page.locator("#settings-backups-section")).toBeVisible();

  const currentLabel = await page.locator("#settings-data-redaction-label").textContent();
  await page.locator("#settings-data-redaction-toggle").click();
  const newLabel = currentLabel === "Enabled" ? "Disabled" : "Enabled";
  await expect(page.locator("#settings-data-redaction-label")).toHaveText(newLabel);

  await page.locator("#settings-save-button").click();
  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
});

test("creates and restores a local backup", async ({ page }) => {
  await page.goto("/settings/data.html");

  await expect(page.locator("#page-title")).toHaveText("Settings Data");
  await expect(page.locator("#settings-backups-section")).toBeVisible();
  await expect(page.locator("#backup-dir")).toBeVisible();

  const feedback = page.locator("#backup-feedback");
  const createBtn = page.locator("#create-backup-btn");
  const restoreBtn = page.locator("#restore-backup-btn");

  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });

  await createBtn.click();
  await expect(feedback).toContainText("Backup created:");

  await restoreBtn.click();
  await expect(feedback).toContainText("Restore succeeded:");
});

