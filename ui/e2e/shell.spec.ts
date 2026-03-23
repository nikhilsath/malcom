import { expect, test } from "@playwright/test";
import { installDashboardSettingsFixtures } from "./support/dashboard-settings";

test("keeps shared shell navigation active and persists sidebar collapse", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  await page.goto("/dashboard/home.html");

  await expect(page.locator("#nav-dashboard")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-dashboard-home")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Home");
  await expect(page.locator("#dashboard-overview-summary-queue-status-value")).toHaveText("Running");

  await page.locator("#sidebar-collapse-toggle").click();
  await expect(page.locator("body")).toHaveClass(/sidebar-collapsed/);
  await expect(page.locator("#sidebar-collapse-toggle")).toHaveAttribute("aria-label", "Expand sidebar");

  await page.locator("#nav-settings").click();

  await expect(page).toHaveURL(/\/settings\/workspace\.html$/);
  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("body")).toHaveClass(/sidebar-collapsed/);

  await page.locator("#page-info-badge").click();
  await expect(page.locator("#info-badge-popover")).toBeVisible();
  await expect(page.locator("#info-badge-popover")).toContainText("Configure workspace defaults.");

  await page.keyboard.press("Escape");
  await expect(page.locator("#info-badge-popover")).toBeHidden();
});

test("redirects legacy dashboard and settings routes to the canonical pages", async ({ page }) => {
  await installDashboardSettingsFixtures(page);

  const dashboardRedirects = [
    {
      route: "/dashboard/devices.html",
      url: /\/dashboard\/home\.html#\/devices$/,
      title: "Dashboard Devices",
      sidenavId: "#sidenav-dashboard-devices"
    },
    {
      route: "/dashboard/logs.html",
      url: /\/dashboard\/home\.html#\/logs$/,
      title: "Dashboard Logs",
      sidenavId: "#sidenav-dashboard-logs"
    },
    {
      route: "/dashboard/queue.html",
      url: /\/dashboard\/home\.html#\/queue$/,
      title: null,
      sidenavId: "#sidenav-dashboard-queue"
    }
  ];

  for (const redirect of dashboardRedirects) {
    await page.goto(redirect.route);

    await expect(page).toHaveURL(redirect.url);
    if (redirect.title) {
      await expect(page.locator("#nav-dashboard")).toHaveAttribute("aria-current", "page");
      await expect(page.locator(redirect.sidenavId)).toHaveAttribute("aria-current", "page");
      await expect(page.locator("#dashboard-page-title")).toHaveText(redirect.title);
    }
  }

  await page.goto("/settings/general.html");

  await expect(page).toHaveURL(/\/settings\/workspace\.html$/);
  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#page-title")).toHaveText("Settings Workspace");
});
