import { expect, test } from "@playwright/test";
import { createAutomationSuiteState, installAutomationSuiteRoutes } from "./support/automations-scripts";

const codeMirrorSelectAllShortcut = process.platform === "darwin" ? "Meta+A" : "Control+A";

const replaceCodeMirrorContent = async (page: import("@playwright/test").Page, nextCode: string) => {
  const editor = page.locator("#scripts-library-editor .cm-content");
  await editor.click();
  await page.keyboard.press(codeMirrorSelectAllShortcut);
  await page.keyboard.type(nextCode);
};

test("filters scripts, edits an existing script, validates, and saves changes", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/scripts/library.html");

  await expect(page.locator("#scripts-library-summary-total-value")).toHaveText("2");
  await page.locator("#scripts-library-search-input").fill("delimiter");
  await expect(page.locator("#scripts-library-item-script-change-delimiter")).toBeVisible();
  await expect(page.locator("#scripts-library-item-script-normalize-summary")).toHaveCount(0);

  await page.locator("#scripts-library-search-input").fill("");
  await page.locator("#scripts-library-item-script-change-delimiter").click();
  await expect(page.locator("#scripts-library-editor-modal")).toHaveClass(/modal--open/);
  await expect(page.locator("#scripts-library-name-input")).toHaveValue("Change Delimiter");

  await page.locator("#scripts-library-language-input").selectOption("javascript");
  await replaceCodeMirrorContent(
    page,
    [
      "function run(context, scriptInput) {",
      "  const payload = context?.payload ?? {};",
      "  return scriptInput || payload;",
      "}",
      ""
    ].join("\n")
  );

  await page.locator("#scripts-library-validate-button").click();
  await expect(page.locator("#scripts-library-validation-chip")).toHaveText("Validated");
  await expect(page.locator("#scripts-library-validation-feedback")).toContainText("syntax check passed");

  await page.locator("#scripts-library-name-input").fill("Change Delimiter JS");
  await page.locator("#scripts-library-save-button").click();
  await expect(page.locator("#scripts-library-form-feedback")).toContainText("Script saved to the library.");
  await expect(page.locator("#scripts-library-name-input")).toHaveValue("Change Delimiter JS");
  await expect(page.locator("#scripts-library-item-script-change-delimiter")).toBeVisible();
});

test("creates a new script and switches the starter template language", async ({ page }) => {
  const state = createAutomationSuiteState();
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/scripts/library.html");
  await page.locator("#scripts-library-create-button").click();
  await expect(page.locator("#scripts-library-editor-modal")).toHaveClass(/modal--open/);

  await page.locator("#scripts-library-language-input").selectOption("javascript");
  await expect(page.locator("#scripts-library-editor .cm-content")).toContainText("function run(context, scriptInput)");

  await page.locator("#scripts-library-name-input").fill("Summarize Payload");
  await page.locator("#scripts-library-description-input").fill("Summarizes a payload for downstream steps.");
  await page.locator("#scripts-library-sample-input-input").fill("{\"text\":\"alpha\"}");
  await replaceCodeMirrorContent(
    page,
    [
      "function run(context, scriptInput) {",
      "  return scriptInput || context.payload;",
      "}",
      ""
    ].join("\n")
  );

  await page.locator("#scripts-library-save-button").click();
  await expect(page.locator("#scripts-library-form-feedback")).toContainText("Script saved to the library.");
  await expect(page.locator("#scripts-library-script-id-input")).not.toHaveValue("");
  await expect(page.locator("#scripts-library-name-input")).toHaveValue("Summarize Payload");
  await expect(page.locator("#scripts-library-summary-total-value")).toHaveText("3");
});

test("shows empty and validation error states for scripts", async ({ page }) => {
  const state = createAutomationSuiteState({ scripts: [] });
  await installAutomationSuiteRoutes(page, state);

  await page.goto("/scripts/library.html");
  await expect(page.locator("#scripts-library-empty")).toBeVisible();
  await expect(page.locator("#scripts-library-summary-total-value")).toHaveText("0");

  await page.locator("#scripts-library-create-button").click();
  await page.locator("#scripts-library-language-input").selectOption("javascript");
  await replaceCodeMirrorContent(
    page,
    [
      "function buildPayload() {",
      "  return { ok: true };",
      "}",
      ""
    ].join("\n")
  );

  await page.locator("#scripts-library-validate-button").click();
  await expect(page.locator("#scripts-library-validation-chip")).toHaveText("Needs fixes");
  await expect(page.locator("#scripts-library-validation-feedback")).toContainText("Source code must define a run function.");
});
