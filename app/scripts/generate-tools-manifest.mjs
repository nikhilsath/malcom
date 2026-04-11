import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "../..");
const appDir = path.resolve(__dirname, "..");

const generateManifest = () => {
  const result = spawnSync(
    "python3",
    [
      "-c",
      [
        "from pathlib import Path",
        "from backend.tool_registry import write_tools_manifest",
        `root = Path(${JSON.stringify(workspaceRoot)})`,
        "tools = write_tools_manifest(root)",
        'print(f"Generated app/ui/scripts/tools-manifest.js with {len(tools)} tools.")',
      ].join("; "),
    ],
    {
      cwd: appDir,
      encoding: "utf8",
    },
  );

  if (result.status !== 0) {
    throw new Error(result.stderr.trim() || result.stdout.trim() || "Unable to generate tools manifest.");
  }

  process.stdout.write(result.stdout);
};

try {
  generateManifest();
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
