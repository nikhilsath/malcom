import type { Page, Route } from "@playwright/test";
import {
  buildAppSettingsResponse,
  buildConnectorSettingsPayload,
  createConnectorRecord as createConnectorFixture,
  createGithubOAuthConnector,
  createGoogleOAuthConnector,
  createNotionOAuthConnector,
  createTrelloConnector
} from "./api-response-builders.ts";

type JsonRecord = Record<string, unknown>;

export const defaultSettingsResponse = buildAppSettingsResponse({
  connectors: buildConnectorSettingsPayload(),
});

export type ConnectorRecord = {
  id: string;
  provider: string;
  name: string;
  status: string;
  auth_type: string;
  request_auth_type?: string;
  scopes: string[];
  base_url: string;
  owner: string;
  docs_url?: string;
  credential_ref?: string;
  created_at: string;
  updated_at: string;
  last_tested_at: string | null;
  auth_config: JsonRecord;
};

export type InboundEventRecord = {
  event_id: string;
  received_at: string;
  source_ip: string;
  status: string;
  payload_json: JsonRecord;
  request_headers_subset: JsonRecord;
  error_message?: string | null;
};

export type IncomingApiRecord = {
  id: string;
  name: string;
  description: string;
  path_slug: string;
  enabled: boolean;
  endpoint_path: string;
  endpoint_url: string;
  secret?: string;
  created_at: string;
  updated_at: string;
  last_received_at: string | null;
  last_delivery_status: string;
  events: InboundEventRecord[];
};

export type OutgoingApiRecord = {
  id: string;
  type: "outgoing_scheduled" | "outgoing_continuous";
  name: string;
  description: string;
  path_slug: string;
  enabled: boolean;
  destination_url: string;
  http_method: string;
  auth_type: string;
  auth_config: JsonRecord;
  payload_template: string;
  scheduled_time?: string | null;
  repeat_enabled: boolean;
  repeat_interval_minutes?: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_activity_at: string | null;
  last_run_at?: string | null;
  next_run_at?: string | null;
  last_error?: string | null;
};

export type WebhookRecord = {
  id: string;
  type: "webhook";
  name: string;
  description: string;
  path_slug: string;
  enabled: boolean;
  callback_path: string;
  verification_token: string;
  signing_secret: string;
  signature_header: string;
  event_filter: string;
  created_at: string;
  updated_at: string;
  last_activity_at: string | null;
  last_delivery_status?: string | null;
  events_count?: number;
};

export type ConnectorsApisHarnessOptions = {
  settings?: Partial<JsonRecord>;
  connectors?: ConnectorRecord[];
  inbound?: IncomingApiRecord[];
  outgoingScheduled?: OutgoingApiRecord[];
  outgoingContinuous?: OutgoingApiRecord[];
  webhooks?: WebhookRecord[];
};

const iso = (offsetMinutes = 0) => new Date(Date.parse("2026-03-23T12:00:00.000Z") - offsetMinutes * 60_000).toISOString();

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

const mergeDeep = (base: JsonRecord, override: JsonRecord): JsonRecord => {
  const output: JsonRecord = clone(base);

  for (const [key, value] of Object.entries(override)) {
    if (Array.isArray(value)) {
      output[key] = clone(value);
      continue;
    }

    if (value && typeof value === "object" && !Array.isArray(value)) {
      const baseValue = output[key];
      output[key] = mergeDeep(
        (baseValue && typeof baseValue === "object" && !Array.isArray(baseValue)) ? (baseValue as JsonRecord) : {},
        value as JsonRecord,
      );
      continue;
    }

    output[key] = value;
  }

  return output;
};

const toJson = (body: JsonRecord | JsonRecord[]) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify(body)
});

const createDefaultSettings = (connectors: ConnectorRecord[]) => buildAppSettingsResponse({
  connectors: createDefaultConnectors(connectors),
});

const createDefaultConnectors = (connectors: ConnectorRecord[]) => buildConnectorSettingsPayload({ records: connectors });

const createConnectorRecord = (overrides: Partial<ConnectorRecord> & { id: string; provider: string; name: string }): ConnectorRecord => ({
  ...createConnectorFixture({
    id: overrides.id,
    provider: overrides.provider,
    name: overrides.name,
    status: overrides.status || "draft",
    auth_type: overrides.auth_type || "oauth2",
    scopes: overrides.scopes || [],
    base_url: overrides.base_url || "",
    owner: overrides.owner || "Workspace",
    docs_url: overrides.docs_url,
    credential_ref: overrides.credential_ref || `connector/${overrides.id}`,
    created_at: overrides.created_at || iso(90),
    updated_at: overrides.updated_at || iso(0),
    last_tested_at: overrides.last_tested_at ?? null,
    auth_config: overrides.auth_config || {
      client_id: "",
      username: "",
      header_name: "",
      scope_preset: overrides.provider,
      redirect_uri: "",
      expires_at: null,
      has_refresh_token: false
    }
  })
});

const createIncomingRecord = (overrides: Partial<IncomingApiRecord> & { id: string; name: string; path_slug: string }): IncomingApiRecord => ({
  id: overrides.id,
  name: overrides.name,
  description: overrides.description || "",
  path_slug: overrides.path_slug,
  enabled: overrides.enabled ?? true,
  endpoint_path: overrides.endpoint_path || `/api/v1/inbound/${overrides.id}`,
  endpoint_url: overrides.endpoint_url || `http://127.0.0.1:4173/api/v1/inbound/${overrides.id}`,
  secret: overrides.secret,
  created_at: overrides.created_at || iso(120),
  updated_at: overrides.updated_at || iso(0),
  last_received_at: overrides.last_received_at ?? null,
  last_delivery_status: overrides.last_delivery_status || "No deliveries",
  events: overrides.events ? clone(overrides.events) : []
});

const createOutgoingRecord = (
  overrides: Partial<OutgoingApiRecord> & { id: string; type: "outgoing_scheduled" | "outgoing_continuous"; name: string; path_slug: string }
): OutgoingApiRecord => ({
  id: overrides.id,
  type: overrides.type,
  name: overrides.name,
  description: overrides.description || "",
  path_slug: overrides.path_slug,
  enabled: overrides.enabled ?? true,
  destination_url: overrides.destination_url || "",
  http_method: overrides.http_method || "POST",
  auth_type: overrides.auth_type || "none",
  auth_config: overrides.auth_config || {},
  payload_template: overrides.payload_template || '{ "event": "scheduled.delivery" }',
  scheduled_time: overrides.scheduled_time ?? (overrides.type === "outgoing_scheduled" ? "09:00" : null),
  repeat_enabled: overrides.repeat_enabled ?? false,
  repeat_interval_minutes: overrides.repeat_interval_minutes ?? null,
  status: overrides.status || (overrides.enabled === false ? "paused" : "active"),
  created_at: overrides.created_at || iso(60),
  updated_at: overrides.updated_at || iso(0),
  last_activity_at: overrides.last_activity_at ?? null,
  last_run_at: overrides.last_run_at ?? null,
  next_run_at: overrides.next_run_at ?? (overrides.type === "outgoing_continuous" ? iso(-5) : null),
  last_error: overrides.last_error ?? null
});

const createWebhookRecord = (overrides: Partial<WebhookRecord> & { id: string; name: string; path_slug: string }): WebhookRecord => ({
  id: overrides.id,
  type: "webhook",
  name: overrides.name,
  description: overrides.description || "",
  path_slug: overrides.path_slug,
  enabled: overrides.enabled ?? true,
  callback_path: overrides.callback_path || "/hooks/webhook",
  verification_token: overrides.verification_token || "verify-token",
  signing_secret: overrides.signing_secret || "signing-secret",
  signature_header: overrides.signature_header || "X-Signature",
  event_filter: overrides.event_filter || "order.created",
  created_at: overrides.created_at || iso(30),
  updated_at: overrides.updated_at || iso(0),
  last_activity_at: overrides.last_activity_at ?? null,
  last_delivery_status: overrides.last_delivery_status || "accepted",
  events_count: overrides.events_count ?? 3
});

const createDefaultConnectorFixtures = (): ConnectorRecord[] => [
  createGithubOAuthConnector("github-oauth", {
    last_tested_at: iso(10),
  })
];

const createDefaultIncomingFixtures = (): IncomingApiRecord[] => [
  createIncomingRecord({
    id: "incoming-orders",
    name: "Orders Webhook",
    description: "Receives order events.",
    path_slug: "orders-webhook",
    enabled: true,
    secret: "secret-incoming-orders",
    last_received_at: iso(25),
    last_delivery_status: "accepted",
    events: [
      {
        event_id: "evt-1",
        received_at: iso(25),
        source_ip: "198.51.100.20",
        status: "accepted",
        payload_json: { order_id: 42, event: "order.created", message: "primary payload" },
        request_headers_subset: { "x-request-id": "req-1", "content-type": "application/json" }
      },
      {
        event_id: "evt-2",
        received_at: iso(20),
        source_ip: "127.0.0.1",
        status: "unauthorized",
        payload_json: { order_id: 84, event: "order.updated", message: "warning payload" },
        request_headers_subset: { "x-request-id": "req-2", authorization: "Bearer bad" },
        error_message: "Bearer token did not match."
      },
      {
        event_id: "evt-3",
        received_at: iso(15),
        source_ip: "10.0.0.10",
        status: "invalid_json",
        payload_json: { event: "order.replayed", warning: "invalid json" },
        request_headers_subset: { "x-request-id": "req-3" },
        error_message: "JSON body could not be parsed."
      }
    ]
  })
];

const createDefaultOutgoingFixtures = (): OutgoingApiRecord[] => [
  createOutgoingRecord({
    id: "outgoing-digest",
    type: "outgoing_scheduled",
    name: "Daily Digest",
    description: "Sends a morning summary.",
    path_slug: "daily-digest",
    enabled: true,
    destination_url: "https://example.com/webhooks/digest",
    http_method: "POST",
    auth_type: "bearer",
    auth_config: { token: "digest-token" },
    payload_template: '{ "event": "digest.ready", "sent_at": "{{timestamp}}" }',
    scheduled_time: "09:00",
    repeat_enabled: true,
    status: "active",
    last_activity_at: iso(35)
  }),
  createOutgoingRecord({
    id: "outgoing-heartbeat",
    type: "outgoing_continuous",
    name: "Heartbeat",
    description: "Repeated delivery.",
    path_slug: "heartbeat",
    enabled: true,
    destination_url: "https://example.com/webhooks/heartbeat",
    http_method: "POST",
    auth_type: "header",
    auth_config: { header_name: "X-API-Key", header_value: "heartbeat-key" },
    payload_template: '{ "event": "heartbeat", "status": "{{status}}" }',
    repeat_enabled: true,
    repeat_interval_minutes: 15,
    status: "active",
    last_activity_at: iso(12)
  })
];

const createDefaultWebhookFixtures = (): WebhookRecord[] => [
  createWebhookRecord({
    id: "webhook-orders",
    name: "Order Webhook",
    description: "Publishes order changes.",
    path_slug: "order-webhook",
    enabled: true,
    callback_path: "/publisher/orders",
    verification_token: "verify-token",
    signing_secret: "signing-secret",
    signature_header: "X-Signature",
    event_filter: "order.created",
    last_activity_at: iso(55)
  })
];

const extractPath = (route: Route) => new URL(route.request().url()).pathname;

const writeJson = async (route: Route, body: JsonRecord | JsonRecord[], status = 200) => {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body)
  });
};

const writeRedirectHtml = async (route: Route, destination: string) => {
  const escapedDestination = destination
    .replaceAll("&", "&amp;")
    .replaceAll("\"", "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  await route.fulfill({
    status: 200,
    contentType: "text/html; charset=utf-8",
    body: `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=${escapedDestination}">
    <title>Redirecting…</title>
  </head>
  <body>
    <script>window.location.replace(${JSON.stringify(destination)});</script>
    <a href="${escapedDestination}">Continue</a>
  </body>
</html>`
  });
};

const writeConnectorRedirectHtml = async (route: Route, destination: string, connectorsState: JsonRecord) => {
  const escapedDestination = destination
    .replaceAll("&", "&amp;")
    .replaceAll("\"", "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  await route.fulfill({
    status: 200,
    contentType: "text/html; charset=utf-8",
    body: `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=${escapedDestination}">
    <title>Redirecting…</title>
  </head>
  <body>
    <script>
      try {
        const stateKey = "malcom.playwright.connectors-apis";
        const current = JSON.parse(window.localStorage.getItem(stateKey) || "{}");
        current.connectors = ${JSON.stringify(connectorsState)};
        window.localStorage.setItem(stateKey, JSON.stringify(current));
      } catch {}
      window.location.replace(${JSON.stringify(destination)});
    </script>
    <a href="${escapedDestination}">Continue</a>
  </body>
</html>`
  });
};

const stripSecretFields = (record: ConnectorRecord): JsonRecord => {
  const authConfig = record.auth_config || {};
  const normalizedStatus = record.provider === "google" && authConfig.access_token_input && record.status === "draft"
    ? "connected"
    : record.status;
  return {
    ...record,
    status: normalizedStatus,
    auth_config: {
      ...authConfig,
      client_secret_masked: authConfig.client_secret_masked || (authConfig.client_secret_input ? "••••••••" : authConfig.client_secret_masked),
      access_token_masked: authConfig.access_token_masked || (authConfig.access_token_input ? "••••••••" : authConfig.access_token_masked),
      refresh_token_masked: authConfig.refresh_token_masked || (authConfig.refresh_token_input ? "••••••••" : authConfig.refresh_token_masked),
      api_key_masked: authConfig.api_key_masked || (authConfig.api_key_input ? "••••••••" : authConfig.api_key_masked),
      password_masked: authConfig.password_masked || (authConfig.password_input ? "••••••••" : authConfig.password_masked),
      header_value_masked: authConfig.header_value_masked || (authConfig.header_value_input ? "••••••••" : authConfig.header_value_masked)
    }
  };
};

const findConnector = (connectors: ConnectorRecord[], id: string) => connectors.find((item) => item.id === id) || null;

const upsertConnector = (connectors: ConnectorRecord[], nextRecord: ConnectorRecord) => {
  const existingIndex = connectors.findIndex((item) => item.id === nextRecord.id);
  if (existingIndex >= 0) {
    connectors[existingIndex] = nextRecord;
    return;
  }
  connectors.unshift(nextRecord);
};

const removeConnector = (connectors: ConnectorRecord[], id: string) => {
  const index = connectors.findIndex((item) => item.id === id);
  if (index >= 0) {
    connectors.splice(index, 1);
  }
};

const setConnectorStatus = (record: ConnectorRecord | null, nextStatus: string) => {
  if (!record) {
    return null;
  }

  return {
    ...record,
    status: nextStatus,
    updated_at: iso(0),
    last_tested_at: iso(0)
  };
};

const createConnectorAuthorizationUrl = (provider: string, stateToken: string, redirectUri: string) => {
  const baseUrl = provider === "google"
    ? "https://accounts.google.com/o/oauth2/v2/auth"
    : provider === "github"
      ? "https://github.com/login/oauth/authorize"
      : "https://api.notion.com/v1/oauth/authorize";
  const url = new URL(baseUrl);
  url.searchParams.set("state", stateToken);
  url.searchParams.set("redirect_uri", redirectUri);
  if (provider !== "github") {
    url.searchParams.set("response_type", "code");
  }
  return url.toString();
};

const buildCallbackRedirect = (connectorId: string, status: "success" | "warning" | "error", message: string) => {
  const url = new URL("http://127.0.0.1:4173/settings/connectors.html");
  url.searchParams.set("oauth_status", status);
  url.searchParams.set("oauth_message", message);
  url.searchParams.set("connector_id", connectorId);
  return url.toString();
};

const getProviderBaseUrl = (provider: string) => (
  provider === "google"
    ? "https://www.googleapis.com"
    : provider === "github"
      ? "https://api.github.com"
      : provider === "notion"
        ? "https://api.notion.com/v1"
        : "https://api.trello.com/1"
);

const getProviderDocsUrl = (provider: string) => (
  provider === "google"
    ? "https://developers.google.com"
    : provider === "github"
      ? "https://docs.github.com"
      : provider === "notion"
        ? "https://developers.notion.com/guides/get-started/authorization"
        : "https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/"
);

const getProviderSuccessMessage = (provider: string, action: "test" | "refresh" | "revoke" | "authorize") => {
  if (action === "authorize") {
    return `${provider === "github" ? "GitHub" : provider === "notion" ? "Notion" : "Google"} connector authorized successfully.`;
  }
  if (action === "test") {
    return provider === "google"
      ? "Google connection verified."
      : provider === "github"
        ? "GitHub connection verified."
        : provider === "notion"
          ? "Notion connection verified."
          : "Trello connection verified.";
  }
  if (action === "refresh") {
    return provider === "github"
      ? "GitHub token refreshed."
      : provider === "notion"
        ? "Notion token refreshed."
        : "Google token refreshed.";
  }
  return provider === "github"
    ? "GitHub connector revoked and credentials cleared."
    : provider === "notion"
      ? "Notion connector revoked and credentials cleared."
      : provider === "trello"
        ? "Trello credentials cleared from this workspace."
        : "Google connector revoked and credentials cleared.";
};

const makeCreatedIncoming = (body: JsonRecord, counter: number): IncomingApiRecord => createIncomingRecord({
  id: body.path_slug ? `incoming-${body.path_slug}` : `incoming-${counter}`,
  name: String(body.name || "Incoming API"),
  description: String(body.description || ""),
  path_slug: String(body.path_slug || `incoming-${counter}`),
  enabled: Boolean(body.enabled),
  secret: `secret-${body.path_slug || counter}`,
  last_received_at: null,
  last_delivery_status: "No deliveries",
  events: []
});

const makeCreatedOutgoing = (body: JsonRecord, counter: number): OutgoingApiRecord => createOutgoingRecord({
  id: body.path_slug ? `outgoing-${body.path_slug}` : `outgoing-${counter}`,
  type: body.type as "outgoing_scheduled" | "outgoing_continuous",
  name: String(body.name || "Outgoing API"),
  description: String(body.description || ""),
  path_slug: String(body.path_slug || `outgoing-${counter}`),
  enabled: Boolean(body.enabled),
  destination_url: String(body.destination_url || ""),
  http_method: String(body.http_method || "POST"),
  auth_type: String(body.auth_type || "none"),
  auth_config: clone(body.auth_config || {}),
  payload_template: String(body.payload_template || "{}"),
  scheduled_time: body.scheduled_time ? String(body.scheduled_time) : null,
  repeat_enabled: Boolean(body.repeat_enabled),
  repeat_interval_minutes: body.repeat_interval_minutes ? Number(body.repeat_interval_minutes) : null,
  status: body.enabled === false ? "paused" : "active",
  last_activity_at: null
});

const makeCreatedWebhook = (body: JsonRecord, counter: number): WebhookRecord => createWebhookRecord({
  id: body.path_slug ? `webhook-${body.path_slug}` : `webhook-${counter}`,
  name: String(body.name || "Webhook"),
  description: String(body.description || ""),
  path_slug: String(body.path_slug || `webhook-${counter}`),
  enabled: Boolean(body.enabled),
  callback_path: String(body.callback_path || "/hooks/webhook"),
  verification_token: String(body.verification_token || "verify-token"),
  signing_secret: String(body.signing_secret || "signing-secret"),
  signature_header: String(body.signature_header || "X-Signature"),
  event_filter: String(body.event_filter || "order.created")
});

export function createConnectorsApisHarness(options: ConnectorsApisHarnessOptions = {}) {
  const connectorRecords = options.connectors || createDefaultConnectorFixtures();
  const settings = createDefaultSettings(connectorRecords);
  const connectors = createDefaultConnectors(connectorRecords);
  if (options.settings) {
    Object.assign(settings, mergeDeep(settings, options.settings as JsonRecord));
  }

  const state = {
    settings,
    connectors,
    oauthStateByConnector: {} as Record<string, { state: string; redirectUri: string; provider: string }>,
    inbound: options.inbound ? clone(options.inbound) : createDefaultIncomingFixtures(),
    outgoingScheduled: options.outgoingScheduled ? clone(options.outgoingScheduled) : createDefaultOutgoingFixtures().filter((entry) => entry.type === "outgoing_scheduled"),
    outgoingContinuous: options.outgoingContinuous ? clone(options.outgoingContinuous) : createDefaultOutgoingFixtures().filter((entry) => entry.type === "outgoing_continuous"),
    webhooks: options.webhooks ? clone(options.webhooks) : createDefaultWebhookFixtures(),
    counts: {
      inbound: 1,
      outgoing: 1,
      webhooks: 1
    }
  };

  const nextSettings = () => clone(state.settings);

  const nextConnectorSettings = () => ({
    ...clone(state.connectors),
    records: listConnectors(),
  });

  const updateSettings = (patch: JsonRecord) => {
    state.settings = mergeDeep(state.settings, patch);
    return nextSettings();
  };

  const listConnectors = () => (state.connectors.records || []).map((record: ConnectorRecord) => stripSecretFields(record));

  const replaceConnector = (record: ConnectorRecord) => {
    const connectors = state.connectors.records as ConnectorRecord[];
    upsertConnector(connectors, record);
    state.connectors.records = connectors;
    return record;
  };

  const createOAuthStartResponse = (body: JsonRecord, provider: string) => {
    const connectors = state.connectors.records as ConnectorRecord[];
    const existing = findConnector(connectors, String(body.connector_id || ""));
    const nextRecord = createConnectorRecord({
      id: String(body.connector_id || provider),
      provider,
      name: String(body.name || provider),
      status: "pending_oauth",
      auth_type: "oauth2",
      scopes: Array.isArray(body.scopes) ? body.scopes as string[] : [],
      base_url: getProviderBaseUrl(provider),
      owner: String(body.owner || "Workspace"),
      docs_url: getProviderDocsUrl(provider),
      credential_ref: `connector/${String(body.connector_id || provider)}`,
      auth_config: {
        client_id: String(body.client_id || existing?.auth_config?.client_id || `${provider}-client-id`),
        client_secret_input: String(body.client_secret_input || ""),
        redirect_uri: String(body.redirect_uri || ""),
        scope_preset: provider,
        expires_at: null,
        has_refresh_token: false
      },
      created_at: existing?.created_at || iso(5),
      updated_at: iso(0),
      last_tested_at: null
    });

    replaceConnector(nextRecord);

    const stateToken = `oauth-state-${String(body.connector_id || provider)}`;
    state.oauthStateByConnector[nextRecord.id] = {
      state: stateToken,
      redirectUri: String(body.redirect_uri || ""),
      provider
    };

    return {
      connector: stripSecretFields(nextRecord),
      authorization_url: createConnectorAuthorizationUrl(provider, stateToken, String(body.redirect_uri || "")),
      state: stateToken,
      expires_at: iso(-15),
      code_challenge_method: "S256"
    };
  };

  const createOAuthCallbackResponse = (provider: string, query: URLSearchParams) => {
    const stateToken = String(query.get("state") || "");
    const code = String(query.get("code") || "demo");
    const connectorId = String(query.get("connector_id") || "google");
    const connectors = state.connectors.records as ConnectorRecord[];
    const existing = findConnector(connectors, connectorId);
    const session = state.oauthStateByConnector[connectorId];
    const providerPreset = state.connectors.catalog.find((item: { id: string }) => item.id === provider);

    const hasValidHarnessState = Boolean(session && session.state === stateToken && session.provider === provider);
    const hasValidTokenShape = stateToken === `oauth-state-${connectorId}`;

    if (!hasValidHarnessState && !hasValidTokenShape) {
      return buildCallbackRedirect(connectorId, "error", "Invalid OAuth state.");
    }

    const nextRecord: ConnectorRecord = {
      ...(existing || createConnectorRecord({
        id: connectorId,
        provider,
        name: providerPreset?.name || provider,
        status: "pending_oauth",
        auth_type: "oauth2",
        scopes: existing?.scopes?.length ? existing.scopes : [],
        base_url: getProviderBaseUrl(provider),
        owner: "Workspace",
        docs_url: getProviderDocsUrl(provider),
        auth_config: {
          client_id: `${provider}-client-id`,
          redirect_uri: `http://127.0.0.1:4173/api/v1/connectors/${provider}/oauth/callback`,
          scope_preset: provider,
          expires_at: null,
          has_refresh_token: false
        }
      })),
      status: "connected",
      updated_at: iso(0),
      last_tested_at: iso(0),
      scopes: existing?.scopes?.length ? existing.scopes : [],
      auth_config: {
        ...(existing?.auth_config || {}),
        access_token_input: provider === "github"
          ? `gho_${code.slice(0, 24)}`
          : provider === "notion"
            ? `ntn_${code.slice(0, 24)}`
            : `token_${code.slice(0, 24)}`,
        refresh_token_input: provider === "github"
          ? `ghr_${code.slice(0, 24)}`
          : provider === "notion"
            ? `ntr_${code.slice(0, 24)}`
            : `refresh_${code.slice(0, 24)}`,
        has_refresh_token: true,
        expires_at: iso(60),
        client_secret_input: ""
      }
    };

    replaceConnector(nextRecord);
    return buildCallbackRedirect(connectorId, "success", getProviderSuccessMessage(provider, "authorize"));
  };

  const install = async (page: Page) => {
    await page.addInitScript((initialState) => {
      const stateKey = "malcom.playwright.connectors-apis";
      const clone = (value: unknown) => JSON.parse(JSON.stringify(value));
      const mergeDeep = (base: Record<string, unknown>, override: Record<string, unknown>) => {
        const output = clone(base) as Record<string, unknown>;

        for (const [key, value] of Object.entries(override || {})) {
          if (Array.isArray(value)) {
            output[key] = clone(value);
            continue;
          }

          if (value && typeof value === "object") {
            const baseValue = output[key];
            output[key] = mergeDeep(
              (baseValue && typeof baseValue === "object" && !Array.isArray(baseValue)) ? baseValue as Record<string, unknown> : {},
              value as Record<string, unknown>
            );
            continue;
          }

          output[key] = value;
        }

        return output;
      };

      const loadState = () => {
        try {
          const raw = window.localStorage.getItem(stateKey);
          if (raw) {
            return JSON.parse(raw) as typeof initialState;
          }
        } catch {
          // fall through to initial state
        }

        const nextState = clone(initialState) as typeof initialState;
        window.localStorage.setItem(stateKey, JSON.stringify(nextState));
        return nextState;
      };

      const saveState = (nextState: typeof initialState) => {
        window.localStorage.setItem(stateKey, JSON.stringify(nextState));
        return nextState;
      };

      const upsert = <T extends { id: string }>(items: T[], nextItem: T) => {
        const index = items.findIndex((item) => item.id === nextItem.id);
        if (index >= 0) {
          items[index] = nextItem;
          return;
        }
        items.unshift(nextItem);
      };

      const stripConnectorSecrets = (record: Record<string, unknown>) => {
        const authConfig = (record.auth_config as Record<string, unknown>) || {};
        return {
          ...record,
          auth_config: {
            ...authConfig,
            client_secret_masked: authConfig.client_secret_masked || (authConfig.client_secret_input ? "••••••••" : authConfig.client_secret_masked),
            access_token_masked: authConfig.access_token_masked || (authConfig.access_token_input ? "••••••••" : authConfig.access_token_masked),
            refresh_token_masked: authConfig.refresh_token_masked || (authConfig.refresh_token_input ? "••••••••" : authConfig.refresh_token_masked),
            api_key_masked: authConfig.api_key_masked || (authConfig.api_key_input ? "••••••••" : authConfig.api_key_masked),
            password_masked: authConfig.password_masked || (authConfig.password_input ? "••••••••" : authConfig.password_masked),
            header_value_masked: authConfig.header_value_masked || (authConfig.header_value_input ? "••••••••" : authConfig.header_value_masked)
          }
        };
      };

      let state = loadState();

      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: {
          writeText: async (value: string) => {
            (window as unknown as { __copiedText?: string }).__copiedText = value;
          }
        }
      });

      window.Malcom = window.Malcom || {};
      window.Malcom.requestJson = async (path: string, options: RequestInit = {}) => {
        state = loadState();
        const method = (options.method || "GET").toString().toUpperCase();
        const body = typeof options.body === "string" && options.body
          ? JSON.parse(options.body)
          : {};
        const url = new URL(path, window.location.origin);
        const pathname = url.pathname;

        const respond = (payload: unknown, status = 200) => {
          if (status >= 400) {
            throw new Error((payload as { detail?: string } | null)?.detail || "Request failed.");
          }

          return clone(payload);
        };

        if (pathname === "/api/v1/settings") {
          const response = await fetch(url.toString(), {
            method,
            headers: {
              "Content-Type": "application/json",
              ...(options.headers || {})
            },
            body: typeof options.body === "string" ? options.body : undefined
          });

          if (!response.ok) {
            const text = await response.text();
            throw new Error(text || `Request failed with status ${response.status}.`);
          }

          const text = await response.text();
          return text ? JSON.parse(text) : null;
        }

        if (pathname === "/api/v1/connectors" && method === "GET") {
          const connectorSettings = (state.connectors as Record<string, unknown>) || {};
          const records = Array.isArray(connectorSettings.records)
            ? connectorSettings.records.map((record) => stripConnectorSecrets(record as Record<string, unknown>))
            : [];

          return respond({
            catalog: Array.isArray(connectorSettings.catalog) ? clone(connectorSettings.catalog) : [],
            records,
            metadata: (connectorSettings.metadata && typeof connectorSettings.metadata === "object")
              ? clone(connectorSettings.metadata as Record<string, unknown>)
              : {},
            auth_policy: (connectorSettings.auth_policy && typeof connectorSettings.auth_policy === "object")
              ? clone(connectorSettings.auth_policy as Record<string, unknown>)
              : {}
          });
        }

        if (pathname === "/api/v1/connectors" && method === "POST") {
          const connectorsRoot = state.connectors as Record<string, unknown>;
          const connectors = (connectorsRoot.records as Array<Record<string, unknown>>) || [];
          const connectorId = String(body.id || `${String(body.provider || "connector")}-${Date.now()}`);
          const nextRecord = {
            id: connectorId,
            provider: String(body.provider || ""),
            name: String(body.name || connectorId),
            status: String(body.status || "draft"),
            auth_type: String(body.auth_type || "oauth2"),
            scopes: Array.isArray(body.scopes) ? body.scopes : [],
            base_url: String(body.base_url || ""),
            owner: String(body.owner || "Workspace"),
            docs_url: body.docs_url ? String(body.docs_url) : undefined,
            credential_ref: String(body.credential_ref || `connector/${connectorId}`),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            last_tested_at: null,
            auth_config: (body.auth_config && typeof body.auth_config === "object") ? clone(body.auth_config as Record<string, unknown>) : {}
          };
          upsert(connectors, nextRecord);
          connectorsRoot.records = connectors;
          saveState(state);
          return respond(stripConnectorSecrets(nextRecord), 201);
        }

        const connectorWriteMatch = pathname.match(/^\/api\/v1\/connectors\/([^/]+)$/);
        if (connectorWriteMatch && method === "PATCH") {
          const connectorId = connectorWriteMatch[1];
          const connectorsRoot = state.connectors as Record<string, unknown>;
          const connectors = (connectorsRoot.records as Array<Record<string, unknown>>) || [];
          const existing = connectors.find((record) => record.id === connectorId);
          if (!existing) {
            return respond({ detail: "Connector not found." }, 404);
          }

          const nextRecord = {
            ...existing,
            provider: String(body.provider || existing.provider || ""),
            name: String(body.name || existing.name || connectorId),
            status: String(body.status || existing.status || "draft"),
            auth_type: String(body.auth_type || existing.auth_type || "oauth2"),
            scopes: Array.isArray(body.scopes) ? body.scopes : (existing.scopes || []),
            base_url: String(body.base_url || existing.base_url || ""),
            owner: String(body.owner || existing.owner || "Workspace"),
            docs_url: body.docs_url ? String(body.docs_url) : existing.docs_url,
            credential_ref: String(body.credential_ref || existing.credential_ref || `connector/${connectorId}`),
            updated_at: new Date().toISOString(),
            auth_config: {
              ...((existing.auth_config && typeof existing.auth_config === "object") ? existing.auth_config : {}),
              ...((body.auth_config && typeof body.auth_config === "object") ? clone(body.auth_config as Record<string, unknown>) : {})
            }
          };
          upsert(connectors, nextRecord);
          connectorsRoot.records = connectors;
          saveState(state);
          return respond(stripConnectorSecrets(nextRecord));
        }

        if (connectorWriteMatch && method === "DELETE") {
          const connectorId = connectorWriteMatch[1];
          const connectorsRoot = state.connectors as Record<string, unknown>;
          const connectors = (connectorsRoot.records as Array<Record<string, unknown>>) || [];
          const before = connectors.length;
          const nextRecords = connectors.filter((record) => record.id !== connectorId);
          connectorsRoot.records = nextRecords;
          saveState(state);
          if (before === nextRecords.length) {
            return respond({ detail: "Connector not found." }, 404);
          }
          return respond({ ok: true, removed: connectorId });
        }

        if (pathname === "/api/v1/connectors/auth-policy" && method === "PATCH") {
          const connectorsRoot = state.connectors as Record<string, unknown>;
          const currentPolicy = (connectorsRoot.auth_policy && typeof connectorsRoot.auth_policy === "object")
            ? connectorsRoot.auth_policy as Record<string, unknown>
            : {};
          connectorsRoot.auth_policy = {
            ...currentPolicy,
            ...body,
          };
          saveState(state);
          return respond(clone(connectorsRoot.auth_policy as Record<string, unknown>));
        }

        const connectorStartMatch = pathname.match(/^\/api\/v1\/connectors\/([^/]+)\/oauth\/start$/);
        if (connectorStartMatch && method === "POST") {
          const provider = connectorStartMatch[1];
          const connectorId = String(body.connector_id || provider);
          const connectors = (state.connectors as Record<string, unknown>).records as Array<Record<string, unknown>>;
          const existing = connectors.find((record) => record.id === connectorId);
          const nextRecord = {
            id: connectorId,
            provider,
            name: String(body.name || provider),
            status: "pending_oauth",
            auth_type: "oauth2",
            scopes: Array.isArray(body.scopes) ? body.scopes : [],
            base_url: getProviderBaseUrl(provider),
            owner: String(body.owner || "Workspace"),
            docs_url: getProviderDocsUrl(provider),
            credential_ref: `connector/${connectorId}`,
            created_at: existing?.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            last_tested_at: null,
            auth_config: {
              client_id: String(body.client_id || existing?.auth_config?.client_id || `${provider}-client-id`),
              client_secret_input: String(body.client_secret_input || ""),
              redirect_uri: String(body.redirect_uri || ""),
              scope_preset: provider,
              expires_at: null,
              has_refresh_token: false
            }
          };

          upsert(connectors, nextRecord);
          (state.connectors as Record<string, unknown>).records = connectors;
          (state as Record<string, unknown>).oauthStateByConnector = {
            ...((state as Record<string, unknown>).oauthStateByConnector as Record<string, unknown> || {}),
            [connectorId]: {
              state: `oauth-state-${connectorId}`,
              redirectUri: String(body.redirect_uri || ""),
              provider
            }
          };
          saveState(state);
          return respond({
            connector: stripConnectorSecrets(nextRecord),
            authorization_url: createConnectorAuthorizationUrl(provider, `oauth-state-${connectorId}`, String(body.redirect_uri || "")),
            state: `oauth-state-${connectorId}`,
            expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
            code_challenge_method: "S256"
          });
        }

        const connectorIdMatch = pathname.match(/^\/api\/v1\/connectors\/([^/]+)\/(test|refresh)$/);
        if (connectorIdMatch && method === "POST") {
          const connectorId = connectorIdMatch[1];
          const action = connectorIdMatch[2];
          const connectors = (state.connectors as Record<string, unknown>).records as Array<Record<string, unknown>>;
          const record = connectors.find((item) => item.id === connectorId);
          if (!record) {
            return respond({ detail: "Connector not found." }, 404);
          }

          if (action === "test") {
            record.status = record.status === "revoked" ? "revoked" : "connected";
            record.updated_at = new Date().toISOString();
            record.last_tested_at = new Date().toISOString();
            saveState(state);
            return respond({
              ok: record.status !== "revoked",
              message: record.status === "revoked"
                ? `${record.provider === "trello" ? "Trello" : titleCase(String(record.provider || ""))} connector is revoked.`
                : getProviderSuccessMessage(String(record.provider || ""), "test"),
              connector: stripConnectorSecrets(record)
            });
          }

          record.status = "connected";
          record.updated_at = new Date().toISOString();
          record.last_tested_at = new Date().toISOString();
          record.auth_config = {
            ...record.auth_config,
            access_token_input: record.provider === "github"
              ? `gho_${connectorId.slice(0, 12)}`
              : record.provider === "notion"
                ? `ntn_${connectorId.slice(0, 12)}`
                : `token_${connectorId.slice(0, 12)}`,
            refresh_token_input: record.provider === "github"
              ? `ghr_${connectorId.slice(0, 12)}`
              : record.provider === "notion"
                ? `ntr_${connectorId.slice(0, 12)}`
                : record.auth_config?.refresh_token_input,
            expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
            has_refresh_token: true
          };
          saveState(state);
          return respond({
            ok: true,
            message: getProviderSuccessMessage(String(record.provider || ""), "refresh"),
            connector: stripConnectorSecrets(record)
          });
        }

        if (pathname === "/api/v1/apis/test-delivery" && method === "POST") {
          return respond({
            ok: true,
            status_code: 200,
            response_body: JSON.stringify({ ok: true, destination_url: String(body.destination_url || "") }),
            sent_headers: {
              "Content-Type": "application/json"
            },
            destination_url: String(body.destination_url || "")
          });
        }

        if (pathname === "/api/v1/apis" && method === "POST") {
          const type = String(body.type || "incoming");

          if (type === "incoming") {
            const created = {
              id: body.path_slug ? `incoming-${body.path_slug}` : `incoming-${Date.now()}`,
              name: String(body.name || "Incoming API"),
              description: String(body.description || ""),
              path_slug: String(body.path_slug || `incoming-${Date.now()}`),
              enabled: Boolean(body.enabled),
              endpoint_path: `/api/v1/inbound/${body.path_slug || `incoming-${Date.now()}`}`,
              endpoint_url: `http://127.0.0.1:4173/api/v1/inbound/${body.path_slug || `incoming-${Date.now()}`}`,
              secret: `secret-${body.path_slug || Date.now()}`,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              last_received_at: null,
              last_delivery_status: "No deliveries",
              events: []
            };
            state.inbound.unshift(created);
            saveState(state);
            return respond({
              id: created.id,
              name: created.name,
              description: created.description,
              path_slug: created.path_slug,
              enabled: created.enabled,
              secret: created.secret,
              endpoint_path: created.endpoint_path,
              endpoint_url: created.endpoint_url,
              type: "incoming"
            }, 201);
          }

          if (type === "webhook") {
            const created = {
              id: body.path_slug ? `webhook-${body.path_slug}` : `webhook-${Date.now()}`,
              type: "webhook",
              name: String(body.name || "Webhook"),
              description: String(body.description || ""),
              path_slug: String(body.path_slug || `webhook-${Date.now()}`),
              enabled: Boolean(body.enabled),
              callback_path: String(body.callback_path || "/hooks/webhook"),
              verification_token: String(body.verification_token || "verify-token"),
              signing_secret: String(body.signing_secret || "signing-secret"),
              signature_header: String(body.signature_header || "X-Signature"),
              event_filter: String(body.event_filter || "order.created"),
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              last_activity_at: null
            };
            state.webhooks.unshift(created);
            saveState(state);
            return respond(created, 201);
          }

          const created = {
            id: body.path_slug ? `outgoing-${body.path_slug}` : `outgoing-${Date.now()}`,
            type,
            name: String(body.name || "Outgoing API"),
            description: String(body.description || ""),
            path_slug: String(body.path_slug || `outgoing-${Date.now()}`),
            enabled: Boolean(body.enabled),
            destination_url: String(body.destination_url || ""),
            http_method: String(body.http_method || "POST"),
            auth_type: String(body.auth_type || "none"),
            auth_config: clone(body.auth_config || {}),
            payload_template: String(body.payload_template || "{}"),
            scheduled_time: body.scheduled_time ? String(body.scheduled_time) : null,
            repeat_enabled: Boolean(body.repeat_enabled),
            repeat_interval_minutes: body.repeat_interval_minutes ? Number(body.repeat_interval_minutes) : null,
            status: body.enabled === false ? "paused" : "active",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            last_activity_at: null
          };
          if (type === "outgoing_scheduled") {
            state.outgoingScheduled.unshift(created);
          } else {
            state.outgoingContinuous.unshift(created);
          }
          saveState(state);
          return respond(created, 201);
        }

        if (pathname === "/api/v1/inbound" && method === "GET") {
          return respond(state.inbound.map((entry) => ({
            id: entry.id,
            name: entry.name,
            description: entry.description,
            path_slug: entry.path_slug,
            enabled: entry.enabled,
            endpoint_path: entry.endpoint_path,
            endpoint_url: entry.endpoint_url,
            created_at: entry.created_at,
            updated_at: entry.updated_at,
            last_received_at: entry.last_received_at,
            last_delivery_status: entry.last_delivery_status,
            type: "incoming"
          })));
        }

        const rotateMatch = pathname.match(/^\/api\/v1\/inbound\/([^/]+)\/rotate-secret$/);
        if (rotateMatch && method === "POST") {
          const record = state.inbound.find((entry) => entry.id === rotateMatch[1]);
          if (!record) {
            return respond({ detail: "API not found." }, 404);
          }
          record.secret = `secret-${rotateMatch[1]}-rotated`;
          record.updated_at = new Date().toISOString();
          saveState(state);
          return respond({ id: record.id, secret: record.secret, name: record.name, enabled: record.enabled });
        }

        const inboundMatch = pathname.match(/^\/api\/v1\/inbound\/([^/]+)$/);
        if (inboundMatch) {
          const record = state.inbound.find((entry) => entry.id === inboundMatch[1]);
          if (!record) {
            return respond({ detail: "API not found." }, 404);
          }

          if (method === "GET") {
            return respond(record);
          }

          if (method === "PATCH") {
            record.enabled = typeof body.enabled === "boolean" ? body.enabled : record.enabled;
            record.name = String(body.name || record.name);
            record.description = String(body.description || record.description);
            record.path_slug = String(body.path_slug || record.path_slug);
            record.updated_at = new Date().toISOString();
            saveState(state);
            return respond({
              id: record.id,
              name: record.name,
              description: record.description,
              path_slug: record.path_slug,
              enabled: record.enabled,
              endpoint_path: record.endpoint_path,
              endpoint_url: record.endpoint_url,
              created_at: record.created_at,
              updated_at: record.updated_at,
              last_received_at: record.last_received_at,
              last_delivery_status: record.last_delivery_status,
              type: "incoming"
            });
          }
        }

        if (pathname === "/api/v1/outgoing/scheduled" && method === "GET") {
          return respond(state.outgoingScheduled.map((entry) => ({ ...entry, type: "outgoing_scheduled" })));
        }

        if (pathname === "/api/v1/outgoing/continuous" && method === "GET") {
          return respond(state.outgoingContinuous.map((entry) => ({ ...entry, type: "outgoing_continuous" })));
        }

        const outgoingMatch = pathname.match(/^\/api\/v1\/outgoing\/([^/]+)$/);
        if (outgoingMatch) {
          const record = [...state.outgoingScheduled, ...state.outgoingContinuous].find((entry) => entry.id === outgoingMatch[1]);
          if (!record) {
            return respond({ detail: "Outgoing API not found." }, 404);
          }

          if (method === "GET") {
            return respond(record);
          }

          if (method === "PATCH") {
            record.name = String(body.name || record.name);
            record.description = String(body.description || record.description);
            record.path_slug = String(body.path_slug || record.path_slug);
            record.enabled = typeof body.enabled === "boolean" ? body.enabled : record.enabled;
            record.destination_url = String(body.destination_url || record.destination_url);
            record.http_method = String(body.http_method || record.http_method);
            record.auth_type = String(body.auth_type || record.auth_type);
            record.auth_config = clone(body.auth_config || record.auth_config);
            record.payload_template = String(body.payload_template || record.payload_template);
            record.scheduled_time = body.scheduled_time ? String(body.scheduled_time) : record.scheduled_time;
            record.repeat_enabled = typeof body.repeat_enabled === "boolean" ? body.repeat_enabled : record.repeat_enabled;
            record.repeat_interval_minutes = body.repeat_interval_minutes ? Number(body.repeat_interval_minutes) : record.repeat_interval_minutes;
            record.updated_at = new Date().toISOString();
            saveState(state);
            return respond(record);
          }
        }

        if (pathname === "/api/v1/webhooks" && method === "GET") {
          return respond(state.webhooks.map((entry) => ({ ...entry, type: "webhook" })));
        }

        throw new Error(`Unsupported request: ${method} ${pathname}`);
      };
    }, clone({
      settings,
      connectors: nextConnectorSettings(),
      oauthStateByConnector: {},
      inbound: options.inbound ? clone(options.inbound) : createDefaultIncomingFixtures(),
      outgoingScheduled: options.outgoingScheduled ? clone(options.outgoingScheduled) : createDefaultOutgoingFixtures().filter((entry) => entry.type === "outgoing_scheduled"),
      outgoingContinuous: options.outgoingContinuous ? clone(options.outgoingContinuous) : createDefaultOutgoingFixtures().filter((entry) => entry.type === "outgoing_continuous"),
      webhooks: options.webhooks ? clone(options.webhooks) : createDefaultWebhookFixtures()
    }));

    const syncConnectorsStateFromBrowser = async () => {
      try {
        const browserConnectors = await page.evaluate(() => {
          try {
            const stateKey = "malcom.playwright.connectors-apis";
            const payload = JSON.parse(window.localStorage.getItem(stateKey) || "{}");
            return payload.connectors || null;
          } catch {
            return null;
          }
        });
        if (browserConnectors && typeof browserConnectors === "object") {
          state.connectors = clone(browserConnectors as JsonRecord);
        }
      } catch {
        // Keep existing harness state if the page is between navigations.
      }
    };

    const syncBrowserConnectorsStateFromHarness = async () => {
      try {
        await page.evaluate((connectorsState) => {
          try {
            const stateKey = "malcom.playwright.connectors-apis";
            const payload = JSON.parse(window.localStorage.getItem(stateKey) || "{}");
            payload.connectors = connectorsState;
            window.localStorage.setItem(stateKey, JSON.stringify(payload));
          } catch {
            // Ignore browser-state sync errors during navigation churn.
          }
        }, nextConnectorSettings());
      } catch {
        // Keep existing browser state if the page is between navigations.
      }
    };

    await page.route("**/api/v1/settings", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await writeJson(route, nextSettings());
        return;
      }

      if (method === "PATCH") {
        const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
        state.settings = mergeDeep(state.settings, body);
        await writeJson(route, nextSettings());
        return;
      }

      await route.fallback();
    });

    // Match the real endpoint shape: /api/v1/connectors returns connector settings.
    await page.route("**/api/v1/connectors", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await writeJson(route, nextConnectorSettings() as JsonRecord);
        return;
      }
      await route.fallback();
    });

    await page.route("**/api/v1/connectors/google/oauth/start", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
      await writeJson(route, createOAuthStartResponse(body, "google"));
    });

    await page.route("**/api/v1/connectors/github/oauth/start", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
      await writeJson(route, createOAuthStartResponse(body, "github"));
    });

    await page.route("**/api/v1/connectors/notion/oauth/start", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
      await writeJson(route, createOAuthStartResponse(body, "notion"));
    });

    await page.route("**accounts.google.com/**", async (route) => {
      const url = new URL(route.request().url());
      const stateToken = url.searchParams.get("state") || "oauth-state-google";
      const connectorId = Object.entries(state.oauthStateByConnector).find(([, value]) => value.state === stateToken && value.provider === "google")?.[0] || "google";
      await writeRedirectHtml(route, `http://127.0.0.1:4173/api/v1/connectors/google/oauth/callback?state=${encodeURIComponent(stateToken)}&code=demo-google&connector_id=${encodeURIComponent(connectorId)}`);
    });

    await page.route("**github.com/login/oauth/authorize**", async (route) => {
      const url = new URL(route.request().url());
      const stateToken = url.searchParams.get("state") || "oauth-state-github";
      const session = Object.entries(state.oauthStateByConnector).find(([, value]) => value.state === stateToken && value.provider === "github");
      const connectorId = session?.[0] || "github-oauth";
      await writeRedirectHtml(route, `http://127.0.0.1:4173/api/v1/connectors/github/oauth/callback?state=${encodeURIComponent(stateToken)}&code=demo-github&connector_id=${encodeURIComponent(connectorId)}`);
    });

    await page.route("**api.notion.com/v1/oauth/authorize**", async (route) => {
      const url = new URL(route.request().url());
      const stateToken = url.searchParams.get("state") || "oauth-state-notion";
      const session = Object.entries(state.oauthStateByConnector).find(([, value]) => value.state === stateToken && value.provider === "notion");
      const connectorId = session?.[0] || "notion-oauth";
      await writeRedirectHtml(route, `http://127.0.0.1:4173/api/v1/connectors/notion/oauth/callback?state=${encodeURIComponent(stateToken)}&code=demo-notion&connector_id=${encodeURIComponent(connectorId)}`);
    });

    await page.route("**/api/v1/connectors/google/oauth/callback**", async (route) => {
      const url = new URL(route.request().url());
      const redirectUrl = createOAuthCallbackResponse("google", url.searchParams);
      await writeConnectorRedirectHtml(route, redirectUrl, nextConnectorSettings() as JsonRecord);
    });

    await page.route("**/api/v1/connectors/github/oauth/callback**", async (route) => {
      const url = new URL(route.request().url());
      const redirectUrl = createOAuthCallbackResponse("github", url.searchParams);
      await writeConnectorRedirectHtml(route, redirectUrl, nextConnectorSettings() as JsonRecord);
    });

    await page.route("**/api/v1/connectors/notion/oauth/callback**", async (route) => {
      const url = new URL(route.request().url());
      const redirectUrl = createOAuthCallbackResponse("notion", url.searchParams);
      await writeConnectorRedirectHtml(route, redirectUrl, nextConnectorSettings() as JsonRecord);
    });

    await page.route("**/api/v1/connectors/*/test", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const path = extractPath(route);
      const connectorId = path.split("/")[4];
      const connectors = state.connectors.records as ConnectorRecord[];
      const record = findConnector(connectors, connectorId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Connector not found." }) });
        return;
      }

      const nextStatus = record.status === "revoked" ? "revoked" : "connected";
      const nextRecord = setConnectorStatus(record, nextStatus) || record;
      nextRecord.auth_config = {
        ...nextRecord.auth_config,
        client_secret_input: nextRecord.auth_config.client_secret_input || ""
      };
      replaceConnector(nextRecord);
      await syncBrowserConnectorsStateFromHarness();
      await writeJson(route, {
        ok: nextStatus !== "revoked",
        message: nextStatus === "revoked"
          ? `${record.provider === "trello" ? "Trello" : titleCase(record.provider)} connector is revoked.`
          : record.provider === "trello"
            ? getProviderSuccessMessage("trello", "test")
            : getProviderSuccessMessage(String(record.provider), "test"),
        connector: stripSecretFields(nextRecord)
      });
    });

    await page.route("**/api/v1/connectors/*/refresh", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const path = extractPath(route);
      const connectorId = path.split("/")[4];
      const connectors = state.connectors.records as ConnectorRecord[];
      const record = findConnector(connectors, connectorId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Connector not found." }) });
        return;
      }

      const nextRecord: ConnectorRecord = {
        ...record,
        status: "connected",
        updated_at: iso(0),
        last_tested_at: iso(0),
        auth_config: {
          ...record.auth_config,
          access_token_input: record.provider === "github"
            ? `gho_${connectorId.slice(0, 12)}`
            : record.provider === "notion"
              ? `ntn_${connectorId.slice(0, 12)}`
              : `token_${connectorId.slice(0, 12)}`,
          refresh_token_input: record.provider === "github"
            ? `ghr_${connectorId.slice(0, 12)}`
            : record.provider === "notion"
              ? `ntr_${connectorId.slice(0, 12)}`
              : record.auth_config.refresh_token_input,
          expires_at: iso(60),
          has_refresh_token: true
        }
      };
      replaceConnector(nextRecord);
      await syncBrowserConnectorsStateFromHarness();
      await writeJson(route, {
        ok: true,
        message: getProviderSuccessMessage(String(record.provider), "refresh"),
        connector: stripSecretFields(nextRecord)
      });
    });

    await page.route("**/api/v1/connectors/*/revoke", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await syncConnectorsStateFromBrowser();
      const path = extractPath(route);
      const connectorId = path.split("/")[4];
      const connectors = state.connectors.records as ConnectorRecord[];
      const record = findConnector(connectors, connectorId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Connector not found." }) });
        return;
      }

      const nextRecord: ConnectorRecord = {
        ...record,
        status: "revoked",
        updated_at: iso(0),
        auth_config: {
          ...record.auth_config,
          access_token_input: "",
          refresh_token_input: "",
          api_key_input: "",
          has_refresh_token: false,
          expires_at: null
        }
      };
      replaceConnector(nextRecord);
      await syncBrowserConnectorsStateFromHarness();
      await writeJson(route, {
        ok: true,
        message: getProviderSuccessMessage(String(record.provider), "revoke"),
        connector: stripSecretFields(nextRecord)
      });
    });

    await page.route("**/api/v1/apis/test-delivery", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
      await writeJson(route, {
        ok: true,
        status_code: 200,
        response_body: JSON.stringify({ ok: true, destination_url: body.destination_url || "" }),
        sent_headers: {
          "Content-Type": "application/json"
        },
        destination_url: String(body.destination_url || "")
      });
    });

    await page.route("**/api/v1/apis", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
      const type = String(body.type || "incoming");

      if (type === "incoming") {
        const created = makeCreatedIncoming(body, state.inbound.length + 1);
        state.inbound.unshift(created);
        await writeJson(route, {
          id: created.id,
          name: created.name,
          description: created.description,
          path_slug: created.path_slug,
          enabled: created.enabled,
          secret: created.secret,
          endpoint_path: created.endpoint_path,
          endpoint_url: created.endpoint_url,
          type: "incoming"
        }, 201);
        return;
      }

      if (type === "webhook") {
        const created = makeCreatedWebhook(body, state.webhooks.length + 1);
        state.webhooks.unshift(created);
        await writeJson(route, {
          ...created,
          type: "webhook"
        }, 201);
        return;
      }

      const created = makeCreatedOutgoing(body, state.outgoingScheduled.length + state.outgoingContinuous.length + 1);
      if (created.type === "outgoing_scheduled") {
        state.outgoingScheduled.unshift(created);
      } else {
        state.outgoingContinuous.unshift(created);
      }
      await writeJson(route, {
        ...created
      }, 201);
    });

    await page.route("**/api/v1/inbound", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }

      await writeJson(route, state.inbound.map((entry) => ({
        id: entry.id,
        name: entry.name,
        description: entry.description,
        path_slug: entry.path_slug,
        enabled: entry.enabled,
        endpoint_path: entry.endpoint_path,
        endpoint_url: entry.endpoint_url,
        created_at: entry.created_at,
        updated_at: entry.updated_at,
        last_received_at: entry.last_received_at,
        last_delivery_status: entry.last_delivery_status,
        type: "incoming"
      })));
    });

    await page.route(/\/api\/v1\/inbound\/[^/]+\/rotate-secret(?:\?.*)?$/, async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      const path = extractPath(route);
      const connectorId = path.split("/")[4];
      const record = state.inbound.find((entry) => entry.id === connectorId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "API not found." }) });
        return;
      }

      record.secret = `secret-${connectorId}-rotated`;
      record.updated_at = iso(0);
      await writeJson(route, {
        id: record.id,
        secret: record.secret,
        name: record.name,
        enabled: record.enabled
      });
    });

    await page.route(/\/api\/v1\/inbound\/[^/]+(?:\?.*)?$/, async (route) => {
      const path = extractPath(route);
      const inboundId = path.split("/")[4];
      const record = state.inbound.find((entry) => entry.id === inboundId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "API not found." }) });
        return;
      }

      if (route.request().method() === "GET") {
        await writeJson(route, clone(record));
        return;
      }

      if (route.request().method() === "PATCH") {
        const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
        Object.assign(record, {
          enabled: typeof body.enabled === "boolean" ? body.enabled : record.enabled,
          name: String(body.name || record.name),
          description: String(body.description || record.description),
          path_slug: String(body.path_slug || record.path_slug),
          updated_at: iso(0),
          last_delivery_status: record.last_delivery_status
        });
        await writeJson(route, {
          id: record.id,
          name: record.name,
          description: record.description,
          path_slug: record.path_slug,
          enabled: record.enabled,
          endpoint_path: record.endpoint_path,
          endpoint_url: record.endpoint_url,
          created_at: record.created_at,
          updated_at: record.updated_at,
          last_received_at: record.last_received_at,
          last_delivery_status: record.last_delivery_status,
          type: "incoming"
        });
        return;
      }

      await route.fallback();
    });

    await page.route("**/api/v1/outgoing/scheduled", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }

      await writeJson(route, state.outgoingScheduled.map((entry) => ({ ...entry, type: "outgoing_scheduled" })));
    });

    await page.route("**/api/v1/outgoing/continuous", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }

      await writeJson(route, state.outgoingContinuous.map((entry) => ({ ...entry, type: "outgoing_continuous" })));
    });

    await page.route(/\/api\/v1\/outgoing\/[^/]+(?:\?.*)?$/, async (route) => {
      const path = extractPath(route);
      const outgoingId = path.split("/")[4];
      const record = [...state.outgoingScheduled, ...state.outgoingContinuous].find((entry) => entry.id === outgoingId);
      if (!record) {
        await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Outgoing API not found." }) });
        return;
      }

      if (route.request().method() === "GET") {
        await writeJson(route, clone(record));
        return;
      }

      if (route.request().method() === "PATCH") {
        const body = (route.request().postDataJSON?.() || {}) as JsonRecord;
        const nextRecord = {
          ...record,
          name: String(body.name || record.name),
          description: String(body.description || record.description),
          path_slug: String(body.path_slug || record.path_slug),
          enabled: typeof body.enabled === "boolean" ? body.enabled : record.enabled,
          destination_url: String(body.destination_url || record.destination_url),
          http_method: String(body.http_method || record.http_method),
          auth_type: String(body.auth_type || record.auth_type),
          auth_config: clone(body.auth_config || record.auth_config),
          payload_template: String(body.payload_template || record.payload_template),
          scheduled_time: body.scheduled_time ? String(body.scheduled_time) : record.scheduled_time,
          repeat_enabled: typeof body.repeat_enabled === "boolean" ? body.repeat_enabled : record.repeat_enabled,
          repeat_interval_minutes: body.repeat_interval_minutes ? Number(body.repeat_interval_minutes) : record.repeat_interval_minutes,
          updated_at: iso(0),
          last_activity_at: record.last_activity_at
        } as OutgoingApiRecord;

        const list = record.type === "outgoing_scheduled" ? state.outgoingScheduled : state.outgoingContinuous;
        const index = list.findIndex((entry) => entry.id === outgoingId);
        list[index] = nextRecord;
        await writeJson(route, nextRecord);
        return;
      }

      await route.fallback();
    });

    await page.route("**/api/v1/webhooks", async (route) => {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }

      await writeJson(route, state.webhooks.map((entry) => ({ ...entry, type: "webhook" })));
    });
  };

  return {
    state,
    install,
    connectorRecords: () => listConnectors(),
    getIncoming: () => clone(state.inbound),
    getOutgoingScheduled: () => clone(state.outgoingScheduled),
    getOutgoingContinuous: () => clone(state.outgoingContinuous),
    getWebhooks: () => clone(state.webhooks)
  };
}

export const installClipboardTracker = async (page: Page) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (value: string) => {
          (window as unknown as { __copiedText?: string }).__copiedText = value;
        }
      }
    });
  });
};

export const readClipboardTracker = async (page: Page) => page.evaluate(() => (window as unknown as { __copiedText?: string }).__copiedText || "");
