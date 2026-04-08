import { Switch } from "@base-ui/react/switch";
import type { AutomationStep } from "../types";

type Props = {
  draft: AutomationStep;
  onChange: (step: AutomationStep) => void;
};

export const ConditionStepForm = ({ draft, onChange }: Props) => (
  <>
    <label id="add-step-condition-expression-field" className="automation-field automation-field--full">
      <span id="add-step-condition-expression-label" className="automation-field__label">Expression</span>
      <textarea
        id="add-step-condition-expression-input"
        className="automation-textarea automation-textarea--code automation-code-input"
        rows={4}
        value={draft.config.expression || ""}
        onChange={(e) =>
          onChange({ ...draft, config: { ...draft.config, expression: e.target.value } })
        }
      />
    </label>

    <div id="add-step-condition-stop-field" className="automation-switch-field">
      <div id="add-step-condition-stop-copy" className="automation-switch-field__copy">
        <span id="add-step-condition-stop-label" className="automation-field__label">Stop on false</span>
        <span id="add-step-condition-stop-description" className="automation-switch-field__description">
          Exit the automation when the guard evaluates to false.
        </span>
      </div>
      <Switch.Root
        id="add-step-condition-stop-input"
        checked={Boolean(draft.config.stop_on_false)}
        onCheckedChange={(checked) =>
          onChange({ ...draft, config: { ...draft.config, stop_on_false: checked } })
        }
        className="automation-switch"
      >
        <Switch.Thumb className="automation-switch__thumb" />
      </Switch.Root>
    </div>
  </>
);
