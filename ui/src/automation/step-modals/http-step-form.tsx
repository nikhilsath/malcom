import { useMemo, useState } from "react";
import { normalizeRequestError, requestJson } from "../../lib/request";
import type { AutomationStep, ConnectorRecord } from "../types";

type Props = {
  draft: AutomationStep;
  connectors: ConnectorRecord[];
  onChange: (step: AutomationStep) => void;
  idPrefix?: string;
};

type JsonMapping = {
  key: string;
  path: string;
};

const httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

const normalizeFieldKey = (path: string) => {
  const normalized = path.replace(/[^a-zA-Z0-9_]+/g, "_").replace(/^_+|_+$/g, "").toLowerCase();
  if (!normalized) {
    return "value";
  }
  return /^\d/.test(normalized) ? `field_${normalized}` : normalized;
};

const appendPath = (basePath: string, segment: string | number) => {
  if (typeof segment === "number") {
    return `${basePath}[${segment}]`;
  }
  return basePath ? `${basePath}.${segment}` : segment;
};

const prettyValue = (value: unknown) => {
  if (value === null) return "null";
  if (Array.isArray(value)) return `Array(${value.length})`;
  if (typeof value === "object") return `Object(${Object.keys(value as Record<string, unknown>).length})`;
  return String(value);
};

const JsonTree = ({
  value,
  path,
  onSelect,
  idPrefix
}: {
  value: unknown;
  path: string;
  onSelect: (path: string) => void;
  idPrefix: string;
}) => {
  if (Array.isArray(value)) {
    return (
      <ul id={`${idPrefix}-array-${path || "root"}`} className="automation-json-tree">
        {value.map((item, index) => {
          const nextPath = appendPath(path, index);
          const isBranch = Boolean(item) && typeof item === "object";
          return (
            <li key={nextPath} id={`${idPrefix}-array-item-${nextPath}`} className="automation-json-tree__item">
              <button
                id={`${idPrefix}-select-${nextPath}`}
                type="button"
                className="automation-json-tree__select"
                onClick={() => onSelect(nextPath)}
              >
                <span className="automation-json-tree__path">[{index}]</span>
                <span className="automation-json-tree__value">{prettyValue(item)}</span>
              </button>
              {isBranch ? <JsonTree value={item} path={nextPath} onSelect={onSelect} idPrefix={idPrefix} /> : null}
            </li>
          );
        })}
      </ul>
    );
  }

  if (value && typeof value === "object") {
    return (
      <ul id={`${idPrefix}-object-${path || "root"}`} className="automation-json-tree">
        {Object.entries(value as Record<string, unknown>).map(([key, childValue]) => {
          const nextPath = appendPath(path, key);
          const isBranch = Boolean(childValue) && typeof childValue === "object";
          return (
            <li key={nextPath} id={`${idPrefix}-object-item-${nextPath}`} className="automation-json-tree__item">
              <button
                id={`${idPrefix}-select-${nextPath}`}
                type="button"
                className="automation-json-tree__select"
                onClick={() => onSelect(nextPath)}
              >
                <span className="automation-json-tree__path">{key}</span>
                <span className="automation-json-tree__value">{prettyValue(childValue)}</span>
              </button>
              {isBranch ? <JsonTree value={childValue} path={nextPath} onSelect={onSelect} idPrefix={idPrefix} /> : null}
            </li>
          );
        })}
      </ul>
    );
  }

  return null;
};

export const HttpStepForm = ({ draft, connectors, onChange, idPrefix = "add-step-http" }: Props) => {
  const [sampleResponse, setSampleResponse] = useState<unknown | null>(null);
  const [sampleError, setSampleError] = useState<string>("");
  const [sampleLoading, setSampleLoading] = useState(false);

  const responseMappings = useMemo(
    () => (draft.config.response_mappings || []).map((mapping) => ({ key: mapping.key || "", path: mapping.path || "" })),
    [draft.config.response_mappings]
  );

  const updateConfig = (nextConfig: AutomationStep["config"]) => onChange({ ...draft, config: nextConfig });

  const setMappings = (mappings: JsonMapping[]) => {
    updateConfig({ ...draft.config, response_mappings: mappings });
  };

  const handlePathSelect = (path: string) => {
    const pathSegments = path.split(".");
    const defaultKey = normalizeFieldKey(pathSegments[pathSegments.length - 1] || path);
    const exists = responseMappings.some((mapping) => mapping.path === path);
    if (exists) {
      return;
    }
    setMappings([...responseMappings, { key: defaultKey, path }]);
  };

  const loadSampleResponse = async () => {
    setSampleLoading(true);
    setSampleError("");
    try {
      const result = await requestJson("/api/v1/apis/test-delivery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "outgoing_scheduled",
          destination_url: draft.config.destination_url || "",
          http_method: draft.config.http_method || "POST",
          auth_type: draft.config.auth_type || "none",
          auth_config: null,
          payload_template: draft.config.payload_template || "{}",
          connector_id: draft.config.connector_id || null
        })
      });
      const parsed = typeof result.response_body === "string" ? JSON.parse(result.response_body) : result.response_body;
      setSampleResponse(parsed);
    } catch (error) {
      setSampleResponse(null);
      setSampleError(normalizeRequestError(error, "Unable to load a sample response.").message);
    } finally {
      setSampleLoading(false);
    }
  };

  return (
    <>
      <label id={`${idPrefix}-method-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-method-label`} className="automation-field__label">HTTP method</span>
        <select
          id={`${idPrefix}-method-input`}
          className="automation-native-select"
          value={draft.config.http_method || "POST"}
          onChange={(e) => updateConfig({ ...draft.config, http_method: e.target.value })}
        >
          {httpMethods.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </label>

      <label id={`${idPrefix}-connector-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-connector-label`} className="automation-field__label">Saved connector</span>
        <select
          id={`${idPrefix}-connector-input`}
          className="automation-native-select"
          value={draft.config.connector_id || ""}
          onChange={(e) => updateConfig({ ...draft.config, connector_id: e.target.value })}
        >
          <option value="">None</option>
          {connectors.map((c) => {
            const statusLabel = c.status ? `[${c.status}]` : "";
            const ownerLabel = c.owner ? ` (${c.owner})` : "";
            const displayLabel = `${c.name}${ownerLabel} ${statusLabel}`;
            return (
              <option key={c.id} value={c.id}>{displayLabel}</option>
            );
          })}
        </select>
      </label>

      {draft.config.connector_id && connectors.some((c) => c.id === draft.config.connector_id) && (
        <div id={`${idPrefix}-connector-info`} className="automation-field automation-field--full">
          {(() => {
            const selectedConnector = connectors.find((c) => c.id === draft.config.connector_id);
            if (!selectedConnector) return null;
            return (
              <div id={`${idPrefix}-connector-scopes-info`} className="automation-field automation-field__info">
                <div id={`${idPrefix}-scopes-label`} className="automation-field__label">Available APIs/Scopes</div>
                {selectedConnector.scopes && selectedConnector.scopes.length > 0 ? (
                  <ul id={`${idPrefix}-scopes-list`} className="automation-scopes-list">
                    {selectedConnector.scopes.map((scope) => (
                      <li key={scope} id={`${idPrefix}-scope-${scope.replace(/\//g, "-").replace(/\./g, "-")}`} className="automation-scopes-list__item">
                        {scope}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p id={`${idPrefix}-no-scopes-message`} className="automation-field__help-text">
                    No scopes authorized yet. Authorize this connector first.
                  </p>
                )}
              </div>
            );
          })()}
        </div>
      )}
      <label id={`${idPrefix}-url-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-url-label`} className="automation-field__label">Destination URL</span>
        <input
          id={`${idPrefix}-url-input`}
          className="automation-input"
          value={draft.config.destination_url || ""}
          onChange={(e) => updateConfig({ ...draft.config, destination_url: e.target.value })}
        />
      </label>

      <label id={`${idPrefix}-payload-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-payload-label`} className="automation-field__label">Payload template</span>
        <textarea
          id={`${idPrefix}-payload-input`}
          className="automation-textarea automation-textarea--code automation-code-input"
          rows={6}
          value={draft.config.payload_template || ""}
          onChange={(e) => updateConfig({ ...draft.config, payload_template: e.target.value })}
        />
      </label>

      <div id={`${idPrefix}-wait-toggle-field`} className="automation-switch-field automation-field--full">
        <div id={`${idPrefix}-wait-toggle-copy`} className="automation-switch-field__copy">
          <span id={`${idPrefix}-wait-toggle-label`} className="automation-field__label">Wait for response</span>
          <span id={`${idPrefix}-wait-toggle-description`} className="automation-switch-field__description">
            Blocking mode extracts fields before the next step. Background mode logs the response later.
          </span>
        </div>
        <label id={`${idPrefix}-wait-toggle-control`} className="automation-inline-checkbox">
          <input
            id={`${idPrefix}-wait-toggle-input`}
            type="checkbox"
            checked={draft.config.wait_for_response !== false}
            onChange={(e) => updateConfig({ ...draft.config, wait_for_response: e.target.checked })}
          />
          <span id={`${idPrefix}-wait-toggle-text`} className="automation-inline-checkbox__label">
            {draft.config.wait_for_response !== false ? "Blocking" : "Continue immediately"}
          </span>
        </label>
      </div>

      <details
        id={`${idPrefix}-response-mapping-section`}
        className="automation-advanced-section"
        open={Boolean(responseMappings.length || sampleResponse)}
      >
        <summary id={`${idPrefix}-response-mapping-summary`} className="automation-advanced-section__summary">
          Response mapping
        </summary>
        <div id={`${idPrefix}-response-mapping-content`} className="automation-advanced-section__content automation-http-mapping-panel">
          <div id={`${idPrefix}-response-actions`} className="automation-http-mapping-panel__actions">
            <button
              id={`${idPrefix}-sample-response-button`}
              type="button"
              className="button button--secondary"
              onClick={() => { void loadSampleResponse(); }}
              disabled={sampleLoading}
            >
              {sampleLoading ? "Loading sample…" : "Load sample response"}
            </button>
            <span id={`${idPrefix}-sample-response-hint`} className="automation-switch-field__description">
              Uses the current request settings to inspect a real JSON response.
            </span>
          </div>

          {sampleError ? <p id={`${idPrefix}-sample-response-error`} className="automation-form-feedback automation-form-feedback--error">{sampleError}</p> : null}

          {responseMappings.length > 0 ? (
            <div id={`${idPrefix}-mapping-table-wrapper`} className="automation-http-mapping-table-wrapper">
              <table id={`${idPrefix}-mapping-table`} className="automation-http-mapping-table">
                <thead>
                  <tr>
                    <th id={`${idPrefix}-mapping-key-header`}>Field key</th>
                    <th id={`${idPrefix}-mapping-path-header`}>JSON path</th>
                    <th id={`${idPrefix}-mapping-actions-header`}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {responseMappings.map((mapping, index) => (
                    <tr key={`${mapping.path}-${index}`} id={`${idPrefix}-mapping-row-${index}`}>
                      <td>
                        <input
                          id={`${idPrefix}-mapping-key-${index}`}
                          className="automation-input"
                          value={mapping.key}
                          onChange={(event) => {
                            const next = [...responseMappings];
                            next[index] = { ...next[index], key: event.target.value };
                            setMappings(next);
                          }}
                        />
                      </td>
                      <td>
                        <code id={`${idPrefix}-mapping-path-${index}`} className="automation-http-mapping-table__path">{mapping.path}</code>
                      </td>
                      <td>
                        <button
                          id={`${idPrefix}-mapping-remove-${index}`}
                          type="button"
                          className="button button--danger"
                          onClick={() => setMappings(responseMappings.filter((_, candidateIndex) => candidateIndex !== index))}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p id={`${idPrefix}-mapping-empty`} className="automation-switch-field__description">
              Load a sample response, then select fields from the JSON tree to create reusable outputs.
            </p>
          )}

          {sampleResponse ? (
            <div id={`${idPrefix}-json-tree-panel`} className="automation-http-json-panel">
              <div id={`${idPrefix}-json-tree-header`} className="automation-http-json-panel__header">
                <span id={`${idPrefix}-json-tree-title`} className="automation-field__label">Sample JSON</span>
                <span id={`${idPrefix}-json-tree-copy`} className="automation-switch-field__description">Click any node to add its JSON path.</span>
              </div>
              <JsonTree value={sampleResponse} path="" onSelect={handlePathSelect} idPrefix={idPrefix} />
            </div>
          ) : null}
        </div>
      </details>
    </>
  );
};
