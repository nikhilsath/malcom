import { expect, test } from "@playwright/test";

import { stubLocalLlmTool, stubToolSettings } from "./support/tools";

test("applies a preset, saves the config, and streams a chat response", async ({ page }) => {
  await stubToolSettings(page);
  const llm = await stubLocalLlmTool(page);

  await page.goto("/tools/llm-deepl.html");
  await expect(page.locator("#tools-local-llm-status-value")).toHaveText("Enabled");
  await expect(page.locator("#tools-local-llm-summary-preset-value")).toHaveText("LM Studio API v1");
  await expect(page.locator("#tools-local-llm-endpoints-chat-value")).toHaveText("http://127.0.0.1:1234/api/v1/chat");

  await page.locator("#tools-local-llm-provider-input").selectOption("openai_compat");
  await page.locator("#tools-local-llm-apply-preset-button").click();
  await expect(page.locator("#tools-local-llm-server-input")).toHaveValue("http://127.0.0.1:11434");
  await expect(page.locator("#tools-local-llm-endpoints-chat-value")).toHaveText("http://127.0.0.1:11434/v1/chat/completions");

  await page.locator("#tools-local-llm-model-input").fill("llama3.2");
  await page.locator("#tools-local-llm-save-button").click();
  await expect.poll(() => llm.savedConfigs.length).toBe(1);
  await expect(page.locator("#tools-local-llm-summary-preset-value")).toHaveText("OpenAI-compatible");
  await expect(page.locator("#tools-local-llm-summary-model-value")).toHaveText("llama3.2");

  await page.locator("#tools-local-llm-chat-system-input").fill("Reply in one sentence.");
  await page.locator("#tools-local-llm-chat-user-input").fill("Hello model");
  await page.locator("#tools-local-llm-chat-send-button").click();

  await expect.poll(() => {
    const request = llm.getLastChatRequest() as { messages?: Array<{ role: string; content: string }> } | null;
    return request?.messages?.length || 0;
  }).toBe(2);
  const chatRequest = llm.getLastChatRequest() as { messages?: Array<{ role: string; content: string }> } | null;
  expect(chatRequest?.messages?.[0]?.role).toBe("system");
  expect(chatRequest?.messages?.[0]?.content).toBe("Reply in one sentence.");
  expect(chatRequest?.messages?.[1]?.role).toBe("user");
  expect(chatRequest?.messages?.[1]?.content).toBe("Hello model");

  await expect(page.locator("#tools-local-llm-chat-message-2")).toContainText("Local LLM reply: Hello model");
  await expect(page.locator("#tools-local-llm-chat-feedback")).toHaveText("Response received.");

  await page.locator("#tools-local-llm-chat-clear-button").click();
  await expect(page.locator("#tools-local-llm-chat-empty")).toBeVisible();
});
