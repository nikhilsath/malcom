import { expect, test } from "@playwright/test";

test("creates and persists a GitHub trigger automation through the builder", async ({ page, request }) => {
  const automationName = `GitHub trigger ${Date.now()}`;
  const automationDescription = "Saves GitHub trigger settings through the real builder UI.";
  const workflowNameInput = page.locator("#automations-workflow-name-input");
  const workflowDescriptionInput = page.locator("#automations-workflow-description-input");

  await page.goto("/automations/builder.html?new=true");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("#automations-builder-mode-guided")).toHaveAttribute("aria-pressed", "true");
  await page.locator("#automations-new-button").click();
  await expect(workflowNameInput).toHaveValue("");
  await expect(workflowDescriptionInput).toHaveValue("");

  await workflowNameInput.fill(automationName);
  await workflowDescriptionInput.fill(automationDescription);
  await expect(workflowNameInput).toHaveValue(automationName);
  await expect(workflowDescriptionInput).toHaveValue(automationDescription);
  await expect(page.locator("#automations-guided-item-name-state")).toHaveText("Done");
  await page.locator("#automations-guided-item-trigger-action").click();
  await expect(page.locator("#automations-editor-modal-title")).toContainText("Edit");

  await page.locator("#automations-editor-modal-trigger-back").click();
  await expect(page.locator("#automations-editor-modal-title")).toHaveText("Choose trigger type");
  await page.locator("#automations-trigger-modal-trigger-type-option-github").click();
  await expect(page.locator("#automations-editor-modal-title")).toContainText(/github/i);

  await page.locator("#automations-trigger-modal-trigger-github-owner-input").fill("octocat");
  await page.locator("#automations-trigger-modal-trigger-github-repo-input").fill("hello-world");
  await page.locator("#automations-trigger-modal-trigger-github-events-input").fill("push,pull_request");
  await page.locator("#automations-trigger-modal-trigger-github-secret-input").fill("super-secret");
  await page.locator("#automations-editor-modal-done").click();

  await page.locator("#automations-guided-item-step-action").click();
  await expect(page.locator("#add-step-modal")).toBeVisible();
  await page.locator("#add-step-type-outbound_request").click();
  await page.locator("#add-step-name-input").fill("Notify webhook");
  await page.locator("#add-step-http-url-input").fill("https://example.com/github-hook");
  await page.locator("#add-step-http-payload-input").fill("{\"event\":\"github\"}");
  await page.locator("#add-step-modal-confirm").click();
  await expect(page.locator("#add-step-modal")).toBeHidden();

  if ((await workflowNameInput.inputValue()) !== automationName) {
    await workflowNameInput.fill(automationName);
  }
  if ((await workflowDescriptionInput.inputValue()) !== automationDescription) {
    await workflowDescriptionInput.fill(automationDescription);
  }
  await expect(workflowNameInput).toHaveValue(automationName);
  await expect(workflowDescriptionInput).toHaveValue(automationDescription);
  await expect(page.locator("#automations-guided-item-name-state")).toHaveText("Done");

  await page.locator("#automations-guided-save-button").click();
  await expect(page.locator("#automations-feedback-banner")).toContainText(/Automation (created|updated)\./);
  await expect(page).toHaveURL(/builder\.html\?id=/);

  const automationId = new URL(page.url()).searchParams.get("id");
  expect(automationId).toBeTruthy();

  const response = await request.get(`/api/v1/automations/${automationId}`);
  expect(response.ok()).toBeTruthy();

  const automation = await response.json();
  expect(automation.trigger_type).toBe("github");
  expect(automation.trigger_config).toMatchObject({
    github_owner: "octocat",
    github_repo: "hello-world",
    github_events: ["push", "pull_request"],
    github_secret: "super-secret"
  });

  await page.reload();
  await expect(workflowNameInput).toHaveValue(automationName);
  await expect(workflowDescriptionInput).toHaveValue(automationDescription);
  await page.locator("#automations-guided-item-trigger-action").click();
  await expect(page.locator("#automations-trigger-modal-trigger-github-owner-input")).toHaveValue("octocat");
  await expect(page.locator("#automations-trigger-modal-trigger-github-repo-input")).toHaveValue("hello-world");
  await expect(page.locator("#automations-trigger-modal-trigger-github-events-input")).toHaveValue("push,pull_request");
  await expect(page.locator("#automations-trigger-modal-trigger-github-secret-input")).toHaveValue("super-secret");
});
