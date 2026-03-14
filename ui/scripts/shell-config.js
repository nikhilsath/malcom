export const shellBrand = {
  homeHref: "dashboard/overview.html#/overview",
  iconHref: new URL("../assets/malcom-icon.svg", import.meta.url).href,
  iconAlt: "Malcom icon",
  title: "Malcom"
};

export const topNavItems = [
  {
    id: "nav-dashboard",
    label: "Dashboard",
    href: "dashboard/overview.html#/overview",
    section: "dashboard"
  },
  {
    id: "nav-apis",
    label: "APIs",
    href: "apis/overview.html",
    section: "apis"
  },
  {
    id: "nav-tools",
    label: "Tools",
    href: "tools/overview.html",
    section: "tools"
  },
  {
    id: "nav-settings",
    label: "Settings",
    href: "settings/general.html",
    section: "settings"
  }
];

export const shellSections = {
  dashboard: {
    id: "dashboard",
    items: [
      {
        id: "sidenav-dashboard-overview",
        label: "Overview",
        href: "dashboard/overview.html#/overview",
        route: "/overview",
        pageTitle: "Dashboard Overview",
        description: "Monitor the middleware at a glance and review the current workspace state."
      },
      {
        id: "sidenav-dashboard-devices",
        label: "Devices",
        href: "dashboard/overview.html#/devices",
        route: "/devices",
        pageTitle: "Dashboard Devices",
        description: "Review connected devices, runtime endpoints, and related middleware assets."
      },
      {
        id: "sidenav-dashboard-logs",
        label: "Logs",
        href: "dashboard/overview.html#/logs",
        route: "/logs",
        pageTitle: "Dashboard Logs",
        description: "Inspect recent runtime activity, operator events, and system history."
      }
    ]
  },
  apis: {
    id: "apis",
    items: [
      {
        id: "sidenav-apis-overview",
        label: "Overview",
        href: "apis/overview.html",
        pageTitle: "APIs Overview",
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
        "aria-controls": "apis-create-modal",
        "aria-haspopup": "dialog",
        type: "button"
      }
    }
  },
  tools: {
    id: "tools",
    items: [
      {
        id: "sidenav-tools-overview",
        label: "Overview",
        href: "tools/overview.html",
        pageTitle: "Tools Overview",
        description: "Manage local and external tools connected to the automation engine."
      },
      {
        id: "sidenav-tools-sftp",
        label: "SFTP",
        href: "tools/sftp.html",
        pageTitle: "SFTP Tools",
        description: "Review file transfer tooling, remote hosts, and connection readiness."
      },
      {
        id: "sidenav-tools-storage",
        label: "Storage",
        href: "tools/storage.html",
        pageTitle: "Storage Tools",
        description: "Inspect storage-oriented tools, mounted targets, and persistence workflows."
      }
    ]
  },
  settings: {
    id: "settings",
    items: [
      {
        id: "sidenav-settings-general",
        label: "General",
        href: "settings/general.html",
        pageTitle: "Settings General",
        description: "Configure workspace defaults that shape new automations and operator-facing timestamps."
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
        id: "sidenav-settings-security",
        label: "Access",
        href: "settings/security.html",
        pageTitle: "Settings Access",
        description: "Configure approval and session controls that govern access to production workflows."
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
