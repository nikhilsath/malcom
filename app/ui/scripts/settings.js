const settingsElements = {
  form: document.getElementById("settings-form"),
  feedback: document.getElementById("settings-feedback"),
  resetButton: document.getElementById("settings-reset-button"),
  clearButton: document.getElementById("settings-clear-logs-button"),
  totalLogsValue: document.getElementById("settings-log-total-value"),
  newestLogValue: document.getElementById("settings-log-newest-value"),
  workspaceEnvironmentSelect: document.getElementById("settings-workspace-environment-select"),
  workspaceTimezoneSelect: document.getElementById("settings-workspace-timezone-select"),
  workspaceToolRetriesInput: document.getElementById("settings-workspace-tool-retries-input"),
  workspaceProxyDomainInput: document.getElementById("settings-workspace-proxy-domain-input"),
  workspaceProxyHttpPortInput: document.getElementById("settings-workspace-proxy-http-port-input"),
  workspaceProxyHttpsPortInput: document.getElementById("settings-workspace-proxy-https-port-input"),
  workspaceProxyEnabledToggle: document.getElementById("settings-workspace-proxy-enabled-toggle"),
  workspaceProxyEnabledCheckbox: document.getElementById("settings-workspace-proxy-enabled-checkbox"),
  workspaceProxyTestButton: document.getElementById("settings-workspace-proxy-test-button"),
  workspaceProxyTestFeedback: document.getElementById("settings-workspace-proxy-test-feedback"),
  retentionInput: document.getElementById("settings-log-retention-input"),
  visibleInput: document.getElementById("settings-log-visible-input"),
  detailInput: document.getElementById("settings-log-detail-input"),
  fileSizeInput: document.getElementById("settings-log-file-size-input"),
  notificationsChannelSelect: document.getElementById("settings-notifications-channel-select"),
  notificationsDigestSelect: document.getElementById("settings-notifications-digest-select"),
  dataRedactionCheckbox: document.getElementById("settings-data-redaction-checkbox"),
  storageMaxMbInput: document.getElementById("settings-storage-max-mb-input"),
  accessSessionSelect: document.getElementById("settings-access-session-select"),
  accessApprovalCheckbox: document.getElementById("settings-access-approval-checkbox"),
  accessTokenSelect: document.getElementById("settings-access-token-select")
};

const currentSettingsSection = document.body?.dataset.settingsSection || null;

const formatSettingsDateTime = (value) => {
  if (!value) {
    return "No logs recorded";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

const getSettingsStore = () => window.MalcomLogStore;

const renderSelectOptions = (element, options = []) => {
  if (!(element instanceof HTMLSelectElement)) {
    return;
  }

  element.innerHTML = options
    .map((option) => `<option value="${option.value}">${option.label}</option>`)
    .join("");
};

const setSettingsFeedback = (message, tone) => {
  if (!settingsElements.feedback) {
    return;
  }

  settingsElements.feedback.textContent = message;
  settingsElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const setWorkspaceProxyTestFeedback = (message, tone = "") => {
  if (!settingsElements.workspaceProxyTestFeedback) {
    return;
  }

  settingsElements.workspaceProxyTestFeedback.textContent = message;
  if (tone) {
    settingsElements.workspaceProxyTestFeedback.dataset.state = tone;
    return;
  }
  delete settingsElements.workspaceProxyTestFeedback.dataset.state;
};

const formatProxyCheckSummary = (checks) => {
  if (!Array.isArray(checks) || checks.length === 0) {
    return "";
  }

  const endpointChecks = checks.filter((check) => check?.scheme === "http" || check?.scheme === "https");
  if (endpointChecks.length === 0) {
    return "";
  }

  return endpointChecks
    .map((check) => {
      const scheme = String(check.scheme || "").toUpperCase();
      if (check.reachable) {
        const statusCode = Number.isFinite(check.status_code) ? ` ${check.status_code}` : "";
        return `${scheme}${statusCode}`;
      }
      const detail = check.detail ? ` (${check.detail})` : "";
      return `${scheme} unreachable${detail}`;
    })
    .join(" | ");
};

const testWorkspaceProxyConnection = async () => {
  if (!settingsElements.workspaceProxyTestButton) {
    return;
  }

  const domain = (settingsElements.workspaceProxyDomainInput?.value || "").trim();
  if (!domain) {
    setWorkspaceProxyTestFeedback("Enter a domain before running the proxy test.", "error");
    return;
  }

  const parsedHttpPort = Number.parseInt(
    settingsElements.workspaceProxyHttpPortInput?.value || "",
    10
  );
  const parsedHttpsPort = Number.parseInt(
    settingsElements.workspaceProxyHttpsPortInput?.value || "",
    10
  );
  const payload = {
    domain,
    http_port: Number.isFinite(parsedHttpPort) ? parsedHttpPort : 80,
    https_port: Number.isFinite(parsedHttpsPort) ? parsedHttpsPort : 443,
    enabled: Boolean(settingsElements.workspaceProxyEnabledCheckbox?.checked)
  };

  settingsElements.workspaceProxyTestButton.disabled = true;
  setWorkspaceProxyTestFeedback("Testing connection...", "warning");

  try {
    const response = await window.Malcom?.requestJson?.("/api/v1/settings/proxy/test", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    const summary = formatProxyCheckSummary(response?.checks);
    if (response?.ok) {
      setWorkspaceProxyTestFeedback(
        summary ? `${response.message} ${summary}` : response.message,
        "success"
      );
    } else {
      setWorkspaceProxyTestFeedback(
        summary ? `${response?.message || "Proxy test failed."} ${summary}` : (response?.message || "Proxy test failed."),
        "error"
      );
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to run proxy test.";
    setWorkspaceProxyTestFeedback(message, "error");
  } finally {
    settingsElements.workspaceProxyTestButton.disabled = false;
  }
};

const renderSettingsSummary = () => {
  if (!settingsElements.totalLogsValue || !settingsElements.newestLogValue) {
    return;
  }

  const store = getSettingsStore();
  const logs = store.getLogs();

  settingsElements.totalLogsValue.textContent = String(logs.length);
  settingsElements.newestLogValue.textContent = formatSettingsDateTime(logs[0]?.timestamp);
};

const updateTogglePresentation = (input) => {
  const toggle = input.closest(".toggle");
  const label = toggle?.querySelector(".toggle__label");

  if (!toggle || !label) {
    return;
  }

  const isChecked = input.checked;
  toggle.classList.toggle("toggle--on", isChecked);

  if (label.id.includes("approval")) {
    label.textContent = isChecked ? "Required" : "Optional";
    return;
  }

  label.textContent = isChecked ? "Enabled" : "Disabled";
};

const initSettingsToggles = () => {
  const toggleInputs = document.querySelectorAll(".settings-option-card__toggle input[type=\"checkbox\"]");

  toggleInputs.forEach((input) => {
    updateTogglePresentation(input);
    input.addEventListener("change", () => updateTogglePresentation(input));
  });
};

const buildSectionPatch = (section, fallbackSettings) => {
  if (section === "workspace") {
    const parsedHttpPort = Number.parseInt(
      settingsElements.workspaceProxyHttpPortInput?.value || "",
      10
    );
    const parsedHttpsPort = Number.parseInt(
      settingsElements.workspaceProxyHttpsPortInput?.value || "",
      10
    );

    return {
      general: {
        environment: "live",
        timezone: settingsElements.workspaceTimezoneSelect?.value || fallbackSettings.general.timezone
      },
      automation: {
        default_tool_retries: Number.parseInt(
          settingsElements.workspaceToolRetriesInput?.value || "",
          10
        )
      },
      proxy: {
        domain: (settingsElements.workspaceProxyDomainInput?.value || "").trim(),
        http_port: Number.isFinite(parsedHttpPort)
          ? parsedHttpPort
          : (fallbackSettings.proxy?.http_port || 80),
        https_port: Number.isFinite(parsedHttpsPort)
          ? parsedHttpsPort
          : (fallbackSettings.proxy?.https_port || 443),
        enabled: settingsElements.workspaceProxyEnabledCheckbox?.checked
          ?? Boolean(fallbackSettings.proxy?.enabled)
      }
    };
  }

  if (section === "logging") {
    return {
      logging: {
        max_stored_entries: Number.parseInt(settingsElements.retentionInput?.value || "", 10),
        max_visible_entries: Number.parseInt(settingsElements.visibleInput?.value || "", 10),
        max_detail_characters: Number.parseInt(settingsElements.detailInput?.value || "", 10),
        max_file_size_mb: Number.parseInt(settingsElements.fileSizeInput?.value || "", 10)
      }
    };
  }

  if (section === "notifications") {
    return {
      notifications: {
        channel: settingsElements.notificationsChannelSelect?.value || fallbackSettings.notifications.channel,
        digest: settingsElements.notificationsDigestSelect?.value || fallbackSettings.notifications.digest
      }
    };
  }


  if (section === "data") {
    const maxStorageMb = Number.parseInt(settingsElements.storageMaxMbInput?.value || "", 10);

    return {
      data: {
        payload_redaction: settingsElements.dataRedactionCheckbox?.checked ?? fallbackSettings.data.payload_redaction
      },
      logging: {
        ...fallbackSettings.logging,
        max_file_size_mb: Number.isFinite(maxStorageMb)
          ? Math.min(100, Math.max(1, maxStorageMb))
          : fallbackSettings.logging.max_file_size_mb
      }
    };
  }

  if (section === "access") {
    return {
      security: {
        session_timeout_minutes: Number.parseInt(
          settingsElements.accessSessionSelect?.value || "",
          10
        ) || fallbackSettings.security.session_timeout_minutes,
        dual_approval_required: settingsElements.accessApprovalCheckbox?.checked
          ?? fallbackSettings.security.dual_approval_required,
        token_rotation_days: Number.parseInt(
          settingsElements.accessTokenSelect?.value || "",
          10
        ) || fallbackSettings.security.token_rotation_days
      }
    };
  }

  return {};
};

const buildSettingsPayload = () => {
  const currentSettings = getSettingsStore().getAppSettings();

  return buildSectionPatch(currentSettingsSection, currentSettings);
};

const applySettingsToPage = (settings) => {
  renderSelectOptions(settingsElements.notificationsChannelSelect, settings.options?.notification_channels || []);
  renderSelectOptions(settingsElements.notificationsDigestSelect, settings.options?.notification_digests || []);

  if (settingsElements.workspaceEnvironmentSelect) {
    settingsElements.workspaceEnvironmentSelect.value = "Live";
  }

  if (settingsElements.workspaceTimezoneSelect) {
    settingsElements.workspaceTimezoneSelect.value = settings.general.timezone;
  }

  if (settingsElements.workspaceToolRetriesInput) {
    settingsElements.workspaceToolRetriesInput.value = String(settings.automation.default_tool_retries);
  }

  if (settingsElements.workspaceProxyDomainInput) {
    settingsElements.workspaceProxyDomainInput.value = settings.proxy?.domain || "";
  }

  if (settingsElements.workspaceProxyHttpPortInput) {
    settingsElements.workspaceProxyHttpPortInput.value = String(settings.proxy?.http_port || 80);
  }

  if (settingsElements.workspaceProxyHttpsPortInput) {
    settingsElements.workspaceProxyHttpsPortInput.value = String(settings.proxy?.https_port || 443);
  }

  if (settingsElements.workspaceProxyEnabledCheckbox) {
    settingsElements.workspaceProxyEnabledCheckbox.checked = Boolean(settings.proxy?.enabled);
  }

  if (settingsElements.retentionInput) {
    settingsElements.retentionInput.value = String(settings.logging.max_stored_entries);
  }

  if (settingsElements.visibleInput) {
    settingsElements.visibleInput.value = String(settings.logging.max_visible_entries);
  }

  if (settingsElements.detailInput) {
    settingsElements.detailInput.value = String(settings.logging.max_detail_characters);
  }

  if (settingsElements.fileSizeInput) {
    settingsElements.fileSizeInput.value = String(settings.logging.max_file_size_mb);
  }

  if (settingsElements.notificationsChannelSelect) {
    settingsElements.notificationsChannelSelect.value = settings.notifications.channel;
  }

  if (settingsElements.notificationsDigestSelect) {
    settingsElements.notificationsDigestSelect.value = settings.notifications.digest;
  }

  if (settingsElements.dataRedactionCheckbox) {
    settingsElements.dataRedactionCheckbox.checked = settings.data.payload_redaction;
  }

  if (settingsElements.accessSessionSelect) {
    settingsElements.accessSessionSelect.value = String(settings.security.session_timeout_minutes);
  }

  if (settingsElements.accessApprovalCheckbox) {
    settingsElements.accessApprovalCheckbox.checked = Boolean(settings.security.dual_approval_required);
  }

  if (settingsElements.accessTokenSelect) {
    settingsElements.accessTokenSelect.value = String(settings.security.token_rotation_days);
  }

  if (settingsElements.storageMaxMbInput) {
    settingsElements.storageMaxMbInput.value = String(settings.logging.max_file_size_mb);
  }

  document
    .querySelectorAll(".settings-option-card__toggle input[type=\"checkbox\"]")
    .forEach((input) => updateTogglePresentation(input));

  renderSettingsSummary();
};

const logSettingsChange = (action, message, details) => {
  getSettingsStore().log({
    source: "ui.settings",
    category: "configuration",
    action,
    level: "info",
    message,
    details,
    context: {
      path: window.location.pathname,
      section: currentSettingsSection
    }
  });
};

const saveCurrentSettings = async ({ action = "settings_saved", message = "Updated workspace settings." } = {}) => {
  const settings = await getSettingsStore().updateAppSettings(buildSettingsPayload());
  applySettingsToPage(settings);
  setSettingsFeedback("Settings saved to the database.", "success");
  logSettingsChange(action, message, {
    section: currentSettingsSection
  });
};

const bindSettingsEvents = () => {
  settingsElements.form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await saveCurrentSettings();
    } catch {
      setSettingsFeedback("Unable to save settings.", "danger");
    }
  });

  if (currentSettingsSection === "workspace") {
    settingsElements.workspaceProxyEnabledToggle?.addEventListener("click", async () => {
      // Let the checkbox state update first, then persist the section patch.
      await Promise.resolve();
      try {
        await saveCurrentSettings({
          action: "settings_saved_auto_toggle",
          message: "Updated workspace proxy toggle setting."
        });
      } catch {
        setSettingsFeedback("Unable to save settings.", "danger");
      }
    });

    settingsElements.workspaceProxyTestButton?.addEventListener("click", async () => {
      await testWorkspaceProxyConnection();
    });
  }

  settingsElements.resetButton?.addEventListener("click", async () => {
    try {
      const settings = await getSettingsStore().resetAppSettings();
      applySettingsToPage(settings);
      setSettingsFeedback("Default settings restored from the database.", "success");
      logSettingsChange("settings_reset", "Restored default workspace settings.", {
        section: currentSettingsSection
      });
    } catch {
      setSettingsFeedback("Unable to reset settings.", "danger");
    }
  });

  settingsElements.clearButton?.addEventListener("click", () => {
    const store = getSettingsStore();
    store.clearLogs();
    store.log({
      source: "ui.settings",
      category: "maintenance",
      action: "logs_cleared",
      level: "warning",
      message: "Stored runtime logs cleared from browser storage.",
      details: {
        clearedAt: new Date().toISOString()
      },
      context: {
        path: window.location.pathname,
        section: currentSettingsSection
      }
    });
    renderSettingsSummary();
    setSettingsFeedback("Stored logs cleared.", "success");
  });

  window.addEventListener("malcom:logs-updated", renderSettingsSummary);
  window.addEventListener("malcom:app-settings-updated", (event) => {
    if (event.detail?.settings) {
      applySettingsToPage(event.detail.settings);
    }
  });
};

const initSettingsPage = async () => {
  const hasSettingsControls = Object.values(settingsElements).some(Boolean);

  if (!hasSettingsControls) {
    return;
  }

  initSettingsToggles();
  renderSettingsSummary();
  bindSettingsEvents();

  try {
    const settings = await getSettingsStore().ready();
    applySettingsToPage(settings);
  } catch {
    applySettingsToPage(getSettingsStore().getAppSettings());
    setSettingsFeedback("Using fallback settings because the database is unavailable.", "warning");
  }
};

initSettingsPage();
