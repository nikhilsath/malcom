import "../settings.js";

// ── Log table storage management ─────────────────────────────────────────────

const collapseToggle = document.getElementById("settings-log-storage-collapse-toggle");
const collapseBody = document.getElementById("settings-log-storage-body");
const collapseSymbol = document.getElementById("settings-log-storage-collapse-symbol");

if (collapseToggle && collapseBody && collapseSymbol) {
    collapseToggle.addEventListener("click", () => {
        const isExpanded = collapseToggle.getAttribute("aria-expanded") === "true";
        collapseToggle.setAttribute("aria-expanded", String(!isExpanded));
        collapseBody.hidden = isExpanded;
        collapseSymbol.textContent = isExpanded ? "+" : "−";
        if (!isExpanded) {
            loadLogTableStats();
        }
    });
}

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

