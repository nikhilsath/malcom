import { expect, test } from "@playwright/test";

import {
  getCopiedText,
  installClipboardMock,
  stubSmtpTool,
  stubToolSettings
} from "./support/tools";

test("copies mailbox details and sends a local test email", async ({ page }) => {
  await stubToolSettings(page);
  const smtp = await stubSmtpTool(page);
  await installClipboardMock(page);

  await page.goto("/tools/smtp.html");
  await expect(page.locator("#tools-smtp-runtime-status-value")).toHaveText("running");
  await expect(page.locator("#tools-smtp-summary-messages-value")).toHaveText("2");
  await expect(page.locator("#tools-smtp-mailbox-item-smtp-message-2")).toBeVisible();

  await page.locator("#tools-smtp-mailbox-item-smtp-message-2").click();
  await expect(page.locator("#tools-smtp-message-meta-subject-value")).toHaveText("Invoice ready");

  await page.locator("#tools-smtp-copy-email-button").click();
  await expect.poll(async () => getCopiedText(page)).toBe("inbox@example.com");

  await page.locator("#tools-smtp-copy-endpoint-button").click();
  await expect.poll(async () => getCopiedText(page)).toBe("127.0.0.1:2525");

  await page.locator("#tools-smtp-open-test-modal-button").click();
  await expect(page.locator("#tools-smtp-test-modal")).toHaveClass(/modal--open/);
  await page.locator("#tools-smtp-test-body-input").fill("Smoke test body.");
  await page.locator("#tools-smtp-test-submit-button").click();

  await expect.poll(() => smtp.testPayloads.length).toBe(1);
  await expect(page.locator("#tools-smtp-test-feedback")).toHaveText("Test email sent through the local SMTP listener.");
  await expect(page.locator("#tools-smtp-summary-messages-value")).toHaveText("3");
  await expect(page.locator("#tools-smtp-mailbox-item-smtp-message-new")).toBeVisible();

  await page.locator("#tools-smtp-mailbox-item-smtp-message-new").click();
  await page.locator("#tools-smtp-copy-raw-message-button").click();
  await expect.poll(async () => getCopiedText(page)).toContain("Smoke test body.");
});

test("saves SMTP assignment, starts and stops the listener, and sends a relay message", async ({ page }) => {
  await stubToolSettings(page);
  const smtp = await stubSmtpTool(page, {
    config: {
      enabled: false,
      target_worker_id: null,
      bind_host: "127.0.0.1",
      port: 2526,
      recipient_email: null
    },
    runtime: {
      status: "stopped",
      message: "SMTP listener stopped.",
      listening_host: null,
      listening_port: null,
      selected_machine_id: null,
      selected_machine_name: null,
      last_started_at: null,
      last_stopped_at: "2026-03-20T09:00:00.000Z",
      last_error: null,
      session_count: 0,
      message_count: 0,
      last_message_at: null,
      last_mail_from: null,
      last_recipient: null,
      recent_messages: []
    },
    inbound_identity: {
      display_address: "inbox@example.com",
      configured_recipient_email: null,
      accepts_any_recipient: true,
      listening_host: null,
      listening_port: null,
      connection_hint: "Start the listener to receive mail."
    }
  });

  await page.goto("/tools/smtp.html");
  await expect(page.locator("#tools-smtp-runtime-status-value")).toHaveText("stopped");
  await expect(page.locator("#tools-smtp-start-button")).toBeVisible();
  await expect(page.locator("#tools-smtp-stop-button")).toBeHidden();

  await page.locator("#tools-smtp-bind-host-input").fill("0.0.0.0");
  await page.locator("#tools-smtp-port-input").fill("2527");
  await page.locator("#tools-smtp-recipient-email-input").fill("alerts@example.com");
  await page.locator("#tools-smtp-save-button").click();
  await expect.poll(() => smtp.savedConfigs.length).toBe(1);
  await expect(page.locator("#tools-smtp-form-feedback")).toHaveText("SMTP assignment saved.");

  await page.locator("#tools-smtp-start-button").click();
  await expect.poll(() => smtp.startCalls.length).toBe(1);
  await expect(page.locator("#tools-smtp-runtime-status-value")).toHaveText("running");

  await page.locator("#tools-smtp-stop-button").click();
  await expect.poll(() => smtp.stopCalls.length).toBe(1);
  await expect(page.locator("#tools-smtp-runtime-status-value")).toHaveText("stopped");

  await page.locator("#tools-smtp-open-relay-modal-button").click();
  await expect(page.locator("#tools-smtp-relay-modal")).toHaveClass(/modal--open/);
  await page.locator("#tools-smtp-relay-auth-mode-input").selectOption("password");
  await expect(page.locator("#tools-smtp-relay-username-field")).toBeVisible();
  await expect(page.locator("#tools-smtp-relay-password-field")).toBeVisible();
  await page.locator("#tools-smtp-relay-host-input").fill("smtp.example.com");
  await page.locator("#tools-smtp-relay-port-input").fill("587");
  await page.locator("#tools-smtp-relay-username-input").fill("mailer");
  await page.locator("#tools-smtp-relay-password-input").fill("secret");
  await page.locator("#tools-smtp-relay-from-input").fill("alerts@example.com");
  await page.locator("#tools-smtp-relay-to-input").fill("ops@example.com");
  await page.locator("#tools-smtp-relay-subject-input").fill("Relay smoke");
  await page.locator("#tools-smtp-relay-body-input").fill("Relay body");
  await page.locator("#tools-smtp-relay-submit-button").click();

  await expect.poll(() => smtp.relayPayloads.length).toBe(1);
  await expect(page.locator("#tools-smtp-relay-feedback")).toHaveText("Email sent through the external SMTP relay.");
});
