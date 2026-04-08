import { expect, test } from "@playwright/test";

import { stubImageMagicTool, stubToolSettings } from "./support/tools";

test("rejects a bad local enablement command, then saves a remote assignment", async ({ page }) => {
  await stubToolSettings(page);
  const imageMagic = await stubImageMagicTool(page);

  await page.goto("/tools/image-magic.html");
  await expect(page.locator("#tools-image-magic-status-value")).toHaveText("Disabled");
  await expect(page.locator("#tools-image-magic-default-retries-value")).toHaveText("2");

  await page.locator("#tools-image-magic-machine-input").selectOption("worker-local-1");
  await expect(page.locator("#tools-image-magic-status-message")).toContainText("Local Worker");

  await page.locator("#tools-image-magic-command-input").fill("missing-magick");
  await page.locator("#tools-image-magic-enabled-input").check();
  await page.locator("#tools-image-magic-save-button").click();

  await expect(page.locator("#tools-image-magic-form-feedback")).toContainText("Image Magic command is not executable on this host: missing-magick");
  await expect(page.locator("#tools-image-magic-form-feedback")).toContainText("Install ImageMagick on this host or update the command before enabling the tool.");

  await page.locator("#tools-image-magic-machine-input").selectOption("worker-remote-1");
  await expect(page.locator("#tools-image-magic-status-message")).toContainText("Remote Worker");
  await page.locator("#tools-image-magic-command-input").fill("magick");
  await page.locator("#tools-image-magic-save-button").click();

  await expect.poll(() => imageMagic.savedConfigs.length).toBe(2);
  await expect(page.locator("#tools-image-magic-status-value")).toHaveText("Enabled");
  await expect(page.locator("#tools-image-magic-form-feedback")).toHaveText("Settings saved.");
});
