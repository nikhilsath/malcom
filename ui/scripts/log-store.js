const malcomLogStorageKeys = {
  entries: "malcom.runtimeLogs"
};

const malcomDefaultAppSettings = {
  general: {
    environment: "live",
    timezone: "local"
  },
  logging: {
    max_stored_entries: 250,
    max_visible_entries: 50,
    max_detail_characters: 4000,
    max_file_size_mb: 5
  },
  notifications: {
    channel: "email",
    digest: "hourly"
  },
  data: {
    payload_redaction: true,
    export_window_utc: "02:00"
  },
  automation: {
    default_tool_retries: 2
  },
  connectors: {
    catalog: [],
    records: [],
    auth_policy: {
      rotation_interval_days: 90,
      reconnect_requires_approval: true,
      credential_visibility: "masked"
    }
  }
};

const malcomAllowedLevels = new Set(["debug", "info", "warning", "error"]);

const cloneJsonValue = (value) => {
  if (value === undefined) {
    return undefined;
  }

  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return String(value);
  }
};

const clampInteger = (value, minimum, maximum, fallback) => {
  const parsed = Number.parseInt(value, 10);

  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.min(maximum, Math.max(minimum, parsed));
};

const readStoredJson = (storageKey, fallbackValue) => {
  try {
    const rawValue = localStorage.getItem(storageKey);

    if (!rawValue) {
      return fallbackValue;
    }

    return JSON.parse(rawValue);
  } catch {
    return fallbackValue;
  }
};

const writeStoredJson = (storageKey, value) => {
  localStorage.setItem(storageKey, JSON.stringify(value));
};

const mergeJsonValue = (base, override) => {
  if (Array.isArray(base) || Array.isArray(override)) {
    return override ?? base;
  }

  if (base && override && typeof base === "object" && typeof override === "object") {
    const mergedEntries = new Map();

    for (const [key, value] of Object.entries(base)) {
      mergedEntries.set(key, value);
    }

    for (const [key, value] of Object.entries(override)) {
      mergedEntries.set(key, mergeJsonValue(mergedEntries.get(key), value));
    }

    return Object.fromEntries(mergedEntries);
  }

  return override ?? base;
};

const createDefaultAppSettings = () => cloneJsonValue(malcomDefaultAppSettings);

const sanitizeLoggingSettings = (loggingSettings = {}) => ({
  max_stored_entries: clampInteger(
    loggingSettings.max_stored_entries,
    50,
    5000,
    malcomDefaultAppSettings.logging.max_stored_entries
  ),
  max_visible_entries: clampInteger(
    loggingSettings.max_visible_entries,
    10,
    500,
    malcomDefaultAppSettings.logging.max_visible_entries
  ),
  max_detail_characters: clampInteger(
    loggingSettings.max_detail_characters,
    500,
    20000,
    malcomDefaultAppSettings.logging.max_detail_characters
  ),
  max_file_size_mb: clampInteger(
    loggingSettings.max_file_size_mb,
    1,
    100,
    malcomDefaultAppSettings.logging.max_file_size_mb
  )
});

let cachedAppSettings = createDefaultAppSettings();
let pendingSettingsRequest = null;
let hasLoadedAppSettings = false;

const normalizeAppSettings = (settings = {}) => ({
  general: {
    ...malcomDefaultAppSettings.general,
    ...(settings.general || {}),
    environment: "live"
  },
  logging: sanitizeLoggingSettings(settings.logging),
  notifications: {
    ...malcomDefaultAppSettings.notifications,
    ...(settings.notifications || {})
  },
  security: {
    ...malcomDefaultAppSettings.security,
    ...(settings.security || {})
  },
  data: {
    ...malcomDefaultAppSettings.data,
    ...(settings.data || {})
  },
  automation: {
    ...malcomDefaultAppSettings.automation,
    ...(settings.automation || {})
  },
  connectors: {
    ...cloneJsonValue(malcomDefaultAppSettings.connectors),
    ...(settings.connectors || {}),
    catalog: Array.isArray(settings.connectors?.catalog) ? settings.connectors.catalog : [],
    records: Array.isArray(settings.connectors?.records) ? settings.connectors.records : [],
    auth_policy: {
      ...malcomDefaultAppSettings.connectors.auth_policy,
      ...(settings.connectors?.auth_policy || {})
    }
  }
});

const dispatchLogEvent = (eventName, detail) => {
  window.dispatchEvent(new CustomEvent(eventName, { detail }));
};

const emitSettingsUpdated = () => {
  dispatchLogEvent("malcom:app-settings-updated", { settings: cloneJsonValue(cachedAppSettings) });
  dispatchLogEvent("malcom:log-settings-updated", {
    settings: getLogSettings()
  });
};

const loadAppSettings = async ({ force = false } = {}) => {
  if (pendingSettingsRequest && !force) {
    return pendingSettingsRequest;
  }

  pendingSettingsRequest = window.Malcom?.requestJson?.("/api/v1/settings")
    .then((settings) => {
      cachedAppSettings = normalizeAppSettings(settings);
      hasLoadedAppSettings = true;
      emitSettingsUpdated();
      return cloneJsonValue(cachedAppSettings);
    })
    .catch((error) => {
      pendingSettingsRequest = null;
      throw error;
    })
    .finally(() => {
      pendingSettingsRequest = null;
    });

  return pendingSettingsRequest;
};

const updateAppSettings = async (settings) => {
  let baseSettings = getAppSettings();

  if (!hasLoadedAppSettings) {
    try {
      baseSettings = await loadAppSettings();
    } catch {
      baseSettings = getAppSettings();
    }
  }

  const nextSettings = normalizeAppSettings(mergeJsonValue(baseSettings, settings));
  const response = await window.Malcom?.requestJson?.("/api/v1/settings", {
    method: "PATCH",
    body: JSON.stringify(nextSettings)
  });
  cachedAppSettings = normalizeAppSettings(response);
  hasLoadedAppSettings = true;
  emitSettingsUpdated();
  const entries = readLogEntries();
  writeLogEntries(entries);
  return cloneJsonValue(cachedAppSettings);
};

const resetAppSettings = () => updateAppSettings(createDefaultAppSettings());

const getAppSettings = () => cloneJsonValue(cachedAppSettings);

const getLogSettings = () => ({
  maxStoredEntries: cachedAppSettings.logging.max_stored_entries,
  maxVisibleEntries: cachedAppSettings.logging.max_visible_entries,
  maxDetailCharacters: cachedAppSettings.logging.max_detail_characters,
  maxFileSizeMb: cachedAppSettings.logging.max_file_size_mb
});

const readLogEntries = () => {
  const entries = readStoredJson(malcomLogStorageKeys.entries, []);
  return Array.isArray(entries) ? entries : [];
};

const writeLogEntries = (entries) => {
  const settings = getLogSettings();
  const trimmedEntries = entries.slice(0, settings.maxStoredEntries);
  writeStoredJson(malcomLogStorageKeys.entries, trimmedEntries);
  dispatchLogEvent("malcom:logs-updated", { entries: trimmedEntries });
  return trimmedEntries;
};

const createLogId = () => `log_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

const createLogEntry = (entry = {}) => {
  const level = malcomAllowedLevels.has(entry.level) ? entry.level : "info";

  return {
    id: entry.id || createLogId(),
    timestamp: entry.timestamp || new Date().toISOString(),
    level,
    source: entry.source || "ui.shell",
    category: entry.category || "system",
    action: entry.action || "event",
    message: entry.message || "Runtime event recorded.",
    details: cloneJsonValue(entry.details ?? {}),
    context: cloneJsonValue(entry.context ?? {})
  };
};

const appendLogEntry = (entry) => {
  const entries = readLogEntries();
  const nextEntries = [createLogEntry(entry), ...entries];
  const storedEntries = writeLogEntries(nextEntries);
  return storedEntries[0];
};

const seedLogEntries = () => {
  const existingEntries = readLogEntries();

  if (existingEntries.length > 0) {
    return;
  }

  const seededEntries = [
    createLogEntry({
      timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      source: "system.bootstrap",
      category: "runtime",
      action: "startup",
      message: "Client-side runtime logging initialized.",
      details: {
        storage: "localStorage",
        filters: ["level", "source", "category", "time", "search"]
      },
      context: {
        environment: "browser"
      }
    }),
    createLogEntry({
      timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      source: "system.settings",
      category: "configuration",
      action: "defaults_loaded",
      message: "Default settings loaded.",
      details: getLogSettings(),
      context: {
        boot: true
      }
    })
  ];

  writeStoredJson(malcomLogStorageKeys.entries, seededEntries);
};

seedLogEntries();
loadAppSettings().catch(() => {
  dispatchLogEvent("malcom:log-settings-updated", { settings: getLogSettings() });
});

window.MalcomLogStore = {
  defaults: {
    maxStoredEntries: malcomDefaultAppSettings.logging.max_stored_entries,
    maxVisibleEntries: malcomDefaultAppSettings.logging.max_visible_entries,
    maxDetailCharacters: malcomDefaultAppSettings.logging.max_detail_characters,
    maxFileSizeMb: malcomDefaultAppSettings.logging.max_file_size_mb
  },
  ready: () => loadAppSettings(),
  getAppSettings() {
    return getAppSettings();
  },
  updateAppSettings(settings) {
    return updateAppSettings(settings);
  },
  resetAppSettings() {
    return resetAppSettings();
  },
  getSettings() {
    return getLogSettings();
  },
  updateSettings(settings) {
    return updateAppSettings({
      ...getAppSettings(),
      logging: {
        max_stored_entries: settings.maxStoredEntries,
        max_visible_entries: settings.maxVisibleEntries,
        max_detail_characters: settings.maxDetailCharacters,
        max_file_size_mb: settings.maxFileSizeMb
      }
    }).then((nextSettings) => ({
      maxStoredEntries: nextSettings.logging.max_stored_entries,
      maxVisibleEntries: nextSettings.logging.max_visible_entries,
      maxDetailCharacters: nextSettings.logging.max_detail_characters,
      maxFileSizeMb: nextSettings.logging.max_file_size_mb
    }));
  },
  resetSettings() {
    return resetAppSettings().then((nextSettings) => ({
      maxStoredEntries: nextSettings.logging.max_stored_entries,
      maxVisibleEntries: nextSettings.logging.max_visible_entries,
      maxDetailCharacters: nextSettings.logging.max_detail_characters,
      maxFileSizeMb: nextSettings.logging.max_file_size_mb
    }));
  },
  getLogs() {
    return readLogEntries();
  },
  log(entry) {
    return appendLogEntry(entry);
  },
  clearLogs() {
    writeLogEntries([]);
  }
};
