import { resolve } from "node:path";
import pageRegistry from "./page-registry.json";

export type UiServeMode = "served" | "redirect";

export interface UiPageRegistryEntry {
    routePath: string;
    sourceHtmlPath: string;
    serveMode: UiServeMode;
    canonicalRoutePath?: string;
    redirectTarget?: string;
    legacyAliases?: string[];
}

interface UiPageRegistryDocument {
    pages: UiPageRegistryEntry[];
}

const registryDocument = pageRegistry as UiPageRegistryDocument;

export const uiPageRegistry = registryDocument.pages;

export const buildableUiPages = uiPageRegistry.filter((entry) => entry.serveMode === "served");

function toInputName(sourceHtmlPath: string): string {
    const [firstSegment, ...restSegments] = sourceHtmlPath.replace(/\.html$/, "").split(/[/.-]+/);
    return [firstSegment, ...restSegments.map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))].join("");
}

export function getViteUiInputs(rootDir: string): Record<string, string> {
    return Object.fromEntries(
        buildableUiPages.map((entry) => [toInputName(entry.sourceHtmlPath), resolve(rootDir, entry.sourceHtmlPath)]),
    );
}
