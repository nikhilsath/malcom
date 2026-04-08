import { expect, Page } from "@playwright/test";
import { buildAppSettingsResponse } from "./api-response-builders.ts";

export const defaultSettingsResponse = buildAppSettingsResponse({
  notifications: {
    channel: "slack",
    digest: "hourly"
  }
});

export const defaultToolsDirectory = [
  {
    id: "smtp",
    name: "SMTP relay",
    description: "Send email through the local SMTP relay.",
    enabled: true,
    category: "messaging",
    page_href: "/tools/smtp.html",
    inputs: [],
    outputs: []
  },
  {
    id: "llm-deepl",
    name: "Local LLM",
    description: "Chat against a local LLM endpoint.",
    enabled: true,
    category: "ai",
    page_href: "/tools/llm-deepl.html",
    inputs: [],
    outputs: []
  },
  {
    id: "image-magic",
    name: "Image Magic",
    description: "Local image conversion runtime.",
    enabled: true,
    category: "media",
    page_href: "/tools/image-magic.html",
    inputs: [],
    outputs: []
  },
  {
    id: "coqui-tts",
    name: "Coqui TTS",
    description: "Text-to-speech runtime.",
    enabled: true,
    category: "audio",
    page_href: "/tools/coqui-tts.html",
    inputs: [],
    outputs: []
  }
];

function mergeJsonValue(base: unknown, override: unknown): unknown {
  if (Array.isArray(base) || Array.isArray(override)) {
    return override ?? base;
  }

  if (base && override && typeof base === "object" && typeof override === "object") {
    const mergedEntries = new Map<string, unknown>();

    for (const [key, value] of Object.entries(base)) {
      mergedEntries.set(key, value);
    }

    for (const [key, value] of Object.entries(override)) {
      mergedEntries.set(key, mergeJsonValue(mergedEntries.get(key), value));
    }

    return Object.fromEntries(mergedEntries);
  }

  return override ?? base;
}

export function buildSettingsResponse(overrides: Record<string, unknown> = {}) {
  return mergeJsonValue(defaultSettingsResponse, overrides);
}

export async function stubSettings(page: Page, overrides: Record<string, unknown> = {}) {
  const response = buildSettingsResponse(overrides);

  await page.route("**/api/v1/settings", async (route) => {
    const method = route.request().method();

    if (method === "GET" || method === "PATCH") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response)
      });
      return;
    }

    await route.fallback();
  });
}

export async function stubToolsDirectory(page: Page, tools = defaultToolsDirectory) {
  await page.route("**/api/v1/tools", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tools)
    });
  });
}

export async function acceptDialogs(page: Page) {
  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });
}

export async function seedRuntimeLogs(page: Page, entries: unknown[] = []) {
  await page.addInitScript((seededEntries) => {
    window.localStorage.setItem("malcom.runtimeLogs", JSON.stringify(seededEntries));
  }, entries);
}

export async function expectModalClosed(page: Page, selector: string) {
  await expect(page.locator(selector)).not.toHaveClass(/modal--open/);
}

export async function expectModalOpen(page: Page, selector: string) {
  await expect(page.locator(selector)).toHaveClass(/modal--open/);
}
