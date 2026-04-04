/// <reference types="vite/client" />

declare module "../../scripts/shell-config.js" {
  export type ShellNavItem = {
    id: string;
    label: string;
    href: string;
    section?: string;
    route?: string;
    pageTitle?: string;
    description?: string;
    align?: "right";
  };

  export const shellBrand: {
    homeHref: string;
    iconHref: string;
    iconAlt: string;
    title: string;
  };

  export const topNavItems: ShellNavItem[];

  export const getSectionConfig: (sectionId: string) => {
    id: string;
    items: ShellNavItem[];
  } | null;

  export const resolveShellHref: (pathPrefix?: string, href?: string) => string;
}
