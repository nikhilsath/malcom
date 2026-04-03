import { requestJson } from "../lib/request";
import type { Automation, AutomationDetail, AutomationRunDetail, BuilderSupportData, ToolDirectoryEntryApi } from "./builder-types";
import type { ConnectorActivityDefinition, HttpPreset, InboundApiOption, ScriptLibraryItem, WorkflowBuilderConnectorOption } from "./builder-types";
import { mapToolDirectoryEntry } from "./builder-utils";

declare global {
  interface Window {
    Malcom?: {
      requestJson?: (path: string, options?: RequestInit) => Promise<unknown>;
    };
  }
}

export const requestJsonCompat = async <T = unknown>(path: string, options?: RequestInit): Promise<T> => {
  if (typeof window !== "undefined" && typeof window.Malcom?.requestJson === "function") {
    return (await window.Malcom.requestJson(path, options)) as T;
  }
  return (await requestJson(path, options)) as T;
};

export const loadAutomationList = () => requestJsonCompat<Automation[]>("/api/v1/automations");

export const loadAutomationDetail = (automationId: string) => requestJsonCompat<AutomationDetail>(`/api/v1/automations/${automationId}`);

export const loadBuilderSupportData = async (): Promise<BuilderSupportData> => {
  // Data lineage: See README.md > Data Lineage Reference > Automation Builder Data Sources
  // Loads all dropdown data for the automation builder in parallel: connectors, scripts, 
  // connector activities, HTTP presets, and tools. Single API call per data type maintains
  // database as the source of truth.
  const [connectorOptions, inbound, scriptItems, activityItems, presetItems, toolItems] = await Promise.all([
    // Data lineage: Saved Connectors → GET /api/v1/automations/workflow-connectors
    requestJsonCompat<WorkflowBuilderConnectorOption[]>("/api/v1/automations/workflow-connectors"),
    // Data lineage: Inbound APIs → GET /api/v1/inbound
    requestJsonCompat<Array<{ id: string; name: string }>>("/api/v1/inbound"),
    // Data lineage: Scripts → GET /api/v1/scripts
    requestJsonCompat<ScriptLibraryItem[]>("/api/v1/scripts"),
    // Data lineage: Connector Activities → GET /api/v1/connectors/activity-catalog
    requestJsonCompat<ConnectorActivityDefinition[]>("/api/v1/connectors/activity-catalog"),
    // Data lineage: HTTP Presets → GET /api/v1/connectors/http-presets
    requestJsonCompat<HttpPreset[]>("/api/v1/connectors/http-presets"),
    // Data lineage: Tools Manifest → GET /api/v1/tools
    requestJsonCompat<ToolDirectoryEntryApi[]>("/api/v1/tools")
  ]);

  return {
    connectors: connectorOptions,
    inboundApis: inbound.map((api): InboundApiOption => ({ id: api.id, name: api.name })),
    scripts: scriptItems,
    activityCatalog: activityItems,
    httpPresets: presetItems,
    toolsManifest: toolItems.map(mapToolDirectoryEntry)
  };
};

export const saveAutomationRequest = (automation: AutomationDetail) => {
  const payload = {
    name: automation.name,
    description: automation.description,
    enabled: automation.enabled,
    trigger_type: automation.trigger_type,
    trigger_config: automation.trigger_config,
    steps: automation.steps
  };

  return automation.id
    ? requestJsonCompat<AutomationDetail>(`/api/v1/automations/${automation.id}`, { method: "PATCH", body: JSON.stringify(payload) })
    : requestJsonCompat<AutomationDetail>("/api/v1/automations", { method: "POST", body: JSON.stringify(payload) });
};

export const validateAutomationRequest = (automationId: string) =>
  requestJsonCompat<{ valid: boolean; issues: string[] }>(`/api/v1/automations/${automationId}/validate`, { method: "POST" });

export const executeAutomationRequest = (automationId: string) =>
  requestJsonCompat<AutomationRunDetail>(`/api/v1/automations/${automationId}/execute`, { method: "POST" });

export const deleteAutomationRequest = (automationId: string) =>
  requestJsonCompat(`/api/v1/automations/${automationId}`, { method: "DELETE" });
