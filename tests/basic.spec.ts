import { test, expect } from '@playwright/test';

test.describe('Basic Functionality Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    // Wait for JavaScript to populate the year dropdown
    await page.waitForFunction(() => {
      const yearSelect = document.getElementById('year') as HTMLSelectElement;
      return yearSelect.options.length > 0;
    });
  });

  test('should display form elements correctly', async ({ page }) => {
    // Check that main form elements are present
    await expect(page.locator('#station_search')).toBeVisible();
    await expect(page.locator('#year')).toBeVisible();
    await expect(page.locator('#month')).toBeVisible();
    await expect(page.locator('#generate_btn')).toBeVisible();
    
    // Check page title and header
    await expect(page).toHaveTitle(/Tide Calendar/);
    await expect(page.locator('h1')).toContainText('Tide Calendar Generator');
  });

  test('should show error for invalid station ID', async ({ page }) => {
    // Enter invalid station ID
    await page.fill('#station_search', 'invalid123');
    
    // Select year and month (use years that are available: 2025-2040)
    await page.selectOption('#year', '2025');
    await page.selectOption('#month', '01');
    
    // Submit form
    await page.click('#generate_btn');
    
    // Should navigate to error page
    await expect(page.locator('h2')).toContainText('⚠️ Error ⚠️');
    await expect(page.locator('p')).toContainText('Station ID must be a number');
  });

  test('should have all 12 months in dropdown', async ({ page }) => {
    const monthSelect = page.locator('#month');
    const monthOptions = await monthSelect.locator('option').count();
    
    // Should have 12 months
    expect(monthOptions).toBe(12);
    
    // Check for January and December
    await expect(monthSelect.locator('option[value="01"]')).toContainText('January');
    await expect(monthSelect.locator('option[value="12"]')).toContainText('December');
  });

  test('should validate year selection bounds', async ({ page }) => {
    // Check that year dropdown has reasonable bounds (2025-2040)
    const yearSelect = page.locator('#year');
    
    // Should have options for current years
    await expect(yearSelect.locator('option[value="2025"]')).toBeVisible();
    await expect(yearSelect.locator('option[value="2040"]')).toBeVisible();
    
    // Count should be reasonable (16 years: 2025-2040)
    const yearOptions = await yearSelect.locator('option').count();
    expect(yearOptions).toBe(16);
  });
});
