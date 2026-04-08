#!/usr/bin/env node
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, posix, relative } from 'node:path';

const repoRoot = process.cwd();
const appDir = join(repoRoot, 'app');
const uiRoot = join(appDir, 'ui');
const scriptsRoot = join(uiRoot, 'scripts');
const allowedSharedUtilities = new Set([
  'utils.js',
  'log-store.js',
  'navigation.js'
]);
const approvedRootLevelUtilities = new Set([
  'apis.js',
  'connectors.js',
  'dashboard-logs.js',
  'collapsible.js',
  'format-utils.js',
  'request.js',
  'settings.js',
  'shell-config.js',
  'storage.js',
  'tool-config.js',
  'tools-manifest.js',
  'utils.js',
  'log-store.js',
  'navigation.js'
]);

const htmlFiles = [];
const rootScriptFiles = [];

const walk = (dir) => {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      if (entry === 'dist' || entry === 'node_modules') {
        continue;
      }
      walk(fullPath);
      continue;
    }
    if (fullPath.endsWith('.html')) {
      htmlFiles.push(fullPath);
    }
  }
};

walk(uiRoot);
for (const entry of readdirSync(scriptsRoot)) {
  const fullPath = join(scriptsRoot, entry);
  if (statSync(fullPath).isFile() && entry.endsWith('.js')) {
    rootScriptFiles.push(entry);
  }
}

const errors = [];
const scriptSrcPattern = /<script[^>]+src="([^"]+)"/g;

for (const htmlFile of htmlFiles) {
  const source = readFileSync(htmlFile, 'utf8');
  const relativeHtmlPath = relative(repoRoot, htmlFile);
  for (const match of source.matchAll(scriptSrcPattern)) {
    const src = match[1];
    if (!src.startsWith('../scripts/')) {
      continue;
    }
    const scriptPath = src.slice('../scripts/'.length);
    if (!scriptPath.endsWith('.js')) {
      continue;
    }
    if (!scriptPath.includes('/')) {
      if (!allowedSharedUtilities.has(scriptPath)) {
        errors.push(`${relativeHtmlPath}: disallowed root-level script import ${src}`);
      }
      continue;
    }

    const normalized = posix.normalize(scriptPath);
    const expectedPrefix = `${posix.basename(posix.dirname(relativeHtmlPath))}/`;
    if (!normalized.startsWith(expectedPrefix)) {
      errors.push(`${relativeHtmlPath}: page entry ${src} must stay within ../scripts/${expectedPrefix}`);
    }
  }
}

for (const scriptFile of rootScriptFiles) {
  if (approvedRootLevelUtilities.has(scriptFile)) {
    continue;
  }
  errors.push(`ui/scripts/${scriptFile}: root-level script file is not an approved shared utility`);
}

if (errors.length > 0) {
  console.error('UI page-entry controller check failed:');
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log('UI page-entry controller check passed.');
