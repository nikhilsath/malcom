import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import { AutomationLibraryApp } from "./library";

const rootElement = document.getElementById("automations-library-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AutomationLibraryApp />
    </React.StrictMode>
  );
}
