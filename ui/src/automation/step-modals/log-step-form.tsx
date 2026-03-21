import { useEffect, useState } from "react";
import type { AutomationStep, LogDbColumnDef, LogDbTableOption } from "../types";

type Props = {
  draft: AutomationStep;
  onChange: (step: AutomationStep) => void;
};

const COLUMN_DATA_TYPES = ["text", "integer", "real", "boolean", "timestamp"] as const;

const emptyColumn = (): LogDbColumnDef => ({
  column_name: "",
  data_type: "text",
  nullable: true,
  default_value: "",
});

export const LogStepForm = ({ draft, onChange }: Props) => {
  const [mode, setMode] = useState<"existing" | "new">(
    draft.config.log_table_id ? "existing" : "new"
  );
  const [tables, setTables] = useState<LogDbTableOption[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [newColumns, setNewColumns] = useState<LogDbColumnDef[]>([emptyColumn()]);
  const [newTableName, setNewTableName] = useState("");
  const [newTableDesc, setNewTableDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  const selectedTableId = draft.config.log_table_id || "";
  const mappings = draft.config.log_column_mappings || {};

  // The columns of the currently-selected existing table
  const selectedTable = tables.find((t) => t.id === selectedTableId) ?? null;

  const fetchTables = () => {
    setLoadingTables(true);
    fetch("/api/v1/log-tables")
      .then((r) => r.json())
      .then((data) => {
        setTables(Array.isArray(data) ? data : []);
        setLoadingTables(false);
      })
      .catch(() => setLoadingTables(false));
  };

  useEffect(() => {
    if (mode === "existing") fetchTables();
  }, [mode]);

  const handleModeChange = (next: "existing" | "new") => {
    setMode(next);
    // Clear log_table_id when switching to new
    if (next === "new") {
      onChange({ ...draft, config: { ...draft.config, log_table_id: "", log_column_mappings: {} } });
      setCreateError(null);
      setCreateSuccess(null);
    } else {
      fetchTables();
    }
  };

  const handleTableSelect = (tableId: string) => {
    const table = tables.find((t) => t.id === tableId);
    const freshMappings: Record<string, string> = {};
    if (table) {
      for (const col of table.columns) {
        freshMappings[col.column_name] = mappings[col.column_name] ?? "";
      }
    }
    onChange({ ...draft, config: { ...draft.config, log_table_id: tableId, log_column_mappings: freshMappings } });
  };

  const handleMappingChange = (colName: string, value: string) => {
    onChange({
      ...draft,
      config: {
        ...draft.config,
        log_column_mappings: { ...mappings, [colName]: value },
      },
    });
  };

  const addColumn = () => setNewColumns((cols) => [...cols, emptyColumn()]);

  const removeColumn = (index: number) =>
    setNewColumns((cols) => cols.filter((_, i) => i !== index));

  const updateColumn = (index: number, field: keyof LogDbColumnDef, value: string | boolean) =>
    setNewColumns((cols) =>
      cols.map((col, i) => (i === index ? { ...col, [field]: value } : col))
    );

  const handleCreateTable = async () => {
    setCreateError(null);
    setCreateSuccess(null);
    if (!newTableName.trim()) {
      setCreateError("Table name is required.");
      return;
    }
    const invalidCols = newColumns.filter((c) => !c.column_name.trim());
    if (invalidCols.length > 0) {
      setCreateError("All columns must have a name.");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch("/api/v1/log-tables", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newTableName.trim(),
          description: newTableDesc.trim(),
          columns: newColumns.map((c) => ({
            column_name: c.column_name.trim(),
            data_type: c.data_type,
            nullable: c.nullable,
            default_value: c.default_value || null,
          })),
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setCreateError(errData.detail ?? "Failed to create table.");
        setCreating(false);
        return;
      }
      const created = await res.json();
      setCreateSuccess(`Table "${created.name}" created.`);
      setMode("existing");
      // Reload tables and auto-select the new one
      const listRes = await fetch("/api/v1/log-tables");
      const allTables = await listRes.json();
      setTables(Array.isArray(allTables) ? allTables : []);
      const freshMappings: Record<string, string> = {};
      for (const col of created.columns ?? []) {
        freshMappings[col.column_name] = "";
      }
      onChange({
        ...draft,
        config: { ...draft.config, log_table_id: created.id, log_column_mappings: freshMappings },
      });
    } catch (err) {
      setCreateError("Unexpected error creating table.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div id="log-step-form-root" className="log-step-form">
      {/* Mode toggle */}
      <div id="log-step-mode-row" className="automation-field automation-field--full">
        <span id="log-step-mode-label" className="automation-field__label">Target table</span>
        <div id="log-step-mode-options" className="log-step-mode-options">
          <label id="log-step-mode-existing-label" className="log-step-mode-option">
            <input
              id="log-step-mode-existing"
              type="radio"
              name="log-step-mode"
              value="existing"
              checked={mode === "existing"}
              onChange={() => handleModeChange("existing")}
            />
            Use existing table
          </label>
          <label id="log-step-mode-new-label" className="log-step-mode-option">
            <input
              id="log-step-mode-new"
              type="radio"
              name="log-step-mode"
              value="new"
              checked={mode === "new"}
              onChange={() => handleModeChange("new")}
            />
            Create new table
          </label>
        </div>
      </div>

      {/* ── Existing table mode ── */}
      {mode === "existing" && (
        <>
          <label id="log-step-table-field" className="automation-field automation-field--full">
            <span id="log-step-table-label" className="automation-field__label">Table</span>
            {loadingTables ? (
              <span id="log-step-table-loading" className="automation-field__hint">Loading tables…</span>
            ) : (
              <select
                id="log-step-table-select"
                className="automation-native-select"
                value={selectedTableId}
                onChange={(e) => handleTableSelect(e.target.value)}
              >
                <option value="">— select a table —</option>
                {tables.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            )}
          </label>

          {selectedTable && (
            <div id="log-step-mappings" className="log-step-mappings">
              <span id="log-step-mappings-label" className="automation-field__label">
                Column value mappings
                <span id="log-step-mappings-hint" className="automation-field__hint">
                  {" "}— use {"{{variable}}"} templates
                </span>
              </span>
              {selectedTable.columns.map((col) => (
                <label
                  key={col.column_name}
                  id={`log-step-mapping-${col.column_name}-field`}
                  className="automation-field automation-field--full log-step-mapping-row"
                >
                  <span id={`log-step-mapping-${col.column_name}-label`} className="log-step-mapping-col-name">
                    {col.column_name}
                    <em id={`log-step-mapping-${col.column_name}-type`} className="log-step-mapping-col-type">
                      {" "}({col.data_type})
                    </em>
                  </span>
                  <input
                    id={`log-step-mapping-${col.column_name}-input`}
                    type="text"
                    className="automation-input"
                    placeholder={`{{steps.prev.output}} or literal`}
                    value={mappings[col.column_name] ?? ""}
                    onChange={(e) => handleMappingChange(col.column_name, e.target.value)}
                  />
                </label>
              ))}
            </div>
          )}

          {tables.length === 0 && !loadingTables && (
            <p id="log-step-no-tables-hint" className="automation-field__hint">
              No tables yet. Switch to "Create new table" to define one.
            </p>
          )}
        </>
      )}

      {/* ── Create new table mode ── */}
      {mode === "new" && (
        <div id="log-step-create-table" className="log-step-create-table">
          <label id="log-step-new-table-name-field" className="automation-field automation-field--full">
            <span id="log-step-new-table-name-label" className="automation-field__label">Table name</span>
            <input
              id="log-step-new-table-name-input"
              type="text"
              className="automation-input"
              placeholder="e.g. order_events"
              value={newTableName}
              onChange={(e) => setNewTableName(e.target.value)}
            />
            <span id="log-step-new-table-name-hint" className="automation-field__hint">
              Lowercase letters, digits, underscores only. Must start with a letter.
            </span>
          </label>

          <label id="log-step-new-table-desc-field" className="automation-field automation-field--full">
            <span id="log-step-new-table-desc-label" className="automation-field__label">Description (optional)</span>
            <input
              id="log-step-new-table-desc-input"
              type="text"
              className="automation-input"
              placeholder="What does this table store?"
              value={newTableDesc}
              onChange={(e) => setNewTableDesc(e.target.value)}
            />
          </label>

          <div id="log-step-columns-section" className="log-step-columns-section">
            <span id="log-step-columns-label" className="automation-field__label">Columns</span>
            {newColumns.map((col, index) => (
              <div key={index} id={`log-step-col-${index}`} className="log-step-column-row">
                <input
                  id={`log-step-col-${index}-name`}
                  type="text"
                  className="automation-input log-step-column-row__name"
                  placeholder="column_name"
                  value={col.column_name}
                  onChange={(e) => updateColumn(index, "column_name", e.target.value)}
                />
                <select
                  id={`log-step-col-${index}-type`}
                  className="automation-native-select log-step-column-row__type"
                  value={col.data_type}
                  onChange={(e) => updateColumn(index, "data_type", e.target.value)}
                >
                  {COLUMN_DATA_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <label id={`log-step-col-${index}-nullable-label`} className="log-step-column-row__nullable">
                  <input
                    id={`log-step-col-${index}-nullable`}
                    type="checkbox"
                    checked={col.nullable}
                    onChange={(e) => updateColumn(index, "nullable", e.target.checked)}
                  />
                  nullable
                </label>
                <input
                  id={`log-step-col-${index}-default`}
                  type="text"
                  className="automation-input log-step-column-row__default"
                  placeholder="default (optional)"
                  value={col.default_value}
                  onChange={(e) => updateColumn(index, "default_value", e.target.value)}
                />
                {newColumns.length > 1 && (
                  <button
                    id={`log-step-col-${index}-remove`}
                    type="button"
                    className="log-step-column-row__remove"
                    aria-label={`Remove column ${index + 1}`}
                    onClick={() => removeColumn(index)}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            <button
              id="log-step-add-column"
              type="button"
              className="button button--secondary log-step-add-column"
              onClick={addColumn}
            >
              + Add column
            </button>
          </div>

          {createError && (
            <p id="log-step-create-error" className="log-step-create-error" role="alert">
              {createError}
            </p>
          )}
          {createSuccess && (
            <p id="log-step-create-success" className="log-step-create-success" role="status">
              {createSuccess}
            </p>
          )}

          <button
            id="log-step-create-submit"
            type="button"
            className="button button--primary log-step-create-submit"
            disabled={creating}
            onClick={handleCreateTable}
          >
            {creating ? "Creating…" : "Create table"}
          </button>
        </div>
      )}
    </div>
  );
};
