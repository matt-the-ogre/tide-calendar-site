import { test, expect } from '@playwright/test';

/**
 * Smoke Test Suite
 * Quick validation that the site is up and basic functionality works.
 * Designed to run in under 1 minute.
 */
test.describe('Smoke Tests', () => {
  test('homepage loads and displays form', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');

    // Verify page title
    await expect(page).toHaveTitle(/Tide Calendar/);

    // Verify main heading
    await expect(page.locator('h1')).toContainText('Tide Calendar Generator');

    // Verify form elements are present
    await expect(page.locator('#station_search')).toBeVisible();
    await expect(page.locator('#year')).toBeVisible();
    await expect(page.locator('#month')).toBeVisible();
    await expect(page.locator('#generate_btn')).toBeVisible();
  });

  test('form dropdowns are populated', async ({ page }) => {
    await page.goto('/');

    // Wait for JavaScript to populate year dropdown
    await page.waitForFunction(() => {
      const yearSelect = document.getElementById('year') as HTMLSelectElement;
      return yearSelect && yearSelect.options.length > 0;
    }, { timeout: 5000 });

    // Check year dropdown has options
    const yearOptions = await page.locator('#year option').count();
    expect(yearOptions).toBeGreaterThan(0);

    // Check month dropdown has 12 months
    const monthOptions = await page.locator('#month option').count();
    expect(monthOptions).toBe(12);
  });

  test('form accepts valid input', async ({ page }) => {
    await page.goto('/');

    // Wait for form to be ready
    await page.waitForSelector('#generate_btn');

    // Fill in a valid station ID
    await page.fill('#station_search', '9449639');

    // Select year and month
    await page.selectOption('#year', '2025');
    await page.selectOption('#month', '01');

    // Verify button is clickable (don't actually submit to avoid long PDF generation)
    const button = page.locator('#generate_btn');
    await expect(button).toBeEnabled();
  });
});
