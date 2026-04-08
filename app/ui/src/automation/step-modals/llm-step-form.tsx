import { useRef, useState } from "react";
import type { DataFlowToken } from "../data-flow";
import { AUTOMATION_PROMPT_TOKEN_TARGET_OPTIONS } from "../constants";
import { TokenPicker } from "../token-picker";
import type { AutomationStep } from "../types";

type Props = {
  draft: AutomationStep;
  dataFlowTokens?: DataFlowToken[];
  onChange: (step: AutomationStep) => void;
};

const insertTokenAtCursor = (input: HTMLTextAreaElement | null, currentValue: string, token: string) => {
  if (!input) {
    return `${currentValue}${token}`;
  }
  const selectionStart = input.selectionStart ?? currentValue.length;
  const selectionEnd = input.selectionEnd ?? selectionStart;
  return `${currentValue.slice(0, selectionStart)}${token}${currentValue.slice(selectionEnd)}`;
};

export const LlmStepForm = ({ draft, dataFlowTokens = [], onChange }: Props) => {
  const systemPromptRef = useRef<HTMLTextAreaElement | null>(null);
  const userPromptRef = useRef<HTMLTextAreaElement | null>(null);
  const [tokenTarget, setTokenTarget] = useState<"system" | "user">("user");

  return (
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
          ref={systemPromptRef}
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
          ref={userPromptRef}
          className="automation-textarea automation-textarea--code automation-code-input"
          rows={7}
          value={draft.config.user_prompt || ""}
          onChange={(e) =>
            onChange({ ...draft, config: { ...draft.config, user_prompt: e.target.value } })
          }
        />
      </label>

      {dataFlowTokens.length > 0 ? (
        <label id="add-step-llm-token-target-field" className="automation-field automation-field--full automation-field--inline-label">
          <span id="add-step-llm-token-target-label" className="automation-field__label">Token target</span>
          <select
            id="add-step-llm-token-target-input"
            className="automation-native-select"
            value={tokenTarget}
            onChange={(event) => setTokenTarget(event.target.value as "system" | "user")}
          >
            {AUTOMATION_PROMPT_TOKEN_TARGET_OPTIONS.map((targetOption) => (
              <option key={targetOption.value} value={targetOption.value}>{targetOption.label}</option>
            ))}
          </select>
        </label>
      ) : null}

      {dataFlowTokens.length > 0 ? (
        <TokenPicker
          idPrefix="add-step-llm"
          tokens={dataFlowTokens}
          description="Insert workflow tokens into prompts."
          onInsert={(token) => {
            if (tokenTarget === "system") {
              const nextSystemPrompt = insertTokenAtCursor(systemPromptRef.current, draft.config.system_prompt || "", token);
              onChange({ ...draft, config: { ...draft.config, system_prompt: nextSystemPrompt } });
              return;
            }
            const nextUserPrompt = insertTokenAtCursor(userPromptRef.current, draft.config.user_prompt || "", token);
            onChange({ ...draft, config: { ...draft.config, user_prompt: nextUserPrompt } });
          }}
        />
      ) : null}
    </>
  );
};
