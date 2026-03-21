import type { AutomationStep, ConnectorRecord } from "../types";

type Props = {
  draft: AutomationStep;
  connectors: ConnectorRecord[];
  onChange: (step: AutomationStep) => void;
};

const httpMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"];

export const HttpStepForm = ({ draft, connectors, onChange }: Props) => (
  <>
    <label id="add-step-http-method-field" className="automation-field automation-field--full automation-field--inline-label">
      <span id="add-step-http-method-label" className="automation-field__label">HTTP method</span>
      <select
        id="add-step-http-method-input"
        className="automation-native-select"
        value={draft.config.http_method || "POST"}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, http_method: e.target.value } })
        }
      >
        {httpMethods.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    </label>

    <label id="add-step-http-connector-field" className="automation-field automation-field--full automation-field--inline-label">
      <span id="add-step-http-connector-label" className="automation-field__label">Saved connector</span>
      <select
        id="add-step-http-connector-input"
        className="automation-native-select"
        value={draft.config.connector_id || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, connector_id: e.target.value } })
        }
      >
        <option value="">None</option>
        {connectors.map((c) => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
    </label>

    <label id="add-step-http-url-field" className="automation-field automation-field--full automation-field--inline-label">
      <span id="add-step-http-url-label" className="automation-field__label">Destination URL</span>
      <input
        id="add-step-http-url-input"
        className="automation-input"
        value={draft.config.destination_url || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, destination_url: e.target.value } })
        }
      />
    </label>

    <label id="add-step-http-payload-field" className="automation-field automation-field--full automation-field--inline-label">
      <span id="add-step-http-payload-label" className="automation-field__label">Payload template</span>
      <textarea
        id="add-step-http-payload-input"
        className="automation-textarea automation-textarea--code"
        rows={6}
        value={draft.config.payload_template || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, payload_template: e.target.value } })
        }
      />
    </label>
  </>
);
