import type { Page, Route } from "@playwright/test";

type JsonObject = Record<string, unknown>;

type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends (infer U)[] ? U[]
    : T[K] extends object ? DeepPartial<T[K]>
      : T[K];
};

export type ToolDirectoryEntry = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  page_href: string;
};

type RuntimeMachine = {
  id: string;
  name: string;
  address: string;
  hostname: string;
  status: string;
  capabilities: string[];
  is_local: boolean;
};

type SmtpMessage = {
  id: string;
  received_at: string;
  mail_from: string;
  recipients: string[];
  peer: string;
  size_bytes: number;
  subject: string;
  body_preview: string;
  body: string;
  raw_message: string;
};

type SmtpToolState = {
  tool_id: "smtp";
  config: {
    enabled: boolean;
    target_worker_id: string | null;
    bind_host: string;
    port: number;
    recipient_email: string | null;
  };
  runtime: {
    status: "stopped" | "running" | "assigned" | "error";
    message: string;
    listening_host: string | null;
    listening_port: number | null;
    selected_machine_id: string | null;
    selected_machine_name: string | null;
    last_started_at: string | null;
    last_stopped_at: string | null;
    last_error: string | null;
    session_count: number;
    message_count: number;
    last_message_at: string | null;
    last_mail_from: string | null;
    last_recipient: string | null;
    recent_messages: SmtpMessage[];
  };
  inbound_identity: {
    display_address: string;
    configured_recipient_email: string | null;
    accepts_any_recipient: boolean;
    listening_host: string | null;
    listening_port: number | null;
    connection_hint: string;
  };
  machines: RuntimeMachine[];
};

type LocalLlmPreset = {
  id: string;
  label: string;
  server_base_url: string;
  endpoints: {
    models: string;
    chat: string;
    model_load: string;
    model_download: string;
    model_download_status: string;
  };
};

type LocalLlmToolState = {
  tool_id: "llm-deepl";
  config: {
    enabled: boolean;
    provider: string;
    server_base_url: string;
    model_identifier: string;
    endpoints: {
      models: string;
      chat: string;
      model_load: string;
      model_download: string;
      model_download_status: string;
    };
  };
  presets: LocalLlmPreset[];
};

type ImageMagicToolState = {
  tool_id: "image-magic";
  config: {
    enabled: boolean;
    target_worker_id: string | null;
    command: string;
    default_retries: number;
  };
  machines: RuntimeMachine[];
};

type CoquiTtsToolState = {
  tool_id: "coqui-tts";
  config: {
    enabled: boolean;
    command: string;
    model_name: string;
    speaker: string;
    language: string;
    output_directory: string;
  };
};

const deepClone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const mergeDeep = <T>(base: T, override: DeepPartial<T>): T => {
  const clonedBase = deepClone(base);

  const mergeValue = (target: unknown, next: unknown): unknown => {
    if (Array.isArray(next)) {
      return deepClone(next);
    }

    if (next && typeof next === "object" && !Array.isArray(next)) {
      const nextObject = next as JsonObject;
      const targetObject = (target && typeof target === "object" && !Array.isArray(target) ? target : {}) as JsonObject;
      const merged: JsonObject = { ...targetObject };

      for (const [key, value] of Object.entries(nextObject)) {
        merged[key] = mergeValue(targetObject[key], value);
      }

      return merged;
    }

    return next === undefined ? target : next;
  };

  return mergeValue(clonedBase, override) as T;
};

const defaultSettingsResponse = {
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
    digest: "hourly",
    escalate_oncall: true
  },
  security: {
    session_timeout_minutes: 30,
    dual_approval_required: true,
    token_rotation_days: 90
  },
  data: {
    payload_redaction: true,
    export_window_utc: "02:00"
  },
  automation: {
    default_tool_retries: 2
  },
  connectors: {
    catalog: [],
    records: [],
    auth_policy: {
      rotation_interval_days: 90,
      reconnect_requires_approval: true,
      credential_visibility: "masked"
    }
  }
};

const defaultTools: ToolDirectoryEntry[] = [
  {
    id: "smtp",
    name: "SMTP relay",
    description: "Send email through the local SMTP relay.",
    enabled: true,
    page_href: "/tools/smtp.html"
  },
  {
    id: "llm-deepl",
    name: "Local LLM",
    description: "Chat against a local LLM endpoint.",
    enabled: true,
    page_href: "/tools/llm-deepl.html"
  },
  {
    id: "image-magic",
    name: "Image Magic",
    description: "Local image conversion runtime.",
    enabled: false,
    page_href: "/tools/image-magic.html"
  },
  {
    id: "coqui-tts",
    name: "Coqui TTS",
    description: "Text-to-speech runtime.",
    enabled: true,
    page_href: "/tools/coqui-tts.html"
  }
];

const defaultMachines: RuntimeMachine[] = [
  {
    id: "worker-local-1",
    name: "Local Worker",
    address: "127.0.0.1",
    hostname: "local-worker",
    status: "online",
    capabilities: ["smtp", "filesystem", "image-magic"],
    is_local: true
  },
  {
    id: "worker-remote-1",
    name: "Remote Worker",
    address: "10.0.0.42",
    hostname: "remote-worker",
    status: "online",
    capabilities: ["image-magic"],
    is_local: false
  }
];

const defaultSmtpToolState: SmtpToolState = {
  tool_id: "smtp",
  config: {
    enabled: true,
    target_worker_id: "worker-local-1",
    bind_host: "127.0.0.1",
    port: 2525,
    recipient_email: "inbox@example.com"
  },
  runtime: {
    status: "running",
    message: "SMTP listener running locally.",
    listening_host: "127.0.0.1",
    listening_port: 2525,
    selected_machine_id: "worker-local-1",
    selected_machine_name: "Local Worker",
    last_started_at: "2026-03-20T09:00:00.000Z",
    last_stopped_at: null,
    last_error: null,
    session_count: 1,
    message_count: 2,
    last_message_at: "2026-03-20T10:00:00.000Z",
    last_mail_from: "alice@example.com",
    last_recipient: "inbox@example.com",
    recent_messages: [
      {
        id: "smtp-message-2",
        received_at: "2026-03-20T10:00:00.000Z",
        mail_from: "alice@example.com",
        recipients: ["inbox@example.com"],
        peer: "127.0.0.1:51234",
        size_bytes: 2048,
        subject: "Invoice ready",
        body_preview: "Invoice attachment available.",
        body: "Invoice attachment available.",
        raw_message: "Subject: Invoice ready\n\nInvoice attachment available."
      },
      {
        id: "smtp-message-1",
        received_at: "2026-03-20T09:30:00.000Z",
        mail_from: "bob@example.com",
        recipients: ["inbox@example.com"],
        peer: "127.0.0.1:51235",
        size_bytes: 1024,
        subject: "Status update",
        body_preview: "Build completed successfully.",
        body: "Build completed successfully.",
        raw_message: "Subject: Status update\n\nBuild completed successfully."
      }
    ]
  },
  inbound_identity: {
    display_address: "inbox@example.com",
    configured_recipient_email: "inbox@example.com",
    accepts_any_recipient: false,
    listening_host: "127.0.0.1",
    listening_port: 2525,
    connection_hint: "Connect to 127.0.0.1:2525."
  },
  machines: defaultMachines
};

const defaultLocalLlmToolState: LocalLlmToolState = {
  tool_id: "llm-deepl",
  config: {
    enabled: true,
    provider: "lm_studio_api_v1",
    server_base_url: "http://127.0.0.1:1234",
    model_identifier: "qwen/qwen3.5-9b",
    endpoints: {
      models: "/api/v1/models",
      chat: "/api/v1/chat",
      model_load: "/api/v1/models/load",
      model_download: "/api/v1/models/download",
      model_download_status: "/api/v1/models/download/status/:job_id"
    }
  },
  presets: [
    {
      id: "lm_studio_api_v1",
      label: "LM Studio API v1",
      server_base_url: "http://127.0.0.1:1234",
      endpoints: {
        models: "/api/v1/models",
        chat: "/api/v1/chat",
        model_load: "/api/v1/models/load",
        model_download: "/api/v1/models/download",
        model_download_status: "/api/v1/models/download/status/:job_id"
      }
    },
    {
      id: "openai_compat",
      label: "OpenAI-compatible",
      server_base_url: "http://127.0.0.1:11434",
      endpoints: {
        models: "/v1/models",
        chat: "/v1/chat/completions",
        model_load: "/v1/models/load",
        model_download: "/v1/models/download",
        model_download_status: "/v1/models/download/status/:job_id"
      }
    }
  ]
};

const defaultImageMagicToolState: ImageMagicToolState = {
  tool_id: "image-magic",
  config: {
    enabled: false,
    target_worker_id: "worker-local-1",
    command: "magick",
    default_retries: 2
  },
  machines: defaultMachines
};

const defaultCoquiTtsToolState: CoquiTtsToolState = {
  tool_id: "coqui-tts",
  config: {
    enabled: false,
    command: "tts",
    model_name: "tts_models/en/ljspeech/tacotron2-DDC",
    speaker: "ljspeech",
    language: "en",
    output_directory: "backend/data/generated/coqui-tts"
  }
};

const fulfillJson = async (route: Route, body: unknown, status = 200) => {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body)
  });
};

export async function stubToolSettings(page: Page, overrides: DeepPartial<typeof defaultSettingsResponse> = {}) {
  const response = mergeDeep(defaultSettingsResponse, overrides);

  await page.route("**/api/v1/settings", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await fulfillJson(route, response);
  });
}

export async function installClipboardMock(page: Page) {
  await page.addInitScript(() => {
    const globalWindow = window as typeof window & { __copiedText?: string };
    globalWindow.__copiedText = "";
    const clipboard = navigator.clipboard as Clipboard & { writeText?: (value: string) => Promise<void> } | undefined;
    if (clipboard) {
      Object.defineProperty(clipboard, "writeText", {
        value: async (value: string) => {
          globalWindow.__copiedText = value;
        },
        configurable: true
      });
      return;
    }

    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: async (value: string) => {
          globalWindow.__copiedText = value;
        }
      },
      configurable: true
    });
  });
}

export async function getCopiedText(page: Page) {
  return page.evaluate(() => {
    const globalWindow = window as typeof window & { __copiedText?: string };
    return globalWindow.__copiedText || "";
  });
}

export async function stubToolCatalog(page: Page, entries: ToolDirectoryEntry[] = defaultTools) {
  let currentEntries = deepClone(entries);
  const patches: JsonObject[] = [];

  await page.route("**/api/v1/tools", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }

    await fulfillJson(route, currentEntries);
  });

  await page.route("**/api/v1/tools/*/directory", async (route) => {
    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }

    const toolId = new URL(route.request().url()).pathname.split("/")[4];
    const payload = route.request().postDataJSON() as JsonObject;
    const currentTool = currentEntries.find((entry) => entry.id === toolId);

    if (!currentTool) {
      await fulfillJson(route, { detail: "Tool not found." }, 404);
      return;
    }

    if (!Object.keys(payload).length) {
      await fulfillJson(route, { detail: "No tool changes provided." }, 400);
      return;
    }

    patches.push({ toolId, ...payload });

    currentEntries = currentEntries.map((entry) => {
      if (entry.id !== toolId) {
        return entry;
      }

      return {
        ...entry,
        ...(typeof payload.name === "string" ? { name: payload.name } : {}),
        ...(typeof payload.description === "string" ? { description: payload.description } : {}),
        ...(typeof payload.enabled === "boolean" ? { enabled: payload.enabled } : {})
      };
    });

    await fulfillJson(route, currentEntries.find((entry) => entry.id === toolId));
  });

  return {
    getEntries: () => deepClone(currentEntries),
    patches
  };
}

export async function stubSmtpTool(page: Page, overrides: DeepPartial<SmtpToolState> = {}) {
  let state = mergeDeep(defaultSmtpToolState, overrides);
  const savedConfigs: JsonObject[] = [];
  const testPayloads: JsonObject[] = [];
  const relayPayloads: JsonObject[] = [];
  const startCalls: number[] = [];
  const stopCalls: number[] = [];

  const respond = async (route: Route) => {
    await fulfillJson(route, state);
  };

  await page.route("**/api/v1/tools/smtp", async (route) => {
    if (route.request().method() === "GET") {
      await respond(route);
      return;
    }

    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    savedConfigs.push(payload);

    state = mergeDeep(state, {
      config: {
        enabled: typeof payload.enabled === "boolean" ? payload.enabled : state.config.enabled,
        target_worker_id: Object.prototype.hasOwnProperty.call(payload, "target_worker_id")
          ? (payload.target_worker_id as string | null)
          : state.config.target_worker_id,
        bind_host: typeof payload.bind_host === "string" ? payload.bind_host : state.config.bind_host,
        port: typeof payload.port === "number" ? payload.port : state.config.port,
        recipient_email: Object.prototype.hasOwnProperty.call(payload, "recipient_email")
          ? (payload.recipient_email as string | null)
          : state.config.recipient_email
      }
    });

    await respond(route);
  });

  await page.route("**/api/v1/tools/smtp/start", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    startCalls.push(Date.now());
    state = mergeDeep(state, {
      config: {
        enabled: true
      },
      runtime: {
        status: "running",
        message: "SMTP listener started locally.",
        last_started_at: "2026-03-20T11:00:00.000Z",
        last_error: null
      }
    });
    await respond(route);
  });

  await page.route("**/api/v1/tools/smtp/stop", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    stopCalls.push(Date.now());
    state = mergeDeep(state, {
      config: {
        enabled: false
      },
      runtime: {
        status: "stopped",
        message: "SMTP listener stopped.",
        listening_host: null,
        listening_port: null,
        last_stopped_at: "2026-03-20T11:05:00.000Z"
      }
    });
    await respond(route);
  });

  await page.route("**/api/v1/tools/smtp/send-test", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    testPayloads.push(payload);

    const recipients = Array.isArray(payload.recipients) ? payload.recipients.map((value) => String(value)) : [];
    const nextMessage: SmtpMessage = {
      id: "smtp-message-new",
      received_at: "2026-03-20T11:10:00.000Z",
      mail_from: String(payload.mail_from || ""),
      recipients,
      peer: "127.0.0.1:55555",
      size_bytes: 4096,
      subject: String(payload.subject || ""),
      body_preview: String(payload.body || "").slice(0, 80),
      body: String(payload.body || ""),
      raw_message: `Subject: ${String(payload.subject || "")}\n\n${String(payload.body || "")}`
    };

    state = mergeDeep(state, {
      runtime: {
        message_count: state.runtime.message_count + 1,
        last_message_at: nextMessage.received_at,
        last_mail_from: nextMessage.mail_from,
        last_recipient: recipients[0] || state.runtime.last_recipient,
        recent_messages: [nextMessage, ...state.runtime.recent_messages]
      }
    });

    await fulfillJson(route, {
      ok: true,
      message: "Test email sent through the local SMTP listener.",
      message_id: nextMessage.id
    });
  });

  await page.route("**/api/v1/tools/smtp/send-relay", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    relayPayloads.push(payload);

    await fulfillJson(route, {
      ok: true,
      status: "sent",
      message: "Email sent through the external SMTP relay."
    });
  });

  return {
    getState: () => deepClone(state),
    savedConfigs,
    testPayloads,
    relayPayloads,
    startCalls,
    stopCalls
  };
}

export async function stubLocalLlmTool(page: Page, overrides: DeepPartial<LocalLlmToolState> = {}) {
  let state = mergeDeep(defaultLocalLlmToolState, overrides);
  const savedConfigs: JsonObject[] = [];
  let lastChatRequest: JsonObject | null = null;

  await page.route("**/api/v1/tools/llm-deepl/local-llm", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, state);
      return;
    }

    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    savedConfigs.push(payload);

    const nextEndpoints = {
      ...state.config.endpoints,
      ...(payload.endpoints && typeof payload.endpoints === "object" ? payload.endpoints as JsonObject : {})
    };

    state = mergeDeep(state, {
      config: {
        enabled: typeof payload.enabled === "boolean" ? payload.enabled : state.config.enabled,
        provider: typeof payload.provider === "string" ? payload.provider : state.config.provider,
        server_base_url: typeof payload.server_base_url === "string" ? payload.server_base_url : state.config.server_base_url,
        model_identifier: typeof payload.model_identifier === "string" ? payload.model_identifier : state.config.model_identifier,
        endpoints: nextEndpoints
      }
    });

    await fulfillJson(route, state);
  });

  await page.route("**/api/v1/tools/llm-deepl/chat/stream", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    lastChatRequest = route.request().postDataJSON() as JsonObject;
    const messages = Array.isArray(lastChatRequest.messages) ? lastChatRequest.messages as JsonObject[] : [];
    const userMessage = [...messages].reverse().find((message) => String(message.role) === "user") as JsonObject | undefined;
    const userText = String(userMessage?.content || "message");
    const assistantText = `Local LLM reply: ${userText}`;

    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        `event: delta\ndata: ${JSON.stringify({ content: assistantText.slice(0, 18) })}\n\n`,
        `event: delta\ndata: ${JSON.stringify({ content: assistantText.slice(18) })}\n\n`,
        `event: done\ndata: ${JSON.stringify({ response_id: "response-local-1", response_text: assistantText })}\n\n`
      ].join("")
    });
  });

  return {
    getState: () => deepClone(state),
    savedConfigs,
    getLastChatRequest: () => deepClone(lastChatRequest)
  };
}

export async function stubImageMagicTool(page: Page, overrides: DeepPartial<ImageMagicToolState> = {}) {
  let state = mergeDeep(defaultImageMagicToolState, overrides);
  const savedConfigs: JsonObject[] = [];
  const executeRequests: JsonObject[] = [];

  const maybeRejectForLocalEnable = (payload: JsonObject) => {
    const enabling = typeof payload.enabled === "boolean" ? payload.enabled : state.config.enabled;
    const command = typeof payload.command === "string" ? payload.command : state.config.command;
    const targetWorkerId = Object.prototype.hasOwnProperty.call(payload, "target_worker_id")
      ? payload.target_worker_id as string | null
      : state.config.target_worker_id;

    return enabling && (!targetWorkerId || targetWorkerId === "worker-local-1") && command === "missing-magick";
  };

  await page.route("**/api/v1/tools/image-magic", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, state);
      return;
    }

    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    savedConfigs.push(payload);

    if (maybeRejectForLocalEnable(payload)) {
      await fulfillJson(route, { detail: "Image Magic command is not executable on this host: missing-magick" }, 422);
      return;
    }

    state = mergeDeep(state, {
      config: {
        enabled: typeof payload.enabled === "boolean" ? payload.enabled : state.config.enabled,
        target_worker_id: Object.prototype.hasOwnProperty.call(payload, "target_worker_id")
          ? (payload.target_worker_id as string | null)
          : state.config.target_worker_id,
        command: typeof payload.command === "string" ? payload.command : state.config.command
      }
    });

    await fulfillJson(route, state);
  });

  await page.route("**/api/v1/tools/image-magic/execute", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    executeRequests.push(payload);
    await fulfillJson(route, {
      ok: true,
      output_file_path: "backend/data/generated/image-magic/output.png",
      worker_id: "worker-local-1",
      worker_name: "Local Worker"
    });
  });

  return {
    getState: () => deepClone(state),
    savedConfigs,
    executeRequests
  };
}

export async function stubCoquiTtsTool(page: Page, overrides: DeepPartial<CoquiTtsToolState> = {}) {
  let state = mergeDeep(defaultCoquiTtsToolState, overrides);
  const savedConfigs: JsonObject[] = [];

  await page.route("**/api/v1/tools/coqui-tts", async (route) => {
    if (route.request().method() === "GET") {
      await fulfillJson(route, state);
      return;
    }

    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as JsonObject;
    savedConfigs.push(payload);

    state = mergeDeep(state, {
      config: {
        enabled: typeof payload.enabled === "boolean" ? payload.enabled : state.config.enabled,
        command: typeof payload.command === "string" ? payload.command : state.config.command,
        model_name: typeof payload.model_name === "string" ? payload.model_name : state.config.model_name,
        speaker: typeof payload.speaker === "string" ? payload.speaker : state.config.speaker,
        language: typeof payload.language === "string" ? payload.language : state.config.language,
        output_directory: typeof payload.output_directory === "string" ? payload.output_directory : state.config.output_directory
      }
    });

    await fulfillJson(route, state);
  });

  return {
    getState: () => deepClone(state),
    savedConfigs
  };
}

export {
  defaultMachines,
  defaultSettingsResponse,
  defaultTools,
  defaultSmtpToolState,
  defaultLocalLlmToolState,
  defaultImageMagicToolState,
  defaultCoquiTtsToolState
};
