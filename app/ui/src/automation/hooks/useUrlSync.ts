import { useEffect } from "react";
import { inferBuilderModeFromSearch } from "../builder-utils";

type UrlSyncArgs = {
  builderMode: any;
  setBuilderMode: (mode: any) => void;
  applyNewAutomationDraft: ({ updateUrl }?: { updateUrl?: boolean }) => void;
  loadSupportData: () => Promise<void>;
  loadAutomations: (nextSelectedId?: string) => Promise<void>;
  setAutomations: (list: any[]) => void;
  setFeedback: (msg: string) => void;
  setFeedbackTone: (tone: "success" | "error" | "") => void;
};

export const useUrlSync = ({ builderMode, setBuilderMode, applyNewAutomationDraft, loadSupportData, loadAutomations, setAutomations, setFeedback, setFeedbackTone }: UrlSyncArgs) => {
  const updateBuilderUrl = ({ automationId, useNewDraft, mode }: { automationId?: string; useNewDraft: boolean; mode: any; }) => {
    const params = new URLSearchParams();
    if (automationId) {
      params.set("id", automationId);
    } else if (useNewDraft) {
      params.set("new", "true");
    }
    params.set("mode", mode);
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  const syncModeOnlyInUrl = (mode: any) => {
    const params = new URLSearchParams(window.location.search);
    params.set("mode", mode);
    if (!params.get("id") && params.get("new") !== "true") {
      params.set("new", "true");
    }
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get("id") ?? undefined;
    const isNewDraft = params.get("new") === "true";
    const urlMode = inferBuilderModeFromSearch(window.location.search);
    setBuilderMode(urlMode);
    if (params.get("mode") !== urlMode) {
      const normalized = new URLSearchParams(params);
      normalized.set("mode", urlMode);
      window.history.replaceState({}, "", `builder.html?${normalized.toString()}`);
    }

    Promise.all([
      loadSupportData(),
      isNewDraft
        ? loadAutomations().then((list) => {
          // loadAutomations will call applyNewAutomationDraft when appropriate; keep controller behavior.
          return list;
        })
        : loadAutomations(urlId)
    ]).catch((error: Error) => {
      setFeedback(error.message);
      setFeedbackTone("error");
    });
  }, []);

  return { updateBuilderUrl, syncModeOnlyInUrl } as const;
};

export default useUrlSync;
