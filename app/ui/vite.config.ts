import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { getViteUiInputs } from "./page-registry";

export default defineConfig({
    plugins: [react()],
    build: {
      minify: false,
      cssMinify: false,
      sourcemap: true,
      rollupOptions: {
        input: getViteUiInputs(__dirname)
      }
    },
    test: {
      environment: "jsdom",
      setupFiles: "./vitest.setup.ts",
      globals: true,
      exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"]
    }
});
