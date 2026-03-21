import { useEffect, useState } from "react";

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

  const handleSelectTable = (tableId: string) => {
    setSelectedTableId(tableId);
    setRowsData(null);
    setRowsError(null);
    setRowsLoading(true);
    fetchJson(`/api/v1/log-tables/${tableId}/rows?limit=${limit}`)
      .then((data) => {
        setRowsData(data);
        setRowsLoading(false);
      })
      .catch(() => {
        setRowsError("Failed to load rows.");
        setRowsLoading(false);
      });
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
    setSelectedTableId(null);
    setRowsData(null);
    loadTables();
  };

  const selectedTable = tables.find((t) => t.id === selectedTableId) ?? null;

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
      {/* Table selector sidebar */}
      <aside id="automations-data-sidebar" className="automations-data-sidebar">
        <h3 id="automations-data-sidebar-title" className="automations-data-sidebar__title">Tables</h3>
        <ul id="automations-data-table-list" className="automations-data-table-list" role="listbox" aria-label="Log tables">
          {tables.map((table) => (
            <li key={table.id}>
              <button
                id={`automations-data-table-${table.id}`}
                type="button"
                role="option"
                aria-selected={selectedTableId === table.id}
                className={`automations-data-table-item${selectedTableId === table.id ? " automations-data-table-item--active" : ""}`}
                onClick={() => handleSelectTable(table.id)}
              >
                <span id={`automations-data-table-${table.id}-name`} className="automations-data-table-item__name">{table.name}</span>
                <span id={`automations-data-table-${table.id}-count`} className="automations-data-table-item__count">{table.row_count} rows</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Row browser */}
      <section id="automations-data-browser" className="automations-data-browser">
        {!selectedTable && (
          <p id="automations-data-select-hint" className="automation-empty-state">Select a table to view its data.</p>
        )}

        {selectedTable && (
          <>
            <div id="automations-data-browser-header" className="automations-data-browser-header">
              <h3 id="automations-data-browser-title" className="automations-data-browser__title">{selectedTable.name}</h3>
              {selectedTable.description && (
                <p id="automations-data-browser-desc" className="automations-data-browser__desc">{selectedTable.description}</p>
              )}
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
                      if (selectedTableId) handleSelectTable(selectedTableId);
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
                  className="button button--secondary"
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
            </div>

            {rowsLoading && <p id="automations-data-rows-loading" className="automation-empty-state">Loading rows…</p>}
            {rowsError && <p id="automations-data-rows-error" className="automation-empty-state automation-empty-state--error" role="alert">{rowsError}</p>}

            {rowsData && !rowsLoading && (
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
                            <th
                              key={col}
                              id={`automations-data-th-${col}`}
                              scope="col"
                            >
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
            )}
          </>
        )}
      </section>
    </div>
  );
};
