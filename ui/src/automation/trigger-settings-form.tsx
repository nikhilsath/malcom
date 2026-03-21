import { Select } from "@base-ui/react/select";
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
};

const FlowSelect = <T extends string>({
  rootId,
  labelId,
  value,
  placeholder,
  options,
  onValueChange
}: {
  rootId: string;
  labelId: string;
  value: T;
  placeholder: string;
  options: Array<{ value: T; label: string }>;
  onValueChange: (value: T) => void;
}) => (
  <Select.Root value={value} onValueChange={(nextValue) => onValueChange(String(nextValue) as T)}>
    <Select.Trigger id={rootId} className="automation-select-trigger" aria-labelledby={labelId}>
      <Select.Value placeholder={placeholder} />
      <Select.Icon className="automation-select-trigger__icon">▾</Select.Icon>
    </Select.Trigger>
    <Select.Portal>
      <Select.Positioner className="automation-select-positioner">
        <Select.Popup className="automation-select-popup">
          <Select.List className="automation-select-list">
            {options.map((option) => (
              <Select.Item
                key={option.value}
                id={`${rootId}-option-${option.value}`}
                className="automation-select-item"
                value={option.value}
              >
                <Select.ItemText>{option.label}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.List>
        </Select.Popup>
      </Select.Positioner>
    </Select.Portal>
  </Select.Root>
);

export const TriggerSettingsForm = ({ idPrefix, value, onPatch }: Props) => {
  const id = (suffix: string) => `${idPrefix}-${suffix}`;

  return (
    <div id={id("form")} className="automation-form">
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

      <div id={id("trigger-type-field")} className="automation-field automation-field--full">
        <span id={id("trigger-type-label")} className="automation-field__label">Trigger type</span>
        <FlowSelect
          rootId={id("trigger-type-input")}
          labelId={id("trigger-type-label")}
          value={value.trigger_type}
          placeholder="Choose a trigger"
          options={triggerTypeOptions}
          onValueChange={(nextValue) => onPatch({ trigger_type: nextValue, trigger_config: {} })}
        />
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
