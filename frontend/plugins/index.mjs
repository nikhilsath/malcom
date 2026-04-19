import { apisPlugin } from "./apis/src/index.mjs";
import { automationsPlugin } from "./automations/src/index.mjs";
import { dashboardPlugin } from "./dashboard/src/index.mjs";
import { docsPlugin } from "./docs/src/index.mjs";
import { scriptsPlugin } from "./scripts/src/index.mjs";
import { settingsPlugin } from "./settings/src/index.mjs";
import { toolsPlugin } from "./tools/src/index.mjs";

export const firstPartyPlugins = {
  dashboard: dashboardPlugin,
  automations: automationsPlugin,
  apis: apisPlugin,
  tools: toolsPlugin,
  scripts: scriptsPlugin,
  settings: settingsPlugin,
  docs: docsPlugin
};

export const getFirstPartyPluginImplementation = (pluginId) => firstPartyPlugins[pluginId] || null;
