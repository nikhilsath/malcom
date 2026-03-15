const localLlmElements = {
  title: document.getElementById("tools-local-llm-title"),
  description: document.getElementById("tools-local-llm-description"),
  statusValue: document.getElementById("tools-local-llm-status-value"),
  statusMessage: document.getElementById("tools-local-llm-status-message"),
  summaryPresetValue: document.getElementById("tools-local-llm-summary-preset-value"),
  summaryServerValue: document.getElementById("tools-local-llm-summary-server-value"),
  summaryModelValue: document.getElementById("tools-local-llm-summary-model-value"),
  form: document.getElementById("tools-local-llm-form"),
  enabledInput: document.getElementById("tools-local-llm-enabled-input"),
  providerInput: document.getElementById("tools-local-llm-provider-input"),
  serverInput: document.getElementById("tools-local-llm-server-input"),
  modelInput: document.getElementById("tools-local-llm-model-input"),
  modelsEndpointInput: document.getElementById("tools-local-llm-models-endpoint-input"),
  chatEndpointInput: document.getElementById("tools-local-llm-chat-endpoint-input"),
  loadEndpointInput: document.getElementById("tools-local-llm-load-endpoint-input"),
  downloadEndpointInput: document.getElementById("tools-local-llm-download-endpoint-input"),
  downloadStatusEndpointInput: document.getElementById("tools-local-llm-download-status-endpoint-input"),
  feedback: document.getElementById("tools-local-llm-form-feedback"),
  applyPresetButton: document.getElementById("tools-local-llm-apply-preset-button"),
  saveButton: document.getElementById("tools-local-llm-save-button"),
  endpointModelsValue: document.getElementById("tools-local-llm-endpoints-models-value"),
  endpointChatValue: document.getElementById("tools-local-llm-endpoints-chat-value"),
  endpointLoadValue: document.getElementById("tools-local-llm-endpoints-load-value"),
  endpointDownloadValue: document.getElementById("tools-local-llm-endpoints-download-value"),
  endpointDownloadStatusValue: document.getElementById("tools-local-llm-endpoints-download-status-value"),
  chatTranscript: document.getElementById("tools-local-llm-chat-transcript"),
  chatForm: document.getElementById("tools-local-llm-chat-form"),
  chatSystemInput: document.getElementById("tools-local-llm-chat-system-input"),
  chatUserInput: document.getElementById("tools-local-llm-chat-user-input"),
  chatFeedback: document.getElementById("tools-local-llm-chat-feedback"),
  chatSendButton: document.getElementById("tools-local-llm-chat-send-button"),
  chatClearButton: document.getElementById("tools-local-llm-chat-clear-button")
};

let localLlmState = null;
let saving = false;
let chatMessages = [];
let chatPreviousResponseId = null;
let chatSending = false;

const getBaseUrl = () => {
  if (window.location.protocol === "file:" || window.location.origin === "null") {
    return "http://localhost:8000";
  }

  if (window.location.origin === "http://localhost:8000" || window.location.origin === "http://127.0.0.1:8000") {
    return "";
  }

  return window.location.origin;
};

const setFeedback = (message, tone = "") => {
  localLlmElements.feedback.textContent = message;
  localLlmElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const setChatFeedback = (message, tone = "") => {
  localLlmElements.chatFeedback.textContent = message;
  localLlmElements.chatFeedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const fetchJson = async (path, options = {}) => {
  const response = await fetch(`${getBaseUrl()}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || "Local LLM request failed.");
  }

  return payload;
};

const getPresetMap = () => {
  const presets = localLlmState?.presets || [];
  return new Map(presets.map((preset) => [preset.id, preset]));
};

const resolveEndpointUrl = (baseUrl, path) => {
  const trimmedBaseUrl = (baseUrl || "").trim().replace(/\/+$/, "");
  const trimmedPath = (path || "").trim();

  if (!trimmedBaseUrl && !trimmedPath) {
    return "Not configured";
  }

  if (!trimmedBaseUrl) {
    return trimmedPath || "Not configured";
  }

  if (!trimmedPath) {
    return trimmedBaseUrl;
  }

  if (/^https?:\/\//i.test(trimmedPath)) {
    return trimmedPath;
  }

  return `${trimmedBaseUrl}${trimmedPath.startsWith("/") ? "" : "/"}${trimmedPath}`;
};

const populatePresetOptions = () => {
  const presets = localLlmState?.presets || [];
  localLlmElements.providerInput.innerHTML = presets
    .map((preset) => `<option value="${preset.id}">${preset.label}</option>`)
    .join("");
};

const applyPresetToForm = ({ announce = false } = {}) => {
  const preset = getPresetMap().get(localLlmElements.providerInput.value);

  if (!preset) {
    return;
  }

  localLlmElements.serverInput.value = preset.server_base_url || "";
  localLlmElements.modelsEndpointInput.value = preset.endpoints.models || "";
  localLlmElements.chatEndpointInput.value = preset.endpoints.chat || "";
  localLlmElements.loadEndpointInput.value = preset.endpoints.model_load || "";
  localLlmElements.downloadEndpointInput.value = preset.endpoints.model_download || "";
  localLlmElements.downloadStatusEndpointInput.value = preset.endpoints.model_download_status || "";
  renderEndpointPreview();

  if (announce) {
    setFeedback(`${preset.label} preset applied. Review and save when ready.`, "success");
  }
};

const renderEndpointPreview = () => {
  const baseUrl = localLlmElements.serverInput.value;
  localLlmElements.endpointModelsValue.textContent = resolveEndpointUrl(baseUrl, localLlmElements.modelsEndpointInput.value);
  localLlmElements.endpointChatValue.textContent = resolveEndpointUrl(baseUrl, localLlmElements.chatEndpointInput.value);
  localLlmElements.endpointLoadValue.textContent = resolveEndpointUrl(baseUrl, localLlmElements.loadEndpointInput.value);
  localLlmElements.endpointDownloadValue.textContent = resolveEndpointUrl(baseUrl, localLlmElements.downloadEndpointInput.value);
  localLlmElements.endpointDownloadStatusValue.textContent = resolveEndpointUrl(baseUrl, localLlmElements.downloadStatusEndpointInput.value);
};

const renderTool = () => {
  if (!localLlmState) {
    return;
  }

  const { config } = localLlmState;
  const preset = getPresetMap().get(config.provider);

  localLlmElements.title.textContent = "Local LLM configuration";
  localLlmElements.description.textContent = "Configure the local inference server, model identifier, and API endpoints.";
  localLlmElements.statusValue.textContent = config.enabled ? "Enabled" : "Disabled";
  localLlmElements.statusMessage.textContent = config.enabled
    ? "The tool is available to the middleware with the saved local server settings."
    : "The tool stays hidden from enabled workflows until you turn it on.";
  localLlmElements.summaryPresetValue.textContent = preset?.label || config.provider;
  localLlmElements.summaryServerValue.textContent = config.server_base_url || "Not configured";
  localLlmElements.summaryModelValue.textContent = config.model_identifier || "Not configured";
  populatePresetOptions();
  localLlmElements.enabledInput.value = String(Boolean(config.enabled));
  localLlmElements.providerInput.value = config.provider;
  localLlmElements.serverInput.value = config.server_base_url || "";
  localLlmElements.modelInput.value = config.model_identifier || "";
  localLlmElements.modelsEndpointInput.value = config.endpoints.models || "";
  localLlmElements.chatEndpointInput.value = config.endpoints.chat || "";
  localLlmElements.loadEndpointInput.value = config.endpoints.model_load || "";
  localLlmElements.downloadEndpointInput.value = config.endpoints.model_download || "";
  localLlmElements.downloadStatusEndpointInput.value = config.endpoints.model_download_status || "";
  renderEndpointPreview();
  renderChatTranscript();
};

const renderChatTranscript = () => {
  if (!localLlmElements.chatTranscript) {
    return;
  }

  if (chatMessages.length === 0) {
    localLlmElements.chatTranscript.innerHTML = `
      <article id="tools-local-llm-chat-empty" class="api-system-alert">
        Start a session to test the configured Local LLM endpoint.
      </article>
    `;
    return;
  }

  localLlmElements.chatTranscript.innerHTML = chatMessages.map((message, index) => `
    <article id="tools-local-llm-chat-message-${index + 1}" class="local-llm-chat-message local-llm-chat-message--${message.role}">
      <p id="tools-local-llm-chat-message-role-${index + 1}" class="local-llm-chat-message__role">${message.role}</p>
      <pre id="tools-local-llm-chat-message-content-${index + 1}" class="api-code-block local-llm-chat-message__content">${message.content}</pre>
    </article>
  `).join("");
  localLlmElements.chatTranscript.scrollTop = localLlmElements.chatTranscript.scrollHeight;
};

const readSseStream = async (response, handlers) => {
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    chunks.forEach((chunk) => {
      const lines = chunk.split("\n");
      let eventName = "message";
      const dataLines = [];
      lines.forEach((line) => {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        }
        if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      });
      if (dataLines.length === 0) {
        return;
      }
      const payload = JSON.parse(dataLines.join("\n"));
      handlers[eventName]?.(payload);
    });
  }
};

const loadTool = async () => {
  localLlmState = await fetchJson("/api/v1/tools/llm-deepl/local-llm");
  renderTool();
};

localLlmElements.providerInput?.addEventListener("change", () => {
  applyPresetToForm();
});

localLlmElements.applyPresetButton?.addEventListener("click", () => {
  applyPresetToForm({ announce: true });
});

[
  localLlmElements.serverInput,
  localLlmElements.modelsEndpointInput,
  localLlmElements.chatEndpointInput,
  localLlmElements.loadEndpointInput,
  localLlmElements.downloadEndpointInput,
  localLlmElements.downloadStatusEndpointInput
].forEach((input) => {
  input?.addEventListener("input", renderEndpointPreview);
});

localLlmElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!localLlmState || saving) {
    return;
  }

  saving = true;
  localLlmElements.saveButton.disabled = true;
  localLlmElements.saveButton.textContent = "Saving...";
  setFeedback("");

  try {
    localLlmState = await fetchJson("/api/v1/tools/llm-deepl/local-llm", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        enabled: localLlmElements.enabledInput.value === "true",
        provider: localLlmElements.providerInput.value,
        server_base_url: localLlmElements.serverInput.value.trim(),
        model_identifier: localLlmElements.modelInput.value.trim(),
        endpoints: {
          models: localLlmElements.modelsEndpointInput.value.trim(),
          chat: localLlmElements.chatEndpointInput.value.trim(),
          model_load: localLlmElements.loadEndpointInput.value.trim(),
          model_download: localLlmElements.downloadEndpointInput.value.trim(),
          model_download_status: localLlmElements.downloadStatusEndpointInput.value.trim()
        }
      })
    });
    renderTool();
    window.dispatchEvent(new CustomEvent("malcom:tools-directory-updated"));
    setFeedback("Local LLM configuration saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save Local LLM configuration.", "error");
  } finally {
    saving = false;
    localLlmElements.saveButton.disabled = false;
    localLlmElements.saveButton.textContent = "Save configuration";
  }
});

loadTool().catch((error) => {
  setFeedback(error instanceof Error ? error.message : "Unable to load Local LLM configuration.", "error");
});

localLlmElements.chatClearButton?.addEventListener("click", () => {
  chatMessages = [];
  chatPreviousResponseId = null;
  renderChatTranscript();
  setChatFeedback("Chat session cleared.", "success");
});

localLlmElements.chatForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (chatSending || !localLlmState) {
    return;
  }

  const userMessage = localLlmElements.chatUserInput.value.trim();
  const systemPrompt = localLlmElements.chatSystemInput.value.trim();
  if (!userMessage) {
    setChatFeedback("Enter a message before sending.", "error");
    return;
  }

  chatSending = true;
  localLlmElements.chatSendButton.disabled = true;
  localLlmElements.chatSendButton.textContent = "Streaming...";
  setChatFeedback("");

  const requestMessages = [];
  if (systemPrompt && chatMessages.length === 0) {
    requestMessages.push({ role: "system", content: systemPrompt });
  }
  if (chatMessages.length > 0 && !(localLlmState.config.endpoints.chat || "").endsWith("/api/v1/chat")) {
    requestMessages.push(...chatMessages.filter((message) => message.role !== "system"));
  }
  requestMessages.push({ role: "user", content: userMessage });

  chatMessages = [...chatMessages, { role: "user", content: userMessage }, { role: "assistant", content: "" }];
  renderChatTranscript();
  localLlmElements.chatUserInput.value = "";

  try {
    const response = await fetch(`${getBaseUrl()}/api/v1/tools/llm-deepl/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: requestMessages,
        previous_response_id: chatPreviousResponseId,
        model_identifier: localLlmState.config.model_identifier || undefined
      })
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Unable to stream Local LLM response.");
    }

    let assistantContent = "";
    await readSseStream(response, {
      delta: (payload) => {
        assistantContent += payload.content || "";
        chatMessages[chatMessages.length - 1] = { role: "assistant", content: assistantContent };
        renderChatTranscript();
      },
      done: (payload) => {
        chatPreviousResponseId = payload.response_id || chatPreviousResponseId;
        if (!assistantContent && payload.response_text) {
          assistantContent = payload.response_text;
          chatMessages[chatMessages.length - 1] = { role: "assistant", content: assistantContent };
          renderChatTranscript();
        }
        setChatFeedback("Response received.", "success");
      },
      error: (payload) => {
        throw new Error(payload.message || "Streaming response failed.");
      }
    });
  } catch (error) {
    chatMessages[chatMessages.length - 1] = {
      role: "assistant",
      content: error instanceof Error ? error.message : "Unable to reach the Local LLM endpoint."
    };
    renderChatTranscript();
    setChatFeedback(error instanceof Error ? error.message : "Unable to reach the Local LLM endpoint.", "error");
  } finally {
    chatSending = false;
    localLlmElements.chatSendButton.disabled = false;
    localLlmElements.chatSendButton.textContent = "Send message";
  }
});
