import { render, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TriggerSettingsForm } from "../trigger-settings-form";

const triggerTypeOptions = [
  { value: "manual", label: "Manual" },
  { value: "schedule", label: "Schedule" },
  { value: "inbound_api", label: "Inbound API" },
  { value: "smtp_email", label: "SMTP email" },
  { value: "github", label: "GitHub webhook" }
];

describe("TriggerSettingsForm — GitHub trigger fields", () => {
  it("renders GitHub owner, repo, events and secret fields", () => {
    const onPatch = vi.fn();

    render(
      <TriggerSettingsForm
        idPrefix="automation-trigger"
        triggerTypeOptions={triggerTypeOptions}
        value={{
          name: "Repo watcher",
          description: "Watch a repo",
          enabled: true,
          trigger_type: "github",
          trigger_config: { github_owner: "octocat", github_repo: "hello-world", github_events: ["push"] }
        }}
        onPatch={onPatch}
      />
    );

    expect(document.querySelector("#automation-trigger-trigger-github-owner-input")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-github-repo-input")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-github-events-input")).toBeInTheDocument();
    expect(document.querySelector("#automation-trigger-trigger-github-secret-input")).toBeInTheDocument();
  });

  it("patches trigger_config when fields change", () => {
    const onPatch = vi.fn();

    render(
      <TriggerSettingsForm
        idPrefix="automation-trigger"
        triggerTypeOptions={triggerTypeOptions}
        value={{
          name: "Repo watcher",
          description: "Watch a repo",
          enabled: true,
          trigger_type: "github",
          trigger_config: {}
        }}
        onPatch={onPatch}
      />
    );

    const ownerInput = document.querySelector<HTMLInputElement>("#automation-trigger-trigger-github-owner-input");
    const repoInput = document.querySelector<HTMLInputElement>("#automation-trigger-trigger-github-repo-input");
    const eventsInput = document.querySelector<HTMLInputElement>("#automation-trigger-trigger-github-events-input");
    const secretInput = document.querySelector<HTMLInputElement>("#automation-trigger-trigger-github-secret-input");

    expect(ownerInput).not.toBeNull();
    expect(repoInput).not.toBeNull();

    fireEvent.change(ownerInput!, { target: { value: "new-owner" } });
    expect(onPatch).toHaveBeenCalled();
    const firstCallArg = onPatch.mock.calls[0][0];
    expect(firstCallArg).toHaveProperty("trigger_config");
    expect(firstCallArg.trigger_config).toHaveProperty("github_owner", "new-owner");

    fireEvent.change(repoInput!, { target: { value: "new-repo" } });
    fireEvent.change(eventsInput!, { target: { value: "push,pull_request" } });
    fireEvent.change(secretInput!, { target: { value: "s3cr3t" } });

    // last call should include github_secret
    const lastCallArg = onPatch.mock.calls[onPatch.mock.calls.length - 1][0];
    expect(lastCallArg.trigger_config.github_secret).toBe("s3cr3t");
  });
});
