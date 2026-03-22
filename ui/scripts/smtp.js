import { formatDateTime, formatSize, createElementMap } from "./format-utils.js";
import { normalizeRequestError, requestJson as fetchJson } from "./request.js";

const smtpElements = createElementMap({
  form: "tools-smtp-form",
  machineInput: "tools-smtp-machine-input",
  bindHostInput: "tools-smtp-bind-host-input",
  portInput: "tools-smtp-port-input",
  recipientEmailInput: "tools-smtp-recipient-email-input",
  feedback: "tools-smtp-form-feedback",
  saveButton: "tools-smtp-save-button",
  startButton: "tools-smtp-start-button",
  stopButton: "tools-smtp-stop-button",
  runtimeStatusValue: "tools-smtp-runtime-status-value",
  runtimeStatusMessage: "tools-smtp-runtime-status-message",
  runtimeBanner: "tools-smtp-runtime-banner",
  runtimeBannerTitle: "tools-smtp-runtime-banner-title",
  runtimeBannerBody: "tools-smtp-runtime-banner-body",
  summaryMachineValue: "tools-smtp-summary-machine-value",
  summaryReceiveValue: "tools-smtp-summary-receive-value",
  summaryReceiveCopy: "tools-smtp-summary-receive-copy",
  summaryEndpointValue: "tools-smtp-summary-endpoint-value",
  summaryMessagesValue: "tools-smtp-summary-messages-value",
  activityStartedValue: "tools-smtp-activity-started-value",
  activityStoppedValue: "tools-smtp-activity-stopped-value",
  activitySessionsValue: "tools-smtp-activity-sessions-value",
  activityLastMessageValue: "tools-smtp-activity-last-message-value",
  activitySenderValue: "tools-smtp-activity-sender-value",
  activityRecipientValue: "tools-smtp-activity-recipient-value",
  machinesBody: "tools-smtp-machines-body",
  receiveAddress: "tools-smtp-receive-address",
  receiveHint: "tools-smtp-receive-hint",
  copyEmailButton: "tools-smtp-copy-email-button",
  copyEndpointButton: "tools-smtp-copy-endpoint-button",
  outboundFeedback: "tools-smtp-outbound-feedback",
  openTestModalButton: "tools-smtp-open-test-modal-button",
  openRelayModalButton: "tools-smtp-open-relay-modal-button",
  mailboxEmpty: "tools-smtp-mailbox-empty",
  mailboxList: "tools-smtp-mailbox-list",
  messageEmpty: "tools-smtp-message-empty",
  messageDetail: "tools-smtp-message-detail",
  messageSubjectValue: "tools-smtp-message-meta-subject-value",
  messageFromValue: "tools-smtp-message-meta-from-value",
  messageToValue: "tools-smtp-message-meta-to-value",
  messageTimeValue: "tools-smtp-message-meta-time-value",
  messagePeerValue: "tools-smtp-message-meta-peer-value",
  messageSizeValue: "tools-smtp-message-meta-size-value",
  messageBodyValue: "tools-smtp-message-body-value",
  messageRawValue: "tools-smtp-message-raw-value",
  copyRawMessageButton: "tools-smtp-copy-raw-message-button",
  testModal: "tools-smtp-test-modal",
  testForm: "tools-smtp-test-form",
  testFromInput: "tools-smtp-test-from-input",
  testToInput: "tools-smtp-test-to-input",
  testSubjectInput: "tools-smtp-test-subject-input",
  testBodyInput: "tools-smtp-test-body-input",
  testFeedback: "tools-smtp-test-feedback",
  testSubmitButton: "tools-smtp-test-submit-button",
  relayModal: "tools-smtp-relay-modal",
  relayForm: "tools-smtp-relay-form",
  relayHostInput: "tools-smtp-relay-host-input",
  relayPortInput: "tools-smtp-relay-port-input",
  relaySecurityInput: "tools-smtp-relay-security-input",
  relayAuthModeInput: "tools-smtp-relay-auth-mode-input",
  relayUsernameInput: "tools-smtp-relay-username-input",
  relayPasswordInput: "tools-smtp-relay-password-input",
  relayFromInput: "tools-smtp-relay-from-input",
  relayToInput: "tools-smtp-relay-to-input",
  relaySubjectInput: "tools-smtp-relay-subject-input",
  relayBodyInput: "tools-smtp-relay-body-input",
  relayFeedback: "tools-smtp-relay-feedback",
  relaySubmitButton: "tools-smtp-relay-submit-button",
  relayUsernameField: "tools-smtp-relay-username-field",
  relayPasswordField: "tools-smtp-relay-password-field"
});

const smtpState = {
  tool: null,
  pendingRequest: false,
  refreshTimer: null,
  selectedMessageId: null,
  highlightedMessageId: null
};

const setFeedback = (element, message, tone = "") => {
  if (!element) {
    return;
  }

  element.textContent = message;
  element.className = tone ? `api-form-feedback api-form-feedback--${tone}` : "api-form-feedback";
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

const getSelectedMachine = (machines, machineId) => (
  machines.find((machine) => machine.id === machineId)
  || machines.find((machine) => machine.is_local)
  || machines[0]
  || null
);

const getUiState = (data) => {
  const status = data?.runtime?.status || "stopped";
  return {
    canStart: status === "stopped" || status === "error",
    canStop: status === "running" || status === "assigned",
    isRemoteAssignment: status === "assigned",
    isLocalListening: status === "running" && Boolean(data?.runtime?.listening_host) && data?.runtime?.listening_port !== null
  };
};

const renderMachineOptions = (data) => {
  const selectedMachineId = data.config.target_worker_id || getSelectedMachine(data.machines, null)?.id || "";
  const fragment = document.createDocumentFragment();

  data.machines.forEach((machine) => {
    const option = document.createElement("option");
    option.id = `tools-smtp-machine-option-${machine.id}`;
    option.value = machine.id;
    option.textContent = machine.is_local ? `${machine.name} (Local)` : `${machine.name} (${machine.address})`;
    option.selected = machine.id === selectedMachineId;
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
    capabilitiesCell.textContent = machine.capabilities.length > 0 ? machine.capabilities.join(", ") : "No declared capabilities";

    row.append(nameCell, addressCell, statusCell, capabilitiesCell);
    fragment.appendChild(row);
  });

  smtpElements.machinesBody.replaceChildren(fragment);
};

const renderRuntimeBanner = (data, uiState) => {
  let tone = "";
  let title = "SMTP listener is stopped";
  let body = "Start the listener to receive mail and unlock the local test-send flow.";

  if (uiState.isLocalListening) {
    tone = "success";
    title = "SMTP listener is running locally";
    body = data.inbound_identity.connection_hint;
  } else if (uiState.isRemoteAssignment) {
    tone = "warning";
    title = "SMTP is assigned remotely";
    body = "Remote execution is visible for planning purposes, but only local listener execution is wired today.";
  } else if (data.runtime.status === "error") {
    tone = "error";
    title = "SMTP listener failed to start";
    body = data.runtime.last_error || data.runtime.message;
  }

  smtpElements.runtimeBanner.className = tone ? `api-system-alert api-system-alert--${tone}` : "api-system-alert";
  smtpElements.runtimeBannerTitle.textContent = title;
  smtpElements.runtimeBannerBody.textContent = body;
};

const renderReceiveIdentity = (data) => {
  const identity = data.inbound_identity;
  smtpElements.summaryReceiveValue.textContent = identity.display_address;
  smtpElements.summaryReceiveCopy.textContent = identity.accepts_any_recipient
    ? "Catch-all mode accepts any recipient at the current listener endpoint."
    : "Only the configured mailbox address is accepted by the listener.";
  smtpElements.receiveAddress.textContent = identity.display_address;
  smtpElements.receiveHint.textContent = identity.connection_hint;
  smtpElements.copyEmailButton.disabled = !identity.configured_recipient_email;
  smtpElements.copyEndpointButton.disabled = !(identity.listening_host && identity.listening_port !== null);
};

const renderMailboxList = (data) => {
  const recentMessages = Array.isArray(data.runtime.recent_messages) ? data.runtime.recent_messages : [];
  smtpElements.mailboxEmpty.hidden = recentMessages.length > 0;

  if (recentMessages.length === 0) {
    smtpElements.mailboxList.replaceChildren();
    smtpState.selectedMessageId = null;
    renderSelectedMessage(null);
    return;
  }

  if (!recentMessages.some((messageEntry) => messageEntry.id === smtpState.selectedMessageId)) {
    smtpState.selectedMessageId = smtpState.highlightedMessageId && recentMessages.some((messageEntry) => messageEntry.id === smtpState.highlightedMessageId)
      ? smtpState.highlightedMessageId
      : recentMessages[0].id;
  }

  const fragment = document.createDocumentFragment();
  recentMessages.forEach((messageEntry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `tools-smtp-mailbox-item-${messageEntry.id}`;
    button.className = "smtp-mailbox-item";
    if (messageEntry.id === smtpState.selectedMessageId) {
      button.classList.add("smtp-mailbox-item--selected");
    }
    if (messageEntry.id === smtpState.highlightedMessageId) {
      button.classList.add("smtp-mailbox-item--highlighted");
    }
    button.dataset.messageId = messageEntry.id;

    const header = document.createElement("div");
    header.id = `tools-smtp-mailbox-item-header-${messageEntry.id}`;
    header.className = "smtp-mailbox-item__header";

    const subject = document.createElement("p");
    subject.id = `tools-smtp-mailbox-item-subject-${messageEntry.id}`;
    subject.className = "smtp-mailbox-item__subject";
    subject.textContent = messageEntry.subject || "(No subject)";

    const timestamp = document.createElement("p");
    timestamp.id = `tools-smtp-mailbox-item-timestamp-${messageEntry.id}`;
    timestamp.className = "smtp-mailbox-item__timestamp";
    timestamp.textContent = formatDateTime(messageEntry.received_at, "Unknown");

    const from = document.createElement("p");
    from.id = `tools-smtp-mailbox-item-from-${messageEntry.id}`;
    from.className = "smtp-mailbox-item__meta";
    from.textContent = `From ${messageEntry.mail_from || "unknown sender"}`;

    const to = document.createElement("p");
    to.id = `tools-smtp-mailbox-item-to-${messageEntry.id}`;
    to.className = "smtp-mailbox-item__meta";
    to.textContent = `To ${(messageEntry.recipients || []).join(", ") || "unknown recipient"}`;

    const preview = document.createElement("p");
    preview.id = `tools-smtp-mailbox-item-preview-${messageEntry.id}`;
    preview.className = "smtp-mailbox-item__preview";
    preview.textContent = messageEntry.body_preview || "No preview available.";

    header.append(subject, timestamp);
    button.append(header, from, to, preview);
    fragment.appendChild(button);
  });

  smtpElements.mailboxList.replaceChildren(fragment);
  renderSelectedMessage(recentMessages.find((entry) => entry.id === smtpState.selectedMessageId) || recentMessages[0]);
};

const renderSelectedMessage = (messageEntry) => {
  if (!messageEntry) {
    smtpElements.messageEmpty.hidden = false;
    smtpElements.messageDetail.hidden = true;
    return;
  }

  smtpElements.messageEmpty.hidden = true;
  smtpElements.messageDetail.hidden = false;
  smtpElements.messageSubjectValue.textContent = messageEntry.subject || "(No subject)";
  smtpElements.messageFromValue.textContent = messageEntry.mail_from || "Unknown";
  smtpElements.messageToValue.textContent = (messageEntry.recipients || []).join(", ") || "Unknown";
  smtpElements.messageTimeValue.textContent = formatDateTime(messageEntry.received_at, "Unknown");
  smtpElements.messagePeerValue.textContent = messageEntry.peer || "Unknown";
  smtpElements.messageSizeValue.textContent = formatSize(messageEntry.size_bytes);
  smtpElements.messageBodyValue.textContent = messageEntry.body || messageEntry.body_preview || "No body available.";
  smtpElements.messageRawValue.textContent = messageEntry.raw_message || "No raw message available.";
  smtpElements.copyRawMessageButton.disabled = !messageEntry.raw_message;
};

const setBusyState = (isBusy, actionLabel = "") => {
  smtpState.pendingRequest = isBusy;
  smtpElements.saveButton.disabled = isBusy;
  smtpElements.startButton.disabled = isBusy;
  smtpElements.stopButton.disabled = isBusy;
  smtpElements.testSubmitButton.disabled = isBusy;
  smtpElements.relaySubmitButton.disabled = isBusy;

  smtpElements.saveButton.textContent = isBusy && actionLabel === "save" ? "Saving..." : "Save assignment";
  smtpElements.startButton.textContent = isBusy && actionLabel === "start" ? "Starting..." : "Start SMTP server";
  smtpElements.stopButton.textContent = isBusy && actionLabel === "stop" ? "Stopping..." : "Stop SMTP server";
  smtpElements.testSubmitButton.textContent = isBusy && actionLabel === "test" ? "Sending..." : "Send test email";
  smtpElements.relaySubmitButton.textContent = isBusy && actionLabel === "relay" ? "Sending..." : "Send relay email";
};

const toggleModal = (modal, shouldOpen) => {
  if (!modal) {
    return;
  }

  modal.classList.toggle("modal--open", shouldOpen);
  modal.setAttribute("aria-hidden", String(!shouldOpen));
  document.body.classList.toggle("modal-open", Boolean(document.querySelector(".modal.modal--open")));
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

const readTestPayload = () => {
  const mailFrom = smtpElements.testFromInput.value.trim().toLowerCase();
  const recipient = smtpElements.testToInput.value.trim().toLowerCase();
  if (!mailFrom || !recipient) {
    throw new Error("Both sender and recipient email addresses are required.");
  }

  return {
    mail_from: mailFrom,
    recipients: [recipient],
    subject: smtpElements.testSubjectInput.value.trim(),
    body: smtpElements.testBodyInput.value
  };
};

const readRelayPayload = () => {
  const host = smtpElements.relayHostInput.value.trim();
  const port = Number.parseInt(smtpElements.relayPortInput.value, 10);
  const recipients = smtpElements.relayToInput.value
    .split(/[\n,]+/)
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);

  if (!host) {
    throw new Error("SMTP host is required.");
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("Port must be between 1 and 65535.");
  }

  return {
    host,
    port,
    security: smtpElements.relaySecurityInput.value,
    auth_mode: smtpElements.relayAuthModeInput.value,
    username: smtpElements.relayUsernameInput.value.trim() || null,
    password: smtpElements.relayPasswordInput.value || null,
    mail_from: smtpElements.relayFromInput.value.trim().toLowerCase(),
    recipients,
    subject: smtpElements.relaySubjectInput.value.trim(),
    body: smtpElements.relayBodyInput.value
  };
};

const applyState = (data) => {
  const previousMessageCount = smtpState.tool?.runtime?.message_count ?? 0;
  smtpState.tool = data;

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

  const uiState = getUiState(data);
  smtpElements.startButton.hidden = !uiState.canStart;
  smtpElements.stopButton.hidden = !uiState.canStop;
  smtpElements.openTestModalButton.disabled = !uiState.isLocalListening || smtpState.pendingRequest;
  smtpElements.openRelayModalButton.disabled = smtpState.pendingRequest;

  smtpElements.relayUsernameField.hidden = smtpElements.relayAuthModeInput.value !== "password";
  smtpElements.relayPasswordField.hidden = smtpElements.relayAuthModeInput.value !== "password";

  renderRuntimeBanner(data, uiState);
  renderReceiveIdentity(data);
  renderMailboxList(data);

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
    smtpState.highlightedMessageId = recentMessages[0].id;
    smtpState.selectedMessageId = recentMessages[0].id;
    renderMailboxList(data);
    setFeedback(smtpElements.feedback, `Received email for ${recentMessages[0].recipients?.[0] || "configured mailbox"}.`, "success");
  }
};

const refreshState = async () => {
  const data = await fetchJson("/api/v1/tools/smtp");
  applyState(data);
};

const saveSmtpConfig = async () => {
  const payload = readFormPayload();
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
  const data = await fetchJson("/api/v1/tools/smtp/start", { method: "POST" });
  applyState(data);
};

const stopSmtpServer = async () => {
  const data = await fetchJson("/api/v1/tools/smtp/stop", { method: "POST" });
  applyState(data);
};

const copyText = async (text, successMessage) => {
  if (!text) {
    setFeedback(smtpElements.outboundFeedback, "Nothing available to copy.", "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    setFeedback(smtpElements.outboundFeedback, successMessage, "success");
  } catch (error) {
    setFeedback(smtpElements.outboundFeedback, normalizeRequestError(error, "Unable to copy value.").message, "error");
  }
};

const scheduleRefresh = () => {
  if (smtpState.refreshTimer !== null) {
    window.clearInterval(smtpState.refreshTimer);
  }

  smtpState.refreshTimer = window.setInterval(() => {
    if (smtpState.pendingRequest) {
      return;
    }

    refreshState().catch(() => {});
  }, 5000);
};

smtpElements.form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (smtpState.pendingRequest) {
    return;
  }

  setBusyState(true, "save");
  setFeedback(smtpElements.feedback, "");

  try {
    await saveSmtpConfig();
    setFeedback(smtpElements.feedback, "SMTP assignment saved.", "success");
  } catch (error) {
    setFeedback(smtpElements.feedback, normalizeRequestError(error, "Unable to save SMTP assignment.").message, "error");
  } finally {
    setBusyState(false);
    if (smtpState.tool) {
      applyState(smtpState.tool);
    }
  }
});

smtpElements.startButton?.addEventListener("click", async () => {
  if (smtpState.pendingRequest) {
    return;
  }

  setBusyState(true, "start");
  setFeedback(smtpElements.feedback, "");

  try {
    await startSmtpServer();
    setFeedback(smtpElements.feedback, "SMTP server started.", "success");
  } catch (error) {
    setFeedback(smtpElements.feedback, normalizeRequestError(error, "Unable to start SMTP server.").message, "error");
  } finally {
    setBusyState(false);
    if (smtpState.tool) {
      applyState(smtpState.tool);
    }
  }
});

smtpElements.stopButton?.addEventListener("click", async () => {
  if (smtpState.pendingRequest) {
    return;
  }

  setBusyState(true, "stop");
  setFeedback(smtpElements.feedback, "");

  try {
    await stopSmtpServer();
    setFeedback(smtpElements.feedback, "SMTP server stopped.", "success");
  } catch (error) {
    setFeedback(smtpElements.feedback, normalizeRequestError(error, "Unable to stop SMTP server.").message, "error");
  } finally {
    setBusyState(false);
    if (smtpState.tool) {
      applyState(smtpState.tool);
    }
  }
});

smtpElements.mailboxList?.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-message-id]");
  if (!(trigger instanceof HTMLElement) || !smtpState.tool) {
    return;
  }

  smtpState.selectedMessageId = trigger.dataset.messageId || null;
  smtpState.highlightedMessageId = smtpState.highlightedMessageId === smtpState.selectedMessageId ? null : smtpState.highlightedMessageId;
  renderMailboxList(smtpState.tool);
});

smtpElements.openTestModalButton?.addEventListener("click", () => {
  const identity = smtpState.tool?.inbound_identity;
  smtpElements.testFromInput.value ||= "smtp-test@malcom.local";
  smtpElements.testToInput.value = identity?.configured_recipient_email || "";
  smtpElements.testToInput.disabled = !identity?.accepts_any_recipient && Boolean(identity?.configured_recipient_email);
  setFeedback(smtpElements.testFeedback, "");
  toggleModal(smtpElements.testModal, true);
});

smtpElements.openRelayModalButton?.addEventListener("click", () => {
  setFeedback(smtpElements.relayFeedback, "");
  toggleModal(smtpElements.relayModal, true);
});

smtpElements.testForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (smtpState.pendingRequest) {
    return;
  }

  setBusyState(true, "test");
  setFeedback(smtpElements.testFeedback, "");
  setFeedback(smtpElements.outboundFeedback, "");

  try {
    const payload = readTestPayload();
    const result = await fetchJson("/api/v1/tools/smtp/send-test", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    emitSmtpLog({
      id: `smtp_test_send_${Date.now()}`,
      timestamp: new Date().toISOString(),
      action: "smtp_test_send_succeeded",
      message: `Sent a test email to ${payload.recipients[0]}.`,
      details: payload
    });
    smtpState.highlightedMessageId = result.message_id || null;
    await refreshState();
    setFeedback(smtpElements.testFeedback, result.message, "success");
    setFeedback(smtpElements.outboundFeedback, result.message, "success");
  } catch (error) {
    emitSmtpLog({
      id: `smtp_test_send_failed_${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: "error",
      action: "smtp_test_send_failed",
      message: "Failed to send a local SMTP test message."
    });
    setFeedback(smtpElements.testFeedback, normalizeRequestError(error, "Unable to send test email.").message, "error");
  } finally {
    setBusyState(false);
    if (smtpState.tool) {
      applyState(smtpState.tool);
    }
  }
});

smtpElements.relayForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (smtpState.pendingRequest) {
    return;
  }

  setBusyState(true, "relay");
  setFeedback(smtpElements.relayFeedback, "");
  setFeedback(smtpElements.outboundFeedback, "");

  try {
    const payload = readRelayPayload();
    const result = await fetchJson("/api/v1/tools/smtp/send-relay", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    emitSmtpLog({
      id: `smtp_relay_send_${Date.now()}`,
      timestamp: new Date().toISOString(),
      action: "smtp_relay_send_succeeded",
      message: `Relay email sent through ${payload.host}:${payload.port}.`,
      details: {
        host: payload.host,
        port: payload.port,
        security: payload.security,
        recipients: payload.recipients
      }
    });
    setFeedback(smtpElements.relayFeedback, result.message, "success");
    setFeedback(smtpElements.outboundFeedback, result.message, "success");
  } catch (error) {
    emitSmtpLog({
      id: `smtp_relay_send_failed_${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: "error",
      action: "smtp_relay_send_failed",
      message: "Failed to send an external relay email."
    });
    setFeedback(smtpElements.relayFeedback, normalizeRequestError(error, "Unable to send relay email.").message, "error");
  } finally {
    setBusyState(false);
    if (smtpState.tool) {
      applyState(smtpState.tool);
    }
  }
});

smtpElements.copyEmailButton?.addEventListener("click", () => {
  copyText(smtpState.tool?.inbound_identity?.configured_recipient_email || "", "Receive email copied.");
});

smtpElements.copyEndpointButton?.addEventListener("click", () => {
  const identity = smtpState.tool?.inbound_identity;
  const endpoint = identity?.listening_host && identity?.listening_port !== null
    ? `${identity.listening_host}:${identity.listening_port}`
    : "";
  copyText(endpoint, "Listener endpoint copied.");
});

smtpElements.copyRawMessageButton?.addEventListener("click", () => {
  copyText(smtpElements.messageRawValue.textContent || "", "Raw SMTP content copied.");
});

smtpElements.relayAuthModeInput?.addEventListener("change", () => {
  const usesPassword = smtpElements.relayAuthModeInput.value === "password";
  smtpElements.relayUsernameField.hidden = !usesPassword;
  smtpElements.relayPasswordField.hidden = !usesPassword;
});

document.addEventListener("click", (event) => {
  const closeTarget = event.target.closest("[data-modal-close]");
  if (!(closeTarget instanceof HTMLElement)) {
    return;
  }

  const modalId = closeTarget.dataset.modalClose;
  if (modalId === "tools-smtp-test-modal") {
    toggleModal(smtpElements.testModal, false);
  }
  if (modalId === "tools-smtp-relay-modal") {
    toggleModal(smtpElements.relayModal, false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }

  if (smtpElements.testModal?.classList.contains("modal--open")) {
    toggleModal(smtpElements.testModal, false);
  }
  if (smtpElements.relayModal?.classList.contains("modal--open")) {
    toggleModal(smtpElements.relayModal, false);
  }
});

refreshState().catch((error) => {
  setFeedback(smtpElements.feedback, normalizeRequestError(error, "Unable to load SMTP tool.").message, "error");
});

scheduleRefresh();
