import { expect, Page } from "@playwright/test";

export const defaultSettingsResponse = {
  general: {
    environment: "live",
    timezone: "local"
  },
  logging: {
    max_stored_entries: 250,
    max_visible_entries: 50,
    max_detail_characters: 4000,
    max_file_size_mb: 5
  },
  notifications: {
    channel: "slack",
    digest: "hourly"
  },
  data: {
    payload_redaction: true,
    export_window_utc: "02:00"
  },
  automation: {
    default_tool_retries: 2
  },
  connectors: {
    catalog: [
      {
        id: "google",
        name: "Google",
        description: "Google APIs",
        category: "productivity",
        auth_types: ["oauth2"],
        default_scopes: [
          "https://www.googleapis.com/auth/gmail.readonly"
        ],
        docs_url: "https://developers.google.com",
        base_url: "https://www.googleapis.com"
      },
      {
        id: "github",
        name: "GitHub",
        description: "GitHub APIs",
        category: "engineering",
        auth_types: ["bearer"],
        default_scopes: ["repo"],
        docs_url: "https://docs.github.com",
        base_url: "https://api.github.com"
      }
    ],
    records: [],
    auth_policy: {
      rotation_interval_days: 90,
      reconnect_requires_approval: true,
      credential_visibility: "masked"
    }
  }
};

export const defaultToolsDirectory = [
  {
    id: "smtp",
    name: "SMTP relay",
    description: "Send email through the local SMTP relay.",
    enabled: true,
    category: "messaging",
    route_path: "/tools/smtp.html"
  },
  {
    id: "llm-deepl",
    name: "Local LLM",
    description: "Chat against a local LLM endpoint.",
    enabled: true,
    category: "ai",
    route_path: "/tools/llm-deepl.html"
  },
  {
    id: "image-magic",
    name: "Image Magic",
    description: "Local image conversion runtime.",
    enabled: true,
    category: "media",
    route_path: "/tools/image-magic.html"
  },
  {
    id: "coqui-tts",
    name: "Coqui TTS",
    description: "Text-to-speech runtime.",
    enabled: true,
    category: "audio",
    route_path: "/tools/coqui-tts.html"
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
