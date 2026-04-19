import React from "react";
import ReactDOM from "react-dom/client";
import "@xyflow/react/dist/style.css";
import "../../styles/styles.css";
import { AutomationApp } from "./app";

declare global {
  interface Window {
    __MALCOM_PLATFORM_EMBED_CONTEXT__?: Record<string, unknown>;
  }
}

const rootElement = document.getElementById("automations-react-root") || document.getElementById("automation-react-root");

const installHostedEmbedCompatibility = (element: HTMLElement) => {
  if (window.parent === window) {
    return;
  }

  const search = new URLSearchParams(window.location.search);
  const handshakeChannel = search.get("platform_handshake_channel");
  if (!handshakeChannel) {
    return;
  }

  const notifyParent = (type: "ready" | "resize" | "teardown", detail: Record<string, unknown> = {}) => {
    window.parent.postMessage(
      {
        channel: handshakeChannel,
        type,
        detail
      },
      "*"
    );
  };

  const resizeObserver = new ResizeObserver(() => {
    notifyParent("resize", { height: Math.ceil(element.getBoundingClientRect().height) });
  });
  resizeObserver.observe(element);

  const messageListener = (event: MessageEvent) => {
    const data = event.data;
    if (!data || typeof data !== "object" || data.channel !== handshakeChannel) {
      return;
    }
    if (data.type === "mount") {
      window.__MALCOM_PLATFORM_EMBED_CONTEXT__ = data.payload || {};
      notifyParent("ready", {
        route: window.location.pathname,
        compatibilityMode: search.get("platform_embed_mode") || "legacy-backend-ui"
      });
    }
  };

  const teardownListener = () => {
    notifyParent("teardown", { route: window.location.pathname });
    window.removeEventListener("message", messageListener);
    window.removeEventListener("beforeunload", teardownListener);
    resizeObserver.disconnect();
  };

  window.addEventListener("message", messageListener);
  window.addEventListener("beforeunload", teardownListener);
};

if (rootElement) {
  installHostedEmbedCompatibility(rootElement);
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <AutomationApp />
    </React.StrictMode>
  );
}
