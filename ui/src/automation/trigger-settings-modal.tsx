import { Dialog } from "@base-ui/react/dialog";
import type { TriggerType } from "./types";
import { TriggerSettingsForm } from "./trigger-settings-form";

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
  open: boolean;
  onClose: () => void;
  value: TriggerSettingsValue;
  onPatch: (patch: Partial<TriggerSettingsValue>) => void;
};

export const TriggerSettingsModal = ({ open, onClose, value, onPatch }: Props) => (
  <Dialog.Root open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
    <Dialog.Portal>
      <Dialog.Backdrop id="trigger-settings-modal-backdrop" className="automation-dialog-backdrop" />
      <Dialog.Popup id="trigger-settings-modal" className="automation-dialog automation-dialog--wide">
        <div id="trigger-settings-modal-dismiss-row" className="automation-dialog__dismiss-row">
          <Dialog.Close
            id="trigger-settings-modal-close"
            className="modal__close-icon-button automation-dialog__close-button"
            aria-label="Close trigger settings modal"
          >
            ×
          </Dialog.Close>
        </div>
        <Dialog.Title id="trigger-settings-modal-title" className="automation-dialog__title">
          Trigger settings
        </Dialog.Title>
        <Dialog.Description id="trigger-settings-modal-description" className="automation-dialog__description">
          Configure automation identity, trigger type, and trigger-specific filters.
        </Dialog.Description>

        <div id="trigger-settings-modal-form" className="automation-form--modal">
          <TriggerSettingsForm
            idPrefix="trigger-settings-modal"
            value={value}
            onPatch={onPatch}
          />
        </div>
      </Dialog.Popup>
    </Dialog.Portal>
  </Dialog.Root>
);
