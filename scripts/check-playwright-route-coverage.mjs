import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const registryPath = path.join(rootDir, "ui", "page-registry.json");
const coveragePath = path.join(rootDir, "ui", "e2e", "coverage-route-map.json");

const readJson = (targetPath) => JSON.parse(fs.readFileSync(targetPath, "utf8"));

const ensureArray = (value) => (Array.isArray(value) ? value : []);

const formatBulletList = (items) => items.map((item) => `  - ${item}`).join("\n");

const validateOwners = (owners, routePath, bucketLabel, invalidEntries) => {
  if (!Array.isArray(owners) || owners.length === 0) {
    invalidEntries.push(`${bucketLabel} ${routePath} has no owning spec entries.`);
    return;
  }

  owners.forEach((owner, ownerIndex) => {
    const spec = typeof owner?.spec === "string" ? owner.spec.trim() : "";
    const testIds = ensureArray(owner?.testIds).filter((item) => typeof item === "string" && item.trim().length > 0);

    if (!spec) {
      invalidEntries.push(`${bucketLabel} ${routePath} owner #${ownerIndex + 1} is missing a spec path.`);
      return;
    }

    const specPath = path.join(rootDir, spec);
    if (!fs.existsSync(specPath)) {
      invalidEntries.push(`${bucketLabel} ${routePath} references missing spec ${spec}.`);
    }

    if (testIds.length === 0) {
      invalidEntries.push(`${bucketLabel} ${routePath} owner ${spec} has no test IDs.`);
    }
  });
};

const registry = readJson(registryPath);
const coverageMap = readJson(coveragePath);

const servedRegistryRoutes = ensureArray(registry.pages)
  .filter((page) => page?.serveMode === "served" && typeof page?.routePath === "string")
  .map((page) => page.routePath);
const redirectRegistryRoutes = ensureArray(registry.pages)
  .filter((page) => page?.serveMode === "redirect" && typeof page?.routePath === "string")
  .map((page) => page.routePath);

const servedRegistrySet = new Set(servedRegistryRoutes);
const redirectRegistrySet = new Set(redirectRegistryRoutes);

const missingServedRoutes = [];
const duplicateServedRoutes = [];
const unknownServedRoutes = [];
const invalidServedEntries = [];

const seenServedRoutes = new Set();
for (const entry of ensureArray(coverageMap.servedRoutes)) {
  const routePath = typeof entry?.routePath === "string" ? entry.routePath.trim() : "";
  if (!routePath) {
    invalidServedEntries.push("servedRoutes contains an entry without a routePath.");
    continue;
  }

  if (redirectRegistrySet.has(routePath)) {
    invalidServedEntries.push(`servedRoutes must not include redirect-only route ${routePath}.`);
    continue;
  }

  if (!servedRegistrySet.has(routePath)) {
    unknownServedRoutes.push(routePath);
    continue;
  }

  if (seenServedRoutes.has(routePath)) {
    duplicateServedRoutes.push(routePath);
    continue;
  }

  seenServedRoutes.add(routePath);

  if (typeof entry?.workflowContract !== "string" || entry.workflowContract.trim().length === 0) {
    invalidServedEntries.push(`served route ${routePath} is missing a workflowContract summary.`);
  }

  validateOwners(entry.owners, routePath, "served route", invalidServedEntries);
}

for (const routePath of servedRegistryRoutes) {
  if (!seenServedRoutes.has(routePath)) {
    missingServedRoutes.push(routePath);
  }
}

const redirectIssues = [];
const seenRedirectRoutes = new Set();
for (const entry of ensureArray(coverageMap.redirectRoutes)) {
  const routePath = typeof entry?.routePath === "string" ? entry.routePath.trim() : "";
  if (!routePath) {
    redirectIssues.push("redirectRoutes contains an entry without a routePath.");
    continue;
  }

  if (!redirectRegistrySet.has(routePath)) {
    redirectIssues.push(`redirect route ${routePath} is not defined as a redirect in ui/page-registry.json.`);
    continue;
  }

  if (seenRedirectRoutes.has(routePath)) {
    redirectIssues.push(`redirect route ${routePath} is listed more than once.`);
    continue;
  }

  seenRedirectRoutes.add(routePath);

  if (entry.owners !== undefined) {
    const owners = ensureArray(entry.owners);
    owners.forEach((owner, ownerIndex) => {
      const spec = typeof owner?.spec === "string" ? owner.spec.trim() : "";
      const testIds = ensureArray(owner?.testIds).filter((item) => typeof item === "string" && item.trim().length > 0);

      if (!spec) {
        redirectIssues.push(`redirect route ${routePath} owner #${ownerIndex + 1} is missing a spec path.`);
        return;
      }

      const specPath = path.join(rootDir, spec);
      if (!fs.existsSync(specPath)) {
        redirectIssues.push(`redirect route ${routePath} references missing spec ${spec}.`);
      }

      if (testIds.length === 0) {
        redirectIssues.push(`redirect route ${routePath} owner ${spec} has no test IDs.`);
      }
    });
  }
}

const missingRedirectDocumentation = redirectRegistryRoutes.filter((routePath) => !seenRedirectRoutes.has(routePath));
if (missingRedirectDocumentation.length > 0) {
  redirectIssues.push(
    `redirectRoutes is missing documented redirect paths: ${missingRedirectDocumentation.join(", ")}.`
  );
}

const issueGroups = [
  ["Missing served routes", missingServedRoutes],
  ["Duplicate served routes", duplicateServedRoutes],
  ["Unknown served routes", unknownServedRoutes],
  ["Invalid served route entries", invalidServedEntries],
  ["Redirect documentation issues", redirectIssues]
].filter(([, issues]) => issues.length > 0);

if (issueGroups.length > 0) {
  console.error(`Playwright route coverage validation failed for ${coveragePath}`);
  for (const [label, issues] of issueGroups) {
    console.error(`\n${label}:`);
    console.error(formatBulletList(issues));
  }
  process.exit(1);
}

console.log(
  `Playwright route coverage OK: ${servedRegistryRoutes.length} served routes mapped, ${redirectRegistryRoutes.length} redirect routes documented.`
);
