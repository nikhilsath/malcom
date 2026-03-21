import { Switch } from "@base-ui/react/switch";
import type { TriggerType } from "./types";
import { triggerTypeOptions } from "./types";

type TriggerSettingsValue = {
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: TriggerType;
  trigger_config: {
    schedule_time?: string | null;
    inbound_api_id?: string | null;
    smtp_subject?: string | null;
    smtp_recipient_email?: string | null;
  };
};

type Props = {
  idPrefix: string;
  value: TriggerSettingsValue;
  onPatch: (patch: Partial<TriggerSettingsValue>) => void;
  showWorkflowFields?: boolean;
  showEnabledField?: boolean;
};

const triggerDescriptions: Record<TriggerType, string> = {
  manual: "Run the workflow only when an operator starts it.",
  schedule: "Start automatically at a set time each day.",
  inbound_api: "Start when an inbound API endpoint receives an event.",
  smtp_email: "Start when incoming email matches your filters."
};

export const TriggerSettingsForm = ({
  idPrefix,
  value,
  onPatch,
  showWorkflowFields = true,
  showEnabledField = true
}: Props) => {
  const id = (suffix: string) => `${idPrefix}-${suffix}`;

  return (
    <div id={id("form")} className="automation-form">
      {showWorkflowFields ? (
        <>
          <label id={id("name-field")} className="automation-field automation-field--full">
            <span id={id("name-label")} className="automation-field__label">Name</span>
            <input
              id={id("name-input")}
              className="automation-input"
              value={value.name}
              onChange={(event) => onPatch({ name: event.target.value })}
            />
          </label>

          <label id={id("description-field")} className="automation-field automation-field--full">
            <span id={id("description-label")} className="automation-field__label">Description</span>
            <textarea
              id={id("description-input")}
              className="automation-textarea"
              rows={4}
              value={value.description}
              onChange={(event) => onPatch({ description: event.target.value })}
            />
          </label>
        </>
      ) : null}

      {showEnabledField ? (
        <div id={id("enabled-field")} className="automation-switch-field">
          <div id={id("enabled-copy")} className="automation-switch-field__copy">
            <span id={id("enabled-label")} className="automation-field__label">Enabled</span>
            <span id={id("enabled-description")} className="automation-switch-field__description">
              {value.enabled ? "The runtime can execute this automation." : "The automation stays visible but will not execute."}
            </span>
          </div>
          <Switch.Root
            id={id("enabled-input")}
            checked={value.enabled}
            onCheckedChange={(checked) => onPatch({ enabled: checked })}
            className="automation-switch"
          >
            <Switch.Thumb className="automation-switch__thumb" />
          </Switch.Root>
        </div>
      ) : null}

      <div id={id("trigger-type-field")} className="automation-field automation-field--full">
        <span id={id("trigger-type-label")} className="automation-field__label">Trigger type</span>
        <div id={id("trigger-type-options")} className="automation-trigger-options" role="radiogroup" aria-labelledby={id("trigger-type-label")}>
          {triggerTypeOptions.map((option) => {
            const selected = value.trigger_type === option.value;
            return (
              <button
                key={option.value}
                id={id(`trigger-type-option-${option.value}`)}
                type="button"
                role="radio"
                aria-checked={selected}
                className={`automation-trigger-option${selected ? " automation-trigger-option--selected" : ""}`}
                onClick={() => onPatch({ trigger_type: option.value, trigger_config: {} })}
              >
                <span id={id(`trigger-type-option-${option.value}-label`)} className="automation-trigger-option__label">
                  {option.label}
                </span>
                <span id={id(`trigger-type-option-${option.value}-description`)} className="automation-trigger-option__description">
                  {triggerDescriptions[option.value]}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {value.trigger_type === "schedule" ? (
        <label id={id("trigger-schedule-field")} className="automation-field automation-field--full">
          <span id={id("trigger-schedule-label")} className="automation-field__label">Daily run time</span>
          <input
            id={id("trigger-schedule-input")}
            className="automation-input"
            type="time"
            value={value.trigger_config.schedule_time || ""}
            onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, schedule_time: event.target.value } })}
          />
        </label>
      ) : null}

      {value.trigger_type === "inbound_api" ? (
        <label id={id("trigger-api-field")} className="automation-field automation-field--full">
          <span id={id("trigger-api-label")} className="automation-field__label">Inbound API id</span>
          <input
            id={id("trigger-api-input")}
            className="automation-input"
            value={value.trigger_config.inbound_api_id || ""}
            onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, inbound_api_id: event.target.value } })}
          />
        </label>
      ) : null}

      {value.trigger_type === "smtp_email" ? (
        <>
          <label id={id("trigger-smtp-subject-field")} className="automation-field automation-field--full">
            <span id={id("trigger-smtp-subject-label")} className="automation-field__label">Email subject</span>
            <input
              id={id("trigger-smtp-subject-input")}
              className="automation-input"
              value={value.trigger_config.smtp_subject || ""}
              onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, smtp_subject: event.target.value } })}
            />
          </label>
          <label id={id("trigger-smtp-recipient-field")} className="automation-field automation-field--full">
            <span id={id("trigger-smtp-recipient-label")} className="automation-field__label">Recipient filter</span>
            <input
              id={id("trigger-smtp-recipient-input")}
              className="automation-input"
              value={value.trigger_config.smtp_recipient_email || ""}
              onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, smtp_recipient_email: event.target.value } })}
            />
          </label>
        </>
      ) : null}
    </div>
  );
};
