import { defineConfig, devices } from "@playwright/test";
import { execSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_PLAYWRIGHT_PORT = 4173;
const MAX_FALLBACK_ATTEMPTS = 25;
const configDir = dirname(fileURLToPath(import.meta.url));
const coquiTtsFixtureCommand = resolve(configDir, "e2e", "fixtures", "coqui-tts-command", "tts");

const parsePort = (value: string | undefined, fallback: number) => {
  const parsed = Number.parseInt(String(value || ""), 10);
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 65535) {
    return fallback;
  }
  return parsed;
};

const isPortListening = (port: number) => {
  try {
    execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
};

const resolvePlaywrightPort = () => {
  const requestedFromEnv = process.env.PLAYWRIGHT_PORT;
  const requestedPort = parsePort(requestedFromEnv, DEFAULT_PLAYWRIGHT_PORT);

  // If already set by caller/parent process, use it exactly to keep all Playwright
  // phases (webServer + workers) on the same port.
  if (requestedFromEnv) {
    return requestedPort;
  }

  if (!isPortListening(requestedPort)) {
    process.env.PLAYWRIGHT_PORT = String(requestedPort);
    return requestedPort;
  }

  for (let offset = 1; offset <= MAX_FALLBACK_ATTEMPTS; offset += 1) {
    const candidatePort = requestedPort + offset;
    if (!isPortListening(candidatePort)) {
      console.warn(`[playwright] Port ${requestedPort} is busy; using fallback port ${candidatePort}.`);
      process.env.PLAYWRIGHT_PORT = String(candidatePort);
      return candidatePort;
    }
  }

  process.env.PLAYWRIGHT_PORT = String(requestedPort);
  return requestedPort;
};

const port = resolvePlaywrightPort();
const hostedFrontendPort = port + 1;
process.env.PLAYWRIGHT_HOSTED_FRONTEND_PORT = String(hostedFrontendPort);

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: 1,
  expect: {
    timeout: 5_000
  },
  fullyParallel: true,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure"
  },
  projects: [
    {
      // Critical project: minimal real subset run by default in test-system.sh.
      // Proves the product boots and critical UI flows work against the real backend.
      name: "critical",
      use: { ...devices["Desktop Chrome"] },
      testMatch: ["**/shell.spec.ts", "**/settings.spec.ts"]
    },
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
  webServer: [
    {
      command: `bash ./scripts/run_playwright_server.sh ${port}`,
      cwd: "..",
      url: `http://127.0.0.1:${port}/health`,
      reuseExistingServer: false,
      env: {
        PLAYWRIGHT_PORT: String(port),
        MALCOM_FRONTEND_BOOTSTRAP_TOKEN:
          process.env.MALCOM_FRONTEND_BOOTSTRAP_TOKEN || "playwright-platform-bootstrap",
        MALCOM_DATABASE_URL:
          process.env.MALCOM_TEST_DATABASE_URL ||
          process.env.MALCOM_DATABASE_URL ||
          "postgresql://postgres:postgres@127.0.0.1:5432/malcom_test",
        MALCOM_COQUI_TTS_COMMAND_SOURCE:
          process.env.MALCOM_COQUI_TTS_COMMAND_SOURCE || coquiTtsFixtureCommand
      }
    },
    {
      command: `python3 -m http.server ${hostedFrontendPort} --bind 127.0.0.1 --directory frontend`,
      cwd: "../..",
      url: `http://127.0.0.1:${hostedFrontendPort}/apps/host/index.html`,
      reuseExistingServer: false
    }
  ]
});
