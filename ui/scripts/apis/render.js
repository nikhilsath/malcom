import {
  hasOutgoingRegistryElements,
  hasOverviewElements,
  hasOverviewLandingElements,
  hasWebhookRegistryElements
} from "./dom.js";
import {
  buildEndpointUrl,
  buildEventSearchValue,
  buildSampleCurl,
  classifyEventSource,
  deriveEventLabel,
  escapeHtml,
  formatBytes,
  formatDateTime,
  formatIntervalMinutes,
  formatOutgoingSendTime,
  formatRate,
  formatRelativeActivity,
  getEntryLastActivity,
  getEntryPrimaryLocation,
  getEntryStatusLabel,
  getEntryStatusTone,
  getOutgoingRegistryStatusLabel,
  getOutgoingRegistryStatusTone,
  getScheduledStatus,
  sortEventsByStatus,
  stringifyPreviewValue,
  titleCase,
  truncatePreview
} from "./utils.js";

export const createApiRenderer = ({ elements, state, actions }) => {
  const setAlert = (message, tone = "info") => {
    if (!elements.alert) {
      return;
    }

    if (!message) {
      elements.alert.hidden = true;
      elements.alert.textContent = "";
      elements.alert.className = "api-system-alert";
      return;
    }

    elements.alert.hidden = false;
    elements.alert.textContent = message;
    elements.alert.className = `api-system-alert api-system-alert--${tone}`;
  };

  const setAutomationAlert = (message, tone = "info") => {
    if (!elements.automationAlert) {
      return;
    }

    if (!message) {
      elements.automationAlert.hidden = true;
      elements.automationAlert.textContent = "";
      elements.automationAlert.className = "api-system-alert";
      return;
    }

    elements.automationAlert.hidden = false;
    elements.automationAlert.textContent = message;
    elements.automationAlert.className = `api-system-alert api-system-alert--${tone}`;
  };

  const renderTable = () => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    elements.tableBody.textContent = "";
    const hasEntries = state.entries.length > 0;

    elements.directoryEmpty.hidden = hasEntries;
    elements.tableShell.hidden = !hasEntries;

    if (!hasEntries) {
      return;
    }

    const fragment = document.createDocumentFragment();

    state.entries.forEach((entry) => {
      const row = document.createElement("tr");
      row.id = `api-directory-row-${entry.id}`;
      row.className = "api-directory-row";
      row.tabIndex = 0;
      row.dataset.apiId = entry.id;
      row.setAttribute("role", "button");
      row.setAttribute("aria-pressed", String(state.selectedApiId === entry.id));

      if (state.selectedApiId === entry.id) {
        row.classList.add("api-directory-row--selected");
      }

      row.innerHTML = `
        <td id="api-directory-name-${entry.id}" class="api-directory-cell api-directory-cell--name">
          <span id="api-directory-name-value-${entry.id}" class="api-directory-name">${escapeHtml(entry.name)}</span>
          <span id="api-directory-description-value-${entry.id}" class="api-directory-description">${escapeHtml(entry.description || "No description provided.")}</span>
        </td>
        <td id="api-directory-status-${entry.id}" class="api-directory-cell">
          <span id="api-directory-status-badge-${entry.id}" class="status-badge ${entry.enabled ? "status-badge--success" : "status-badge--muted"}">${entry.enabled ? "Enabled" : "Disabled"}</span>
        </td>
        <td id="api-directory-path-${entry.id}" class="api-directory-cell api-directory-cell--path">${escapeHtml(entry.endpoint_path || `/api/v1/inbound/${entry.id}`)}</td>
        <td id="api-directory-received-${entry.id}" class="api-directory-cell">${escapeHtml(formatDateTime(entry.last_received_at))}</td>
        <td id="api-directory-result-${entry.id}" class="api-directory-cell">${escapeHtml(entry.last_delivery_status || "No deliveries")}</td>
      `;

      row.addEventListener("click", () => {
        state.detailReturnFocusElement = row;
        actions.loadApiDetail(entry.id);
      });

      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          state.detailReturnFocusElement = row;
          actions.loadApiDetail(entry.id);
        }
      });

      fragment.appendChild(row);
    });

    elements.tableBody.appendChild(fragment);
  };

  const renderMetadata = (entry) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    const metadataRows = [
      { label: "Endpoint URL", value: entry.endpoint_url || buildEndpointUrl(entry.id) },
      { label: "Endpoint path", value: entry.endpoint_path || `/api/v1/inbound/${entry.id}` },
      { label: "Authentication", value: "Bearer secret" },
      { label: "Status", value: entry.enabled ? "Enabled" : "Disabled" },
      { label: "Created", value: formatDateTime(entry.created_at) },
      { label: "Updated", value: formatDateTime(entry.updated_at) },
      { label: "Last received", value: formatDateTime(entry.last_received_at) }
    ];

    elements.detailMetadata.innerHTML = metadataRows.map((item, index) => `
      <div id="api-detail-metadata-row-${index}" class="api-detail-metadata-row">
        <dt id="api-detail-metadata-label-${index}" class="api-detail-metadata-label">${escapeHtml(item.label)}</dt>
        <dd id="api-detail-metadata-value-${index}" class="api-detail-metadata-value">${escapeHtml(item.value)}</dd>
      </div>
    `).join("");
  };

  const renderSecretPanel = (entry) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    const latestSecret = state.lastSecretByApiId[entry.id];

    if (!latestSecret) {
      elements.secretPanel.hidden = true;
      elements.secretValue.textContent = "";
      elements.secretCurl.textContent = "";
      return;
    }

    elements.secretPanel.hidden = false;
    elements.secretValue.textContent = latestSecret;
    elements.secretCurl.textContent = buildSampleCurl(entry.id, latestSecret);
  };

  const renderLogSummary = (events) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    const acceptedCount = events.filter((eventItem) => eventItem.status === "accepted").length;
    const needsAttentionCount = events.filter((eventItem) => eventItem.status !== "accepted").length;

    elements.logsSummaryTotalValue.textContent = String(events.length);
    elements.logsSummaryAcceptedValue.textContent = String(acceptedCount);
    elements.logsSummaryErrorsValue.textContent = String(needsAttentionCount);
  };

  const getFilteredEvents = (events) => {
    const filters = state.detailLogFilters;
    const searchTerm = filters.search.trim().toLowerCase();

    const filteredEvents = events.filter((eventItem) => {
      if (filters.status !== "all" && eventItem.status !== filters.status) {
        return false;
      }

      if (filters.source !== "all" && classifyEventSource(eventItem) !== filters.source) {
        return false;
      }

      if (searchTerm && !buildEventSearchValue(eventItem).includes(searchTerm)) {
        return false;
      }

      return true;
    });

    if (filters.sort === "oldest") {
      return filteredEvents.sort((left, right) => new Date(left.received_at || 0) - new Date(right.received_at || 0));
    }

    if (filters.sort === "status") {
      return filteredEvents.sort(sortEventsByStatus);
    }

    return filteredEvents.sort((left, right) => new Date(right.received_at || 0) - new Date(left.received_at || 0));
  };

  const renderLogs = (events) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    elements.logList.textContent = "";
    const filteredEvents = getFilteredEvents(events);
    renderLogSummary(filteredEvents);
    elements.logsEmpty.hidden = filteredEvents.length > 0;

    const logsEmptyTitle = document.getElementById("api-logs-empty-title");
    const logsEmptyDescription = document.getElementById("api-logs-empty-description");

    if (logsEmptyTitle && logsEmptyDescription) {
      if (events.length > 0 && filteredEvents.length === 0) {
        logsEmptyTitle.textContent = "No logs match the current filters";
        logsEmptyDescription.textContent = "Clear the current search or filters to see the full event history for this endpoint.";
      } else {
        logsEmptyTitle.textContent = "No requests received yet";
        logsEmptyDescription.textContent = "Send a JSON payload to this endpoint to populate the delivery log.";
      }
    }

    if (filteredEvents.length === 0) {
      return;
    }

    const fragment = document.createDocumentFragment();

    filteredEvents.forEach((eventItem) => {
      const card = document.createElement("article");
      card.id = `api-log-card-${eventItem.event_id}`;
      card.className = "api-log-card";
      const payloadPreview = truncatePreview(eventItem.payload_json);
      const headersPreview = truncatePreview(eventItem.request_headers_subset);
      const headerCount = Object.keys(eventItem.request_headers_subset || {}).length;
      const payloadBytes = stringifyPreviewValue(eventItem.payload_json).length;
      const sourceClass = classifyEventSource(eventItem);
      const eventLabel = deriveEventLabel(eventItem);
      const statusTone = eventItem.status === "accepted" ? "status-badge--success" : "status-badge--warning";

      card.innerHTML = `
        <div id="api-log-header-${eventItem.event_id}" class="api-log-card__header">
          <div id="api-log-header-copy-${eventItem.event_id}" class="api-log-card__header-copy">
            <h5 id="api-log-title-${eventItem.event_id}" class="api-log-card__title">${escapeHtml(eventLabel)}</h5>
            <p id="api-log-meta-${eventItem.event_id}" class="api-log-card__meta">${escapeHtml(formatDateTime(eventItem.received_at))} • ${escapeHtml(eventItem.source_ip || "Unknown source")}</p>
            <div id="api-log-summary-${eventItem.event_id}" class="api-log-card__summary">
              <span id="api-log-summary-id-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(eventItem.event_id)}</span>
              <span id="api-log-summary-source-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(titleCase(sourceClass))} source</span>
              <span id="api-log-summary-headers-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(`${headerCount} headers`)}</span>
              <span id="api-log-summary-bytes-${eventItem.event_id}" class="api-log-card__metric">${escapeHtml(formatBytes(payloadBytes))}</span>
            </div>
          </div>
          <div id="api-log-actions-${eventItem.event_id}" class="api-log-card__actions">
            <span id="api-log-status-${eventItem.event_id}" class="status-badge ${statusTone}">${escapeHtml(eventItem.status)}</span>
            <button type="button" id="api-log-copy-payload-${eventItem.event_id}" class="button button--secondary secondary-action-button" data-copy-log="payload" data-event-id="${escapeHtml(eventItem.event_id)}">Copy payload</button>
            <button type="button" id="api-log-copy-headers-${eventItem.event_id}" class="button button--secondary secondary-action-button" data-copy-log="headers" data-event-id="${escapeHtml(eventItem.event_id)}">Copy headers</button>
          </div>
        </div>
        <div id="api-log-grid-${eventItem.event_id}" class="api-log-card__grid">
          <div id="api-log-headers-panel-${eventItem.event_id}" class="api-log-card__panel">
            <p id="api-log-headers-label-${eventItem.event_id}" class="api-log-card__label">Headers</p>
            <pre id="api-log-headers-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(headersPreview.preview)}</pre>
            <p id="api-log-headers-helper-${eventItem.event_id}" class="api-log-card__helper" ${headersPreview.truncated ? "" : "hidden"}>Header preview trimmed to match current logging detail settings.</p>
          </div>
          <div id="api-log-payload-panel-${eventItem.event_id}" class="api-log-card__panel">
            <p id="api-log-payload-label-${eventItem.event_id}" class="api-log-card__label">Payload</p>
            <pre id="api-log-payload-value-${eventItem.event_id}" class="api-code-block">${escapeHtml(payloadPreview.preview)}</pre>
            <p id="api-log-payload-helper-${eventItem.event_id}" class="api-log-card__helper" ${payloadPreview.truncated ? "" : "hidden"}>Payload preview trimmed to match current logging detail settings.</p>
          </div>
        </div>
        <p id="api-log-error-${eventItem.event_id}" class="api-log-card__error" ${eventItem.error_message ? "" : "hidden"}>${escapeHtml(eventItem.error_message || "")}</p>
      `;

      fragment.appendChild(card);
    });

    elements.logList.appendChild(fragment);
  };

  const setDetailState = (isVisible) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    elements.detailEmpty.hidden = isVisible;
    elements.detailContent.hidden = !isVisible;
  };

  const renderDetail = (entry) => {
    if (!hasOverviewElements(elements)) {
      return;
    }

    const statusCopy = document.getElementById("api-directory-status-copy");

    if (!entry) {
      state.detailEvents = [];
      renderLogSummary([]);
      setDetailState(false);
      if (statusCopy) {
        statusCopy.textContent = "Choose a row to open the detail workspace. The selected endpoint stays highlighted in the directory.";
      }
      return;
    }

    setDetailState(true);
    state.detailEvents = Array.isArray(entry.events) ? entry.events : [];
    elements.detailTitle.textContent = entry.name;
    elements.detailDescription.textContent = entry.description || "No description provided.";
    elements.toggleStatusButton.textContent = entry.enabled ? "Disable endpoint" : "Enable endpoint";
    if (statusCopy) {
      statusCopy.textContent = `Inspecting ${entry.name}. The directory highlight tracks the active endpoint while you review logs and metadata.`;
    }
    renderMetadata(entry);
    renderSecretPanel(entry);
    renderLogs(state.detailEvents);
  };

  const renderResourceList = (container, emptyState, entries, sectionIdPrefix) => {
    if (!container || !emptyState) {
      return;
    }

    container.textContent = "";
    emptyState.hidden = entries.length > 0;

    if (entries.length === 0) {
      return;
    }

    const fragment = document.createDocumentFragment();

    entries.forEach((entry) => {
      const metadataItems = [];
      const signalItems = [
        getEntryStatusLabel(entry),
        getEntryPrimaryLocation(entry),
        formatRelativeActivity(getEntryLastActivity(entry))
      ];
      const quickActions = [];

      if (entry.type.startsWith("outgoing")) {
        metadataItems.push(
          { label: "Destination", value: entry.destination_url || "Not configured" },
          { label: "Method", value: entry.http_method || "POST" },
          { label: "Auth", value: titleCase(entry.auth_type || "none") }
        );

        if (entry.type === "outgoing_scheduled") {
          metadataItems.push({ label: "Send time", value: entry.scheduled_time || "Not set" });
          metadataItems.push({ label: "Delivery policy", value: entry.repeat_enabled ? "Repeats daily" : "One-time send, auto-disable after delivery" });
        }

        if (entry.type === "outgoing_continuous") {
          metadataItems.push({
            label: "Delivery policy",
            value: entry.repeat_enabled
              ? `Repeats every ${formatIntervalMinutes(entry.repeat_interval_minutes)}`
              : "One-time send, auto-disable after delivery"
          });
        }

        quickActions.push(
          {
            id: `${sectionIdPrefix}-copy-destination-${entry.id}`,
            label: "Copy destination",
            action: "copy-entry-value",
            value: entry.destination_url || "",
            valueLabel: "Destination URL"
          },
          {
            id: `${sectionIdPrefix}-open-outgoing-${entry.id}`,
            label: "Open outgoing",
            href: actions.resolvePageHref("/ui/apis/outgoing.html")
          }
        );
      } else if (entry.type === "webhook") {
        metadataItems.push(
          { label: "Callback path", value: entry.callback_path || "Not configured" },
          { label: "Signature header", value: entry.signature_header || "Not configured" },
          { label: "Event filter", value: entry.event_filter || "All events" }
        );

        quickActions.push(
          {
            id: `${sectionIdPrefix}-copy-callback-${entry.id}`,
            label: "Copy callback",
            action: "copy-entry-value",
            value: entry.callback_path || "",
            valueLabel: "Callback path"
          },
          {
            id: `${sectionIdPrefix}-open-webhooks-${entry.id}`,
            label: "Open webhooks",
            href: actions.resolvePageHref("/ui/apis/webhooks.html")
          }
        );
      } else {
        metadataItems.push(
          { label: "Endpoint", value: entry.endpoint_path || `/api/v1/inbound/${entry.id}` },
          { label: "Last received", value: formatDateTime(entry.last_received_at) },
          { label: "Recent result", value: entry.last_delivery_status || "No deliveries" }
        );

        quickActions.push(
          {
            id: `${sectionIdPrefix}-copy-endpoint-${entry.id}`,
            label: "Copy endpoint",
            action: "copy-entry-value",
            value: entry.endpoint_url || buildEndpointUrl(entry.id),
            valueLabel: "Endpoint URL"
          },
          {
            id: `${sectionIdPrefix}-open-incoming-${entry.id}`,
            label: "Open incoming",
            href: actions.resolvePageHref("/ui/apis/incoming.html")
          }
        );
      }

      const card = document.createElement("article");
      card.id = `${sectionIdPrefix}-card-${entry.id}`;
      card.className = "resource-card";
      card.innerHTML = `
        <div id="${sectionIdPrefix}-header-${entry.id}" class="resource-card__header">
          <div id="${sectionIdPrefix}-copy-${entry.id}">
            <h4 id="${sectionIdPrefix}-title-${entry.id}" class="resource-card__title">${escapeHtml(entry.name)}</h4>
            <p id="${sectionIdPrefix}-description-${entry.id}" class="resource-card__description">${escapeHtml(entry.description || "No description provided.")}</p>
          </div>
          <span id="${sectionIdPrefix}-status-${entry.id}" class="status-badge ${getEntryStatusTone(entry)}">${escapeHtml(getEntryStatusLabel(entry))}</span>
        </div>
        <div id="${sectionIdPrefix}-signals-${entry.id}" class="resource-card__signal-row">
          ${signalItems.map((item, signalIndex) => `
            <span id="${sectionIdPrefix}-signal-${signalIndex}-${entry.id}" class="resource-card__signal">${escapeHtml(item)}</span>
          `).join("")}
        </div>
        <div id="${sectionIdPrefix}-meta-${entry.id}" class="resource-card__meta">
          ${metadataItems.map((item, metaIndex) => `
            <div id="${sectionIdPrefix}-meta-${metaIndex}-${entry.id}" class="resource-card__meta-item">
              <span id="${sectionIdPrefix}-meta-label-${metaIndex}-${entry.id}" class="resource-card__meta-label">${escapeHtml(item.label)}</span>
              <span id="${sectionIdPrefix}-meta-value-${metaIndex}-${entry.id}" class="resource-card__meta-value">${escapeHtml(item.value)}</span>
            </div>
          `).join("")}
        </div>
        <div id="${sectionIdPrefix}-actions-${entry.id}" class="resource-card__actions">
          ${quickActions.map((action) => action.href
            ? `<a id="${action.id}" class="button button--secondary secondary-action-button resource-card__action resource-card__action-link" href="${escapeHtml(action.href)}">${escapeHtml(action.label)}</a>`
            : `<button type="button" id="${action.id}" class="button button--secondary secondary-action-button resource-card__action" data-resource-action="${escapeHtml(action.action)}" data-resource-value="${escapeHtml(action.value)}" data-resource-label="${escapeHtml(action.valueLabel)}" data-resource-entry-id="${escapeHtml(entry.id)}">${escapeHtml(action.label)}</button>`
          ).join("")}
        </div>
      `;
      fragment.appendChild(card);
    });

    container.appendChild(fragment);
  };

  const renderOutgoingRegistryList = (container, emptyState, entries, sectionIdPrefix) => {
    if (!container || !emptyState) {
      return;
    }

    container.textContent = "";
    emptyState.hidden = entries.length > 0;

    if (entries.length === 0) {
      return;
    }

    const fragment = document.createDocumentFragment();

    entries.forEach((entry) => {
      const row = document.createElement("article");
      row.id = `${sectionIdPrefix}-row-${entry.id}`;
      row.className = "apis-outgoing-list__row";
      row.tabIndex = 0;
      row.dataset.outgoingId = entry.id;
      row.dataset.outgoingType = entry.type;
      row.setAttribute("role", "button");
      row.setAttribute("aria-pressed", String(state.selectedOutgoingApiId === entry.id));
      if (state.selectedOutgoingApiId === entry.id) {
        row.classList.add("apis-outgoing-list__row--selected");
      }
      row.innerHTML = `
        <div id="${sectionIdPrefix}-name-cell-${entry.id}" class="apis-outgoing-list__cell apis-outgoing-list__cell--name">
          <div id="${sectionIdPrefix}-name-stack-${entry.id}" class="apis-outgoing-list__name-stack">
            <span id="${sectionIdPrefix}-name-${entry.id}" class="apis-outgoing-list__name">${escapeHtml(entry.name)}</span>
            <span id="${sectionIdPrefix}-type-${entry.id}" class="apis-outgoing-list__type">${escapeHtml(entry.type === "outgoing_scheduled" ? "Scheduled" : "Continuous")}</span>
          </div>
          <span id="${sectionIdPrefix}-status-${entry.id}" class="status-badge ${getOutgoingRegistryStatusTone(entry)}">${escapeHtml(getOutgoingRegistryStatusLabel(entry))}</span>
        </div>
        <div id="${sectionIdPrefix}-last-fired-cell-${entry.id}" class="apis-outgoing-list__cell">
          <span id="${sectionIdPrefix}-last-fired-label-${entry.id}" class="apis-outgoing-list__label">Last fired</span>
          <span id="${sectionIdPrefix}-last-fired-value-${entry.id}" class="apis-outgoing-list__value">${escapeHtml(formatDateTime(getEntryLastActivity(entry)))}</span>
        </div>
        <div id="${sectionIdPrefix}-send-time-cell-${entry.id}" class="apis-outgoing-list__cell">
          <span id="${sectionIdPrefix}-send-time-label-${entry.id}" class="apis-outgoing-list__label">Send time</span>
          <span id="${sectionIdPrefix}-send-time-value-${entry.id}" class="apis-outgoing-list__value">${escapeHtml(formatOutgoingSendTime(entry))}</span>
        </div>
        <div id="${sectionIdPrefix}-url-cell-${entry.id}" class="apis-outgoing-list__cell apis-outgoing-list__cell--url">
          <span id="${sectionIdPrefix}-url-label-${entry.id}" class="apis-outgoing-list__label">URL</span>
          <span id="${sectionIdPrefix}-url-value-${entry.id}" class="apis-outgoing-list__value apis-outgoing-list__value--url">${escapeHtml(entry.destination_url || "Not configured")}</span>
        </div>
      `;

      row.addEventListener("click", () => {
        actions.loadOutgoingEditDetail(entry.id, entry.type, row);
      });

      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          row.click();
        }
      });

      fragment.appendChild(row);
    });

    container.appendChild(fragment);
  };

  const syncOutgoingEditRowSelection = () => {
    document.querySelectorAll(".apis-outgoing-list__row[data-outgoing-id]").forEach((row) => {
      const isSelected = row.getAttribute("data-outgoing-id") === state.selectedOutgoingApiId;
      row.setAttribute("aria-pressed", String(isSelected));
      row.classList.toggle("apis-outgoing-list__row--selected", isSelected);
    });
  };

  const syncOverviewLandingSummary = ({
    incomingEntries,
    scheduledEntries,
    continuousEntries,
    webhookEntries
  }) => {
    if (!hasOverviewLandingElements(elements)) {
      return;
    }

    const totalCount = incomingEntries.length + scheduledEntries.length + continuousEntries.length + webhookEntries.length;
    const activeScheduledCalls = scheduledEntries.filter((entry) => getScheduledStatus(entry) === "active").length;
    const scheduledRepeatsPerHour = scheduledEntries
      .filter((entry) => getScheduledStatus(entry) === "active" && entry.repeat_enabled)
      .length / 24;
    const continuousRepeatsPerHour = continuousEntries
      .filter((entry) => entry.enabled && entry.repeat_enabled && entry.repeat_interval_minutes)
      .reduce((sum, entry) => sum + (60 / entry.repeat_interval_minutes), 0);
    const monitoredWebhooks = webhookEntries.filter((entry) => entry.enabled).length;
    const callsPerHour = scheduledRepeatsPerHour + continuousRepeatsPerHour;
    const callsPerDay = callsPerHour * 24;

    elements.overviewTotalCount.textContent = `${totalCount} configured APIs`;
    elements.overviewHelper.textContent = totalCount > 0
      ? "Across all configured API registries."
      : "Create an API to add it to the registry.";
    elements.overviewScheduledActiveCount.textContent = String(activeScheduledCalls);
    elements.overviewCallsPerHour.textContent = formatRate(callsPerHour);
    elements.overviewCallsPerDay.textContent = formatRate(callsPerDay);
    elements.overviewMonitoredWebhooksCount.textContent = String(monitoredWebhooks);
  };

  return {
    setAlert,
    setAutomationAlert,
    renderTable,
    renderMetadata,
    renderSecretPanel,
    renderLogSummary,
    getFilteredEvents,
    renderLogs,
    setDetailState,
    renderDetail,
    renderResourceList,
    renderOutgoingRegistryList,
    syncOutgoingEditRowSelection,
    syncOverviewLandingSummary
  };
};
