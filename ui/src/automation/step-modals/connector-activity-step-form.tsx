import type { AutomationStep, ConnectorActivityDefinition, ConnectorRecord } from "../types";

type Props = {
  draft: AutomationStep;
  connectors: ConnectorRecord[];
  activityCatalog: ConnectorActivityDefinition[];
  onChange: (step: AutomationStep) => void;
  idPrefix?: string;
};

const resolveInputValue = (value: unknown) => (value === null || value === undefined ? "" : String(value));

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

      <label id={`${idPrefix}-activity-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-activity-label`} className="automation-field__label">Prebuilt activity</span>
        <select
          id={`${idPrefix}-activity-input`}
          className="automation-native-select"
          value={draft.config.activity_id || ""}
          disabled={!selectedConnector}
          onChange={(event) => updateConfig({ ...draft.config, activity_id: event.target.value, activity_inputs: {} })}
        >
          <option value="">{selectedConnector ? "Choose an activity" : "Select a connector first"}</option>
          {providerActivities.map((activity) => (
            <option key={activity.activity_id} value={activity.activity_id}>{activity.label}</option>
          ))}
        </select>
      </label>

      {selectedActivity ? (
        <div id={`${idPrefix}-activity-summary`} className="automation-field automation-field--full automation-field__info">
          <div id={`${idPrefix}-activity-description`} className="automation-switch-field__description">{selectedActivity.description}</div>
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
        const nextInputs = { ...(draft.config.activity_inputs || {}) };
        const setFieldValue = (nextValue: string) => {
          nextInputs[field.key] = field.type === "integer" && nextValue ? Number(nextValue) : nextValue;
          updateConfig({ ...draft.config, activity_inputs: nextInputs });
        };

        return (
          <label key={field.key} id={`${fieldId}-field`} className="automation-field automation-field--full automation-field--inline-label">
            <span id={`${fieldId}-label`} className="automation-field__label">{field.label}</span>
            {field.type === "select" ? (
              <select id={fieldId} className="automation-native-select" value={resolveInputValue(value || field.default)} onChange={(event) => setFieldValue(event.target.value)}>
                {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            ) : (
              <input
                id={fieldId}
                className="automation-input"
                type={field.type === "integer" ? "number" : "text"}
                required={field.required}
                placeholder={field.placeholder || undefined}
                value={resolveInputValue(value ?? field.default)}
                onChange={(event) => setFieldValue(event.target.value)}
              />
            )}
          </label>
        );
      })}

      {selectedActivity ? (
        <div id={`${idPrefix}-outputs`} className="automation-field automation-field--full automation-field__info">
          <div id={`${idPrefix}-outputs-label`} className="automation-field__label">Known outputs</div>
          <ul id={`${idPrefix}-outputs-list`} className="automation-scopes-list">
            {selectedActivity.output_schema.map((field) => (
              <li key={field.key} id={`${idPrefix}-output-${field.key}`} className="automation-scopes-list__item">
                {field.key} · {field.type}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
};
