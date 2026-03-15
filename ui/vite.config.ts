import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        settings: resolve(__dirname, "settings.html"),
        settingsGeneral: resolve(__dirname, "settings/general.html"),
        settingsLogging: resolve(__dirname, "settings/logging.html"),
        settingsNotifications: resolve(__dirname, "settings/notifications.html"),
        settingsSecurity: resolve(__dirname, "settings/security.html"),
        settingsData: resolve(__dirname, "settings/data.html"),
        apis: resolve(__dirname, "apis.html"),
        tools: resolve(__dirname, "tools.html"),
        dashboardOverview: resolve(__dirname, "dashboard/overview.html"),
        dashboardDevices: resolve(__dirname, "dashboard/devices.html"),
        dashboardLogs: resolve(__dirname, "dashboard/logs.html"),
        apisOverview: resolve(__dirname, "apis/overview.html"),
        apisIncoming: resolve(__dirname, "apis/incoming.html"),
        apisOutgoing: resolve(__dirname, "apis/outgoing.html"),
        apisWebhooks: resolve(__dirname, "apis/webhooks.html"),
        apisAutomation: resolve(__dirname, "apis/automation.html"),
        toolsOverview: resolve(__dirname, "tools/overview.html"),
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
