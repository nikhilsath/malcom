import "../settings.js";
import { bindCollapsibleSection } from "../collapsible.js";

const backupDirEl = () => document.getElementById("backup-dir");
const createBtn = () => document.getElementById("create-backup-btn");
const backupList = () => document.getElementById("backup-list");
const restoreBtn = () => document.getElementById("restore-backup-btn");
const feedbackEl = () => document.getElementById("backup-feedback");

function getErrorMessage(error) {
    if (error instanceof Error && error.message) {
        return error.message;
    }
    return "Unknown error";
}

function setBackupFeedback(message, state = "neutral") {
    const feedback = feedbackEl();
    if (!feedback) {
        return;
    }
    feedback.textContent = message;
    feedback.dataset.state = state;
}

function updateRestoreButtonState() {
    const list = backupList();
    const restore = restoreBtn();
    if (!(list instanceof HTMLSelectElement) || !(restore instanceof HTMLButtonElement)) {
        return;
    }

    const hasSelectedBackup = Boolean(list.value) && list.dataset.empty !== "true";
    restore.disabled = !hasSelectedBackup;
}

function renderBackupOptions(backups, preferredFilename = "") {
    const list = backupList();
    if (!(list instanceof HTMLSelectElement)) {
        return;
    }

    list.innerHTML = "";

    if (!Array.isArray(backups) || backups.length === 0) {
        const emptyOption = document.createElement("option");
        emptyOption.id = "backup-list-empty-option";
        emptyOption.value = "";
        emptyOption.textContent = "No backups available yet";
        emptyOption.disabled = true;
        emptyOption.selected = true;
        list.appendChild(emptyOption);
        list.dataset.empty = "true";
        updateRestoreButtonState();
        return;
    }

    list.dataset.empty = "false";

    backups.forEach((backup, index) => {
        const option = document.createElement("option");
        option.id = `backup-list-option-${index}`;
        option.value = backup.filename || backup.id || "";
        option.textContent = formatBackupOptionLabel(backup);
        list.appendChild(option);
    });

    const selectedValue = preferredFilename && backups.some((backup) => (backup.filename || backup.id || "") === preferredFilename)
        ? preferredFilename
        : list.value || list.options[0]?.value || "";
    list.value = selectedValue;
    updateRestoreButtonState();
}

function formatBackupOptionLabel(backup) {
    const filename = backup?.filename || backup?.id || "backup";
    if (!backup?.created_at) {
        return filename;
    }
    return `${formatDate(backup.created_at)} - ${filename}`;
}

function setBackupControlsBusy(isBusy) {
    const create = createBtn();
    const restore = restoreBtn();
    const list = backupList();

    if (create instanceof HTMLButtonElement) {
        create.disabled = isBusy;
    }
    if (restore instanceof HTMLButtonElement) {
        restore.disabled = isBusy || !(list instanceof HTMLSelectElement) || !list.value || list.dataset.empty === "true";
    }
    if (list instanceof HTMLSelectElement) {
        list.disabled = isBusy;
    }
}

async function loadBackups({ preferredFilename = "", keepFeedback = false } = {}) {
    const directory = backupDirEl();
    if (directory) {
        directory.textContent = "Loading backup directory…";
    }
    if (!keepFeedback) {
        setBackupFeedback("Loading backups...");
    }
    try {
        const response = await fetch("/api/v1/settings/data/backups");
        if (!response.ok) {
            throw new Error((await response.text()) || response.statusText);
        }
        const payload = await response.json();
        if (directory) {
            directory.textContent = payload.directory || "Backup directory unavailable";
        }
        renderBackupOptions(payload.backups || [], preferredFilename);
        if (!keepFeedback) {
            setBackupFeedback((payload.backups || []).length ? "" : "No local backups found yet.");
        }
    } catch (error) {
        if (directory) {
            directory.textContent = "Backup directory unavailable";
        }
        renderBackupOptions([]);
        setBackupFeedback(`Error loading backups: ${getErrorMessage(error)}`, "error");
    }
}

async function createBackup() {
    setBackupControlsBusy(true);
    setBackupFeedback("Creating backup...");
    try {
        const response = await fetch("/api/v1/settings/data/backups", { method: "POST" });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload.ok === false) {
            throw new Error(payload.message || payload.error || response.statusText || "Create failed");
        }
        const filename = payload.backup?.filename || "";
        await loadBackups({ preferredFilename: filename, keepFeedback: true });
        setBackupFeedback(filename ? `Backup created: ${filename}` : "Backup created.", "success");
    } catch (error) {
        setBackupFeedback(`Create failed: ${getErrorMessage(error)}`, "error");
    } finally {
        setBackupControlsBusy(false);
    }
}

async function restoreBackup() {
    const list = backupList();
    if (!(list instanceof HTMLSelectElement)) {
        setBackupFeedback("Backup list is unavailable.", "error");
        return;
    }

    const selected = list.value;
    if (!selected) {
        setBackupFeedback("Select a backup to restore.", "error");
        updateRestoreButtonState();
        return;
    }

    if (!confirm("Restore selected backup? This will overwrite local settings. Continue?")) {
        return;
    }

    setBackupControlsBusy(true);
    setBackupFeedback("Restoring backup...");
    try {
        const response = await fetch("/api/v1/settings/data/backups/restore", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ backup_id: selected })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload.ok === false) {
            throw new Error(payload.message || payload.error || response.statusText || "Restore failed");
        }
        setBackupFeedback(`Restore succeeded: ${selected}`, "success");
    } catch (error) {
        setBackupFeedback(`Restore failed: ${getErrorMessage(error)}`, "error");
    } finally {
        setBackupControlsBusy(false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const create = createBtn();
    const restore = restoreBtn();
    const list = backupList();
    if (!(create instanceof HTMLButtonElement) || !(restore instanceof HTMLButtonElement) || !(list instanceof HTMLSelectElement)) {
        return;
    }

    create.addEventListener("click", createBackup);
    restore.addEventListener("click", restoreBackup);
    list.addEventListener("change", updateRestoreButtonState);
    setBackupControlsBusy(false);
    loadBackups();
});

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

const toTitleCase = (value) => value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());

const normalizeProvider = (provider) => {
    return (provider || "").toString().trim().toLowerCase();
};

const getEnabledConnectorStorageOptions = (connectors) => {
    const records = connectors?.records || [];
    const activeStatuses = new Set(connectors?.metadata?.active_storage_statuses || []);
    const providerCatalog = new Map((connectors?.catalog || []).map((preset) => [preset.id, preset.name]));
    const enabledRecords = records.filter((record) => activeStatuses.has((record.status || "").toLowerCase()));
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
                title: providerCatalog.get(provider) || "Google",
                location: `Enabled via connector: ${record.name || "Google"}`,
                type: "connector"
            });
            continue;
        }

        options.push({
            id: `settings-storage-connector-${provider}`,
            title: providerCatalog.get(provider) || `${toTitleCase(provider)} storage`,
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
    const connectors = window.MalcomLogStore?.getConnectors?.() || null;
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

    const connectorOptions = getEnabledConnectorStorageOptions(connectors);
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

    window.addEventListener("malcom:connectors-updated", () => {
        renderStorageLocations();
    });

    Promise.allSettled([
        window.MalcomLogStore?.ready?.(),
        window.MalcomLogStore?.loadConnectors?.()
    ]).then(() => {
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
