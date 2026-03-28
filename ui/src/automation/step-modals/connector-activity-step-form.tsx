import { useEffect, useState } from "react";
import { TokenPicker } from "../token-picker";
import type { DataFlowToken } from "../data-flow";
import type { AutomationStep, ConnectorActivityDefinition, ConnectorActivitySchemaField, ConnectorRecord } from "../types";

type Props = {
  draft: AutomationStep;
  connectors: ConnectorRecord[];
  activityCatalog: ConnectorActivityDefinition[];
  onChange: (step: AutomationStep) => void;
  dataFlowTokens?: DataFlowToken[];
  idPrefix?: string;
};

const resolveInputValue = (value: unknown) => (value === null || value === undefined ? "" : String(value));

const getFieldDescription = (field: ConnectorActivitySchemaField) => [field.help_text, field.value_hint].filter(Boolean).join(" ");
const GOOGLE_SERVICE_ORDER = ["gmail", "drive", "calendar", "sheets"];
const GOOGLE_SERVICE_LABELS: Record<string, string> = {
  gmail: "Gmail",
  drive: "Drive",
  calendar: "Calendar",
  sheets: "Sheets",
};

const normalizeService = (service: string) => service.trim().toLowerCase();
const getServiceLabel = (service: string) => GOOGLE_SERVICE_LABELS[service] || service.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const getOrderedServices = (activities: ConnectorActivityDefinition[]) => {
  const uniqueServices = Array.from(
    new Set(
      activities
        .map((activity) => normalizeService(activity.service || ""))
        .filter(Boolean),
    ),
  );

  return uniqueServices.sort((left, right) => {
    const leftIndex = GOOGLE_SERVICE_ORDER.indexOf(left);
    const rightIndex = GOOGLE_SERVICE_ORDER.indexOf(right);

    if (leftIndex === -1 && rightIndex === -1) {
      return left.localeCompare(right);
    }
    if (leftIndex === -1) {
      return 1;
    }
    if (rightIndex === -1) {
      return -1;
    }
    return leftIndex - rightIndex;
  });
};

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
  dataFlowTokens = [],
  idPrefix = "add-step-connector-activity",
}: Props) => {
  const [showTokenPicker, setShowTokenPicker] = useState(false);
  const [selectedService, setSelectedService] = useState("");
  const selectedConnector = connectors.find((connector) => connector.id === (draft.config.connector_id || ""));
  const selectedConnectorProvider = (selectedConnector?.provider || "").toLowerCase();
  const providerActivities = selectedConnector ? activityCatalog.filter((activity) => activity.provider_id === selectedConnector.provider) : [];
  const selectedActivity = providerActivities.find((activity) => activity.activity_id === draft.config.activity_id);
  const googleServiceOptions = selectedConnectorProvider === "google" ? getOrderedServices(providerActivities) : [];
  const requiresGoogleServiceSelection = selectedConnectorProvider === "google" && googleServiceOptions.length > 1;
  const visibleActivities = requiresGoogleServiceSelection
    ? providerActivities.filter((activity) => normalizeService(activity.service || "") === selectedService)
    : providerActivities;
  const missingScopes = selectedConnector && selectedActivity
    ? selectedActivity.required_scopes.filter((scope) => !(selectedConnector.scopes || []).includes(scope))
    : [];
  const groupedActivities = visibleActivities.reduce<Record<string, ConnectorActivityDefinition[]>>((groups, activity) => {
    const key = `${normalizeService(activity.service || "")}:${activity.operation_type}`;
    groups[key] = groups[key] || [];
    groups[key].push(activity);
    return groups;
  }, {});

  const updateConfig = (nextConfig: AutomationStep["config"]) => onChange({ ...draft, config: nextConfig });

  useEffect(() => {
    if (selectedConnectorProvider !== "google") {
      setSelectedService("");
      return;
    }

    const selectedActivityService = normalizeService(selectedActivity?.service || "");
    if (selectedActivityService && googleServiceOptions.includes(selectedActivityService)) {
      setSelectedService(selectedActivityService);
      return;
    }

    if (googleServiceOptions.length === 1) {
      setSelectedService(googleServiceOptions[0]);
      return;
    }

    setSelectedService((current) => (googleServiceOptions.includes(current) ? current : ""));
  }, [selectedActivity?.service, selectedConnectorProvider, googleServiceOptions]);

  const handleServiceChange = (nextService: string) => {
    setSelectedService(nextService);
    if (!draft.config.activity_id) {
      return;
    }

    const matchesSelectedService = providerActivities.some(
      (activity) => activity.activity_id === draft.config.activity_id && normalizeService(activity.service || "") === nextService,
    );

    if (!matchesSelectedService) {
      updateConfig({ ...draft.config, activity_id: "", activity_inputs: {} });
    }
  };

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

      {selectedConnectorProvider === "google" && googleServiceOptions.length > 0 ? (
        <label id={`${idPrefix}-service-field`} className="automation-field automation-field--full automation-field--inline-label">
          <span id={`${idPrefix}-service-label`} className="automation-field__label">Google app</span>
          <select
            id={`${idPrefix}-service-input`}
            className="automation-native-select"
            value={selectedService}
            onChange={(event) => handleServiceChange(event.target.value)}
          >
            <option value="">{requiresGoogleServiceSelection ? "Choose a Google app" : "Select an app"}</option>
            {googleServiceOptions.map((service) => (
              <option key={service} value={service}>{getServiceLabel(service)}</option>
            ))}
          </select>
        </label>
      ) : null}

      <div id={`${idPrefix}-activity-picker`} className="automation-field automation-field--full automation-field__info">
        <div id={`${idPrefix}-activity-picker-label`} className="automation-field__label">Connector actions</div>
        {!selectedConnector ? (
          <div id={`${idPrefix}-activity-picker-empty`} className="automation-switch-field__description">Select a connector to view its supported actions.</div>
        ) : requiresGoogleServiceSelection && !selectedService ? (
          <div id={`${idPrefix}-activity-picker-empty`} className="automation-switch-field__description">Choose a Google app to view its supported actions.</div>
        ) : visibleActivities.length === 0 ? (
          <div id={`${idPrefix}-activity-picker-empty`} className="automation-switch-field__description">No connector actions are available for this selection.</div>
        ) : (
          <div id={`${idPrefix}-activity-groups`} className="automation-connector-activity-groups">
            {Object.entries(groupedActivities).map(([groupKey, activities]) => {
              const [service, operationType] = groupKey.split(":");
              return (
                <section key={groupKey} id={`${idPrefix}-group-${groupKey.replace(/[:]/g, "-")}`} className="automation-connector-activity-group">
                  <div id={`${idPrefix}-group-header-${groupKey.replace(/[:]/g, "-")}`} className="automation-connector-activity-group__header">
                    <span className="automation-field__label">{getServiceLabel(service)}</span>
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
          disabled={!selectedConnector || (requiresGoogleServiceSelection && !selectedService)}
          onChange={(event) => updateConfig({ ...draft.config, activity_id: event.target.value, activity_inputs: {} })}
        >
          <option value="">
            {!selectedConnector
              ? "Select a connector first"
              : requiresGoogleServiceSelection && !selectedService
                ? "Choose a Google app first"
                : "Choose an action"}
          </option>
          {visibleActivities.map((activity) => (
            <option key={activity.activity_id} value={activity.activity_id}>{`${getServiceLabel(normalizeService(activity.service || ""))} · ${activity.operation_type.toUpperCase()} · ${activity.label}`}</option>
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
        const supportsTokenInsertion = ["string", "text", "textarea", "json"].includes(field.type);

        return (
          <label key={field.key} id={`${fieldId}-field`} className="automation-field automation-field--full automation-field--inline-label">
            <span id={`${fieldId}-label`} className="automation-field__label">{field.label}</span>
            {renderFieldInput(field, fieldId, value, setFieldValue)}
            {getFieldDescription(field) ? <span id={`${fieldId}-help`} className="automation-field__help-text">{getFieldDescription(field)}</span> : null}
            {supportsTokenInsertion && dataFlowTokens.length > 0 && (
              <button
                id={`${fieldId}-token-button`}
                type="button"
                className="button button--outline button--small"
                onClick={() => setShowTokenPicker(!showTokenPicker)}
              >
                {showTokenPicker ? "Hide available data" : "Show available data"}
              </button>
            )}
          </label>
        );
      })}

      {showTokenPicker && dataFlowTokens.length > 0 && selectedActivity ? (
        <div id={`${idPrefix}-available-data-panel`} className="automation-field automation-field--full automation-available-data-panel">
          <div id={`${idPrefix}-available-data-title`} className="automation-field__label">Available step outputs</div>
          <TokenPicker
            idPrefix={`${idPrefix}-token-picker`}
            tokens={dataFlowTokens}
            onInsert={(token) => {
              // Find the last focused text-like input and insert the token
              const inputs = document.querySelectorAll(`[id^="${idPrefix}-input-"]`);
              const lastInput = inputs[inputs.length - 1] as HTMLTextAreaElement | HTMLInputElement | null;
              if (lastInput && ["string", "text", "textarea", "json"].includes((lastInput as any).type || lastInput.tagName)) {
                const currentValue = lastInput.value || "";
                lastInput.value = currentValue + token;
                lastInput.dispatchEvent(new Event("change", { bubbles: true }));
              }
            }}
            description="Insert any available step output as a variable reference into the selected field."
          />
        </div>
      ) : null}

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
