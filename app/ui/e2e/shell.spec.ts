import { expect, test, type Page } from "@playwright/test";

const hostedFrontendUrl = `http://127.0.0.1:${process.env.PLAYWRIGHT_HOSTED_FRONTEND_PORT || "4174"}/apps/host/index.html`;

const signIntoHostedFrontend = async (page: Page, baseURL: string) => {
  await page.goto(hostedFrontendUrl);
  await page.locator("#backend-url").fill(baseURL);
  await page.locator("#bootstrap-token").fill("playwright-platform-bootstrap");
  await page.locator("#operator-name").fill("Playwright Operator");
  await page.locator("#auth-form").getByRole("button", { name: "Sign In" }).click();
  await expect(page.locator("#route-title")).toHaveText("Dashboard");
};

const getIndicatorMetrics = async (page: Page, activeSelector: string) => {
  return page.evaluate((selector) => {
    const indicator = document.querySelector("#topnav-active-indicator");
    const activeLink = document.querySelector(selector);
    const nav = document.querySelector("#topnav-primary");

    if (!(indicator instanceof HTMLElement) || !(activeLink instanceof HTMLElement) || !(nav instanceof HTMLElement)) {
      return null;
    }

    const indicatorRect = indicator.getBoundingClientRect();
    const activeRect = activeLink.getBoundingClientRect();
    const navRect = nav.getBoundingClientRect();

    return {
      indicator: {
        x: indicatorRect.x,
        y: indicatorRect.y,
        width: indicatorRect.width,
        height: indicatorRect.height
      },
      active: {
        x: activeRect.x,
        y: activeRect.y,
        width: activeRect.width,
        height: activeRect.height
      },
      nav: {
        x: navRect.x,
        y: navRect.y,
        width: navRect.width,
        height: navRect.height
      },
      ready: nav.dataset.indicatorReady
    };
  }, activeSelector);
};

const expectIndicatorToAlign = async (page: Page, activeSelector: string) => {
  await expect
    .poll(async () => {
      const metrics = await getIndicatorMetrics(page, activeSelector);

      if (metrics?.ready !== "true") {
        return false;
      }

      return (
        Math.abs((metrics.indicator.x ?? 0) - (metrics.active.x ?? 0)) < 2 &&
        Math.abs((metrics.indicator.y ?? 0) - (metrics.active.y ?? 0)) < 2 &&
        Math.abs((metrics.indicator.width ?? 0) - (metrics.active.width ?? 0)) < 2 &&
        Math.abs((metrics.indicator.height ?? 0) - (metrics.active.height ?? 0)) < 2
      );
    })
    .toBe(true);
};

test("keeps shared shell navigation active and persists sidebar collapse", async ({ page }) => {
  await page.goto("/dashboard/home.html");

  await expect(page.locator("#nav-dashboard")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#topnav-active-indicator")).toBeVisible();
  await expect(page.locator("#nav-docs")).toBeVisible();
  await expect(page.locator("#sidenav-dashboard-home")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#dashboard-page-title")).toHaveText("Dashboard Home");
  await expectIndicatorToAlign(page, "#nav-dashboard");

  await page.locator("#sidebar-collapse-toggle").click();
  await expect(page.locator("body")).toHaveClass(/sidebar-collapsed/);
  await expect(page.locator("#sidebar-collapse-toggle")).toHaveAttribute("aria-label", "Expand sidebar");

  await page.locator("#nav-settings").click();

  await expect(page).toHaveURL(/\/settings\/workspace\.html$/);
  await expect(page.locator("#nav-settings")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#topnav-active-indicator")).toBeVisible();
  await expect(page.locator("#sidenav-settings-workspace")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("body")).toHaveClass(/sidebar-collapsed/);
  await expectIndicatorToAlign(page, "#nav-settings");

  await page.locator("#page-info-badge").click();
  await expect(page.locator("#info-badge-popover")).toBeVisible();
  await expect(page.locator("#info-badge-popover")).toContainText("Configure workspace defaults.");

  await page.keyboard.press("Escape");
  await expect(page.locator("#info-badge-popover")).toBeHidden();
});

test("redirects legacy dashboard and settings routes to the canonical pages", async ({ page }) => {
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

test("keeps the animated top-nav indicator aligned on narrow widths", async ({ page }) => {
  await page.setViewportSize({ width: 700, height: 900 });

  await page.goto("/dashboard/home.html");

  await expect(page.locator("#nav-dashboard")).toHaveAttribute("aria-current", "page");
  await expect(page.locator("#topnav-active-indicator")).toBeVisible();
  await expectIndicatorToAlign(page, "#nav-dashboard");

  const metrics = await getIndicatorMetrics(page, "#nav-dashboard");
  expect(metrics?.ready).toBe("true");
  expect((metrics?.indicator.width ?? 0)).toBeGreaterThan(0);
  expect((metrics?.indicator.height ?? 0)).toBeGreaterThan(0);
  expect((metrics?.indicator.x ?? 0)).toBeGreaterThanOrEqual((metrics?.nav.x ?? 0));
  expect((metrics?.indicator.y ?? 0)).toBeGreaterThanOrEqual((metrics?.nav.y ?? 0));
  expect((metrics?.indicator.x ?? 0) + (metrics?.indicator.width ?? 0)).toBeLessThanOrEqual((metrics?.nav.x ?? 0) + (metrics?.nav.width ?? 0) + 2);
  expect((metrics?.indicator.y ?? 0) + (metrics?.indicator.height ?? 0)).toBeLessThanOrEqual((metrics?.nav.y ?? 0) + (metrics?.nav.height ?? 0) + 2);
});

test("loads docs index and library routes", async ({ page }) => {
  await page.goto("/docs/index.html");
  await expect(page).toHaveURL(/\/docs\/index\.html$/);

  await page.goto("/docs/library.html");
  await expect(page).toHaveURL(/\/docs\/library\.html$/);
});

test("hosted frontend shell signs in and opens the builder compatibility route", async ({ page, baseURL }) => {
  await signIntoHostedFrontend(page, baseURL || "http://127.0.0.1:4173");

  await page.locator('.nav-button[data-route-path="/automations/builder"]').click();

  await expect(page.locator("#route-title")).toHaveText("Workflow Builder");
  await expect(page.locator("#platform-embed-status")).toBeVisible();
  await expect(page.locator("iframe")).toBeVisible();
  await expect(page.frameLocator("iframe").locator("#automations-builder-page-title")).toHaveText("Automation Builder");
  await expect.poll(async () => (await page.locator("#platform-embed-status").textContent()) || "").toMatch(
    /loaded|ready|height/i
  );
});
