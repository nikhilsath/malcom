import { appendToken } from "../builder-utils";
import { TokenPicker } from "../token-picker";
import type { AutomationStep } from "../types";
import type { DataFlowToken } from "../data-flow";

type Props = {
  draft: AutomationStep;
  dataFlowTokens: DataFlowToken[];
  onChange: (updater: (step: AutomationStep) => AutomationStep) => void;
};

export const LlmChatStepEditor = ({ draft, dataFlowTokens, onChange }: Props) => (
  <>
    <label id="automations-step-llm-model-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-model-label" className="automation-field__label">Model override</span>
      <input
        id="automations-step-llm-model-input"
        className="automation-input"
        value={draft.config.model_identifier || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, config: { ...currentStep.config, model_identifier: event.target.value } }))}
      />
    </label>
    <label id="automations-step-llm-system-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-system-label" className="automation-field__label">System prompt</span>
      <textarea
        id="automations-step-llm-system-input"
        className="automation-textarea automation-textarea--code"
        rows={5}
        value={draft.config.system_prompt || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, config: { ...currentStep.config, system_prompt: event.target.value } }))}
      />
    </label>
    <label id="automations-step-llm-user-field" className="automation-field automation-field--full">
      <span id="automations-step-llm-user-label" className="automation-field__label">User prompt</span>
      <textarea
        id="automations-step-llm-user-input"
        className="automation-textarea automation-textarea--code"
        rows={7}
        value={draft.config.user_prompt || ""}
        onChange={(event) => onChange((currentStep) => ({ ...currentStep, config: { ...currentStep.config, user_prompt: event.target.value } }))}
      />
    </label>
    {dataFlowTokens.length > 0 ? (
      <TokenPicker
        idPrefix="automations-step-llm"
        tokens={dataFlowTokens}
        description="Insert workflow output tokens into prompts."
        onInsert={(token) => onChange((currentStep) => ({
          ...currentStep,
          config: { ...currentStep.config, user_prompt: appendToken(currentStep.config.user_prompt || "", token) }
        }))}
      />
    ) : null}
  </>
);
