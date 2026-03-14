const dashboardLogElements = {
  totalCount: document.getElementById("dashboard-logs-total-value"),
  filteredCount: document.getElementById("dashboard-logs-filtered-value"),
  latestValue: document.getElementById("dashboard-logs-latest-value"),
  retentionValue: document.getElementById("dashboard-logs-retention-value"),
  searchInput: document.getElementById("dashboard-logs-search-input"),
  levelSelect: document.getElementById("dashboard-logs-level-select"),
  sourceSelect: document.getElementById("dashboard-logs-source-select"),
  categorySelect: document.getElementById("dashboard-logs-category-select"),
  timeSelect: document.getElementById("dashboard-logs-time-select"),
  resetButton: document.getElementById("dashboard-logs-reset-button"),
  clearButton: document.getElementById("dashboard-logs-clear-button"),
  feedback: document.getElementById("dashboard-logs-feedback"),
  emptyState: document.getElementById("dashboard-logs-empty"),
  resultCount: document.getElementById("dashboard-logs-results-count"),
  list: document.getElementById("dashboard-logs-list")
};

const formatDashboardDateTime = (value) => {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

const escapeDashboardHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const stringifyDashboardValue = (value, maxCharacters) => {
  const rawValue = JSON.stringify(value ?? {}, null, 2);

  if (rawValue.length <= maxCharacters) {
    return rawValue;
  }

  return `${rawValue.slice(0, maxCharacters)}\n… truncated`;
};

const getDashboardLogStore = () => window.MalcomLogStore;

const setDashboardFeedback = (message, tone) => {
  dashboardLogElements.feedback.textContent = message;
  dashboardLogElements.feedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const readDashboardFilters = () => ({
  query: dashboardLogElements.searchInput.value.trim().toLowerCase(),
  level: dashboardLogElements.levelSelect.value,
  source: dashboardLogElements.sourceSelect.value,
  category: dashboardLogElements.categorySelect.value,
  timeframe: dashboardLogElements.timeSelect.value
});

const withinDashboardTimeframe = (timestamp, timeframe) => {
  if (timeframe === "all") {
    return true;
  }

  const createdAt = new Date(timestamp).getTime();

  if (!Number.isFinite(createdAt)) {
    return false;
  }

  const now = Date.now();
  const timeframeHours = {
    "1h": 1,
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30
  };
  const hourWindow = timeframeHours[timeframe];

  if (!hourWindow) {
    return true;
  }

  return createdAt >= now - hourWindow * 60 * 60 * 1000;
};

const populateDashboardSelect = (selectElement, values, labelPrefix) => {
  const currentValue = selectElement.value;
  const options = ['<option value="all">All</option>'];

  values.forEach((value) => {
    options.push(`<option value="${escapeDashboardHtml(value)}">${escapeDashboardHtml(value)}</option>`);
  });

  selectElement.innerHTML = options.join("");
  selectElement.setAttribute("aria-label", labelPrefix);

  if (values.includes(currentValue)) {
    selectElement.value = currentValue;
    return;
  }

  selectElement.value = "all";
};

const syncDashboardFilterOptions = (logs) => {
  const sources = [...new Set(logs.map((log) => log.source).filter(Boolean))].sort();
  const categories = [...new Set(logs.map((log) => log.category).filter(Boolean))].sort();

  populateDashboardSelect(dashboardLogElements.sourceSelect, sources, "Filter logs by source");
  populateDashboardSelect(dashboardLogElements.categorySelect, categories, "Filter logs by category");
};

const filterDashboardLogs = (logs, filters) => logs.filter((logEntry) => {
  if (filters.level !== "all" && logEntry.level !== filters.level) {
    return false;
  }

  if (filters.source !== "all" && logEntry.source !== filters.source) {
    return false;
  }

  if (filters.category !== "all" && logEntry.category !== filters.category) {
    return false;
  }

  if (!withinDashboardTimeframe(logEntry.timestamp, filters.timeframe)) {
    return false;
  }

  if (!filters.query) {
    return true;
  }

  const searchableValue = JSON.stringify(logEntry).toLowerCase();
  return searchableValue.includes(filters.query);
});

const renderDashboardLogs = () => {
  const store = getDashboardLogStore();

  if (!store) {
    return;
  }

  const settings = store.getSettings();
  const logs = store.getLogs();
  syncDashboardFilterOptions(logs);
  const filters = readDashboardFilters();
  const filteredLogs = filterDashboardLogs(logs, filters);
  const visibleLogs = filteredLogs.slice(0, settings.maxVisibleEntries);

  dashboardLogElements.totalCount.textContent = String(logs.length);
  dashboardLogElements.filteredCount.textContent = String(filteredLogs.length);
  dashboardLogElements.latestValue.textContent = logs[0]
    ? formatDashboardDateTime(logs[0].timestamp)
    : "No logs yet";
  dashboardLogElements.retentionValue.textContent = `${settings.maxStoredEntries} stored / ${settings.maxVisibleEntries} shown`;
  dashboardLogElements.resultCount.textContent = `${filteredLogs.length} matching logs`;
  dashboardLogElements.clearButton.disabled = logs.length === 0;
  dashboardLogElements.emptyState.hidden = visibleLogs.length > 0;
  dashboardLogElements.list.textContent = "";

  if (visibleLogs.length === 0) {
    return;
  }

  const fragment = document.createDocumentFragment();

  visibleLogs.forEach((logEntry) => {
    const article = document.createElement("article");
    article.id = `dashboard-log-item-${logEntry.id}`;
    article.className = "dashboard-log-item";

    article.innerHTML = `
      <div id="dashboard-log-header-${logEntry.id}" class="dashboard-log-item__header">
        <div id="dashboard-log-header-copy-${logEntry.id}" class="dashboard-log-item__header-copy">
          <p id="dashboard-log-meta-${logEntry.id}" class="dashboard-log-item__meta">
            ${escapeDashboardHtml(formatDashboardDateTime(logEntry.timestamp))} • ${escapeDashboardHtml(logEntry.source)} • ${escapeDashboardHtml(logEntry.action)}
          </p>
          <h4 id="dashboard-log-title-${logEntry.id}" class="dashboard-log-item__title">${escapeDashboardHtml(logEntry.message)}</h4>
        </div>
        <div id="dashboard-log-badges-${logEntry.id}" class="dashboard-log-item__badges">
          <span id="dashboard-log-level-${logEntry.id}" class="status-badge ${logEntry.level === "error" ? "status-badge--danger" : logEntry.level === "warning" ? "status-badge--warning" : logEntry.level === "debug" ? "status-badge--muted" : "status-badge--success"}">${escapeDashboardHtml(logEntry.level)}</span>
          <span id="dashboard-log-category-${logEntry.id}" class="status-badge status-badge--muted">${escapeDashboardHtml(logEntry.category)}</span>
        </div>
      </div>
      <div id="dashboard-log-grid-${logEntry.id}" class="dashboard-log-item__grid">
        <section id="dashboard-log-context-panel-${logEntry.id}" class="dashboard-log-item__panel">
          <p id="dashboard-log-context-label-${logEntry.id}" class="dashboard-log-item__label">Context</p>
          <pre id="dashboard-log-context-value-${logEntry.id}" class="api-code-block">${escapeDashboardHtml(stringifyDashboardValue(logEntry.context, settings.maxDetailCharacters))}</pre>
        </section>
        <section id="dashboard-log-details-panel-${logEntry.id}" class="dashboard-log-item__panel">
          <p id="dashboard-log-details-label-${logEntry.id}" class="dashboard-log-item__label">Details</p>
          <pre id="dashboard-log-details-value-${logEntry.id}" class="api-code-block">${escapeDashboardHtml(stringifyDashboardValue(logEntry.details, settings.maxDetailCharacters))}</pre>
        </section>
      </div>
    `;

    fragment.appendChild(article);
  });

  dashboardLogElements.list.appendChild(fragment);
};

const resetDashboardFilters = () => {
  dashboardLogElements.searchInput.value = "";
  dashboardLogElements.levelSelect.value = "all";
  dashboardLogElements.sourceSelect.value = "all";
  dashboardLogElements.categorySelect.value = "all";
  dashboardLogElements.timeSelect.value = "all";
  setDashboardFeedback("", "");
  renderDashboardLogs();
};

const clearDashboardLogs = () => {
  const store = getDashboardLogStore();

  if (!store) {
    return;
  }

  if (store.getLogs().length === 0) {
    setDashboardFeedback("No stored logs to clear.", "");
    renderDashboardLogs();
    return;
  }

  store.clearLogs();
  setDashboardFeedback("Stored logs cleared.", "success");
};

const bindDashboardLogEvents = () => {
  [
    dashboardLogElements.searchInput,
    dashboardLogElements.levelSelect,
    dashboardLogElements.sourceSelect,
    dashboardLogElements.categorySelect,
    dashboardLogElements.timeSelect
  ].forEach((element) => {
    element.addEventListener("input", renderDashboardLogs);
    element.addEventListener("change", renderDashboardLogs);
  });

  dashboardLogElements.resetButton.addEventListener("click", resetDashboardFilters);
  dashboardLogElements.clearButton.addEventListener("click", clearDashboardLogs);
  window.addEventListener("malcom:logs-updated", renderDashboardLogs);
  window.addEventListener("malcom:log-settings-updated", renderDashboardLogs);
};

const initDashboardLogsPage = () => {
  if (!dashboardLogElements.list) {
    return;
  }

  bindDashboardLogEvents();
  renderDashboardLogs();
};

initDashboardLogsPage();
