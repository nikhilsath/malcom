import { defineConfig, devices } from "@playwright/test";

const port = 4173;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000
  },
  fullyParallel: true,
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] }
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] }
    }
  ],
  webServer: {
    command: ".venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 4173",
    cwd: "..",
    url: `http://127.0.0.1:${port}/health`,
    reuseExistingServer: true,
    env: {
      MALCOM_DATABASE_URL:
        process.env.MALCOM_TEST_DATABASE_URL ||
        process.env.MALCOM_DATABASE_URL ||
        "postgresql://postgres:postgres@127.0.0.1:5432/malcom_test"
    }
  }
});
