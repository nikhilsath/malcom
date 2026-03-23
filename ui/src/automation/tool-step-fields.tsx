import type { AutomationStep, ToolManifestEntry } from "./types";

type Props = {
  idPrefix: string;
  step: AutomationStep;
  toolsManifest: ToolManifestEntry[];
  onChange: (step: AutomationStep) => void;
};

const smtpTemplateHints = [
  "{{payload.mail_from}}",
  "{{payload.subject}}",
  "{{payload.body}}",
  "{{payload.received_at}}",
  "{{payload.recipients}}",
  "{{payload.smtp.subject}}",
];

export const ToolStepFields = ({ idPrefix, step, toolsManifest, onChange }: Props) => {
  const id = (suffix: string) => `${idPrefix}-${suffix}`;
  const idSegment = (value: string) => value.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "value";
  const selectedTool = toolsManifest.find((tool) => tool.id === step.config.tool_id);
  const toolInputs = step.config.tool_inputs || {};

  const updateInput = (key: string, value: string) =>
    onChange({
      ...step,
      config: {
        ...step.config,
        tool_inputs: { ...toolInputs, [key]: value }
      }
    });

  return (
    <>
      <div id={`${idPrefix}-tool-id-field`} className="automation-field automation-field--full">
        <span id={`${idPrefix}-tool-id-label`} className="automation-field__label">Tool</span>
        <select
          id={id("tool-id-input")}
          className="automation-native-select"
          value={step.config.tool_id || ""}
          onChange={(event) =>
            onChange({
              ...step,
              config: { ...step.config, tool_id: event.target.value, tool_inputs: {} }
            })
          }
        >
          <option id={id("tool-id-option-empty")} value="">Select a tool…</option>
          {toolsManifest.map((tool) => (
            <option key={tool.id} id={id(`tool-id-option-${idSegment(tool.id)}`)} value={tool.id}>
              {tool.name}
            </option>
          ))}
        </select>
      </div>

      {selectedTool?.id === "smtp" ? (
        <div id={`${idPrefix}-smtp-hint`} className="automation-switch-field__description">
          Supports template variables in From, To, Subject, and Body. Common inbound email fields: {smtpTemplateHints.join(" · ")}
        </div>
      ) : null}

      {selectedTool && selectedTool.inputs.length > 0 ? (
        <>
          {selectedTool.inputs.map((field) => {
            const fieldId = `${idPrefix}-tool-input-${field.key}`;
            return (
              <label
                key={field.key}
                id={`${fieldId}-field`}
                className="automation-field automation-field--full"
              >
                <span id={`${fieldId}-label`} className="automation-field__label">
                  {field.label}{field.required ? " *" : ""}
                </span>
                {field.type === "text" ? (
                  <textarea
                    id={`${fieldId}-input`}
                    className="automation-textarea"
                    rows={field.key === "body" ? 6 : 4}
                    value={toolInputs[field.key] || ""}
                    onChange={(event) => updateInput(field.key, event.target.value)}
                  />
                ) : field.type === "select" ? (
                  <select
                    id={`${fieldId}-input`}
                    className="automation-native-select"
                    value={toolInputs[field.key] || ""}
                    onChange={(event) => updateInput(field.key, event.target.value)}
                  >
                    <option id={`${fieldId}-option-empty`} value="">Select…</option>
                    {(field.options || []).map((option) => (
                      <option key={option} id={`${fieldId}-option-${idSegment(option)}`} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`${fieldId}-input`}
                    className="automation-input"
                    type={field.type === "number" ? "number" : field.key === "relay_password" ? "password" : "text"}
                    value={toolInputs[field.key] || ""}
                    onChange={(event) => updateInput(field.key, event.target.value)}
                  />
                )}
              </label>
            );
          })}
        </>
      ) : null}

      {selectedTool && selectedTool.outputs.length > 0 ? (
        <div id={`${idPrefix}-tool-outputs-panel`} className="automation-tool-outputs">
          <span id={`${idPrefix}-tool-outputs-label`} className="automation-field__label">Available outputs</span>
          <ul id={`${idPrefix}-tool-outputs-list`} className="automation-tool-outputs__list">
            {selectedTool.outputs.map((output) => {
              const outputId = `${idPrefix}-tool-output-${output.key}`;
              return (
                <li key={output.key} id={outputId} className="automation-tool-outputs__item">
                  <code id={`${outputId}-key`} className="automation-tool-outputs__key">
                    {"{{steps.<step_name>." + output.key + "}}"}
                  </code>
                  <span id={`${outputId}-description`} className="automation-tool-outputs__desc">{output.label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </>
  );
};
