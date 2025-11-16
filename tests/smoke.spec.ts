import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';

/**
 * Smoke Test Suite
 * Quick validation that the site is up and basic functionality works.
 * Designed to run in under 1 minute.
 */
test.describe('Smoke Tests', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
  });

  test('homepage loads and displays form', async ({ page }) => {
    await homePage.navigateToHome();

    // Verify page title
    await expect(page).toHaveTitle(/Tide Calendar/);

    // Verify main heading
    await expect(homePage.mainHeading).toContainText('Tide Calendar Generator');

    // Verify form elements are present
    await expect(homePage.stationSearchInput).toBeVisible();
    await expect(homePage.yearSelect).toBeVisible();
    await expect(homePage.monthSelect).toBeVisible();
    await expect(homePage.generateButton).toBeVisible();
  });

  test('form dropdowns are populated', async () => {
    await homePage.navigateToHome();

    // Wait for year dropdown to be populated
    await homePage.waitForYearDropdownPopulated();

    // Check year dropdown has options
    const yearOptions = await homePage.getYearOptions();
    expect(yearOptions.length).toBeGreaterThan(0);

    // Check month dropdown has 12 months
    const monthOptions = await homePage.getMonthOptions();
    expect(monthOptions.length).toBe(12);
  });

  test('form accepts valid input', async () => {
    await homePage.navigateToHome();

    // Fill in a valid station ID
    await homePage.enterStationSearch('9449639');

    // Select year and month using helper methods
    const firstYearValue = await homePage.getFirstYearOption();
    await homePage.selectYear(firstYearValue);
    await homePage.selectMonth('01');

    // Verify button is clickable (don't actually submit to avoid long PDF generation)
    await expect(homePage.generateButton).toBeEnabled();
  });
});
