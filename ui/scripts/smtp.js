const smtpElements = {
  form: document.getElementById("tools-smtp-form"),
  machineInput: document.getElementById("tools-smtp-machine-input"),
  bindHostInput: document.getElementById("tools-smtp-bind-host-input"),
  portInput: document.getElementById("tools-smtp-port-input"),
  recipientEmailInput: document.getElementById("tools-smtp-recipient-email-input"),
  feedback: document.getElementById("tools-smtp-form-feedback"),
  saveButton: document.getElementById("tools-smtp-save-button"),
  startButton: document.getElementById("tools-smtp-start-button"),
  stopButton: document.getElementById("tools-smtp-stop-button"),
  runtimeStatusValue: document.getElementById("tools-smtp-runtime-status-value"),
  runtimeStatusMessage: document.getElementById("tools-smtp-runtime-status-message"),
  summaryMachineValue: document.getElementById("tools-smtp-summary-machine-value"),
  summaryEndpointValue: document.getElementById("tools-smtp-summary-endpoint-value"),
  summaryMessagesValue: document.getElementById("tools-smtp-summary-messages-value"),
  activityStartedValue: document.getElementById("tools-smtp-activity-started-value"),
  activityStoppedValue: document.getElementById("tools-smtp-activity-stopped-value"),
  activitySessionsValue: document.getElementById("tools-smtp-activity-sessions-value"),
  activityLastMessageValue: document.getElementById("tools-smtp-activity-last-message-value"),
  activitySenderValue: document.getElementById("tools-smtp-activity-sender-value"),
  activityRecipientValue: document.getElementById("tools-smtp-activity-recipient-value"),
  machinesBody: document.getElementById("tools-smtp-machines-body")
};

let smtpState = null;
let pendingRequest = false;
let refreshTimer = null;

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
  smtpElements.feedback.textContent = message;
  smtpElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const emitSmtpLog = ({
  id,
  timestamp,
  level = "info",
  action,
  message,
  details = {},
  context = {}
}) => {
  window.MalcomLogStore?.log({
    id,
    timestamp,
    source: "ui.smtp",
    category: "email",
    level,
    action,
    message,
    details,
    context
  });
};

const hasExistingLogEntry = (logId) => {
  const existingLogs = window.MalcomLogStore?.getLogs?.() || [];
  return existingLogs.some((entry) => entry.id === logId);
};

const formatDateTime = (value, fallback) => {
  if (!value) {
    return fallback;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return fallback;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(parsed);
};

const getSelectedMachine = (machines, machineId) => (
  machines.find((machine) => machine.id === machineId)
  || machines.find((machine) => machine.is_local)
  || machines[0]
  || null
);

const renderMachineOptions = (data) => {
  const selectedMachineId = data.config.target_worker_id || getSelectedMachine(data.machines, null)?.id || "";
  const fragment = document.createDocumentFragment();

  data.machines.forEach((machine) => {
    const option = document.createElement("option");
    option.id = `tools-smtp-machine-option-${machine.id}`;
    option.value = machine.id;
    option.textContent = machine.is_local ? `${machine.name} (Local)` : `${machine.name} (${machine.address})`;
    if (machine.id === selectedMachineId) {
      option.selected = true;
    }
    fragment.appendChild(option);
  });

  smtpElements.machineInput.replaceChildren(fragment);
};

const renderMachinesTable = (machines) => {
  const fragment = document.createDocumentFragment();

  machines.forEach((machine) => {
    const row = document.createElement("tr");
    row.id = `tools-smtp-machine-row-${machine.id}`;

    const nameCell = document.createElement("td");
    nameCell.id = `tools-smtp-machine-name-${machine.id}`;
    nameCell.textContent = machine.is_local ? `${machine.name} (Local)` : machine.name;

    const addressCell = document.createElement("td");
    addressCell.id = `tools-smtp-machine-address-${machine.id}`;
    addressCell.textContent = `${machine.address} · ${machine.hostname}`;

    const statusCell = document.createElement("td");
    statusCell.id = `tools-smtp-machine-status-${machine.id}`;
    statusCell.textContent = machine.status;

    const capabilitiesCell = document.createElement("td");
    capabilitiesCell.id = `tools-smtp-machine-capabilities-${machine.id}`;
    capabilitiesCell.textContent = machine.capabilities.length > 0
      ? machine.capabilities.join(", ")
      : "No declared capabilities";

    row.append(nameCell, addressCell, statusCell, capabilitiesCell);
    fragment.appendChild(row);
  });

  smtpElements.machinesBody.replaceChildren(fragment);
};

const applyState = (data) => {
  const previousMessageCount = smtpState?.runtime?.message_count ?? 0;
  smtpState = data;
  renderMachineOptions(data);
  renderMachinesTable(data.machines);

  smtpElements.bindHostInput.value = data.config.bind_host;
  smtpElements.portInput.value = String(data.config.port);
  smtpElements.recipientEmailInput.value = data.config.recipient_email || "";
  smtpElements.runtimeStatusValue.textContent = data.runtime.status;
  smtpElements.runtimeStatusMessage.textContent = data.runtime.message;

  const selectedMachine = getSelectedMachine(data.machines, data.config.target_worker_id || data.runtime.selected_machine_id);
  smtpElements.summaryMachineValue.textContent = selectedMachine ? selectedMachine.name : "Unassigned";
  smtpElements.summaryEndpointValue.textContent = data.runtime.listening_host && data.runtime.listening_port !== null
    ? `${data.runtime.listening_host}:${data.runtime.listening_port}`
    : "Not listening";
  smtpElements.summaryMessagesValue.textContent = String(data.runtime.message_count);

  smtpElements.activityStartedValue.textContent = formatDateTime(data.runtime.last_started_at, "Never");
  smtpElements.activityStoppedValue.textContent = formatDateTime(data.runtime.last_stopped_at, "Never");
  smtpElements.activitySessionsValue.textContent = String(data.runtime.session_count);
  smtpElements.activityLastMessageValue.textContent = formatDateTime(data.runtime.last_message_at, "No mail received yet");
  smtpElements.activitySenderValue.textContent = data.runtime.last_mail_from || "Unknown";
  smtpElements.activityRecipientValue.textContent = data.runtime.last_recipient || "Unknown";

  const recentMessages = Array.isArray(data.runtime.recent_messages) ? data.runtime.recent_messages : [];
  recentMessages.forEach((messageEntry) => {
    if (hasExistingLogEntry(messageEntry.id)) {
      return;
    }

    emitSmtpLog({
      id: messageEntry.id,
      timestamp: messageEntry.received_at,
      action: "smtp_message_received",
      message: `Email received for ${messageEntry.recipients?.[0] || "configured mailbox"}.`,
      details: {
        subject: messageEntry.subject || null,
        body_preview: messageEntry.body_preview || null,
        recipients: messageEntry.recipients || [],
        peer: messageEntry.peer,
        size_bytes: messageEntry.size_bytes
      },
      context: {
        mail_from: messageEntry.mail_from,
        tool: "smtp"
      }
    });
  });

  if (data.runtime.message_count > previousMessageCount && recentMessages[0]) {
    setFeedback(`Received email for ${recentMessages[0].recipients?.[0] || "configured mailbox"}.`, "success");
  }
};

const setBusyState = (isBusy, actionLabel = "") => {
  pendingRequest = isBusy;
  smtpElements.saveButton.disabled = isBusy;
  smtpElements.startButton.disabled = isBusy;
  smtpElements.stopButton.disabled = isBusy;

  smtpElements.saveButton.textContent = isBusy && actionLabel === "save" ? "Saving..." : "Save assignment";
  smtpElements.startButton.textContent = isBusy && actionLabel === "start" ? "Starting..." : "Start SMTP server";
  smtpElements.stopButton.textContent = isBusy && actionLabel === "stop" ? "Stopping..." : "Stop SMTP server";
};

const fetchJson = async (path, options = {}) => {
  const response = await fetch(`${getBaseUrl()}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || "SMTP request failed.");
  }

  return payload;
};

const readFormPayload = () => {
  const bindHost = smtpElements.bindHostInput.value.trim();
  const portValue = Number.parseInt(smtpElements.portInput.value, 10);

  if (!bindHost) {
    throw new Error("Bind host is required.");
  }

  if (!Number.isInteger(portValue) || portValue < 0 || portValue > 65535) {
    throw new Error("Port must be between 0 and 65535.");
  }

  const recipientEmail = smtpElements.recipientEmailInput.value.trim().toLowerCase();
  if (recipientEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipientEmail)) {
    throw new Error("Recipient email must be a valid email address.");
  }

  return {
    target_worker_id: smtpElements.machineInput.value || null,
    bind_host: bindHost,
    port: portValue,
    recipient_email: recipientEmail || null
  };
};

const refreshState = async () => {
  const data = await fetchJson("/api/v1/tools/smtp");
  applyState(data);
};

const saveSmtpConfig = async (extraPayload = {}) => {
  const payload = {
    ...readFormPayload(),
    ...extraPayload
  };

  const data = await fetchJson("/api/v1/tools/smtp", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  applyState(data);
  return data;
};

const startSmtpServer = async () => {
  await saveSmtpConfig();
  const data = await fetchJson("/api/v1/tools/smtp/start", {
    method: "POST"
  });
  applyState(data);
};

const stopSmtpServer = async () => {
  const data = await fetchJson("/api/v1/tools/smtp/stop", {
    method: "POST"
  });
  applyState(data);
};

const scheduleRefresh = () => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
  }

  refreshTimer = window.setInterval(() => {
    if (pendingRequest) {
      return;
    }

    refreshState().catch(() => {});
  }, 5000);
};

smtpElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (pendingRequest) {
    return;
  }

  setBusyState(true, "save");
  setFeedback("");

  try {
    await saveSmtpConfig();
    setFeedback("SMTP assignment saved.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to save SMTP assignment.", "error");
  } finally {
    setBusyState(false);
  }
});

smtpElements.startButton?.addEventListener("click", async () => {
  if (pendingRequest) {
    return;
  }

  setBusyState(true, "start");
  setFeedback("");

  try {
    await startSmtpServer();
    setFeedback("SMTP server state updated.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to start SMTP server.", "error");
  } finally {
    setBusyState(false);
  }
});

smtpElements.stopButton?.addEventListener("click", async () => {
  if (pendingRequest) {
    return;
  }

  setBusyState(true, "stop");
  setFeedback("");

  try {
    await stopSmtpServer();
    setFeedback("SMTP server stopped.", "success");
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : "Unable to stop SMTP server.", "error");
  } finally {
    setBusyState(false);
  }
});

refreshState().catch((error) => {
  setFeedback(error instanceof Error ? error.message : "Unable to load SMTP tool.", "error");
});

scheduleRefresh();
