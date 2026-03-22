import type { AutomationStep, ToolManifestEntry } from "../types";
import { ToolStepFields } from "../tool-step-fields";

type Props = {
  draft: AutomationStep;
  toolsManifest: ToolManifestEntry[];
  onChange: (step: AutomationStep) => void;
};

export const ToolStepForm = ({ draft, toolsManifest, onChange }: Props) => {
  return <ToolStepFields idPrefix="add-step" step={draft} toolsManifest={toolsManifest} onChange={onChange} />;
};
