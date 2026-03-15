import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
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
        apisRegistry: resolve(__dirname, "apis/registry.html"),
        apisIncoming: resolve(__dirname, "apis/incoming.html"),
        apisOutgoing: resolve(__dirname, "apis/outgoing.html"),
        apisWebhooks: resolve(__dirname, "apis/webhooks.html"),
        apisAutomation: resolve(__dirname, "apis/automation.html"),
        toolsCatalog: resolve(__dirname, "tools/catalog.html"),
        toolsConvertAudio: resolve(__dirname, "tools/convert-audio.html"),
        toolsConvertVideo: resolve(__dirname, "tools/convert-video.html"),
        toolsGrafana: resolve(__dirname, "tools/grafana.html"),
        toolsLlmDeepl: resolve(__dirname, "tools/llm-deepl.html"),
        toolsOcrTranscribe: resolve(__dirname, "tools/ocr-transcribe.html"),
        toolsSmtp: resolve(__dirname, "tools/smtp.html"),
        toolsSftp: resolve(__dirname, "tools/sftp.html"),
        toolsStorage: resolve(__dirname, "tools/storage.html"),
        scripts: resolve(__dirname, "scripts.html"),
        scriptsLibrary: resolve(__dirname, "scripts/library.html")
      }
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    globals: true
  }
});
