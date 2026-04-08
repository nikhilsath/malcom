import { expect, test } from "@playwright/test";

import { stubImageMagicTool, stubToolCatalog, stubToolSettings } from "./support/tools";

test("opens a tool detail, edits metadata, enables it, and follows the config link", async ({ page }) => {
  await stubToolSettings(page);
  await stubImageMagicTool(page);
  const catalog = await stubToolCatalog(page);

  await page.goto("/tools/catalog.html");
  await expect(page.locator("#selected-tools-count")).toHaveText("4 loaded");

  await page.locator("#tool-card-image-magic").click();
  await expect(page.locator("#tool-detail-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#tool-detail-title")).toHaveText("Image Magic");
  await expect(page.locator("#tool-detail-enabled-copy")).toHaveText("Tool is disabled");
  await expect(page.locator("#tool-detail-config-link")).toBeHidden();

  await page.locator("#tool-detail-name-input").fill("Image Magic Pro");
  await page.locator("#tool-detail-description-input").fill("Convert and transform images locally.");
  await page.locator("#tool-detail-enabled-input").check();

  await expect(page.locator("#tool-detail-enabled-copy")).toHaveText("Tool is enabled");
  await expect(page.locator("#tool-card-image-magic-state")).toHaveText("Enabled");
  await expect(page.locator("#tool-detail-config-link")).toBeVisible();
  await expect(page.locator("#tool-detail-config-link")).toHaveAttribute("href", /\/tools\/image-magic\.html$/);
  await expect.poll(() => catalog.patches.length).toBeGreaterThan(0);

  await page.locator("#tool-detail-config-link").click();
  await expect(page).toHaveURL(/\/tools\/image-magic\.html$/);
  await expect(page.locator("#tools-image-magic-status-value")).toHaveText("Disabled");
});
