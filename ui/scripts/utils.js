import { normalizeRequestError, requestJson, resolveBaseUrl } from "./request.js";

window.Malcom = window.Malcom || {};

if (!window.Malcom.getBaseUrl) {
  window.Malcom.getBaseUrl = resolveBaseUrl;
}

if (!window.Malcom.normalizeError) {
  window.Malcom.normalizeError = normalizeRequestError;
}

if (!window.Malcom.parseErrorMessage) {
  window.Malcom.parseErrorMessage = async (response) => {
    try {
      const payload = await response.json();
      return normalizeRequestError(payload).message;
    } catch {
      return "Request failed.";
    }
  };
}

if (!window.Malcom.requestJson) {
  window.Malcom.requestJson = requestJson;
}
