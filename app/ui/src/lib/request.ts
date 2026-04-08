import {
  MalcomRequestError,
  buildQueryString,
  extractErrorMessage,
  normalizeRequestError,
  parseJsonResponse,
  requestJson as requestJsonCore,
  resolveBaseUrl,
  resolveRequestUrl,
  withQueryParams
} from "../../scripts/request.js";

export type RequestErrorShape = ReturnType<typeof normalizeRequestError>;

export const requestJson = async <T = unknown>(path: string, options?: RequestInit): Promise<T> => {
  const runtimeRequest = (globalThis as {
    window?: {
      Malcom?: {
        requestJson?: (requestPath: string, requestOptions?: RequestInit) => Promise<unknown>;
      };
    };
  }).window?.Malcom?.requestJson;

  if (typeof runtimeRequest === "function") {
    return (await runtimeRequest(path, options)) as T;
  }

  return requestJsonCore(path, options) as Promise<T>;
};

export {
  MalcomRequestError,
  buildQueryString,
  extractErrorMessage,
  normalizeRequestError,
  parseJsonResponse,
  resolveBaseUrl,
  resolveRequestUrl,
  withQueryParams
};
