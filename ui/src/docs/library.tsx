import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import DocsApp from "./DocsApp";

const rootElement = document.getElementById("docs-react-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <DocsApp />
    </React.StrictMode>
  );
}
