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

const toIdToken = (value: string, fallback: string): string => {
  const token = value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return token || fallback;
};

export const LogStepForm = ({ draft, onChange }: Props) => {
  // Top-level write destination: "db" (database table) or "file" (filesystem storage)
  const [writeMode, setWriteMode] = useState<"db" | "file">(
    draft.config.storage_type ? "file" : "db"
  );
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
  const disableExistingMode = !loadingTables && tables.length === 0;

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

  useEffect(() => {
    fetchTables();
  }, []);

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
      {/* Write destination toggle: DB table vs File */}
      <div id="log-step-write-mode-row" className="automation-field automation-field--full">
        <span id="log-step-write-mode-label" className="automation-field__label">Write destination</span>
        <div id="log-step-write-mode-options" className="log-step-mode-options">
          <label id="log-step-write-mode-db-label" className="log-step-mode-option">
            <input
              id="log-step-write-mode-db"
              type="radio"
              name="log-step-write-mode"
              value="db"
              checked={writeMode === "db"}
              onChange={() => {
                setWriteMode("db");
                onChange({ ...draft, config: { ...draft.config, storage_type: undefined, storage_target: undefined, storage_new_file: undefined } });
              }}
            />
            Database table
          </label>
          <label id="log-step-write-mode-file-label" className="log-step-mode-option">
            <input
              id="log-step-write-mode-file"
              type="radio"
              name="log-step-write-mode"
              value="file"
              checked={writeMode === "file"}
              onChange={() => {
                setWriteMode("file");
                onChange({ ...draft, config: { ...draft.config, log_table_id: "", log_column_mappings: {}, storage_type: "csv", storage_target: "", storage_new_file: true } });
              }}
            />
            File
          </label>
        </div>
      </div>

      {/* ── File write mode ── */}
      {writeMode === "file" && (
        <div id="log-step-file-options" className="log-step-file-options">
          <label id="log-step-storage-type-field" className="automation-field automation-field--full">
            <span id="log-step-storage-type-label" className="automation-field__label">Storage type</span>
            <select
              id="log-step-storage-type-select"
              className="automation-native-select"
              value={draft.config.storage_type || "csv"}
              onChange={(e) => onChange({ ...draft, config: { ...draft.config, storage_type: e.target.value as "csv" | "table" | "json" | "other" } })}
            >
              <option value="csv">CSV — append rows to a single file</option>
              <option value="table">Table — append rows to a single file</option>
              <option value="json">JSON — new timestamped file per run</option>
              <option value="other">Other — raw payload, timestamped file</option>
            </select>
          </label>

          <label id="log-step-storage-target-field" className="automation-field automation-field--full">
            <span id="log-step-storage-target-label" className="automation-field__label">Target name</span>
            <input
              id="log-step-storage-target-input"
              type="text"
              className="automation-input"
              placeholder="e.g. events or run_output"
              value={draft.config.storage_target || ""}
              onChange={(e) => onChange({ ...draft, config: { ...draft.config, storage_target: e.target.value } })}
            />
            <span id="log-step-storage-target-hint" className="automation-field__hint">
              Used as the file name base under the configured storage folder.
            </span>
          </label>

          {(draft.config.storage_type === "json" || !draft.config.storage_type) && (
            <label id="log-step-storage-new-file-field" className="automation-field automation-field--full log-step-storage-new-file-row">
              <input
                id="log-step-storage-new-file-toggle"
                type="checkbox"
                checked={draft.config.storage_new_file ?? true}
                onChange={(e) => onChange({ ...draft, config: { ...draft.config, storage_new_file: e.target.checked } })}
              />
              <span id="log-step-storage-new-file-label" className="automation-field__label">
                Create a new file for each run
              </span>
              <span id="log-step-storage-new-file-hint" className="automation-field__hint">
                When unchecked, records are appended to a single file.
              </span>
            </label>
          )}
        </div>
      )}

      {/* ── DB table mode ── */}
      {writeMode === "db" && (
        <>
      {/* Mode toggle */}
      <div id="log-step-mode-row" className="automation-field automation-field--full">
        <span id="log-step-mode-label" className="automation-field__label">Target table</span>
        <div id="log-step-mode-options" className="log-step-mode-options">
          <label
            id="log-step-mode-existing-label"
            className={`log-step-mode-option${disableExistingMode ? " log-step-mode-option--disabled" : ""}`}
          >
            <input
              id="log-step-mode-existing"
              type="radio"
              name="log-step-mode"
              value="existing"
              checked={mode === "existing"}
              disabled={disableExistingMode}
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
              {selectedTable.columns.map((col, columnIndex) => {
                const columnToken = toIdToken(col.column_name, `column-${columnIndex + 1}`);
                return (
                <label
                  key={col.column_name}
                  id={`log-step-mapping-column-${columnToken}-field`}
                  className="automation-field automation-field--full log-step-mapping-row"
                >
                  <span id={`log-step-mapping-column-${columnToken}-label`} className="log-step-mapping-col-name">
                    {col.column_name}
                    <em id={`log-step-mapping-column-${columnToken}-type`} className="log-step-mapping-col-type">
                      {" "}({col.data_type})
                    </em>
                  </span>
                  <input
                    id={`log-step-mapping-column-${columnToken}-input`}
                    type="text"
                    className="automation-input"
                    placeholder={`{{steps.prev.output}} or literal`}
                    value={mappings[col.column_name] ?? ""}
                    onChange={(e) => handleMappingChange(col.column_name, e.target.value)}
                  />
                </label>
                );
              })}
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
            {newColumns.map((col, index) => {
              const columnToken = toIdToken(col.column_name, `new-column-${index + 1}`);
              return (
              <div key={index} id={`log-step-column-${columnToken}-row`} className="log-step-column-row">
                <input
                  id={`log-step-column-${columnToken}-name`}
                  type="text"
                  className="automation-input log-step-column-row__name"
                  placeholder="column_name"
                  value={col.column_name}
                  onChange={(e) => updateColumn(index, "column_name", e.target.value)}
                />
                <select
                  id={`log-step-column-${columnToken}-type`}
                  className="automation-native-select log-step-column-row__type"
                  value={col.data_type}
                  onChange={(e) => updateColumn(index, "data_type", e.target.value)}
                >
                  {COLUMN_DATA_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <label id={`log-step-column-${columnToken}-nullable-label`} className="log-step-column-row__nullable">
                  <input
                    id={`log-step-column-${columnToken}-nullable`}
                    type="checkbox"
                    checked={col.nullable}
                    onChange={(e) => updateColumn(index, "nullable", e.target.checked)}
                  />
                  nullable
                </label>
                <input
                  id={`log-step-column-${columnToken}-default`}
                  type="text"
                  className="automation-input log-step-column-row__default"
                  placeholder="default (optional)"
                  value={col.default_value}
                  onChange={(e) => updateColumn(index, "default_value", e.target.value)}
                />
                {newColumns.length > 1 && (
                  <button
                    id={`log-step-column-${columnToken}-remove`}
                    type="button"
                    className="log-step-column-row__remove"
                    aria-label={`Remove column ${index + 1}`}
                    onClick={() => removeColumn(index)}
                  >
                    ×
                  </button>
                )}
              </div>
              );
            })}
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
        </>
      )}
    </div>
  );
};
