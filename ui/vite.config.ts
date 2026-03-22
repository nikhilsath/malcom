import { resolve } from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    minify: "esbuild",
    cssMinify: true,
    rollupOptions: {
      input: {
        settingsWorkspace: resolve(__dirname, "settings/workspace.html"),
        settingsLogging: resolve(__dirname, "settings/logging.html"),
        settingsNotifications: resolve(__dirname, "settings/notifications.html"),
        settingsAccess: resolve(__dirname, "settings/access.html"),
        settingsConnectors: resolve(__dirname, "settings/connectors.html"),
        settingsData: resolve(__dirname, "settings/data.html"),
        dashboardHome: resolve(__dirname, "dashboard/home.html"),
        dashboardDevices: resolve(__dirname, "dashboard/devices.html"),
        dashboardLogs: resolve(__dirname, "dashboard/logs.html"),
        dashboardQueue: resolve(__dirname, "dashboard/queue.html"),
        automationsOverview: resolve(__dirname, "automations/overview.html"),
        automationsLibrary: resolve(__dirname, "automations/library.html"),
        automationsBuilder: resolve(__dirname, "automations/builder.html"),
        automationsData: resolve(__dirname, "automations/data.html"),
        apisRegistry: resolve(__dirname, "apis/registry.html"),
        apisIncoming: resolve(__dirname, "apis/incoming.html"),
        apisOutgoing: resolve(__dirname, "apis/outgoing.html"),
        apisWebhooks: resolve(__dirname, "apis/webhooks.html"),
        apisAutomation: resolve(__dirname, "apis/automation.html"),
        toolsCatalog: resolve(__dirname, "tools/catalog.html"),
        toolsCoquiTts: resolve(__dirname, "tools/coqui-tts.html"),
        toolsLlmDeepl: resolve(__dirname, "tools/llm-deepl.html"),
        toolsSmtp: resolve(__dirname, "tools/smtp.html"),
        toolsConvertAudio: resolve(__dirname, "tools/convert-audio.html"),
        toolsImageMagic: resolve(__dirname, "tools/image-magic.html"),
        scripts: resolve(__dirname, "scripts.html"),
        scriptsLibrary: resolve(__dirname, "scripts/library.html")
      }
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    globals: true,
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"]
  }
});
