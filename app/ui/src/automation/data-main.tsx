import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import { AutomationDataApp } from "./data";

const rootElement = document.getElementById("automations-data-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AutomationDataApp />
    </React.StrictMode>
  );
}
