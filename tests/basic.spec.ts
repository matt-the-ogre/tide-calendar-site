import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';

test.describe('Basic Functionality Tests', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.navigateToHome();
    await homePage.waitForYearDropdownPopulated();
  });

  test('should display form elements correctly', async ({ page }) => {
    // Check that main form elements are present
    await expect(homePage.stationSearchInput).toBeVisible();
    await expect(homePage.yearSelect).toBeVisible();
    await expect(homePage.monthSelect).toBeVisible();
    await expect(homePage.generateButton).toBeVisible();

    // Check page title and header
    await expect(page).toHaveTitle(/Tide Calendar/);
    await expect(homePage.mainHeading).toContainText('Tide Calendar Generator');
  });

  test('should show error for invalid station ID', async ({ page }) => {
    // Enter invalid station ID in search field (not from autocomplete)
    await homePage.enterStationSearch('invalid123');

    // Select year and month (use first available year)
    const firstYear = await homePage.getFirstYearOption();
    await homePage.selectYear(firstYear);
    await homePage.selectMonth('01');

    // Submit form
    await homePage.clickGenerateButton();

    // Should navigate to error page with message about invalid place name
    await expect(page.locator('h2:has-text("⚠️ Error ⚠️")')).toBeVisible();
    await expect(page.locator('p:has-text("Could not find tide station")')).toBeVisible();
  });

  test('should have all 12 months in dropdown', async () => {
    const monthOptions = await homePage.getMonthOptions();

    // Should have 12 months
    expect(monthOptions.length).toBe(12);

    // Check for January and December
    await expect(homePage.monthSelect.locator('option[value="01"]')).toContainText('January');
    await expect(homePage.monthSelect.locator('option[value="12"]')).toContainText('December');
  });

  test('should validate year selection bounds', async () => {
    const yearOptions = await homePage.getYearOptions();

    // Should have options for current years - check they exist, not visibility
    await expect(homePage.yearSelect.locator('option[value="2025"]')).toHaveCount(1);
    await expect(homePage.yearSelect.locator('option[value="2040"]')).toHaveCount(1);

    // Count should be reasonable (16 years: 2025-2040)
    expect(yearOptions.length).toBe(16);
  });
});
