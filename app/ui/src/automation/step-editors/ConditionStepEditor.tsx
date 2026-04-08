import { Switch } from "@base-ui/react/switch";
import { appendToken } from "../builder-utils";
import { TokenPicker } from "../token-picker";
import type { AutomationStep } from "../types";
import type { DataFlowToken } from "../data-flow";

type Props = {
  draft: AutomationStep;
  allSteps: AutomationStep[];
  dataFlowTokens: DataFlowToken[];
  onChange: (updater: (step: AutomationStep) => AutomationStep) => void;
};

export const ConditionStepEditor = ({ draft, allSteps, dataFlowTokens, onChange }: Props) => (
  <>
    <label id="automations-step-condition-expression-field" className="automation-field automation-field--full">
      <span id="automations-step-condition-expression-label" className="automation-field__label">Expression</span>
      <textarea
        id="automations-step-condition-expression-input"
        className="automation-textarea automation-textarea--code"
        rows={4}
        value={draft.config.expression || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, config: { ...currentStep.config, expression: event.target.value } }))}
      />
    </label>
    {dataFlowTokens.length > 0 ? (
      <TokenPicker
        idPrefix="automations-step-condition"
        tokens={dataFlowTokens}
        description="Insert data references into condition expressions."
        onInsert={(token) => onChange((currentStep) => ({
          ...currentStep,
          config: { ...currentStep.config, expression: appendToken(currentStep.config.expression || "", token) }
        }))}
      />
    ) : null}
    <div id="automations-step-condition-stop-field" className="automation-switch-field">
      <div id="automations-step-condition-stop-copy" className="automation-switch-field__copy">
        <span id="automations-step-condition-stop-label" className="automation-field__label">Stop on false</span>
        <span id="automations-step-condition-stop-description" className="automation-switch-field__description">
          Exit the automation when the guard evaluates to false (ignored when a FALSE branch target is set).
        </span>
      </div>
      <Switch.Root
        id="automations-step-condition-stop-input"
        checked={Boolean(draft.config.stop_on_false)}
        onCheckedChange={(checked) => onChange((currentStep) => ({ ...currentStep, config: { ...currentStep.config, stop_on_false: checked } }))}
        className="automation-switch"
      >
        <Switch.Thumb className="automation-switch__thumb" />
      </Switch.Root>
    </div>

    <label id="automations-step-condition-true-branch-field" className="automation-field automation-field--full">
      <span id="automations-step-condition-true-branch-label" className="automation-field__label">On TRUE — jump to step</span>
      <select
        id="automations-step-condition-true-branch-input"
        className="automation-native-select"
        value={draft.on_true_step_id || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, on_true_step_id: event.target.value || null }))}
      >
        <option value="">Continue in sequence</option>
        {allSteps.filter((candidate) => candidate.id !== draft.id).map((candidate) => (
          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
        ))}
      </select>
    </label>

    <label id="automations-step-condition-false-branch-field" className="automation-field automation-field--full">
      <span id="automations-step-condition-false-branch-label" className="automation-field__label">On FALSE — jump to step</span>
      <select
        id="automations-step-condition-false-branch-input"
        className="automation-native-select"
        value={draft.on_false_step_id || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, on_false_step_id: event.target.value || null }))}
      >
        <option value="">Use &ldquo;stop on false&rdquo; setting</option>
        {allSteps.filter((candidate) => candidate.id !== draft.id).map((candidate) => (
          <option key={candidate.id} value={candidate.id}>{candidate.name}</option>
        ))}
      </select>
    </label>
  </>
);
