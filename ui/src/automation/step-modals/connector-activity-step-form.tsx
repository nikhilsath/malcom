import type { AutomationStep, ConnectorActivityDefinition, ConnectorActivitySchemaField, ConnectorRecord } from "../types";

type Props = {
  draft: AutomationStep;
  connectors: ConnectorRecord[];
  activityCatalog: ConnectorActivityDefinition[];
  onChange: (step: AutomationStep) => void;
  idPrefix?: string;
};

const resolveInputValue = (value: unknown) => (value === null || value === undefined ? "" : String(value));

const getFieldDescription = (field: ConnectorActivitySchemaField) => [field.help_text, field.value_hint].filter(Boolean).join(" ");

const renderFieldInput = (
  field: ConnectorActivitySchemaField,
  fieldId: string,
  value: unknown,
  setFieldValue: (nextValue: string | boolean) => void,
) => {
  if (field.type === "select") {
    return (
      <select id={fieldId} className="automation-native-select" value={resolveInputValue(value ?? field.default)} onChange={(event) => setFieldValue(event.target.value)}>
        {(field.options || []).map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    );
  }

  if (field.type === "textarea" || field.type === "json") {
    return (
      <textarea
        id={fieldId}
        className="automation-textarea"
        required={field.required}
        placeholder={field.placeholder || undefined}
        value={resolveInputValue(value ?? field.default)}
        onChange={(event) => setFieldValue(event.target.value)}
        rows={field.type === "json" ? 6 : 5}
      />
    );
  }

  if (field.type === "boolean") {
    return (
      <input
        id={fieldId}
        type="checkbox"
        checked={Boolean(value ?? field.default)}
        onChange={(event) => setFieldValue(event.target.checked)}
      />
    );
  }

  return (
    <input
      id={fieldId}
      className="automation-input"
      type={field.type === "integer" ? "number" : "text"}
      required={field.required}
      placeholder={field.placeholder || undefined}
      value={resolveInputValue(value ?? field.default)}
      onChange={(event) => setFieldValue(event.target.value)}
    />
  );
};

export const ConnectorActivityStepForm = ({
  draft,
  connectors,
  activityCatalog,
  onChange,
  idPrefix = "add-step-connector-activity",
}: Props) => {
  const selectedConnector = connectors.find((connector) => connector.id === (draft.config.connector_id || ""));
  const providerActivities = selectedConnector ? activityCatalog.filter((activity) => activity.provider_id === selectedConnector.provider) : [];
  const selectedActivity = providerActivities.find((activity) => activity.activity_id === draft.config.activity_id);
  const missingScopes = selectedConnector && selectedActivity
    ? selectedActivity.required_scopes.filter((scope) => !(selectedConnector.scopes || []).includes(scope))
    : [];
  const groupedActivities = providerActivities.reduce<Record<string, ConnectorActivityDefinition[]>>((groups, activity) => {
    const key = `${activity.service}:${activity.operation_type}`;
    groups[key] = groups[key] || [];
    groups[key].push(activity);
    return groups;
  }, {});

  const updateConfig = (nextConfig: AutomationStep["config"]) => onChange({ ...draft, config: nextConfig });

  return (
    <>
      <label id={`${idPrefix}-connector-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-connector-label`} className="automation-field__label">Saved connector</span>
        <select
          id={`${idPrefix}-connector-input`}
          className="automation-native-select"
          value={draft.config.connector_id || ""}
          onChange={(event) => updateConfig({ ...draft.config, connector_id: event.target.value, activity_id: "", activity_inputs: {} })}
        >
          <option value="">Choose a connector</option>
          {connectors.map((connector) => (
            <option key={connector.id} value={connector.id}>{connector.name}</option>
          ))}
        </select>
      </label>

      <div id={`${idPrefix}-activity-picker`} className="automation-field automation-field--full automation-field__info">
        <div id={`${idPrefix}-activity-picker-label`} className="automation-field__label">Connector actions</div>
        {!selectedConnector ? (
          <div id={`${idPrefix}-activity-picker-empty`} className="automation-switch-field__description">Select a connector to view its supported actions.</div>
        ) : (
          <div id={`${idPrefix}-activity-groups`} className="automation-connector-activity-groups">
            {Object.entries(groupedActivities).map(([groupKey, activities]) => {
              const [service, operationType] = groupKey.split(":");
              return (
                <section key={groupKey} id={`${idPrefix}-group-${groupKey.replace(/[:]/g, "-")}`} className="automation-connector-activity-group">
                  <div id={`${idPrefix}-group-header-${groupKey.replace(/[:]/g, "-")}`} className="automation-connector-activity-group__header">
                    <span className="automation-field__label">{service.toUpperCase()}</span>
                    <span className={`automation-run-badge automation-run-badge--${operationType === "write" ? "error" : "neutral"}`}>{operationType.toUpperCase()}</span>
                  </div>
                  <div className="automation-connector-activity-list">
                    {activities.map((activity) => {
                      const active = draft.config.activity_id === activity.activity_id;
                      return (
                        <button
                          key={activity.activity_id}
                          id={`${idPrefix}-activity-card-${activity.activity_id}`}
                          type="button"
                          className={`add-step-type-card automation-connector-activity-card${active ? " automation-connector-activity-card--selected" : ""}`}
                          onClick={() => updateConfig({ ...draft.config, activity_id: activity.activity_id, activity_inputs: {} })}
                        >
                          <span className="add-step-type-card__label">{activity.label}</span>
                          <span className="add-step-type-card__description">{activity.description}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </div>

      <label id={`${idPrefix}-activity-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-activity-label`} className="automation-field__label">Selected action</span>
        <select
          id={`${idPrefix}-activity-input`}
          className="automation-native-select"
          value={draft.config.activity_id || ""}
          disabled={!selectedConnector}
          onChange={(event) => updateConfig({ ...draft.config, activity_id: event.target.value, activity_inputs: {} })}
        >
          <option value="">{selectedConnector ? "Choose an action" : "Select a connector first"}</option>
          {providerActivities.map((activity) => (
            <option key={activity.activity_id} value={activity.activity_id}>{`${activity.service.toUpperCase()} · ${activity.operation_type.toUpperCase()} · ${activity.label}`}</option>
          ))}
        </select>
      </label>

      {selectedActivity ? (
        <div id={`${idPrefix}-activity-summary`} className="automation-field automation-field--full automation-field__info">
          <div id={`${idPrefix}-activity-description`} className="automation-switch-field__description">{selectedActivity.description}</div>
          <div id={`${idPrefix}-activity-mode`} className="automation-switch-field__description">{selectedActivity.service.toUpperCase()} · {selectedActivity.operation_type.toUpperCase()} action</div>
          {missingScopes.length > 0 ? (
            <div id={`${idPrefix}-missing-scopes`} className="automation-field__help-text">
              Missing scopes: {missingScopes.join(", ")}
            </div>
          ) : (
            <div id={`${idPrefix}-required-scopes`} className="automation-switch-field__description">
              Required scopes: {selectedActivity.required_scopes.join(", ") || "None"}
            </div>
          )}
        </div>
      ) : null}

      {selectedActivity?.input_schema.map((field) => {
        const value = draft.config.activity_inputs?.[field.key];
        const fieldId = `${idPrefix}-input-${field.key}`;
        const setFieldValue = (nextValue: string | boolean) => {
          const nextInputs = { ...(draft.config.activity_inputs || {}) } as Record<string, string | number | boolean>;
          nextInputs[field.key] = field.type === "integer" && typeof nextValue === "string" && nextValue ? Number(nextValue) : nextValue;
          updateConfig({ ...draft.config, activity_inputs: nextInputs });
        };

        return (
          <label key={field.key} id={`${fieldId}-field`} className="automation-field automation-field--full automation-field--inline-label">
            <span id={`${fieldId}-label`} className="automation-field__label">{field.label}</span>
            {renderFieldInput(field, fieldId, value, setFieldValue)}
            {getFieldDescription(field) ? <span id={`${fieldId}-help`} className="automation-field__help-text">{getFieldDescription(field)}</span> : null}
          </label>
        );
      })}

      {selectedActivity ? (
        <div id={`${idPrefix}-outputs`} className="automation-field automation-field--full automation-field__info">
          <div id={`${idPrefix}-outputs-label`} className="automation-field__label">Expected outputs</div>
          <ul id={`${idPrefix}-outputs-list`} className="automation-scopes-list">
            {selectedActivity.output_schema.map((field) => (
              <li key={field.key} id={`${idPrefix}-output-${field.key}`} className="automation-scopes-list__item">
                <strong>{field.key}</strong> · {field.type}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
};
