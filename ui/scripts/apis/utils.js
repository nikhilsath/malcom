export const sanitizeSlug = (value) => value
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9-]+/g, "-")
  .replace(/-{2,}/g, "-")
  .replace(/^-|-$/g, "");

export const isOutgoingType = (type) => type === "outgoing_scheduled" || type === "outgoing_continuous";

export const extractPayloadVariables = (value) => {
  const matches = value.matchAll(/{{\s*([^{}]+?)\s*}}/g);
  const variables = [];
  const seen = new Set();

  for (const match of matches) {
    const variableName = match[1]?.trim();

    if (!variableName || seen.has(variableName)) {
      continue;
    }

    seen.add(variableName);
    variables.push(variableName);
  }

  return variables;
};

export const titleCase = (value) => value
  .split("_")
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(" ");

export const getScheduledStatus = (entry) => entry.status || (entry.enabled ? "active" : "paused");

export const getEntryStatusLabel = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return titleCase(getScheduledStatus(entry));
  }

  return entry.enabled ? "Enabled" : "Disabled";
};

export const getEntryStatusTone = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return getScheduledStatus(entry) === "active" ? "status-badge--success" : "status-badge--muted";
  }

  return entry.enabled ? "status-badge--success" : "status-badge--muted";
};

export const getOutgoingRegistryStatusLabel = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return getScheduledStatus(entry) === "active" ? "Active" : "Inactive";
  }

  return entry.enabled ? "Active" : "Inactive";
};

export const getOutgoingRegistryStatusTone = (entry) => (getOutgoingRegistryStatusLabel(entry) === "Active"
  ? "status-badge--success"
  : "status-badge--warning");

export const formatRate = (value) => value.toFixed(1);

export { formatDateTime, formatIntervalMinutes } from "../format-utils.js";

export const formatOutgoingSendTime = (entry) => {
  if (entry.type === "outgoing_scheduled") {
    return entry.scheduled_time || "Not set";
  }

  if (!entry.repeat_enabled) {
    return "Manual";
  }

  return entry.repeat_interval_minutes
    ? `Every ${formatIntervalMinutes(entry.repeat_interval_minutes)}`
    : "Repeating";
};

export const formatRelativeActivity = (value) => {
  if (!value) {
    return "No recent activity";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recent activity unknown";
  }

  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.max(1, Math.round(diffMs / 60000));

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);

  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
};

export const getEntryPrimaryLocation = (entry) => {
  if (entry.type === "incoming") {
    return entry.endpoint_path || `/api/v1/inbound/${entry.id}`;
  }

  if (entry.type?.startsWith("outgoing")) {
    return entry.destination_url || "Not configured";
  }

  if (entry.type === "webhook") {
    return entry.callback_path || "Not configured";
  }

  return entry.path_slug || "Not configured";
};

export const getEntryLastActivity = (entry) => entry.last_received_at || entry.updated_at || entry.created_at || "";

export const getLogSettings = () => window.MalcomLogStore?.getSettings?.() || window.MalcomLogStore?.defaults || {
  maxDetailCharacters: 4000
};

export const formatBytes = (value) => {
  if (!Number.isFinite(value) || value < 0) {
    return "0 B";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

export const sortEventsByStatus = (left, right) => {
  const statusWeight = {
    accepted: 0,
    queued: 1,
    unauthorized: 2,
    invalid_json: 3,
    unsupported_media_type: 4,
    disabled: 5
  };

  const leftWeight = statusWeight[left.status] ?? 99;
  const rightWeight = statusWeight[right.status] ?? 99;

  if (leftWeight !== rightWeight) {
    return leftWeight - rightWeight;
  }

  return new Date(right.received_at || 0) - new Date(left.received_at || 0);
};

export const classifyEventSource = (eventItem) => {
  const sourceIp = eventItem.source_ip || "";

  if (!sourceIp) {
    return "unknown";
  }

  if (sourceIp === "127.0.0.1" || sourceIp === "::1" || sourceIp.startsWith("192.168.") || sourceIp.startsWith("10.")) {
    return "internal";
  }

  return "external";
};

export const deriveEventLabel = (eventItem) => {
  const payload = eventItem.payload_json;

  if (payload && typeof payload === "object") {
    if (typeof payload.event === "string" && payload.event.trim()) {
      return payload.event.trim();
    }

    if (typeof payload.type === "string" && payload.type.trim()) {
      return payload.type.trim();
    }
  }

  return "Request event";
};

export const stringifyPreviewValue = (value) => {
  if (value === null || value === undefined) {
    return "null";
  }

  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

export const truncatePreview = (value) => {
  const preview = stringifyPreviewValue(value);
  const maxDetailCharacters = Math.max(500, Number(getLogSettings().maxDetailCharacters) || 4000);

  if (preview.length <= maxDetailCharacters) {
    return {
      preview,
      truncated: false
    };
  }

  return {
    preview: `${preview.slice(0, maxDetailCharacters)}\n… truncated`,
    truncated: true
  };
};

export const buildEventSearchValue = (eventItem) => [
  eventItem.event_id,
  eventItem.status,
  eventItem.source_ip,
  eventItem.error_message,
  stringifyPreviewValue(eventItem.payload_json),
  stringifyPreviewValue(eventItem.request_headers_subset)
].join(" ").toLowerCase();

export const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

export const setFormMessage = (element, message, tone) => {
  if (!element) {
    return;
  }

  element.textContent = message;
  element.className = message
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

export const normalizeError = (error) => {
  if (error instanceof Error) {
    return { message: error.message, stack: error.stack };
  }

  return { message: String(error), stack: undefined };
};

export const resolvePageHref = (absolutePath) => {
  const relativePath = absolutePath.startsWith("/ui/") ? absolutePath.slice(3) : absolutePath;
  return new URL(`..${relativePath}`, window.location.href).href;
};

export const buildEndpointUrl = (apiId) => `${window.Malcom?.getBaseUrl?.() ?? ""}/api/v1/inbound/${apiId}`;

export const buildSampleCurl = (apiId, secret) => {
  const endpoint = buildEndpointUrl(apiId);
  const jsonPayload = JSON.stringify({ hello: "world" }, null, 2);

  return `curl -X POST "${endpoint}" \\
  -H "Authorization: Bearer ${secret}" \\
  -H "Content-Type: application/json" \\
  -d '${jsonPayload}'`;
};
