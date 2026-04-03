import { useEffect, useState } from "react";
import { PROVIDER_SERVICE_LABELS, PROVIDER_SERVICE_ORDER } from "../constants";
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
  connectorsLoading?: boolean;
  connectorsError?: string | null;
  onRetryConnectors?: () => void;
};

const resolveInputValue = (value: unknown) => (value === null || value === undefined ? "" : String(value));

const getFieldDescription = (field: ConnectorActivitySchemaField) => [field.help_text, field.value_hint].filter(Boolean).join(" ");

const normalizeService = (service: string) => service.trim().toLowerCase();
const titleCase = (value: string) => value.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const getProviderDisplayName = (providerId: string) => {
  if (providerId === "github") {
    return "GitHub";
  }
  return titleCase(providerId);
};
const getServiceLabel = (providerId: string, service: string) =>
  PROVIDER_SERVICE_LABELS[providerId]?.[service] || titleCase(service);
const getOrderedServices = (providerId: string, activities: ConnectorActivityDefinition[]) => {
  const uniqueServices = Array.from(
    new Set(
      activities
        .map((activity) => normalizeService(activity.service || ""))
        .filter(Boolean),
    ),
  );

  return uniqueServices.sort((left, right) => {
    const providerOrder = PROVIDER_SERVICE_ORDER[providerId] || [];
    const leftIndex = providerOrder.indexOf(left);
    const rightIndex = providerOrder.indexOf(right);

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
  connectorsLoading = false,
  connectorsError = null,
  onRetryConnectors,
}: Props) => {
  const [showTokenPicker, setShowTokenPicker] = useState(false);
  const [selectedService, setSelectedService] = useState("");
  const selectedConnector = connectors.find((connector) => connector.id === (draft.config.connector_id || ""));
  const selectedConnectorProvider = (selectedConnector?.provider || "").toLowerCase();
  const providerActivities = selectedConnector ? activityCatalog.filter((activity) => activity.provider_id === selectedConnector.provider) : [];
  const selectedActivity = providerActivities.find((activity) => activity.activity_id === draft.config.activity_id);
  const providerServiceOptions = selectedConnectorProvider ? getOrderedServices(selectedConnectorProvider, providerActivities) : [];
  const requiresProviderServiceSelection = providerServiceOptions.length > 1;
  const visibleActivities = requiresProviderServiceSelection
    ? providerActivities.filter((activity) => normalizeService(activity.service || "") === selectedService)
    : providerActivities;
  const missingScopes = selectedConnector && selectedActivity
    ? selectedActivity.required_scopes.filter((scope) => !(selectedConnector.scopes || []).includes(scope))
    : [];

  const updateConfig = (nextConfig: AutomationStep["config"]) => onChange({ ...draft, config: nextConfig });
  const connectorActivitiesByProvider = activityCatalog.reduce<Record<string, ConnectorActivityDefinition[]>>((groups, activity) => {
    groups[activity.provider_id] = groups[activity.provider_id] || [];
    groups[activity.provider_id].push(activity);
    return groups;
  }, {});
  const getConnectorCompatibility = (connector: ConnectorRecord) => {
    const providerId = String(connector.provider || "");
    const providerActivities = connectorActivitiesByProvider[providerId] || [];
    if (providerActivities.length === 0) {
      return {
        compatible: false,
        reason: "No connector actions available for this provider yet.",
      };
    }

    const connectorScopes = new Set((connector.scopes || []).map((scope) => String(scope).trim()));
    const hasCompatibleActivity = providerActivities.some((activity) =>
      activity.required_scopes.every((scope) => connectorScopes.has(scope)),
    );
    if (!hasCompatibleActivity) {
      return {
        compatible: false,
        reason: "Missing required scopes for available connector actions.",
      };
    }

    return { compatible: true, reason: "" };
  };

  useEffect(() => {
    if (!selectedConnectorProvider) {
      setSelectedService("");
      return;
    }

    const selectedActivityService = normalizeService(selectedActivity?.service || "");
    if (selectedActivityService && providerServiceOptions.includes(selectedActivityService)) {
      setSelectedService(selectedActivityService);
      return;
    }

    if (providerServiceOptions.length === 1) {
      setSelectedService(providerServiceOptions[0]);
      return;
    }

    setSelectedService((current) => (providerServiceOptions.includes(current) ? current : ""));
  }, [selectedActivity?.service, selectedConnectorProvider, providerServiceOptions]);

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
          disabled={connectorsLoading}
          aria-busy={connectorsLoading}
          aria-invalid={Boolean(connectorsError)}
          aria-describedby={`${idPrefix}-connector-help ${idPrefix}-connector-state`}
          onChange={(event) => updateConfig({ ...draft.config, connector_id: event.target.value, activity_id: "", activity_inputs: {} })}
        >
          <option value="">
            {connectorsLoading
              ? "Loading connectors..."
              : connectorsError
                ? "Unable to load connectors"
                : "Choose a connector"}
          </option>
          {connectors.map((connector) => {
            const compatibility = getConnectorCompatibility(connector);
            return (
              <option
                key={connector.id}
                value={connector.id}
                disabled={!compatibility.compatible}
                title={compatibility.compatible ? "" : compatibility.reason}
              >
                {`${connector.name} (${connector.provider || "provider"})${connector.status ? ` [${connector.status}]` : ""}${compatibility.compatible ? "" : ` - Unavailable: ${compatibility.reason}`}`}
              </option>
            );
          })}
        </select>
        <span id={`${idPrefix}-connector-help`} className="automation-field__help-text">
          Disabled connectors are unavailable for this step because scopes or provider activities do not match.
        </span>
        <div id={`${idPrefix}-connector-state`} className="automation-switch-field__description" aria-live="polite">
          {connectorsLoading ? "Loading saved connectors..." : null}
          {!connectorsLoading && !connectorsError && connectors.length === 0 ? "No saved connectors found. Create a connector in Settings to continue." : null}
        </div>
        {connectorsError ? (
          <div id={`${idPrefix}-connector-error`} className="automation-field__help-text" role="alert">
            {`Unable to load saved connectors: ${connectorsError}`}
            {onRetryConnectors ? (
              <button
                id={`${idPrefix}-connector-retry`}
                type="button"
                className="button button--outline button--small"
                onClick={() => onRetryConnectors()}
              >
                Retry
              </button>
            ) : null}
          </div>
        ) : null}
      </label>

      {providerServiceOptions.length > 0 ? (
        <label id={`${idPrefix}-service-field`} className="automation-field automation-field--full automation-field--inline-label">
          <span id={`${idPrefix}-service-label`} className="automation-field__label">
            {selectedConnectorProvider === "google" ? "Google app" : `${getProviderDisplayName(selectedConnectorProvider)} area`}
          </span>
          <select
            id={`${idPrefix}-service-input`}
            className="automation-native-select"
            value={selectedService}
            onChange={(event) => handleServiceChange(event.target.value)}
          >
            <option value="">
              {requiresProviderServiceSelection
                ? (selectedConnectorProvider === "google" ? "Choose a Google app" : `Choose a ${getProviderDisplayName(selectedConnectorProvider)} area`)
                : "Select an area"}
            </option>
            {providerServiceOptions.map((service) => (
              <option key={service} value={service}>{getServiceLabel(selectedConnectorProvider, service)}</option>
            ))}
          </select>
        </label>
      ) : null}

      <label id={`${idPrefix}-activity-field`} className="automation-field automation-field--full automation-field--inline-label">
        <span id={`${idPrefix}-activity-label`} className="automation-field__label">Connector action</span>
        <select
          id={`${idPrefix}-activity-input`}
          className="automation-native-select"
          value={draft.config.activity_id || ""}
          disabled={!selectedConnector || (requiresProviderServiceSelection && !selectedService)}
          onChange={(event) => updateConfig({ ...draft.config, activity_id: event.target.value, activity_inputs: {} })}
        >
          <option value="">
            {!selectedConnector
              ? "Select a connector first"
              : requiresProviderServiceSelection && !selectedService
                ? (selectedConnectorProvider === "google" ? "Choose a Google app first" : `Choose a ${getProviderDisplayName(selectedConnectorProvider)} area first`)
                : "Choose an action"}
          </option>
          {visibleActivities.map((activity) => (
            <option key={activity.activity_id} value={activity.activity_id}>{`${getServiceLabel(selectedConnectorProvider, normalizeService(activity.service || ""))} · ${activity.operation_type.toUpperCase()} · ${activity.label}`}</option>
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
