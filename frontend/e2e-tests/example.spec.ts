import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('/');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Aperilex/);
});

test('navigate to filings page', async ({ page }) => {
  await page.goto('/');

  // Click the filings link
  await page.click('text=Filings');

  // Expects page to have a heading with the name of Filings
  await expect(page.getByRole('heading', { name: 'Filings' })).toBeVisible();
});
