import { Switch } from "@base-ui/react/switch";
import type { AutomationDetail } from "./builder-types";

type AutomationSettingsFieldsProps = {
  currentAutomation: AutomationDetail;
  patchAutomation: (patch: Partial<AutomationDetail>) => void;
  variant?: "panel" | "guided-inline";
};

export const AutomationSettingsFields = ({
  currentAutomation,
  patchAutomation,
  variant = "panel"
}: AutomationSettingsFieldsProps) => {
  if (variant === "guided-inline") {
    return (
      <div id="automations-guided-workflow-fields" className="automation-guided-item__fields">
        <label id="automations-guided-workflow-name-field" className="automation-guided-item__field">
          <span id="automations-guided-workflow-name-label" className="automation-guided-item__field-label">Name</span>
          <input
            id="automations-workflow-name-input"
            className="automation-input automation-input--compact"
            placeholder="Name this automation"
            value={currentAutomation.name}
            onChange={(event) => patchAutomation({ name: event.target.value })}
          />
        </label>
        <label id="automations-guided-workflow-description-field" className="automation-guided-item__field">
          <span id="automations-guided-workflow-description-label" className="automation-guided-item__field-label">Description</span>
          <input
            id="automations-workflow-description-input"
            className="automation-input automation-input--compact"
            placeholder="Short purpose"
            value={currentAutomation.description}
            onChange={(event) => patchAutomation({ description: event.target.value })}
          />
        </label>
        <div id="automations-guided-workflow-enabled-field" className="automation-guided-item__toggle">
          <span id="automations-guided-workflow-enabled-label" className="automation-guided-item__field-label">Enabled</span>
          <Switch.Root
            id="automations-workflow-enabled-input"
            checked={currentAutomation.enabled}
            onCheckedChange={(checked) => patchAutomation({ enabled: checked })}
            className="automation-switch"
            aria-labelledby="automations-guided-workflow-enabled-label"
          >
            <Switch.Thumb className="automation-switch__thumb" />
          </Switch.Root>
        </div>
      </div>
    );
  }

  return (
    <>
      <div id="automations-workflow-bar-fields" className="automation-workflow-bar__fields">
        <label id="automations-workflow-name-field" className="automation-field automation-field--full automation-workflow-bar__field">
          <span id="automations-workflow-name-label" className="automation-field__label">Automation name</span>
          <input
            id="automations-workflow-name-input"
            className="automation-input"
            placeholder="Name this automation"
            value={currentAutomation.name}
            onChange={(event) => patchAutomation({ name: event.target.value })}
          />
        </label>
        <label id="automations-workflow-description-field" className="automation-field automation-field--full automation-workflow-bar__field">
          <span id="automations-workflow-description-label" className="automation-field__label">Automation description</span>
          <textarea
            id="automations-workflow-description-input"
            className="automation-textarea"
            rows={2}
            placeholder="Describe what this automation is for"
            value={currentAutomation.description}
            onChange={(event) => patchAutomation({ description: event.target.value })}
          />
        </label>
      </div>

      <div id="automations-workflow-bar-meta" className="automation-workflow-bar__meta">
        <div id="automations-workflow-enabled-field" className="automation-switch-field automation-workflow-card">
          <div id="automations-workflow-enabled-copy" className="automation-switch-field__copy">
            <span id="automations-workflow-enabled-label" className="automation-field__label">Enabled</span>
            <span id="automations-workflow-enabled-description" className="automation-switch-field__description">
              Edit the trigger directly from the canvas trigger node.
            </span>
          </div>
          <Switch.Root
            id="automations-workflow-enabled-input"
            checked={currentAutomation.enabled}
            onCheckedChange={(checked) => patchAutomation({ enabled: checked })}
            className="automation-switch"
          >
            <Switch.Thumb className="automation-switch__thumb" />
          </Switch.Root>
        </div>
      </div>
    </>
  );
};
