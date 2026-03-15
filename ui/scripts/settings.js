const settingsElements = {
  form: document.getElementById("settings-form"),
  feedback: document.getElementById("settings-feedback"),
  resetButton: document.getElementById("settings-reset-button"),
  clearButton: document.getElementById("settings-clear-logs-button"),
  totalLogsValue: document.getElementById("settings-log-total-value"),
  newestLogValue: document.getElementById("settings-log-newest-value"),
  generalEnvironmentSelect: document.getElementById("settings-general-environment-select"),
  generalTimezoneSelect: document.getElementById("settings-general-timezone-select"),
  generalPreviewCheckbox: document.getElementById("settings-general-preview-checkbox"),
  retentionInput: document.getElementById("settings-log-retention-input"),
  visibleInput: document.getElementById("settings-log-visible-input"),
  detailInput: document.getElementById("settings-log-detail-input"),
  fileSizeInput: document.getElementById("settings-log-file-size-input"),
  notificationsChannelSelect: document.getElementById("settings-notifications-channel-select"),
  notificationsDigestSelect: document.getElementById("settings-notifications-digest-select"),
  notificationsOncallCheckbox: document.getElementById("settings-notifications-oncall-checkbox"),
  securitySessionSelect: document.getElementById("settings-security-session-select"),
  securityApprovalCheckbox: document.getElementById("settings-security-approval-checkbox"),
  securityTokenSelect: document.getElementById("settings-security-token-select"),
  dataRedactionCheckbox: document.getElementById("settings-data-redaction-checkbox"),
  dataExportSelect: document.getElementById("settings-data-export-select"),
  dataAuditSelect: document.getElementById("settings-data-audit-select")
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

const setSettingsFeedback = (message, tone) => {
  if (!settingsElements.feedback) {
    return;
  }

  settingsElements.feedback.textContent = message;
  settingsElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
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
  if (section === "general") {
    return {
      general: {
        environment: settingsElements.generalEnvironmentSelect?.value || fallbackSettings.general.environment,
        timezone: settingsElements.generalTimezoneSelect?.value || fallbackSettings.general.timezone,
        preview_mode: settingsElements.generalPreviewCheckbox?.checked ?? fallbackSettings.general.preview_mode
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
        digest: settingsElements.notificationsDigestSelect?.value || fallbackSettings.notifications.digest,
        escalate_oncall: settingsElements.notificationsOncallCheckbox?.checked ?? fallbackSettings.notifications.escalate_oncall
      }
    };
  }

  if (section === "security") {
    return {
      security: {
        session_timeout_minutes: Number.parseInt(settingsElements.securitySessionSelect?.value || "", 10),
        dual_approval_required: settingsElements.securityApprovalCheckbox?.checked ?? fallbackSettings.security.dual_approval_required,
        token_rotation_days: Number.parseInt(settingsElements.securityTokenSelect?.value || "", 10)
      }
    };
  }

  if (section === "data") {
    return {
      data: {
        payload_redaction: settingsElements.dataRedactionCheckbox?.checked ?? fallbackSettings.data.payload_redaction,
        export_window_utc: settingsElements.dataExportSelect?.value || fallbackSettings.data.export_window_utc,
        audit_retention_days: Number.parseInt(settingsElements.dataAuditSelect?.value || "", 10)
      }
    };
  }

  return {};
};

const buildSettingsPayload = () => {
  const currentSettings = getSettingsStore().getAppSettings();

  return {
    ...currentSettings,
    ...buildSectionPatch(currentSettingsSection, currentSettings)
  };
};

const applySettingsToPage = (settings) => {
  if (settingsElements.generalEnvironmentSelect) {
    settingsElements.generalEnvironmentSelect.value = settings.general.environment;
  }

  if (settingsElements.generalTimezoneSelect) {
    settingsElements.generalTimezoneSelect.value = settings.general.timezone;
  }

  if (settingsElements.generalPreviewCheckbox) {
    settingsElements.generalPreviewCheckbox.checked = settings.general.preview_mode;
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

  if (settingsElements.notificationsOncallCheckbox) {
    settingsElements.notificationsOncallCheckbox.checked = settings.notifications.escalate_oncall;
  }

  if (settingsElements.securitySessionSelect) {
    settingsElements.securitySessionSelect.value = String(settings.security.session_timeout_minutes);
  }

  if (settingsElements.securityApprovalCheckbox) {
    settingsElements.securityApprovalCheckbox.checked = settings.security.dual_approval_required;
  }

  if (settingsElements.securityTokenSelect) {
    settingsElements.securityTokenSelect.value = String(settings.security.token_rotation_days);
  }

  if (settingsElements.dataRedactionCheckbox) {
    settingsElements.dataRedactionCheckbox.checked = settings.data.payload_redaction;
  }

  if (settingsElements.dataExportSelect) {
    settingsElements.dataExportSelect.value = settings.data.export_window_utc;
  }

  if (settingsElements.dataAuditSelect) {
    settingsElements.dataAuditSelect.value = String(settings.data.audit_retention_days);
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

const bindSettingsEvents = () => {
  settingsElements.form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const settings = await getSettingsStore().updateAppSettings(buildSettingsPayload());
      applySettingsToPage(settings);
      setSettingsFeedback("Settings saved to the database.", "success");
      logSettingsChange("settings_saved", "Updated workspace settings.", {
        section: currentSettingsSection
      });
    } catch {
      setSettingsFeedback("Unable to save settings.", "danger");
    }
  });

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
