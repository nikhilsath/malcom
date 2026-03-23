import { Switch } from "@base-ui/react/switch";
import { useEffect, useMemo, useRef, useState } from "react";
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
  inboundApiOptions?: Array<{ id: string; name: string }>;
  inboundApiMissingSelection?: boolean;
};

const triggerDescriptions: Record<TriggerType, string> = {
  manual: "Run the automation only when an operator starts it.",
  schedule: "Start automatically at a set time each day.",
  inbound_api: "Start when an inbound API endpoint receives an event.",
  smtp_email: "Start when incoming email matches your filters."
};

const scheduleHourOptions = Array.from({ length: 12 }, (_, index) => String(index + 1));
const scheduleMinuteOptions = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, "0"));

const parseScheduleTime = (scheduleTime?: string | null) => {
  const fallback = { hour: "12", minute: "00", period: "AM" as const };
  if (!scheduleTime || !/^\d{2}:\d{2}$/.test(scheduleTime)) {
    return fallback;
  }

  const [rawHour, rawMinute] = scheduleTime.split(":");
  const hour24 = Number(rawHour);
  const minute = Number(rawMinute);
  if (!Number.isInteger(hour24) || !Number.isInteger(minute) || hour24 < 0 || hour24 > 23 || minute < 0 || minute > 59) {
    return fallback;
  }

  const period = hour24 >= 12 ? "PM" : "AM";
  const hour12 = hour24 % 12 || 12;
  return { hour: String(hour12), minute: String(minute).padStart(2, "0"), period };
};

const formatScheduleTimeLabel = (scheduleTime?: string | null) => {
  if (!scheduleTime || !/^\d{2}:\d{2}$/.test(scheduleTime)) {
    return "Select time";
  }
  const parsed = parseScheduleTime(scheduleTime);
  return `${parsed.hour.padStart(2, "0")}:${parsed.minute} ${parsed.period}`;
};

const to24HourScheduleTime = (hour: string, minute: string, period: "AM" | "PM") => {
  const hour12 = Number(hour);
  const minuteValue = Number(minute);
  if (!Number.isInteger(hour12) || !Number.isInteger(minuteValue) || hour12 < 1 || hour12 > 12 || minuteValue < 0 || minuteValue > 59) {
    return null;
  }
  const hour24 = period === "AM" ? hour12 % 12 : (hour12 % 12) + 12;
  return `${String(hour24).padStart(2, "0")}:${String(minuteValue).padStart(2, "0")}`;
};

export const TriggerSettingsForm = ({
  idPrefix,
  value,
  onPatch,
  showWorkflowFields = true,
  showEnabledField = true,
  inboundApiOptions = [],
  inboundApiMissingSelection = false
}: Props) => {
  const id = (suffix: string) => `${idPrefix}-${suffix}`;
  const schedulePickerLabelId = id("trigger-schedule-picker-title");
  const schedulePickerRef = useRef<HTMLDivElement | null>(null);
  const [schedulePickerOpen, setSchedulePickerOpen] = useState(false);

  const initialSchedule = parseScheduleTime(value.trigger_config.schedule_time);
  const [scheduleHour, setScheduleHour] = useState(initialSchedule.hour);
  const [scheduleMinute, setScheduleMinute] = useState(initialSchedule.minute);
  const [schedulePeriod, setSchedulePeriod] = useState<"AM" | "PM">(initialSchedule.period);

  useEffect(() => {
    const parsed = parseScheduleTime(value.trigger_config.schedule_time);
    setScheduleHour(parsed.hour);
    setScheduleMinute(parsed.minute);
    setSchedulePeriod(parsed.period);
  }, [value.trigger_config.schedule_time]);

  useEffect(() => {
    if (!schedulePickerOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!schedulePickerRef.current || schedulePickerRef.current.contains(event.target as Node)) {
        return;
      }
      setSchedulePickerOpen(false);
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [schedulePickerOpen]);

  const scheduleButtonLabel = useMemo(
    () => formatScheduleTimeLabel(value.trigger_config.schedule_time),
    [value.trigger_config.schedule_time]
  );

  const inboundApiId = value.trigger_config.inbound_api_id || "";
  const inboundApiHasCurrentOption = inboundApiOptions.some((option) => option.id === inboundApiId);

  const inboundApiSelectOptions = useMemo(() => {
    if (!inboundApiId || inboundApiHasCurrentOption) {
      return inboundApiOptions;
    }
    return [{ id: inboundApiId, name: "Unavailable API" }, ...inboundApiOptions];
  }, [inboundApiHasCurrentOption, inboundApiId, inboundApiOptions]);

  const patchScheduleTime = (nextHour: string, nextMinute: string, nextPeriod: "AM" | "PM") => {
    const scheduleTime = to24HourScheduleTime(nextHour, nextMinute, nextPeriod);
    if (!scheduleTime) {
      return;
    }
    onPatch({ trigger_config: { ...value.trigger_config, schedule_time: scheduleTime } });
  };

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
            <Switch.Thumb id={id("enabled-thumb")} className="automation-switch__thumb" />
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
        <div id={id("trigger-schedule-field")} className="automation-field automation-field--full automation-time-picker" ref={schedulePickerRef}>
          <span id={id("trigger-schedule-label")} className="automation-field__label">Daily run time</span>
          <button
            id={id("trigger-schedule-input")}
            className="automation-input automation-time-picker__trigger"
            type="button"
            aria-haspopup="dialog"
            aria-expanded={schedulePickerOpen}
            aria-controls={id("trigger-schedule-picker")}
            onClick={() => setSchedulePickerOpen((open) => !open)}
          >
            {scheduleButtonLabel}
          </button>

          {schedulePickerOpen ? (
            <div
              id={id("trigger-schedule-picker")}
              className="automation-time-picker__panel"
              role="dialog"
              aria-labelledby={schedulePickerLabelId}
            >
              <span id={schedulePickerLabelId} className="sr-only">Schedule time picker</span>
              <label id={id("trigger-schedule-hour-field")} className="automation-field automation-time-picker__field">
                <span id={id("trigger-schedule-hour-label")} className="automation-field__label">Hour</span>
                <select
                  id={id("trigger-schedule-hour-input")}
                  className="automation-input"
                  value={scheduleHour}
                  onChange={(event) => {
                    const nextHour = event.target.value;
                    setScheduleHour(nextHour);
                    patchScheduleTime(nextHour, scheduleMinute, schedulePeriod);
                  }}
                >
                  {scheduleHourOptions.map((hourOption) => (
                    <option key={hourOption} id={id(`trigger-schedule-hour-option-${hourOption}`)} value={hourOption}>
                      {hourOption}
                    </option>
                  ))}
                </select>
              </label>

              <label id={id("trigger-schedule-minute-field")} className="automation-field automation-time-picker__field">
                <span id={id("trigger-schedule-minute-label")} className="automation-field__label">Minute</span>
                <select
                  id={id("trigger-schedule-minute-input")}
                  className="automation-input"
                  value={scheduleMinute}
                  onChange={(event) => {
                    const nextMinute = event.target.value;
                    setScheduleMinute(nextMinute);
                    patchScheduleTime(scheduleHour, nextMinute, schedulePeriod);
                  }}
                >
                  {scheduleMinuteOptions.map((minuteOption) => (
                    <option key={minuteOption} id={id(`trigger-schedule-minute-option-${minuteOption}`)} value={minuteOption}>
                      {minuteOption}
                    </option>
                  ))}
                </select>
              </label>

              <label id={id("trigger-schedule-period-field")} className="automation-field automation-time-picker__field">
                <span id={id("trigger-schedule-period-label")} className="automation-field__label">Period</span>
                <select
                  id={id("trigger-schedule-period-input")}
                  className="automation-input"
                  value={schedulePeriod}
                  onChange={(event) => {
                    const nextPeriod = event.target.value as "AM" | "PM";
                    setSchedulePeriod(nextPeriod);
                    patchScheduleTime(scheduleHour, scheduleMinute, nextPeriod);
                  }}
                >
                  <option id={id("trigger-schedule-period-option-am")} value="AM">AM</option>
                  <option id={id("trigger-schedule-period-option-pm")} value="PM">PM</option>
                </select>
              </label>
            </div>
          ) : null}
        </div>
      ) : null}

      {value.trigger_type === "inbound_api" ? (
        <label id={id("trigger-api-field")} className="automation-field automation-field--full">
          <span id={id("trigger-api-label")} className="automation-field__label">Inbound API</span>
          <select
            id={id("trigger-api-input")}
            className="automation-input"
            value={inboundApiId}
            onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, inbound_api_id: event.target.value } })}
          >
            <option id={id("trigger-api-option-empty")} value="">Select inbound API</option>
            {inboundApiSelectOptions.map((option) => (
              <option key={option.id} id={id(`trigger-api-option-${option.id}`)} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
          {inboundApiMissingSelection ? (
            <span id={id("trigger-api-missing-selection")} className="automation-switch-field__description">
              The selected inbound API is no longer available. Choose another API to continue.
            </span>
          ) : null}
        </label>
      ) : null}

      {value.trigger_type === "smtp_email" ? (
        <>
          <label id={id("trigger-smtp-subject-field")} className="automation-field automation-field--full">
            <span id={id("trigger-smtp-subject-label")} className="automation-field__label">Subject match</span>
            <input
              id={id("trigger-smtp-subject-input")}
              className="automation-input"
              value={value.trigger_config.smtp_subject || ""}
              onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, smtp_subject: event.target.value } })}
              placeholder="Optional exact subject"
            />
          </label>
          <label id={id("trigger-smtp-recipient-field")} className="automation-field automation-field--full">
            <span id={id("trigger-smtp-recipient-label")} className="automation-field__label">Recipient match</span>
            <input
              id={id("trigger-smtp-recipient-input")}
              className="automation-input"
              value={value.trigger_config.smtp_recipient_email || ""}
              onChange={(event) => onPatch({ trigger_config: { ...value.trigger_config, smtp_recipient_email: event.target.value } })}
              placeholder="Optional exact recipient"
            />
          </label>
          <span id={id("trigger-smtp-help")} className="automation-switch-field__description">
            Leave both filters blank to trigger on any inbound email. Matching is exact for now.
          </span>
        </>
      ) : null}
    </div>
  );
};
