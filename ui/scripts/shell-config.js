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
        description: "Monitor the middleware at a glance and review the current workspace state."
      },
      {
        id: "sidenav-dashboard-devices",
        label: "Devices",
        href: "dashboard/devices.html",
        dashboardRoutes: ["/devices"],
        pageTitle: "Dashboard Devices",
        description: "Review connected devices, runtime endpoints, and related middleware assets."
      },
      {
        id: "sidenav-dashboard-logs",
        label: "Logs",
        href: "dashboard/logs.html",
        dashboardRoutes: ["/logs"],
        pageTitle: "Dashboard Logs",
        description: "Inspect recent runtime activity, operator events, and system history."
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
        aliases: ["apis/automation.html"],
        pageTitle: "Automation Overview",
        description: "Design and operate automation workflows from a dedicated control surface."
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
        description: "Manage inbound webhook endpoints, bearer secrets, and delivery logs."
      },
      {
        id: "sidenav-apis-incoming",
        label: "Incoming",
        href: "apis/incoming.html",
        pageTitle: "Incoming APIs",
        description: "Track inbound API traffic, accepted payloads, and pending integrations."
      },
      {
        id: "sidenav-apis-outgoing",
        label: "Outgoing",
        href: "apis/outgoing.html",
        pageTitle: "Outgoing APIs",
        description: "Review outbound requests, destination services, and delivery readiness."
      },
      {
        id: "sidenav-apis-webhooks",
        label: "Webhooks",
        href: "apis/webhooks.html",
        pageTitle: "API Webhooks",
        description: "Manage webhook endpoints, subscriptions, and verification expectations."
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
        description: "Manage local and external tools connected to the automation engine."
      },
      ...toolsManifest.map((tool) => ({
        id: `sidenav-tools-${tool.id}`,
        label: tool.name,
        href: tool.pageHref,
        pageTitle: `${tool.name} Configuration`,
        description: `Configure ${tool.name} and review its metadata, status, and setup notes.`
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
        description: "Manage and organize your automation scripts."
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
        description: "Configure live workspace defaults and operator-facing timestamps."
      },
      {
        id: "sidenav-settings-logging",
        label: "Logging",
        href: "settings/logging.html",
        pageTitle: "Settings Logging",
        description: "Manage log retention, visible history, and maintenance actions for the browser workspace."
      },
      {
        id: "sidenav-settings-notifications",
        label: "Notifications",
        href: "settings/notifications.html",
        pageTitle: "Settings Notifications",
        description: "Control alert routing, digest cadence, and escalation defaults for operators."
      },
      {
        id: "sidenav-settings-access",
        label: "Access",
        href: "settings/access.html",
        aliases: ["settings/security.html"],
        pageTitle: "Settings Access",
        description: "Configure approval and session controls for live workflow access."
      },
      {
        id: "sidenav-settings-connectors",
        label: "Connectors",
        href: "settings/connectors.html",
        pageTitle: "Settings Connectors",
        description: "Manage workspace connector presets, auth flows, and saved credentials."
      },
      {
        id: "sidenav-settings-data",
        label: "Data",
        href: "settings/data.html",
        pageTitle: "Settings Data",
        description: "Set redaction, export, and audit retention defaults for stored operational data."
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
