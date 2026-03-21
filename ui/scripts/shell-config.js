import { toolsManifest } from "./tools-manifest.js";

export const shellBrand = {
  homeHref: "dashboard/home.html",
  iconHref: new URL("../assets/malcom-icon.svg", import.meta.url).href,
  iconAlt: "Malcom icon",
  title: "Malcom"
};

export const topNavItems = [
  {
    id: "nav-dashboard",
    label: "Dashboard",
    href: "dashboard/home.html",
    section: "dashboard"
  },
  {
    id: "nav-automations",
    label: "Automations",
    href: "automations/overview.html",
    section: "automations"
  },
  {
    id: "nav-apis",
    label: "APIs",
    href: "apis/registry.html",
    section: "apis"
  },
  {
    id: "nav-tools",
    label: "Tools",
    href: "tools/catalog.html",
    section: "tools"
  },
  {
    id: "nav-scripts",
    label: "Scripts",
    href: "scripts.html",
    section: "scripts"
  },
  {
    id: "nav-docs",
    label: "Docs",
    href: "docs/search.html",
    section: "docs"
  },
  {
    id: "nav-settings",
    label: "Settings",
    href: "settings/workspace.html",
    section: "settings"
  }
];

export const shellSections = {
  dashboard: {
    id: "dashboard",
    items: [
      {
        id: "sidenav-dashboard-home",
        label: "Home",
        href: "dashboard/home.html",
        aliases: ["dashboard/overview.html"],
        dashboardRoutes: ["/home", "/overview"],
        pageTitle: "Dashboard Home",
        description: "View workspace status at a glance."
      },
      {
        id: "sidenav-dashboard-devices",
        label: "Devices",
        href: "dashboard/devices.html",
        dashboardRoutes: ["/devices"],
        pageTitle: "Dashboard Devices",
        description: "View connected devices and runtime endpoints."
      },
      {
        id: "sidenav-dashboard-logs",
        label: "Logs",
        href: "dashboard/logs.html",
        dashboardRoutes: ["/logs"],
        pageTitle: "Dashboard Logs",
        description: "Review recent runtime logs and events."
      },
      {
        id: "sidenav-dashboard-queue",
        label: "Queue",
        href: "dashboard/queue.html",
        dashboardRoutes: ["/queue"],
        pageTitle: "Dashboard Queue",
        description: "Track pending and claimed queue jobs."
      }
    ]
  },
  automations: {
    id: "automations",
    items: [
      {
        id: "sidenav-automations-overview",
        label: "Overview",
        href: "automations/overview.html",
        pageTitle: "Automation Overview",
        description: "Review automations and tool availability."
      },
      {
        id: "sidenav-automations-library",
        label: "Library",
        href: "automations/library.html",
        aliases: ["apis/automation.html"],
        pageTitle: "Automation Library",
        description: "Search and open saved automations."
      },
      {
        id: "sidenav-automations-builder",
        label: "Builder",
        href: "automations/builder.html",
        pageTitle: "Automation Builder",
        description: "Build and configure an automation workflow."
      }
    ],
    footer: {
      kind: "button",
      id: "automations-create-button",
      label: "Create +",
      className: "button button--success sidenav__action-button",
      attributes: {
        type: "button"
      }
    }
  },
  apis: {
    id: "apis",
    items: [
      {
        id: "sidenav-apis-registry",
        label: "Registry",
        href: "apis/registry.html",
        aliases: ["apis/overview.html"],
        pageTitle: "APIs Registry",
        description: "Manage incoming, outgoing, and webhook APIs."
      },
      {
        id: "sidenav-apis-incoming",
        label: "Incoming",
        href: "apis/incoming.html",
        pageTitle: "Incoming APIs",
        description: "Track incoming API endpoints and events."
      },
      {
        id: "sidenav-apis-outgoing",
        label: "Outgoing",
        href: "apis/outgoing.html",
        pageTitle: "Outgoing APIs",
        description: "Manage outbound API deliveries."
      },
      {
        id: "sidenav-apis-webhooks",
        label: "Webhooks",
        href: "apis/webhooks.html",
        pageTitle: "API Webhooks",
        description: "Manage webhook definitions and verification."
      }
    ],
    footer: {
      kind: "button",
      id: "apis-create-button",
      label: "Create +",
      className: "button button--success sidenav__action-button",
      attributes: {
        "aria-controls": "apis-create-type-modal",
        "aria-expanded": "false",
        "aria-haspopup": "dialog",
        type: "button"
      }
    }
  },
  tools: {
    id: "tools",
    items: [
      {
        id: "sidenav-tools-catalog",
        label: "Catalog",
        href: "tools/catalog.html",
        aliases: ["tools/overview.html"],
        pageTitle: "Tools Catalog",
        description: "Manage tool metadata and availability."
      },
      ...toolsManifest.map((tool) => ({
        id: `sidenav-tools-${tool.id}`,
        label: tool.name,
        href: tool.pageHref,
        pageTitle: `${tool.name} Configuration`,
        description: `Configure ${tool.name}.`
      }))
    ]
  },
  scripts: {
    id: "scripts",
    items: [
      {
        id: "sidenav-scripts-library",
        label: "Library",
        href: "scripts/library.html",
        pageTitle: "Script Library",
        description: "Create and manage reusable scripts."
      }
    ]
  },
  docs: {
    id: "docs",
    items: [
      {
        id: "sidenav-docs-search",
        label: "Search",
        href: "docs/search.html",
        pageTitle: "Documentation Search",
        description: "Search documentation entries."
      },
      {
        id: "sidenav-docs-browse",
        label: "Browse",
        href: "docs/browse.html",
        pageTitle: "Documentation Browse",
        description: "Browse documentation entries."
      },
      {
        id: "sidenav-docs-create",
        label: "Create",
        href: "docs/create.html",
        pageTitle: "Create Documentation",
        description: "Create a documentation entry."
      }
    ]
  },
  settings: {
    id: "settings",
    items: [
      {
        id: "sidenav-settings-workspace",
        label: "Workspace",
        href: "settings/workspace.html",
        aliases: ["settings/general.html"],
        pageTitle: "Settings Workspace",
        description: "Configure workspace defaults."
      },
      {
        id: "sidenav-settings-logging",
        label: "Logging",
        href: "settings/logging.html",
        pageTitle: "Settings Logging",
        description: "Manage log retention and cleanup."
      },
      {
        id: "sidenav-settings-notifications",
        label: "Notifications",
        href: "settings/notifications.html",
        pageTitle: "Settings Notifications",
        description: "Control alert routing and cadence."
      },
      {
        id: "sidenav-settings-access",
        label: "Access",
        href: "settings/access.html",
        aliases: ["settings/security.html"],
        pageTitle: "Settings Access",
        description: "Manage approval and session controls."
      },
      {
        id: "sidenav-settings-connectors",
        label: "Connectors",
        href: "settings/connectors.html",
        pageTitle: "Settings Connectors",
        description: "Manage connector presets and credentials."
      },
      {
        id: "sidenav-settings-data",
        label: "Data",
        href: "settings/data.html",
        pageTitle: "Settings Data",
        description: "Set data handling defaults."
      }
    ],
    footer: {
      kind: "note",
      id: "settings-sidebar-note",
      className: "sidenav__footer-note",
      text: "Settings on this screen apply to the current browser workspace unless noted otherwise."
    }
  }
};

export const getSectionConfig = (sectionId) => shellSections[sectionId] || null;

export const resolveShellHref = (pathPrefix = "", href = "") => {
  if (!href || href.startsWith("#") || /^[a-z]+:/i.test(href)) {
    return href;
  }

  return `${pathPrefix}${href}`;
};
