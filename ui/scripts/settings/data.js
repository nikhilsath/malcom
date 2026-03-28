import "../settings.js";
import { bindCollapsibleSection } from "../collapsible.js";

const LOCAL_STORAGE_SPOTS = [
    {
        id: "settings-storage-local-database",
        title: "Runtime database",
        location: "MALCOM_DATABASE_URL (workspace database)",
        type: "local"
    },
    {
        id: "settings-storage-local-logs",
        title: "Application logs",
        location: "backend/data/logs/",
        type: "local"
    },
    {
        id: "settings-storage-local-media",
        title: "Workspace media",
        location: "media/",
        type: "local"
    }
];

const CONNECTOR_STORAGE_PROVIDER_LABELS = {
    google: "Google Drive",
    dropbox: "Dropbox",
    onedrive: "Microsoft OneDrive",
    box: "Box",
    s3: "Amazon S3"
};

const CONNECTOR_ACTIVE_STATUSES = new Set(["enabled", "connected", "pending_oauth", "needs_attention"]);

const toTitleCase = (value) => value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());

const normalizeProvider = (provider) => {
    const normalized = (provider || "").toString().trim().toLowerCase();
    return normalized.startsWith("google_") ? "google" : normalized;
};

const getEnabledConnectorStorageOptions = (settings) => {
    const records = settings?.connectors?.records || [];
    const enabledRecords = records.filter((record) => CONNECTOR_ACTIVE_STATUSES.has((record.status || "").toLowerCase()));
    const seenProviders = new Set();
    const options = [];

    for (const record of enabledRecords) {
        const provider = normalizeProvider(record.provider);
        if (!provider || seenProviders.has(provider)) {
            continue;
        }

        seenProviders.add(provider);

        if (provider === "google") {
            options.push({
                id: "settings-storage-connector-google-drive",
                title: "Google Drive",
                location: `Enabled via connector: ${record.name || "Google"}`,
                type: "connector"
            });
            continue;
        }

        options.push({
            id: `settings-storage-connector-${provider}`,
            title: CONNECTOR_STORAGE_PROVIDER_LABELS[provider] || `${toTitleCase(provider)} storage`,
            location: `Enabled via connector: ${record.name || toTitleCase(provider)}`,
            type: "connector"
        });
    }

    return options;
};

const renderStorageLocationList = (containerId, items, maxStorageMb, emptyMessage) => {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    if (!items.length) {
        container.innerHTML = `<p id="${containerId}-empty" class="automation-empty-state">${emptyMessage}</p>`;
        return;
    }

    container.innerHTML = items.map((item) => `
        <article id="${item.id}" class="settings-storage-location-item">
            <div id="${item.id}-copy" class="settings-storage-location-item__copy">
                <p id="${item.id}-title" class="settings-storage-location-item__title">${escapeHtml(item.title)}</p>
                <p id="${item.id}-path" class="settings-storage-location-item__path">${escapeHtml(item.location)}</p>
            </div>
            <p id="${item.id}-limit" class="settings-storage-location-item__limit">Max ${maxStorageMb} MB</p>
        </article>
    `).join("");
};

const getMaxStorageMbValue = (settings) => {
    const input = document.getElementById("settings-storage-max-mb-input");
    const fallback = settings?.logging?.max_file_size_mb || 5;
    const parsed = Number.parseInt(input?.value || "", 10);
    if (!Number.isFinite(parsed)) {
        return fallback;
    }
    return Math.min(100, Math.max(1, parsed));
};

const renderStorageLocations = () => {
    const settings = window.MalcomLogStore?.getAppSettings?.() || null;
    if (!settings) {
        return;
    }

    const input = document.getElementById("settings-storage-max-mb-input");
    if (input && !input.value) {
        input.value = String(settings.logging?.max_file_size_mb || 5);
    }

    const maxStorageMb = getMaxStorageMbValue(settings);
    if (input && input.value !== String(maxStorageMb)) {
        input.value = String(maxStorageMb);
    }

    renderStorageLocationList(
        "settings-storage-local-list",
        LOCAL_STORAGE_SPOTS,
        maxStorageMb,
        "No local storage spots configured."
    );

    const connectorOptions = getEnabledConnectorStorageOptions(settings);
    renderStorageLocationList(
        "settings-storage-connectors-list",
        connectorOptions,
        maxStorageMb,
        "No connector-backed storage locations available."
    );
};

const bindStorageLocations = () => {
    const maxStorageInput = document.getElementById("settings-storage-max-mb-input");
    if (maxStorageInput instanceof HTMLInputElement) {
        maxStorageInput.addEventListener("input", () => {
            renderStorageLocations();
        });
    }

    window.addEventListener("malcom:app-settings-updated", () => {
        renderStorageLocations();
    });

    window.MalcomLogStore?.ready?.().then(() => {
        renderStorageLocations();
    }).catch(() => {
        renderStorageLocations();
    });
};

// ── Log table storage management ─────────────────────────────────────────────

bindCollapsibleSection({
    toggleId: "settings-log-storage-collapse-toggle",
    bodyId: "settings-log-storage-body",
    symbolId: "settings-log-storage-collapse-symbol",
    srLabelId: "settings-log-storage-collapse-label",
    expandedLabel: "Collapse log table storage management",
    collapsedLabel: "Expand log table storage management",
    onExpand: () => {
        loadLogTableStats();
    }
});

function renderLogTableStats(tables) {
    const container = document.getElementById("settings-log-tables-stats");
    if (!container) return;
    if (!tables || tables.length === 0) {
        container.innerHTML = '<p id="settings-log-tables-empty" class="automation-empty-state">No log tables found.</p>';
        return;
    }
    const rows = tables.map((t) => `
        <tr id="settings-log-table-row-${t.id}">
            <td id="settings-log-table-name-${t.id}">${escapeHtml(t.name)}</td>
            <td id="settings-log-table-count-${t.id}">${t.row_count.toLocaleString()} rows</td>
            <td id="settings-log-table-updated-${t.id}" class="settings-log-table-date">${formatDate(t.updated_at)}</td>
            <td>
                <button
                    id="settings-log-table-clear-${t.id}"
                    type="button"
                    class="button button--secondary settings-log-table-clear"
                    data-table-id="${t.id}"
                    data-table-name="${escapeHtml(t.name)}"
                >
                    Clear rows
                </button>
            </td>
        </tr>
    `).join("");
    container.innerHTML = `
        <table id="settings-log-tables-table" class="settings-log-tables-table">
            <thead>
                <tr>
                    <th scope="col">Table</th>
                    <th scope="col">Rows</th>
                    <th scope="col">Last updated</th>
                    <th scope="col">Actions</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
    container.querySelectorAll(".settings-log-table-clear").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            const tableId = e.currentTarget.dataset.tableId;
            const tableName = e.currentTarget.dataset.tableName;
            if (!confirm(`Clear all rows from "${tableName}"? This cannot be undone.`)) return;
            await fetch(`/api/v1/log-tables/${tableId}/rows/clear`, { method: "POST" });
            loadLogTableStats();
        });
    });
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(isoStr) {
    if (!isoStr) return "—";
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d);
}

async function loadLogTableStats() {
    const container = document.getElementById("settings-log-tables-stats");
    if (!container) return;
    container.innerHTML = '<p id="settings-log-tables-loading" class="automation-empty-state">Loading…</p>';
    try {
        const res = await fetch("/api/v1/log-tables");
        const tables = await res.json();
        renderLogTableStats(tables);
    } catch {
        if (container) {
            container.innerHTML = '<p id="settings-log-tables-error" class="automation-empty-state">Failed to load log tables.</p>';
        }
    }
}

bindStorageLocations();
