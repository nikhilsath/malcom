import React from "react";
import ReactDOM from "react-dom/client";
import "../../styles/styles.css";
import DocsHomepage from "./DocsHomepage";

const rootElement = document.getElementById("docs-homepage-root");

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <DocsHomepage />
    </React.StrictMode>
  );
}
