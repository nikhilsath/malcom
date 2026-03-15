import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import { AutomationOverviewApp } from "./overview";

const rootElement = document.getElementById("automations-overview-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AutomationOverviewApp />
    </React.StrictMode>
  );
}
