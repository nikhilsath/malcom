import type { Page } from "@playwright/test";

export const installClipboardTracker = async (page: Page) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (value: string) => {
          (window as unknown as { __copiedText?: string }).__copiedText = value;
        }
      }
    });
  });
};

export const readClipboardTracker = async (page: Page) =>
  page.evaluate(() => (window as unknown as { __copiedText?: string }).__copiedText || "");
