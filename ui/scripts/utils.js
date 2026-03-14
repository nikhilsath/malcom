(function () {
  const getBaseUrl = () => {
    if (window.location.protocol === "file:" || window.location.origin === "null") {
      return "http://localhost:8000";
    }

    if (window.location.origin === "http://localhost:8000" || window.location.origin === "http://127.0.0.1:8000") {
      return "";
    }

    return window.location.origin;
  };

  const developerModeEnabled = () => sessionStorage.getItem("developerMode") === "true";

  const parseErrorMessage = async (response) => {
    try {
      const data = await response.json();
      return data.detail || data.message || "Request failed.";
    } catch {
      return "Request failed.";
    }
  };

  const requestJson = async (path, options = {}) => {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      headers: {
        "Content-Type": "application/json",
        "X-Developer-Mode": String(developerModeEnabled()),
        ...(options.headers || {})
      },
      ...options
    });

    if (!response.ok) {
      const message = await parseErrorMessage(response);
      throw new Error(message);
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  };

  window.Malcom = window.Malcom || {};

  if (!window.Malcom.getBaseUrl) {
    window.Malcom.getBaseUrl = getBaseUrl;
  }

  if (!window.Malcom.developerModeEnabled) {
    window.Malcom.developerModeEnabled = developerModeEnabled;
  }

  if (!window.Malcom.parseErrorMessage) {
    window.Malcom.parseErrorMessage = parseErrorMessage;
  }

  if (!window.Malcom.requestJson) {
    window.Malcom.requestJson = requestJson;
  }
})();