const sideNavConfig = {
  dashboard: [
    {
      id: "sidenav-dashboard-overview",
      label: "Overview",
      href: "index.html",
      pageTitle: "Dashboard",
      description: "Welcome to the Malcom automation middleware. Manage your local automations here."
    },
    {
      id: "sidenav-dashboard-automations",
      label: "Automations",
      href: "#dashboard-automations"
    },
    {
      id: "sidenav-dashboard-runs",
      label: "Runs",
      href: "#dashboard-runs"
    },
    {
      id: "sidenav-dashboard-settings",
      label: "Settings",
      href: "#dashboard-settings"
    }
  ],
  apis: [
    {
      id: "sidenav-apis-overview",
      label: "Overview",
      href: "apis.html",
      pageTitle: "APIs",
      description: "Manage inbound webhook endpoints, bearer secrets, and delivery logs."
    },
    {
      id: "sidenav-apis-directory",
      label: "Directory",
      href: "#api-directory-panel"
    },
    {
      id: "sidenav-apis-details",
      label: "Details",
      href: "#api-detail-panel"
    },
    {
      id: "sidenav-apis-logs",
      label: "Logs",
      href: "#api-logs-panel"
    }
  ],
  tools: [
    {
      id: "sidenav-tools-overview",
      label: "Overview",
      href: "tools.html",
      pageTitle: "Tools",
      description: "Manage local and external tools connected to the automation engine."
    },
    {
      id: "sidenav-tools-installed",
      label: "Installed Tools",
      href: "#tools-installed"
    },
    {
      id: "sidenav-tools-connectors",
      label: "Connectors",
      href: "#tools-connectors"
    },
    {
      id: "sidenav-tools-utilities",
      label: "Utilities",
      href: "#tools-utilities"
    }
  ]
};

const renderSideNav = () => {
  const body = document.body;
  const sideNav = document.getElementById("sidenav");
  const sideNavList = document.getElementById("sidebar-navigation-list");

  if (!body || !sideNav || !sideNavList) {
    return;
  }

  const section = body.dataset.section;
  const activeItemId = body.dataset.sidenavItem;
  const items = sideNavConfig[section];

  if (!items) {
    return;
  }

  sideNav.dataset.section = section;
  sideNavList.textContent = "";

  items.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.className = "sidenav__item";

    const link = document.createElement("a");
    link.className = "sidenav__link";
    link.id = item.id;
    link.href = item.href;
    link.textContent = item.label;

    if (item.id === activeItemId) {
      link.setAttribute("aria-current", "page");
    }

    listItem.appendChild(link);
    sideNavList.appendChild(listItem);
  });

  const activeItem = items.find((item) => item.id === activeItemId);

  if (!activeItem) {
    return;
  }

  const pageTitle = document.getElementById("page-title");
  const pageDescription = document.getElementById("page-description");

  if (pageTitle && activeItem.pageTitle) {
    pageTitle.textContent = activeItem.pageTitle;
  }

  if (pageDescription && activeItem.description) {
    pageDescription.textContent = activeItem.description;
  }
};

const initDeveloperModeToggle = () => {
  const toggle = document.getElementById("developer-mode-toggle");
  const checkbox = document.getElementById("developer-mode-checkbox");

  if (!toggle || !checkbox) {
    return;
  }

  const initialState = sessionStorage.getItem("developerMode") === "true";
  checkbox.checked = initialState;

  const updateToggleState = (isEnabled) => {
    toggle.classList.toggle("toggle--on", isEnabled);
  };

  updateToggleState(initialState);

  checkbox.addEventListener("change", () => {
    const isEnabled = checkbox.checked;
    sessionStorage.setItem("developerMode", String(isEnabled));
    updateToggleState(isEnabled);
  });
};

renderSideNav();
initDeveloperModeToggle();
