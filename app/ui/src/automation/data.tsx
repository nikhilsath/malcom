import { useEffect, useRef, useState } from "react";

type LogTableColumn = {
  column_name: string;
  data_type: string;
};

type LogTable = {
  id: string;
  name: string;
  description: string;
  row_count: number;
  created_at: string;
  updated_at: string;
  columns?: LogTableColumn[];
};

type LogRowsResponse = {
  table_id: string;
  table_name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
};

const fetchJson = (path: string) => fetch(path).then((r) => r.json());

export const AutomationDataApp = () => {
  const [tables, setTables] = useState<LogTable[]>([]);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [rowsData, setRowsData] = useState<LogRowsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rowsError, setRowsError] = useState<string | null>(null);
  const [limit, setLimit] = useState(100);
  const [returnFocusId, setReturnFocusId] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  const loadTables = () => {
    setLoading(true);
    setError(null);
    fetchJson("/api/v1/log-tables")
      .then((data) => {
        setTables(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load log tables.");
        setLoading(false);
      });
  };

  useEffect(() => {
    loadTables();
  }, []);

  const handleSelectTable = (tableId: string, triggerId?: string, requestedLimit = limit) => {
    setSelectedTableId(tableId);
    setReturnFocusId(triggerId || null);
    setRowsData(null);
    setRowsError(null);
    setRowsLoading(true);
    fetchJson(`/api/v1/log-tables/${tableId}/rows?limit=${requestedLimit}`)
      .then((data) => {
        setRowsData(data);
        setRowsLoading(false);
      })
      .catch(() => {
        setRowsError("Failed to load rows.");
        setRowsLoading(false);
      });
  };

  const handleCloseModal = () => {
    setSelectedTableId(null);
    setRowsData(null);
    setRowsError(null);
    setRowsLoading(false);
  };

  const handleClearRows = async () => {
    if (!selectedTableId) return;
    if (!window.confirm("Clear all rows from this table? This cannot be undone.")) return;
    await fetch(`/api/v1/log-tables/${selectedTableId}/rows/clear`, { method: "POST" });
    handleSelectTable(selectedTableId);
  };

  const handleDeleteTable = async () => {
    if (!selectedTableId) return;
    if (!window.confirm("Delete this table and all its data? This cannot be undone.")) return;
    await fetch(`/api/v1/log-tables/${selectedTableId}`, { method: "DELETE" });
    handleCloseModal();
    loadTables();
  };

  const selectedTable = tables.find((t) => t.id === selectedTableId) ?? null;

  useEffect(() => {
    if (!selectedTableId) {
      if (returnFocusId) {
        document.getElementById(returnFocusId)?.focus();
      }
      return;
    }

    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleCloseModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedTableId, returnFocusId]);

  if (loading) {
    return <p id="automations-data-loading" className="automation-empty-state">Loading log tables…</p>;
  }

  if (error) {
    return <p id="automations-data-error" className="automation-empty-state automation-empty-state--error" role="alert">{error}</p>;
  }

  if (tables.length === 0) {
    return (
      <div id="automations-data-empty" className="automation-empty-state">
        <p id="automations-data-empty-text">No log tables yet.</p>
        <p id="automations-data-empty-hint" className="automation-empty-state__hint">
          Add a Log step to an automation and create a table from the step configuration.
        </p>
      </div>
    );
  }

  return (
    <div id="automations-data-root" className="automations-data-root">
      <section id="automations-data-directory" className="automations-data-directory card">
        <div id="automations-data-directory-header" className="section-header automation-panel__header">
          <div id="automations-data-directory-copy" className="section-header__copy">
            <div className="title-row">
              <h3 id="automations-data-directory-title" className="section-header__title">Log tables</h3>
              <button type="button" id="automations-data-directory-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-data-directory-description">i</button>
            </div>
            <p id="automations-data-directory-description" className="section-header__description" hidden>Select a table to inspect rows in a modal without leaving the directory list.</p>
          </div>
        </div>
        <ul id="automations-data-table-list" className="automations-data-table-list" role="list" aria-label="Log tables">
          {tables.map((table) => (
            <li key={table.id} id={`automations-data-table-item-${table.id}`}>
              <button
                id={`automations-data-table-${table.id}`}
                type="button"
                className="automations-data-table-item"
                onClick={() => handleSelectTable(table.id, `automations-data-table-${table.id}`)}
              >
                <span id={`automations-data-table-${table.id}-name`} className="automations-data-table-item__name">{table.name}</span>
                {table.description ? (
                  <span id={`automations-data-table-${table.id}-description`} className="automations-data-table-item__description">{table.description}</span>
                ) : null}
                <span id={`automations-data-table-${table.id}-count`} className="automations-data-table-item__count">{table.row_count} rows</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {!selectedTable ? (
        <p id="automations-data-select-hint" className="automation-empty-state">Select a table to view its data.</p>
      ) : null}

      {selectedTable ? (
        <>
          <button
            type="button"
            id="automations-data-modal-backdrop"
            className="automation-dialog-backdrop"
            aria-label="Close log table details"
            onClick={handleCloseModal}
          />
          <div
            id="automations-data-modal"
            className="automation-detail-dialog automations-data-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="automations-data-browser-title"
          >
            <div id="automations-data-modal-dismiss-row" className="automation-dialog__dismiss-row">
              <button
                ref={closeButtonRef}
                id="automations-data-modal-close"
                type="button"
                className="modal__close-icon-button automation-detail-dialog__close-button"
                aria-label="Close log table details"
                onClick={handleCloseModal}
              >
                ×
              </button>
            </div>

            <div id="automations-data-browser-header" className="automation-detail-dialog__header">
              <div id="automations-data-browser-title-row" className="automation-detail-dialog__title-row">
                <h3 id="automations-data-browser-title" className="automation-detail-dialog__title">{selectedTable.name}</h3>
                <button type="button" id="automations-data-browser-badge" className="info-badge" aria-label="More information" aria-expanded="false" aria-controls="automations-data-browser-description">i</button>
              </div>
              <p id="automations-data-browser-description" className="automation-dialog__description" hidden>
                {selectedTable.description || "Inspect the latest rows written to this managed log table."}
              </p>
              <div id="automations-data-browser-stats" className="automation-detail-dialog__stats">
                <div id="automations-data-browser-stat-rows" className="automation-detail-stat">
                  <span id="automations-data-browser-stat-rows-label" className="automation-detail-stat__label">Stored rows</span>
                  <span id="automations-data-browser-stat-rows-value" className="automation-detail-stat__value">{selectedTable.row_count}</span>
                </div>
                <div id="automations-data-browser-stat-created" className="automation-detail-stat">
                  <span id="automations-data-browser-stat-created-label" className="automation-detail-stat__label">Created</span>
                  <span id="automations-data-browser-stat-created-value" className="automation-detail-stat__value">{formatDateTime(selectedTable.created_at)}</span>
                </div>
                <div id="automations-data-browser-stat-updated" className="automation-detail-stat">
                  <span id="automations-data-browser-stat-updated-label" className="automation-detail-stat__label">Updated</span>
                  <span id="automations-data-browser-stat-updated-value" className="automation-detail-stat__value">{formatDateTime(selectedTable.updated_at)}</span>
                </div>
              </div>
            </div>

            <div id="automations-data-browser-actions" className="automations-data-browser-actions">
              <label id="automations-data-limit-label" className="automations-data-limit-label">
                Rows
                <select
                  id="automations-data-limit-select"
                  className="automation-native-select automations-data-limit-select"
                  value={limit}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setLimit(next);
                    if (selectedTableId) handleSelectTable(selectedTableId, returnFocusId || undefined, next);
                  }}
                >
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                  <option value={500}>500</option>
                </select>
              </label>
              <button
                id="automations-data-clear-button"
                type="button"
                className="button button--danger"
                onClick={handleClearRows}
              >
                Clear all rows
              </button>
              <button
                id="automations-data-delete-button"
                type="button"
                className="button button--danger"
                onClick={handleDeleteTable}
              >
                Delete table
              </button>
            </div>

            {rowsLoading && <p id="automations-data-rows-loading" className="automation-empty-state">Loading rows…</p>}
            {rowsError && <p id="automations-data-rows-error" className="automation-empty-state automation-empty-state--error" role="alert">{rowsError}</p>}

            {rowsData && !rowsLoading ? (
              <>
                <p id="automations-data-total-hint" className="automations-data-total-hint">
                  Showing {rowsData.rows.length} of {rowsData.total} rows (most recent first)
                </p>
                {rowsData.rows.length === 0 ? (
                  <p id="automations-data-no-rows" className="automation-empty-state">No rows written yet.</p>
                ) : (
                  <div id="automations-data-table-wrapper" className="automations-data-table-wrapper">
                    <table id="automations-data-table" className="automations-data-table">
                      <thead>
                        <tr id="automations-data-table-head-row">
                          {rowsData.columns.map((col) => (
                            <th key={col} id={`automations-data-th-${col}`} scope="col">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rowsData.rows.map((row, rowIdx) => (
                          <tr key={String(row.row_id ?? rowIdx)} id={`automations-data-row-${String(row.row_id ?? rowIdx)}`}>
                            {rowsData.columns.map((col) => (
                              <td key={col} id={`automations-data-cell-${String(row.row_id ?? rowIdx)}-${col}`}>
                                {row[col] == null ? <em className="automations-data-null">null</em> : String(row[col])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
};
