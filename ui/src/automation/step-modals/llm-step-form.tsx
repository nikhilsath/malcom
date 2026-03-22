import type { AutomationStep } from "../types";

type Props = {
  draft: AutomationStep;
  onChange: (step: AutomationStep) => void;
};

export const LlmStepForm = ({ draft, onChange }: Props) => (
  <>
    <label id="add-step-llm-model-field" className="automation-field automation-field--full">
      <span id="add-step-llm-model-label" className="automation-field__label">Model override</span>
      <input
        id="add-step-llm-model-input"
        className="automation-input"
        placeholder="Leave blank to use workspace default"
        value={draft.config.model_identifier || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, model_identifier: e.target.value } })
        }
      />
    </label>

    <label id="add-step-llm-system-field" className="automation-field automation-field--full">
      <span id="add-step-llm-system-label" className="automation-field__label">System prompt</span>
      <textarea
        id="add-step-llm-system-input"
        className="automation-textarea automation-textarea--code automation-code-input"
        rows={5}
        value={draft.config.system_prompt || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, system_prompt: e.target.value } })
        }
      />
    </label>

    <label id="add-step-llm-user-field" className="automation-field automation-field--full">
      <span id="add-step-llm-user-label" className="automation-field__label">User prompt</span>
      <textarea
        id="add-step-llm-user-input"
        className="automation-textarea automation-textarea--code automation-code-input"
        rows={7}
        value={draft.config.user_prompt || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, user_prompt: e.target.value } })
        }
      />
    </label>
  </>
);
