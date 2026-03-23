import { expect, test } from "@playwright/test";

import { stubCoquiTtsTool, stubToolSettings } from "./support/tools";

test("shows client-side validation and saves the Coqui TTS configuration", async ({ page }) => {
  await stubToolSettings(page);
  const coqui = await stubCoquiTtsTool(page);

  await page.goto("/tools/coqui-tts.html");
  await expect(page.locator("#tools-coqui-status-value")).toHaveText("Disabled");
  await expect(page.locator("#tools-coqui-summary-model-value")).toHaveText("tts_models/en/ljspeech/tacotron2-DDC");

  await page.locator("#tools-coqui-command-input").fill("");
  await page.locator("#tools-coqui-save-button").click();
  await expect(page.locator("#tools-coqui-form-feedback")).toHaveText("Command, model name, and output directory are required.");

  await page.locator("#tools-coqui-enabled-input").selectOption("true");
  await page.locator("#tools-coqui-command-input").fill("tts");
  await page.locator("#tools-coqui-model-input").fill("tts_models/en/vctk/vits");
  await page.locator("#tools-coqui-output-input").fill("backend/data/generated/coqui-tts-alt");
  await page.locator("#tools-coqui-speaker-input").fill("speaker-2");
  await page.locator("#tools-coqui-language-input").fill("en-us");
  await page.locator("#tools-coqui-save-button").click();

  await expect.poll(() => coqui.savedConfigs.length).toBe(1);
  await expect(page.locator("#tools-coqui-status-value")).toHaveText("Enabled");
  await expect(page.locator("#tools-coqui-summary-model-value")).toHaveText("tts_models/en/vctk/vits");
  await expect(page.locator("#tools-coqui-summary-output-value")).toHaveText("backend/data/generated/coqui-tts-alt");
  await expect(page.locator("#tools-coqui-form-feedback")).toHaveText("Coqui TTS configuration saved.");
});
