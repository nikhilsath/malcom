import React from "react";
import ReactDOM from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "../../styles/styles.css";
import { AutomationApp } from "./app";

const rootElement = document.getElementById("automations-react-root") || document.getElementById("automation-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AutomationApp />
    </React.StrictMode>
  );
}
