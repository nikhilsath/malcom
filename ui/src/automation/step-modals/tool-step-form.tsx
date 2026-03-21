import type { AutomationStep, ToolManifestEntry } from "../types";

type Props = {
  draft: AutomationStep;
  toolsManifest: ToolManifestEntry[];
  onChange: (step: AutomationStep) => void;
};

export const ToolStepForm = ({ draft, toolsManifest, onChange }: Props) => {
  const selectedTool = toolsManifest.find((t) => t.id === draft.config.tool_id);
  const toolInputs = draft.config.tool_inputs || {};

  const updateInput = (key: string, value: string) =>
    onChange({
      ...draft,
      config: {
        ...draft.config,
        tool_inputs: { ...toolInputs, [key]: value }
      }
    });

  return (
    <>
      <div id="add-step-tool-id-field" className="automation-field automation-field--full">
        <span id="add-step-tool-id-label" className="automation-field__label">Tool</span>
        <select
          id="add-step-tool-id-input"
          className="automation-native-select"
          value={draft.config.tool_id || ""}
          onChange={(e) =>
            onChange({
              ...draft,
              config: { ...draft.config, tool_id: e.target.value, tool_inputs: {} }
            })
          }
        >
          <option value="">Select a tool…</option>
          {toolsManifest.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </div>

      {selectedTool && selectedTool.inputs.length > 0 ? (
        <>
          {selectedTool.inputs.map((field) => {
            const fieldId = `add-step-tool-input-${field.key}`;
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
                    rows={4}
                    value={toolInputs[field.key] || ""}
                    onChange={(e) => updateInput(field.key, e.target.value)}
                  />
                ) : field.type === "select" ? (
                  <select
                    id={`${fieldId}-input`}
                    className="automation-native-select"
                    value={toolInputs[field.key] || ""}
                    onChange={(e) => updateInput(field.key, e.target.value)}
                  >
                    <option value="">Select…</option>
                    {(field.options || []).map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`${fieldId}-input`}
                    className="automation-input"
                    type={field.type === "number" ? "number" : "text"}
                    value={toolInputs[field.key] || ""}
                    onChange={(e) => updateInput(field.key, e.target.value)}
                  />
                )}
              </label>
            );
          })}
        </>
      ) : null}

      {selectedTool && selectedTool.outputs.length > 0 ? (
        <div id="add-step-tool-outputs-panel" className="automation-tool-outputs">
          <span id="add-step-tool-outputs-label" className="automation-field__label">Available outputs</span>
          <ul id="add-step-tool-outputs-list" className="automation-tool-outputs__list">
            {selectedTool.outputs.map((out) => (
              <li key={out.key} id={`add-step-tool-output-${out.key}`} className="automation-tool-outputs__item">
                <code className="automation-tool-outputs__key">
                  {"{{steps.<step_name>." + out.key + "}}"}
                </code>
                <span className="automation-tool-outputs__desc">{out.label}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
};
