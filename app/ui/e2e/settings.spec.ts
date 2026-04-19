import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const hostedFrontendUrl = `http://127.0.0.1:${process.env.PLAYWRIGHT_HOSTED_FRONTEND_PORT || "4174"}/apps/host/index.html`;

const defaultSettingsPayload = {
  general: {
    environment: "live",
    timezone: "local"
  },
  logging: {
    max_stored_entries: 250,
    max_visible_entries: 50,
    max_detail_characters: 4000,
    max_file_size_mb: 5
  },
  notifications: {
    channel: "email",
    digest: "hourly"
  },
  security: {
    session_timeout_minutes: 60,
    dual_approval_required: false,
    token_rotation_days: 30
  },
  data: {
    payload_redaction: true,
    export_window_utc: "02:00",
    workflow_storage_path: "data/workflows"
  },
  automation: {
    default_tool_retries: 2
  },
  proxy: {
    domain: "",
    http_port: 80,
    https_port: 443,
    enabled: false
  }
};

const resetSettings = async (request: APIRequestContext) => {
  const response = await request.patch("/api/v1/settings", {
    data: defaultSettingsPayload
  });
  expect(response.ok()).toBeTruthy();
};

const seedBrowserLogs = async (page: Page) => {
  await page.addInitScript((entries) => {
    window.localStorage.setItem("malcom.runtimeLogs", JSON.stringify(entries));
  }, [
    {
      id: "log-settings-seeded-1",
      timestamp: "2026-04-11T09:00:00.000Z",
      level: "info",
      source: "system.bootstrap",
      category: "runtime",
      action: "startup",
      message: "Client runtime booted.",
      details: {},
      context: {}
    },
    {
      id: "log-settings-seeded-2",
      timestamp: "2026-04-11T09:05:00.000Z",
      level: "warning",
      source: "system.settings",
      category: "configuration",
      action: "defaults_loaded",
      message: "Defaults loaded.",
      details: {},
      context: {}
    },
    {
      id: "log-settings-seeded-3",
      timestamp: "2026-04-11T09:10:00.000Z",
      level: "error",
      source: "runtime.queue",
      category: "runtime",
      action: "queue_paused",
      message: "Queue paused.",
      details: {},
      context: {}
    }
  ]);
};

const createStorageLocation = async (request: APIRequestContext, id: string, name: string) => {
  const response = await request.post("/api/v1/storage/locations", {
    data: {
      id,
      name,
      location_type: "local",
      path: `/tmp/${id}`,
      max_size_mb: 512,
      is_default_logs: false
    }
  });
  expect(response.ok()).toBeTruthy();
};

const signIntoHostedFrontend = async (page: Page, baseURL: string) => {
  await page.goto(hostedFrontendUrl);
  await page.locator("#backend-url").fill(baseURL);
  await page.locator("#bootstrap-token").fill("playwright-platform-bootstrap");
  await page.locator("#operator-name").fill("Playwright Operator");
  await page.locator("#auth-form").getByRole("button", { name: "Sign In" }).click();
  await expect(page.locator("#route-title")).toHaveText("Dashboard");
};

test("saves and resets workspace defaults against the real settings API", async ({ page, request }) => {
  await resetSettings(request);

  await page.goto("/settings/workspace.html");

  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");

  await page.locator("#settings-workspace-timezone-select").selectOption("utc");
  await page.locator("#settings-workspace-tool-retries-input").fill("4");
  await page.locator("#settings-workspace-proxy-domain-input").fill("tools.example.com");
  await page.locator("#settings-workspace-proxy-http-port-input").fill("8080");
  await page.locator("#settings-workspace-proxy-https-port-input").fill("8443");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("utc");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("4");
  await expect(page.locator("#settings-workspace-proxy-domain-input")).toHaveValue("tools.example.com");
  await expect(page.locator("#settings-workspace-proxy-http-port-input")).toHaveValue("8080");
  await expect(page.locator("#settings-workspace-proxy-https-port-input")).toHaveValue("8443");

  await page.reload();

  await expect(page.locator("#settings-workspace-timezone-select")).toHaveValue("utc");
  await expect(page.locator("#settings-workspace-tool-retries-input")).toHaveValue("4");
  await expect(page.locator("#settings-workspace-proxy-domain-input")).toHaveValue("tools.example.com");

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

test("hosted frontend shell renders the settings plugin surface after sign-in", async ({ page, baseURL }) => {
  await signIntoHostedFrontend(page, baseURL || "http://127.0.0.1:4173");

  await page.locator('.nav-button[data-route-path="/settings"]').click();

  await expect(page.locator("#route-title")).toHaveText("Settings");
  await expect(page.locator("#route-root")).toContainText("admin surfaces run with workspace layout requirements");
  await expect(page.locator("#route-root")).toContainText("Connectors");
  await expect(page.locator("#route-root")).toContainText("Storage");
});

test("autosaves proxy enabled toggle through the real settings API", async ({ page, request }) => {
  await resetSettings(request);

  await page.goto("/settings/workspace.html");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).not.toBeChecked();

  await page.locator("#settings-workspace-proxy-enabled-toggle").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Enabled");

  await page.reload();

  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).toBeChecked();
  await expect(page.locator("#settings-workspace-proxy-enabled-label")).toHaveText("Enabled");

  await page.locator("#settings-reset-button").click();
  await expect(page.locator("#settings-workspace-proxy-enabled-checkbox")).not.toBeChecked();
});

test("saves logging thresholds and clears browser-stored logs", async ({ page, request }) => {
  await resetSettings(request);
  await seedBrowserLogs(page);

  await page.goto("/settings/logging.html");

  await expect.poll(async () => Number.parseInt((await page.locator("#settings-log-total-value").textContent()) || "0", 10)).toBeGreaterThanOrEqual(3);
  await expect(page.locator("#settings-log-newest-value")).not.toHaveText("No logs recorded");

  await page.locator("#settings-log-retention-input").fill("500");
  await page.locator("#settings-log-visible-input").fill("100");
  await page.locator("#settings-log-detail-input").fill("6000");
  await page.locator("#settings-log-file-size-input").fill("8");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-log-retention-input")).toHaveValue("500");
  await expect(page.locator("#settings-log-file-size-input")).toHaveValue("8");

  await page.reload();

  await expect(page.locator("#settings-log-retention-input")).toHaveValue("500");
  await expect(page.locator("#settings-log-file-size-input")).toHaveValue("8");

  await page.locator("#settings-clear-logs-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Stored logs cleared.");
  await expect(page.locator("#settings-log-total-value")).toHaveText("1");
  await expect(page.locator("#settings-log-newest-value")).not.toHaveText("No logs recorded");
});

test("toggles notifications and restores the defaults against the real settings API", async ({ page, request }) => {
  await resetSettings(request);

  await page.goto("/settings/notifications.html");

  await page.locator("#settings-notifications-channel-select").selectOption("pager");
  await page.locator("#settings-notifications-digest-select").selectOption("daily");
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-notifications-channel-select")).toHaveValue("pager");
  await expect(page.locator("#settings-notifications-digest-select")).toHaveValue("daily");

  await page.locator("#settings-reset-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Default settings restored from the database.");
  await expect(page.locator("#settings-notifications-channel-select")).toHaveValue("email");
  await expect(page.locator("#settings-notifications-digest-select")).toHaveValue("hourly");
});

test("saves payload redaction settings from the data page and keeps the toggle active", async ({ page, request }) => {
  await resetSettings(request);

  await page.goto("/settings/data.html");

  await expect(page.locator("#page-title")).toHaveText("Settings Data");
  await expect(page.locator("#settings-data-redaction-description")).not.toContainText("Coming soon");
  await expect(page.locator("#settings-data-redaction-checkbox")).toBeChecked();
  await expect(page.locator("#settings-data-redaction-label")).toHaveText("Enabled");

  await page.locator("#settings-data-redaction-toggle").click();
  await page.locator("#settings-save-button").click();

  await expect(page.locator("#settings-feedback")).toHaveText("Settings saved to the database.");
  await expect(page.locator("#settings-data-redaction-checkbox")).not.toBeChecked();
  await expect(page.locator("#settings-data-redaction-label")).toHaveText("Disabled");

  const response = await request.get("/api/v1/settings");
  expect(response.ok()).toBeTruthy();
  const settings = await response.json();
  expect(settings.data.payload_redaction).toBe(false);

  await page.reload();

  await expect(page.locator("#settings-data-redaction-checkbox")).not.toBeChecked();
  await expect(page.locator("#settings-data-redaction-label")).toHaveText("Disabled");
});

test("saves and resets access security settings against the real settings API", async ({ page, request }) => {
  await resetSettings(request);

  await page.goto("/settings/access.html");

  await expect(page.locator("#page-title")).toHaveText("Settings Access");
  await expect(page.locator("#settings-access-session-select")).toHaveValue("60");
  await expect(page.locator("#settings-access-approval-checkbox")).not.toBeChecked();
  await expect(page.locator("#settings-access-token-select")).toHaveValue("30");

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

test("renders real storage locations and creates plus restores a local backup", async ({ page, request }) => {
  const locationId = `loc_settings_${Date.now()}`;
  await createStorageLocation(request, locationId, "Playwright Storage");

  await page.goto("/settings/data.html");

  await expect(page.locator("#page-title")).toHaveText("Settings Data");
  await expect(page.locator("#settings-storage-locations")).toBeVisible();
  await expect(page.locator("#settings-storage-locations-list")).toContainText("Playwright Storage");
  await expect(page.locator("#settings-backups-section")).toBeVisible();
  await expect(page.locator("#backup-dir")).not.toContainText("Loading");

  const feedback = page.locator("#backup-feedback");
  const createButton = page.locator("#create-backup-btn");
  const restoreButton = page.locator("#restore-backup-btn");
  const backupOptions = page.locator("#backup-list option");
  const initialBackupCount = await backupOptions.count();

  await createButton.click();

  await expect(feedback).toContainText("Backup created:");
  await expect.poll(async () => backupOptions.count()).toBeGreaterThan(initialBackupCount);
  await expect(restoreButton).toBeEnabled();

  page.once("dialog", async (dialog) => {
    await dialog.accept();
  });
  await restoreButton.click();

  await expect(feedback).toContainText("Restore succeeded:");
});
