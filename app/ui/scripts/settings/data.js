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

// ── Storage locations management ─────────────────────────────────────────────

function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(isoStr) {
    if (!isoStr) return "—";
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d);
}

const TYPE_LABELS = { local: "Local folder", google_drive: "Google Drive", repo: "Git repo" };

function renderStorageLocationItem(loc) {
    const typeLabel = TYPE_LABELS[loc.location_type] || loc.location_type;
    const limitText = loc.max_size_mb ? `Max ${loc.max_size_mb} MB` : "No limit";
    const defaultLogsTag = loc.is_default_logs ? ` <span id="storage-loc-${loc.id}-default-logs-tag" class="settings-storage-default-logs-tag">Default logs</span>` : "";
    return `
        <article id="storage-loc-${loc.id}" class="settings-storage-location-item">
            <div id="storage-loc-${loc.id}-copy" class="settings-storage-location-item__copy">
                <p id="storage-loc-${loc.id}-title" class="settings-storage-location-item__title">${escapeHtml(loc.name)}${defaultLogsTag}</p>
                <p id="storage-loc-${loc.id}-meta" class="settings-storage-location-item__path">${escapeHtml(typeLabel)}${loc.path ? ` — ${escapeHtml(loc.path)}` : ""}</p>
            </div>
            <p id="storage-loc-${loc.id}-limit" class="settings-storage-location-item__limit">${limitText}</p>
            <div id="storage-loc-${loc.id}-actions" class="settings-storage-location-item__actions">
                <button type="button" id="storage-loc-${loc.id}-edit-btn" class="button button--secondary settings-storage-edit-btn" data-id="${loc.id}">Edit</button>
                <button type="button" id="storage-loc-${loc.id}-delete-btn" class="button button--secondary settings-storage-delete-btn" data-id="${loc.id}">Delete</button>
            </div>
        </article>
    `;
}

async function loadStorageLocations() {
    const container = document.getElementById("settings-storage-locations-list");
    if (!container) return;
    container.innerHTML = '<p id="settings-storage-locations-loading" class="automation-empty-state">Loading…</p>';
    try {
        const res = await fetch("/api/v1/storage/locations");
        if (!res.ok) throw new Error(res.statusText);
        const locations = await res.json();
        if (!Array.isArray(locations) || locations.length === 0) {
            container.innerHTML = '<p id="settings-storage-locations-empty" class="automation-empty-state">No storage locations configured yet.</p>';
        } else {
            container.innerHTML = locations.map(renderStorageLocationItem).join("");
            container.querySelectorAll(".settings-storage-edit-btn").forEach((btn) => {
                btn.addEventListener("click", () => openStorageModal(btn.dataset.id));
            });
            container.querySelectorAll(".settings-storage-delete-btn").forEach((btn) => {
                btn.addEventListener("click", () => deleteStorageLocation(btn.dataset.id));
            });
        }
    } catch (err) {
        container.innerHTML = `<p id="settings-storage-locations-error" class="automation-empty-state">Failed to load: ${escapeHtml(String(err.message || err))}</p>`;
    }
}

async function deleteStorageLocation(id) {
    if (!confirm("Delete this storage location? This cannot be undone.")) return;
    try {
        const res = await fetch(`/api/v1/storage/locations/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
        await loadStorageLocations();
    } catch (err) {
        alert(`Delete failed: ${err.message || err}`);
    }
}

function openStorageModal(editId = null) {
    const modal = document.getElementById("settings-storage-modal");
    const idInput = document.getElementById("settings-storage-modal-id");
    const nameInput = document.getElementById("settings-storage-modal-name");
    const typeInput = document.getElementById("settings-storage-modal-type");
    const pathInput = document.getElementById("settings-storage-modal-path");
    const maxMbInput = document.getElementById("settings-storage-modal-max-mb");
    const folderTmplInput = document.getElementById("settings-storage-modal-folder-tmpl");
    const fileTmplInput = document.getElementById("settings-storage-modal-file-tmpl");
    const defaultLogsInput = document.getElementById("settings-storage-modal-default-logs");
    const errorEl = document.getElementById("settings-storage-modal-error");
    if (!modal) return;

    // Reset form
    idInput.value = editId || "";
    nameInput.value = "";
    typeInput.value = "local";
    pathInput.value = "";
    maxMbInput.value = "";
    folderTmplInput.value = "";
    fileTmplInput.value = "";
    defaultLogsInput.checked = false;
    if (errorEl) { errorEl.textContent = ""; errorEl.hidden = true; }

    if (editId) {
        // Populate from existing data
        const existing = document.getElementById(`storage-loc-${editId}`);
        if (existing) {
            // Best effort populate from rendered data; real data comes from API in production
        }
        fetch(`/api/v1/storage/locations`)
            .then((r) => r.json())
            .then((locs) => {
                const loc = Array.isArray(locs) ? locs.find((l) => l.id === editId) : null;
                if (!loc) return;
                nameInput.value = loc.name || "";
                typeInput.value = loc.location_type || "local";
                pathInput.value = loc.path || "";
                maxMbInput.value = loc.max_size_mb || "";
                folderTmplInput.value = loc.folder_template || "";
                fileTmplInput.value = loc.file_name_template || "";
                defaultLogsInput.checked = Boolean(loc.is_default_logs);
            })
            .catch(() => {});
    }

    if (typeof modal.showModal === "function") {
        modal.showModal();
    } else {
        modal.setAttribute("open", "");
    }
}

async function saveStorageLocation(e) {
    e.preventDefault();
    const idInput = document.getElementById("settings-storage-modal-id");
    const nameInput = document.getElementById("settings-storage-modal-name");
    const typeInput = document.getElementById("settings-storage-modal-type");
    const pathInput = document.getElementById("settings-storage-modal-path");
    const maxMbInput = document.getElementById("settings-storage-modal-max-mb");
    const folderTmplInput = document.getElementById("settings-storage-modal-folder-tmpl");
    const fileTmplInput = document.getElementById("settings-storage-modal-file-tmpl");
    const defaultLogsInput = document.getElementById("settings-storage-modal-default-logs");
    const errorEl = document.getElementById("settings-storage-modal-error");
    const saveBtn = document.getElementById("settings-storage-modal-save");

    const id = idInput.value;
    const body = {
        name: nameInput.value.trim(),
        location_type: typeInput.value,
        path: pathInput.value.trim() || null,
        max_size_mb: maxMbInput.value ? parseInt(maxMbInput.value, 10) : null,
        folder_template: folderTmplInput.value.trim() || null,
        file_name_template: fileTmplInput.value.trim() || null,
        is_default_logs: defaultLogsInput.checked,
    };

    if (!body.name) {
        if (errorEl) { errorEl.textContent = "Name is required."; errorEl.hidden = false; }
        return;
    }

    if (saveBtn) saveBtn.disabled = true;

    try {
        let res;
        if (id) {
            res = await fetch(`/api/v1/storage/locations/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
        } else {
            res = await fetch("/api/v1/storage/locations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
        }
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            const msg = errData.detail || res.statusText || "Save failed";
            if (errorEl) { errorEl.textContent = msg; errorEl.hidden = false; }
            return;
        }
        const modal = document.getElementById("settings-storage-modal");
        if (modal && typeof modal.close === "function") modal.close();
        await loadStorageLocations();
    } catch (err) {
        if (errorEl) { errorEl.textContent = String(err.message || err); errorEl.hidden = false; }
    } finally {
        if (saveBtn) saveBtn.disabled = false;
    }
}

function bindStorageLocations() {
    const addBtn = document.getElementById("settings-storage-add-btn");
    if (addBtn) addBtn.addEventListener("click", () => openStorageModal(null));

    const modalForm = document.getElementById("settings-storage-modal-form");
    if (modalForm) modalForm.addEventListener("submit", saveStorageLocation);

    const cancelBtn = document.getElementById("settings-storage-modal-cancel");
    const modal = document.getElementById("settings-storage-modal");
    if (cancelBtn && modal) cancelBtn.addEventListener("click", () => {
        if (typeof modal.close === "function") modal.close();
        else modal.removeAttribute("open");
    });

    loadStorageLocations();
}

bindStorageLocations();

// ── Log table storage management ─────────────────────────────────────────────

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
