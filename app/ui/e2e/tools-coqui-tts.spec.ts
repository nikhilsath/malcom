import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

type CoquiOption = {
  disabled?: boolean;
  label?: string;
  value: string;
};

type CoquiConfig = {
  command?: string | null;
  enabled?: boolean;
  language?: string | null;
  model_name?: string | null;
  speaker?: string | null;
};

type CoquiRuntimeInstallationState = {
  installed?: boolean;
};

type CoquiRuntime = {
  command_available?: boolean;
  command_options?: CoquiOption[];
  installation?: CoquiRuntimeInstallationState | null;
  installation_state?: CoquiRuntimeInstallationState | null;
  language_options?: CoquiOption[];
  message?: string | null;
  model_options?: CoquiOption[];
  ready?: boolean;
  speaker_options?: CoquiOption[];
};

type CoquiToolResponse = {
  config: CoquiConfig;
  runtime?: CoquiRuntime | null;
};

const installTimeoutMs = 240000;

const isRuntimeInstalled = (tool: CoquiToolResponse) => {
  const installationState = tool.runtime?.installation ?? tool.runtime?.installation_state;
  if (typeof installationState?.installed === "boolean") {
    return installationState.installed;
  }

  return Boolean(tool.runtime?.ready || tool.runtime?.command_available);
};

const fetchCoquiTool = async (request: APIRequestContext): Promise<CoquiToolResponse> => {
  const response = await request.get("/api/v1/tools/coqui-tts");
  expect(response.ok()).toBeTruthy();
  return response.json();
};

const waitForRuntimeInstalledState = async (
  request: APIRequestContext,
  expectedInstalled: boolean,
) => {
  await expect
    .poll(
      async () => {
        const tool = await fetchCoquiTool(request);
        return isRuntimeInstalled(tool);
      },
      {
        message: `Expected Coqui installed state to become ${expectedInstalled}.`,
        timeout: installTimeoutMs
      },
    )
    .toBe(expectedInstalled);
};

const readSelectOptions = async (page: Page, selector: string): Promise<CoquiOption[]> =>
  page.locator(`${selector} option`).evaluateAll((nodes) =>
    nodes.map((node) => {
      const option = node as HTMLOptionElement;
      return {
        disabled: option.disabled,
        label: option.textContent?.trim() || option.value,
        value: option.value
      };
    })
  );

const pickRequiredValue = (options: CoquiOption[], fieldName: string) => {
  const value = options.find((option) => !option.disabled && option.value)?.value ?? "";
  expect(value, `Expected ${fieldName} to expose at least one selectable runtime option.`).not.toBe("");
  return value;
};

const pickOptionalValue = (options: CoquiOption[]) =>
  options.find((option) => !option.disabled && option.value)?.value ?? "";

const runRuntimeActionFromPage = async (
  page: Page,
  request: APIRequestContext,
  action: "install" | "remove",
) => {
  const expectedInstalled = action === "install";
  const buttonSelector = action === "install" ? "#tools-coqui-install-button" : "#tools-coqui-remove-button";
  const feedbackText =
    action === "install"
      ? "Coqui TTS install request completed."
      : "Coqui TTS removal request completed.";

  await page.locator(buttonSelector).click();
  await expect(page.locator("#tools-coqui-runtime-feedback")).toHaveText(feedbackText, {
    timeout: installTimeoutMs
  });
  await waitForRuntimeInstalledState(request, expectedInstalled);

  if (expectedInstalled) {
    await expect(page.locator("#tools-coqui-remove-button")).toBeEnabled({
      timeout: installTimeoutMs
    });
  } else {
    await expect(page.locator("#tools-coqui-install-button")).toBeEnabled({
      timeout: installTimeoutMs
    });
  }
};

const restoreOriginalState = async (request: APIRequestContext, originalTool: CoquiToolResponse) => {
  const expectedInstalled = isRuntimeInstalled(originalTool);
  const currentTool = await fetchCoquiTool(request);

  if (isRuntimeInstalled(currentTool) !== expectedInstalled) {
    const action = expectedInstalled ? "install" : "remove";
    const response = await request.post(`/api/v1/tools/coqui-tts/${action}`);
    expect(response.ok()).toBeTruthy();
    await waitForRuntimeInstalledState(request, expectedInstalled);
  }

  const payload: Record<string, string | boolean> = {
    enabled: Boolean(originalTool.config.enabled),
    language: originalTool.config.language || "",
    speaker: originalTool.config.speaker || ""
  };

  if (originalTool.config.command) {
    payload.command = originalTool.config.command;
  }
  if (originalTool.config.model_name) {
    payload.model_name = originalTool.config.model_name;
  }

  const response = await request.patch("/api/v1/tools/coqui-tts", {
    data: payload
  });
  expect(response.ok()).toBeTruthy();
};

test("installs, saves runtime-backed defaults, and removes Coqui TTS against the served app", async ({ page, playwright }) => {
  test.setTimeout(installTimeoutMs * 2);
  test.slow();

  await page.goto("/tools/coqui-tts.html");
  const cleanupRequest = await playwright.request.newContext({
    baseURL: new URL(page.url()).origin
  });
  const originalTool = await fetchCoquiTool(cleanupRequest);

  await expect(page.locator("h2, h3").filter({ hasText: "Coqui TTS" })).toHaveCount(1);
  await expect(page.locator("#tools-coqui-install-button")).toBeVisible();
  await expect(page.locator("#tools-coqui-remove-button")).toBeVisible();
  await expect(page.locator("#tools-coqui-config-region")).toBeHidden();

  try {
    if (isRuntimeInstalled(originalTool)) {
      await runRuntimeActionFromPage(page, cleanupRequest, "remove");
      await expect(page.locator("#tools-coqui-status-value")).toHaveText("Unavailable", {
        timeout: installTimeoutMs
      });
    }

    await runRuntimeActionFromPage(page, cleanupRequest, "install");
    await expect(page.locator("#tools-coqui-enabled-input")).not.toBeChecked();
    await page.locator("#tools-coqui-enabled-input").check();
    await expect(page.locator("#tools-coqui-config-region")).toBeVisible();
    await expect(page.locator("#tools-coqui-command-input")).toBeEnabled({
      timeout: installTimeoutMs
    });
    await expect(page.locator("#tools-coqui-model-input")).toBeEnabled({
      timeout: installTimeoutMs
    });

    const command = pickRequiredValue(
      await readSelectOptions(page, "#tools-coqui-command-input"),
      "command",
    );
    const modelName = pickRequiredValue(
      await readSelectOptions(page, "#tools-coqui-model-input"),
      "model",
    );
    const speaker = pickOptionalValue(await readSelectOptions(page, "#tools-coqui-speaker-input"));
    const language = pickOptionalValue(await readSelectOptions(page, "#tools-coqui-language-input"));

    await page.locator("#tools-coqui-command-input").selectOption(command);
    await page.locator("#tools-coqui-model-input").selectOption(modelName);
    if (speaker) {
      await page.locator("#tools-coqui-speaker-input").selectOption(speaker);
    }
    if (language) {
      await page.locator("#tools-coqui-language-input").selectOption(language);
    }

    await page.locator("#tools-coqui-save-button").click();
    await expect(page.locator("#tools-coqui-form-feedback")).toHaveText("Coqui TTS configuration saved.");
    await expect(page.locator("#tools-coqui-summary-model-value")).toHaveText(modelName);
    await expect
      .poll(
        async () => {
          const tool = await fetchCoquiTool(cleanupRequest);
          return {
            command: tool.config.command || "",
            enabled: Boolean(tool.config.enabled),
            installed: isRuntimeInstalled(tool),
            language: tool.config.language || "",
            model_name: tool.config.model_name || "",
            speaker: tool.config.speaker || ""
          };
        },
        {
          message: "Expected the saved Coqui runtime defaults to persist through the real backend.",
          timeout: installTimeoutMs
        },
      )
      .toMatchObject({
        command,
        enabled: true,
        installed: true,
        language,
        model_name: modelName,
        speaker
      });

    await runRuntimeActionFromPage(page, cleanupRequest, "remove");
    await expect(page.locator("#tools-coqui-status-value")).toHaveText("Unavailable", {
      timeout: installTimeoutMs
    });
  } finally {
    await restoreOriginalState(cleanupRequest, originalTool);
    await cleanupRequest.dispose();
  }
});
