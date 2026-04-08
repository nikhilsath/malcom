export class MalcomRequestError extends Error {
  constructor(message, context = {}) {
    super(message || "Request failed.");
    this.name = "MalcomRequestError";
    this.status = context.status ?? null;
    this.statusText = context.statusText ?? "";
    this.payload = context.payload;
    this.detail = context.detail;
    this.url = context.url ?? "";
    this.method = context.method ?? "GET";
    this.cause = context.cause;
  }
}

export const resolveBaseUrl = (locationLike = window.location) => {
  if (!locationLike) {
    return "";
  }

  if (locationLike.protocol === "file:" || locationLike.origin === "null") {
    return "http://localhost:8000";
  }

  if (locationLike.origin === "http://localhost:8000" || locationLike.origin === "http://127.0.0.1:8000") {
    return "";
  }

  return locationLike.origin || "";
};

export const buildQueryString = (params = {}) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, rawValue]) => {
    if (rawValue === undefined || rawValue === null || rawValue === "") {
      return;
    }

    if (Array.isArray(rawValue)) {
      rawValue.forEach((value) => {
        if (value !== undefined && value !== null && value !== "") {
          searchParams.append(key, String(value));
        }
      });
      return;
    }

    searchParams.append(key, String(rawValue));
  });

  const serialized = searchParams.toString();
  return serialized ? `?${serialized}` : "";
};

export const withQueryParams = (path, params = {}) => `${path}${buildQueryString(params)}`;

export const resolveRequestUrl = (path, locationLike = window.location) => {
  if (!path) {
    return resolveBaseUrl(locationLike);
  }

  if (/^[a-z]+:/i.test(path)) {
    return path;
  }

  const baseUrl = resolveBaseUrl(locationLike);
  return `${baseUrl}${path}`;
};

const extractIssueMessages = (issues) => {
  if (!Array.isArray(issues) || issues.length === 0) {
    return "";
  }

  return issues.map((issue) => {
    if (!issue || typeof issue !== "object") {
      return String(issue);
    }

    const location = issue.line
      ? `Line ${issue.line}${issue.column ? `, column ${issue.column}` : ""}: `
      : "";
    return `${location}${issue.message || "Validation failed."}`;
  }).join(" ");
};

export const extractErrorMessage = (payload, fallbackMessage = "Request failed.") => {
  if (!payload) {
    return fallbackMessage;
  }

  if (typeof payload === "string") {
    return payload || fallbackMessage;
  }

  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message.trim();
  }

  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail.trim();
  }

  const detailIssues = extractIssueMessages(payload.detail?.issues);
  if (detailIssues) {
    return detailIssues;
  }

  const issues = extractIssueMessages(payload.issues);
  if (issues) {
    return issues;
  }

  return fallbackMessage;
};

const maybeParseJson = async (response) => {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return null;
  }
};

export const parseJsonResponse = async (response) => {
  if (response.status === 204 || response.status === 205) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new MalcomRequestError("Response was not valid JSON.", {
      status: response.status,
      statusText: response.statusText,
      url: response.url,
      method: "GET"
    });
  }
};

export const requestJson = async (path, options = {}) => {
  const method = (options.method || "GET").toUpperCase();
  const response = await fetch(resolveRequestUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const payload = await maybeParseJson(response);

  if (!response.ok) {
    throw new MalcomRequestError(
      extractErrorMessage(payload, `Request failed with status ${response.status}.`),
      {
        status: response.status,
        statusText: response.statusText,
        payload,
        detail: payload?.detail,
        url: response.url || resolveRequestUrl(path),
        method
      }
    );
  }

  if (response.status === 204 || response.status === 205) {
    return null;
  }

  if (payload !== null) {
    return payload;
  }

  return parseJsonResponse(response);
};

export const normalizeRequestError = (error, fallbackMessage = "Request failed.") => {
  if (error instanceof MalcomRequestError) {
    return {
      message: error.message || fallbackMessage,
      status: error.status,
      statusText: error.statusText,
      payload: error.payload,
      detail: error.detail,
      url: error.url,
      method: error.method,
      cause: error.cause
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message || fallbackMessage,
      status: null,
      statusText: "",
      payload: undefined,
      detail: undefined,
      url: "",
      method: "",
      cause: error.cause
    };
  }

  return {
    message: error ? String(error) : fallbackMessage,
    status: null,
    statusText: "",
    payload: undefined,
    detail: undefined,
    url: "",
    method: "",
    cause: undefined
  };
};
