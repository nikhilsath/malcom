import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import { DashboardApp } from "./app";

const rootElement = document.getElementById("dashboard-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <DashboardApp />
    </React.StrictMode>
  );
}
