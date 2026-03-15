import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import { createDashboardHashRouter } from "./app";
import { RouterProvider } from "react-router-dom";

const rootElement = document.getElementById("dashboard-react-root");

const ensureDashboardHashRoute = () => {
  const initialRoute = document.body.dataset.dashboardRoute || "/overview";

  if (!window.location.hash) {
    window.location.hash = `#${initialRoute}`;
  }
};

if (rootElement) {
  ensureDashboardHashRoute();

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <RouterProvider router={createDashboardHashRouter()} />
    </React.StrictMode>
  );
}
