import { expect, test } from "@playwright/test";

import { stubCoquiTtsTool, stubToolSettings } from "./support/tools";

test("shows a compact Coqui page, hides config while disabled, and saves runtime-backed selections", async ({ page }) => {
  await stubToolSettings(page);
  const coqui = await stubCoquiTtsTool(page);

  await page.goto("/tools/coqui-tts.html");

  await expect(page.locator("h2, h3").filter({ hasText: "Coqui TTS" })).toHaveCount(1);
  await expect(page.locator("#tools-coqui-config-region")).toBeHidden();
  await expect(page.locator("#tools-coqui-output-field")).toHaveCount(0);
  await expect(page.locator("#tools-coqui-status-value")).toHaveText("Ready");
  await expect(page.locator("#tools-coqui-summary-model-value")).toHaveText("tts_models/en/ljspeech/tacotron2-DDC");

  await page.locator("#tools-coqui-enabled-input").check();
  await expect(page.locator("#tools-coqui-config-region")).toBeVisible();

  await page.locator("#tools-coqui-model-input").selectOption("tts_models/en/vctk/vits");
  await expect(page.locator("#tools-coqui-speaker-input")).toHaveValue("");
  await expect(page.locator("#tools-coqui-speaker-input option")).toContainText(["Use model default speaker", "speaker-1", "speaker-2"]);
  await page.locator("#tools-coqui-speaker-input").selectOption("speaker-2");
  await page.locator("#tools-coqui-language-input").selectOption("en-us");
  await page.locator("#tools-coqui-save-button").click();

  await expect.poll(() => coqui.savedConfigs.length).toBe(1);
  expect(coqui.savedConfigs[0]).not.toHaveProperty("output_directory");
  await expect(page.locator("#tools-coqui-enabled-input")).toBeChecked();
  await expect(page.locator("#tools-coqui-summary-model-value")).toHaveText("tts_models/en/vctk/vits");
  await expect(page.locator("#tools-coqui-summary-voice-value")).toHaveText("speaker-2 / en-us");
  await expect(page.locator("#tools-coqui-form-feedback")).toHaveText("Coqui TTS configuration saved.");
});

test("shows an unavailable runtime state when Coqui is not installed on the host", async ({ page }) => {
  await stubToolSettings(page);
  await stubCoquiTtsTool(page, {
    runtime: {
      ready: false,
      command_available: false,
      message: "Coqui TTS command is not executable on this host: tts",
      command_options: [],
      model_options: [],
      speaker_options: [],
      language_options: []
    }
  });

  await page.goto("/tools/coqui-tts.html");

  await expect(page.locator("#tools-coqui-status-value")).toHaveText("Unavailable");
  await expect(page.locator("#tools-coqui-status-message")).toHaveText("Coqui TTS command is not executable on this host: tts");
  await page.locator("#tools-coqui-enabled-input").check();
  await expect(page.locator("#tools-coqui-command-input")).toBeDisabled();
  await expect(page.locator("#tools-coqui-model-input")).toBeDisabled();
});
