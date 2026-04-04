import type { BuilderMode } from "../builder-types";

export const useBuilderUrlSync = () => {
  const updateBuilderUrl = ({
    automationId,
    useNewDraft,
    mode
  }: {
    automationId?: string;
    useNewDraft: boolean;
    mode: BuilderMode;
  }) => {
    const params = new URLSearchParams();
    if (automationId) {
      params.set("id", automationId);
    } else if (useNewDraft) {
      params.set("new", "true");
    }
    params.set("mode", mode);
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  const syncModeOnlyInUrl = (mode: BuilderMode) => {
    const params = new URLSearchParams(window.location.search);
    params.set("mode", mode);
    if (!params.get("id") && params.get("new") !== "true") {
      params.set("new", "true");
    }
    window.history.replaceState({}, "", `builder.html?${params.toString()}`);
  };

  return { updateBuilderUrl, syncModeOnlyInUrl };
};
