import { test, expect } from '@playwright/test';

test('creates a github trigger in builder (smoke)', async ({ page }) => {
  // This is a minimal smoke test placeholder. Repository-specific test harness
  // should provide auth and navigation helpers. The real test should:
  // - open the automation builder
  // - select GitHub trigger
  // - fill owner/repo/events/secret
  // - submit and assert backend API call persisted the trigger

  await page.goto('/automation/builder');
  await expect(page).toHaveTitle(/Automation Builder/i);
});
