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

const getBaseUrl = () => {
  if (window.location.protocol === "file:" || window.location.origin === "null") {
    return "http://localhost:8000";
  }

  if (window.location.origin === "http://localhost:8000" || window.location.origin === "http://127.0.0.1:8000") {
    return "";
  }

  return window.location.origin;
};

const fetchJson = async (path, options = {}) => {
  const response = await fetch(`${getBaseUrl()}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || "Navigation request failed.");
  }

  return payload;
};

const getDashboardHashRoute = () => {
  const currentHash = window.location.hash || "";
  return currentHash.startsWith("#/") ? currentHash.slice(1) : "";
};

const getDashboardItemRoute = (item) => {
  if (!item?.href?.startsWith("dashboard/")) {
    return null;
  }

  const [, pageName] = item.href.split("dashboard/");
  return `/${pageName.replace(/\.html$/, "")}`;
};

const getDashboardItemRoutes = (item) => item?.dashboardRoutes?.length
  ? item.dashboardRoutes
  : [getDashboardItemRoute(item)].filter(Boolean);

const getItemHrefs = (item) => [item.href, ...(item.aliases || [])];

const getNavItemHref = (sectionId, pathPrefix, item) => {
  if (sectionId !== "dashboard") {
    return resolveShellHref(pathPrefix, item.href);
  }

  const route = getDashboardItemRoutes(item)[0];

  if (!route) {
    return resolveShellHref(pathPrefix, item.href);
  }

  return `#${route}`;
};

const getTopNavActiveId = () => {
  const section = document.body?.dataset.section;
  const activeItem = topNavItems.find((item) => item.section === section);
  return activeItem?.id || null;
};

const getToolItemsWithEnabledState = async () => {
  const sectionConfig = getSectionConfig("tools");

  if (!sectionConfig) {
    return [];
  }

  const [catalogItem, ...manifestToolItems] = sectionConfig.items;
  const toolsDirectory = await fetchJson("/api/v1/tools");
  const enabledToolIds = new Set(
    toolsDirectory
      .filter((tool) => tool.enabled)
      .map((tool) => tool.id)
  );

  return [
    catalogItem,
    ...manifestToolItems.filter((item) => enabledToolIds.has(item.id.replace("sidenav-tools-", "")))
  ];
};

const getSectionConfigForRender = async (sectionId) => {
  const sectionConfig = getSectionConfig(sectionId);

  if (!sectionConfig) {
    return null;
  }

  if (sectionId !== "tools") {
    return sectionConfig;
  }

  try {
    return {
      ...sectionConfig,
      items: await getToolItemsWithEnabledState()
    };
  } catch (error) {
    console.error("Unable to load live tool directory for sidenav.", error);
    return sectionConfig;
  }
};

const getActiveSideNavItem = (items, fallbackItemId) => {
  const section = document.body?.dataset.section;
  const currentHash = window.location.hash;
  const currentPath = `${window.location.pathname}${currentHash}`;

  if (section === "dashboard") {
    const currentRoute = getDashboardHashRoute() || document.body?.dataset.dashboardRoute || "/home";
    const matchedDashboardItem = items.find((item) => getDashboardItemRoutes(item).includes(currentRoute));

    if (matchedDashboardItem) {
      return matchedDashboardItem.id;
    }
  }

  const matchedItem = items.find((item) => getItemHrefs(item).some((href) => currentPath.endsWith(href) || currentHash && href.endsWith(currentHash)));

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

  inner.append(nav);
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

const renderSideNav = async () => {
  const body = document.body;
  const sideNav = document.getElementById("sidenav");

  if (!body || !sideNav) {
    return;
  }

  const sectionConfig = await getSectionConfigForRender(body.dataset.section);

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
        href: getNavItemHref(sectionConfig.id, pathPrefix, item)
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

  if (activeItem?.pageTitle) {
    document.title = `Malcom - ${activeItem.pageTitle}`;
  }

  initSidebarCollapse();
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

const closeInfoBadges = () => {
  document.querySelectorAll(".info-badge[aria-controls]").forEach((badge) => {
    const contentId = badge.getAttribute("aria-controls");
    badge.setAttribute("aria-expanded", "false");
    if (contentId) {
      const content = document.getElementById(contentId);
      if (content) {
        content.hidden = true;
      }
    }
  });
};

const initInfoBadges = () => {
  if (document.body.dataset.infoBadgeListenerBound === "true") {
    return;
  }

  document.body.dataset.infoBadgeListenerBound = "true";

  document.addEventListener("click", (event) => {
    const target = event.target;

    if (!(target instanceof Element)) {
      closeInfoBadges();
      return;
    }

    const badge = target.closest(".info-badge[aria-controls]");
    if (badge instanceof HTMLElement) {
      event.stopPropagation();
      const contentId = badge.getAttribute("aria-controls");

      if (!contentId) {
        return;
      }

      const content = document.getElementById(contentId);

      if (!content) {
        return;
      }

      const shouldOpen = badge.getAttribute("aria-expanded") !== "true";
      closeInfoBadges();
      badge.setAttribute("aria-expanded", String(shouldOpen));
      content.hidden = !shouldOpen;
      return;
    }

    if (target.closest(".info-badge")) {
      return;
    }

    const openBadges = document.querySelectorAll(".info-badge[aria-expanded='true']");
    for (const badge of openBadges) {
      const contentId = badge.getAttribute("aria-controls");
      if (contentId) {
        const content = document.getElementById(contentId);
        if (content && content.contains(target)) {
          return;
        }
      }
    }

    closeInfoBadges();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeInfoBadges();
    }
  });
};

renderTopNav();
renderSideNav();
window.addEventListener("hashchange", () => {
  renderSideNav();
});
window.addEventListener("malcom:tools-directory-updated", () => {
  renderSideNav();
});
initInfoBadges();
logPageView();
