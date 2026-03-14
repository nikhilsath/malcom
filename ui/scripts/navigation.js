import { getSectionConfig, resolveShellHref, shellBrand, topNavItems } from "./shell-config.js";

const createElement = (tagName, attributes = {}, textContent = "") => {
  const element = document.createElement(tagName);

  Object.entries(attributes).forEach(([name, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    if (name === "className") {
      element.className = value;
      return;
    }

    element.setAttribute(name, String(value));
  });

  if (textContent) {
    element.textContent = textContent;
  }

  return element;
};

const getShellPathPrefix = () => document.body?.dataset.shellPathPrefix || "";

const getTopNavActiveId = () => {
  const section = document.body?.dataset.section;
  const activeItem = topNavItems.find((item) => item.section === section);
  return activeItem?.id || null;
};

const getActiveSideNavItem = (items, fallbackItemId) => {
  const currentHash = window.location.hash;
  const currentPath = `${window.location.pathname}${currentHash}`;

  const matchedItem = items.find((item) => currentPath.endsWith(item.href) || currentHash && item.href.endsWith(currentHash));

  if (matchedItem) {
    return matchedItem.id;
  }

  return fallbackItemId;
};

const renderTopNav = () => {
  const topNavRoot = document.getElementById("topnav");

  if (!topNavRoot) {
    return;
  }

  const pathPrefix = getShellPathPrefix();
  const activeItemId = getTopNavActiveId();
  const container = createElement("div", { className: "container" });
  const inner = createElement("div", { className: "topnav__inner", id: "topnav-inner" });
  const nav = createElement("nav", { className: "topnav__nav", id: "topnav-primary" });

  topNavItems.forEach((item) => {
    const link = createElement(
      "a",
      {
        id: item.id,
        href: resolveShellHref(pathPrefix, item.href)
      },
      item.label
    );

    if (item.id === activeItemId) {
      link.setAttribute("aria-current", "page");
    }

    nav.appendChild(link);
  });

  const developerModeArea = createElement("div", { className: "topnav__dev", id: "dev-mode-area" });
  const toggle = createElement("label", { className: "toggle", id: "developer-mode-toggle" });
  const checkbox = createElement("input", {
    type: "checkbox",
    class: "sr-only",
    id: "developer-mode-checkbox"
  });
  const slider = createElement("div", {
    className: "toggle__slider",
    id: "developer-mode-slider",
    "aria-hidden": "true"
  });
  const knob = createElement("div", {
    className: "toggle__knob",
    id: "developer-mode-knob",
    "aria-hidden": "true"
  });
  const label = createElement("span", { className: "toggle__label" }, "Developer Mode");

  slider.appendChild(knob);
  toggle.append(checkbox, slider, label);
  developerModeArea.appendChild(toggle);
  inner.append(nav, developerModeArea);
  container.appendChild(inner);

  topNavRoot.className = "topnav";
  topNavRoot.replaceChildren(container);
};

const renderSidebarFooter = (sectionConfig) => {
  const footerConfig = sectionConfig?.footer;

  if (!footerConfig) {
    return null;
  }

  const footer = createElement("div", { className: "sidenav__footer", id: "sidebar-footer" });

  if (footerConfig.kind === "button") {
    const button = createElement(
      "button",
      {
        id: footerConfig.id,
        className: footerConfig.className,
        ...footerConfig.attributes
      },
      footerConfig.label
    );
    footer.appendChild(button);
  }

  if (footerConfig.kind === "note") {
    footer.appendChild(
      createElement(
        "p",
        {
          id: footerConfig.id,
          className: footerConfig.className
        },
        footerConfig.text
      )
    );
  }

  return footer;
};

const renderSideNav = () => {
  const body = document.body;
  const sideNav = document.getElementById("sidenav");

  if (!body || !sideNav) {
    return;
  }

  const sectionConfig = getSectionConfig(body.dataset.section);

  if (!sectionConfig) {
    return;
  }

  const pathPrefix = getShellPathPrefix();
  const activeItemId = getActiveSideNavItem(sectionConfig.items, body.dataset.sidenavItem || sectionConfig.items[0]?.id);
  const header = createElement("div", { className: "sidenav__header", id: "sidebar-header" });
  const brand = createElement("a", {
    href: resolveShellHref(pathPrefix, shellBrand.homeHref),
    id: "sidebar-home-link",
    className: "sidenav__brand project-brand",
    "aria-label": "Malcom home"
  });
  const brandIcon = createElement("img", {
    src: shellBrand.iconHref,
    alt: shellBrand.iconAlt,
    id: "sidebar-project-icon",
    class: "project-icon"
  });
  const brandTitle = createElement("span", {
    className: "sidenav__brand-title",
    id: "sidebar-project-title"
  }, shellBrand.title);
  const toggle = createElement("button", {
    type: "button",
    id: "sidebar-collapse-toggle",
    className: "sidenav__collapse-button",
    "aria-controls": "sidebar-navigation",
    "aria-expanded": "true",
    "aria-label": "Collapse sidebar"
  });
  const toggleIcon = createElement("span", {
    id: "sidebar-collapse-icon",
    className: "sidenav__collapse-icon",
    "aria-hidden": "true"
  });
  const nav = createElement("nav", { className: "sidenav__nav", id: "sidebar-navigation" });
  const list = createElement("ul", { className: "sidenav__list", id: "sidebar-navigation-list" });

  sectionConfig.items.forEach((item) => {
    const listItem = createElement("li", { className: "sidenav__item" });
    const link = createElement(
      "a",
      {
        className: "sidenav__link",
        id: item.id,
        href: resolveShellHref(pathPrefix, item.href)
      },
      item.label
    );

    if (item.id === activeItemId) {
      link.setAttribute("aria-current", "page");
    }

    listItem.appendChild(link);
    list.appendChild(listItem);
  });

  brand.append(brandIcon, brandTitle);
  toggle.appendChild(toggleIcon);
  header.append(brand, toggle);
  nav.appendChild(list);

  sideNav.className = "sidenav";
  sideNav.dataset.section = sectionConfig.id;
  sideNav.replaceChildren(header, nav);

  const footer = renderSidebarFooter(sectionConfig);

  if (footer) {
    sideNav.appendChild(footer);
  }

  const activeItem = sectionConfig.items.find((item) => item.id === activeItemId);
  const pageTitle = document.getElementById("page-title");
  const pageDescription = document.getElementById("page-description");

  if (pageTitle && activeItem?.pageTitle) {
    pageTitle.textContent = activeItem.pageTitle;
  }

  if (pageDescription && activeItem?.description) {
    pageDescription.textContent = activeItem.description;
  }
};

const emitRuntimeLog = (entry) => {
  window.MalcomLogStore?.log(entry);
};

const logPageView = () => {
  const body = document.body;

  if (!body || body.dataset.logPageView === "false") {
    return;
  }

  emitRuntimeLog({
    source: "ui.navigation",
    category: "navigation",
    action: "page_view",
    level: "info",
    message: `Visited ${document.title || "Malcom page"}.`,
    context: {
      path: window.location.pathname,
      section: body.dataset.section || null,
      topnavItem: getTopNavActiveId()
    }
  });
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
    window.dispatchEvent(
      new CustomEvent("malcom:developerModeChanged", {
        detail: { enabled: isEnabled }
      })
    );
    emitRuntimeLog({
      source: "ui.navigation",
      category: "settings",
      action: "developer_mode_toggled",
      level: isEnabled ? "warning" : "info",
      message: `Developer mode ${isEnabled ? "enabled" : "disabled"}.`,
      details: {
        developerMode: isEnabled
      },
      context: {
        path: window.location.pathname
      }
    });
  });
};

const initSidebarCollapse = () => {
  const body = document.body;
  const sideNav = document.getElementById("sidenav");
  const toggle = document.getElementById("sidebar-collapse-toggle");

  if (!body || !sideNav || !toggle) {
    return;
  }

  const storageKey = "sidebarCollapsed";

  const applySidebarState = (isCollapsed) => {
    body.classList.toggle("sidebar-collapsed", isCollapsed);
    sideNav.dataset.collapsed = String(isCollapsed);
    toggle.setAttribute("aria-expanded", String(!isCollapsed));
    toggle.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
  };

  const initialState = sessionStorage.getItem(storageKey) === "true";
  applySidebarState(initialState);

  toggle.addEventListener("click", () => {
    const nextState = !body.classList.contains("sidebar-collapsed");
    sessionStorage.setItem(storageKey, String(nextState));
    applySidebarState(nextState);
    emitRuntimeLog({
      source: "ui.navigation",
      category: "navigation",
      action: nextState ? "sidebar_collapsed" : "sidebar_expanded",
      level: "info",
      message: `Sidebar ${nextState ? "collapsed" : "expanded"}.`,
      context: {
        path: window.location.pathname,
        section: body.dataset.section || null
      }
    });
  });
};

renderTopNav();
renderSideNav();
window.addEventListener("hashchange", renderSideNav);
initDeveloperModeToggle();
initSidebarCollapse();
logPageView();
