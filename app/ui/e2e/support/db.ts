import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = dirname(fileURLToPath(import.meta.url));
const uiDir = resolve(currentDir, "..", "..");
const rootDir = resolve(uiDir, "..");

export function resetPlaywrightDatabase() {
  execFileSync(resolve(rootDir, ".venv", "bin", "python"), [resolve(rootDir, "scripts", "reset_playwright_test_db.py")], {
    cwd: rootDir,
    stdio: "inherit"
  });
}
