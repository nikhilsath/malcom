import type { AutomationStep } from "../types";

type Props = {
  draft: AutomationStep;
  onChange: (step: AutomationStep) => void;
};

export const LogStepForm = ({ draft, onChange }: Props) => (
  <label id="add-step-log-message-field" className="automation-field automation-field--full">
    <span id="add-step-log-message-label" className="automation-field__label">Message</span>
    <textarea
      id="add-step-log-message-input"
      className="automation-textarea"
      rows={4}
      value={draft.config.message || ""}
      onChange={(e) =>
        onChange({ ...draft, config: { ...draft.config, message: e.target.value } })
      }
    />
  </label>
);
