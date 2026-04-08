import type { DataFlowToken } from "../data-flow";
import type { AutomationStep, ToolManifestEntry } from "../types";
import { ToolStepFields } from "../tool-step-fields";

type Props = {
  draft: AutomationStep;
  toolsManifest: ToolManifestEntry[];
  dataFlowTokens?: DataFlowToken[];
  onChange: (step: AutomationStep) => void;
};

export const ToolStepForm = ({ draft, toolsManifest, dataFlowTokens = [], onChange }: Props) => {
  return <ToolStepFields idPrefix="add-step" step={draft} toolsManifest={toolsManifest} dataFlowTokens={dataFlowTokens} onChange={onChange} />;
};
