import type { AutomationStep } from "../types";

type ScriptOption = { id: string; name: string };

type Props = {
  draft: AutomationStep;
  scripts?: ScriptOption[];
  onChange: (step: AutomationStep) => void;
};

export const ScriptStepForm = ({ draft, scripts, onChange }: Props) => (
  <label id="add-step-script-id-field" className="automation-field automation-field--full">
    <span id="add-step-script-id-label" className="automation-field__label">Script</span>
    {scripts && scripts.length > 0 ? (
      <select
        id="add-step-script-id-input"
        className="automation-native-select"
        value={draft.config.script_id || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, script_id: e.target.value } })
        }
      >
        <option value="">Select a script…</option>
        {scripts.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>
    ) : (
      <input
        id="add-step-script-id-input"
        className="automation-input"
        placeholder="Enter script id"
        value={draft.config.script_id || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, script_id: e.target.value } })
        }
      />
    )}
  </label>
);
