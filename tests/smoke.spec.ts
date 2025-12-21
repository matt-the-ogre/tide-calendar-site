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

  test('popular stations list loads with Generate PDF buttons', async ({ page }) => {
    await homePage.navigateToHome();

    // Wait for popular stations to load
    await homePage.waitForPopularStationsLoaded();

    // Verify popular stations list is visible
    await expect(homePage.popularStationsList).toBeVisible();

    // Verify at least 5 popular stations are displayed
    const stationCount = await homePage.popularStationItems.count();
    expect(stationCount).toBeGreaterThanOrEqual(5);

    // Verify first station has a Generate PDF button
    const firstButton = homePage.popularStationItems.first().locator('.quick-generate-btn');
    await expect(firstButton).toBeVisible();
    await expect(firstButton).toBeEnabled();
  });

  test('popular station Generate PDF button works', async ({ page }) => {
    // THIS TEST WOULD HAVE CAUGHT THE BUG!
    // Critical smoke test to verify quick generate endpoint works

    await homePage.navigateToHome();
    await homePage.waitForPopularStationsLoaded();

    // Click first popular station's Generate PDF button
    const firstButton = page.locator('.quick-generate-btn').first();
    await expect(firstButton).toBeVisible();
    await expect(firstButton).toBeEnabled();

    // Verify download starts (proves API endpoint works)
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await firstButton.click();

    const download = await downloadPromise;
    const filename = download.suggestedFilename();

    // Verify filename format
    expect(filename).toMatch(/tide_calendar_.*_\d{4}_\d{2}\.pdf/);
  });

  test('country filter radio buttons are visible and functional', async ({ page }) => {
    await homePage.navigateToHome();

    // Verify all three radio buttons are visible
    await expect(homePage.countryAllRadio).toBeVisible();
    await expect(homePage.countryUSARadio).toBeVisible();
    await expect(homePage.countryCanadaRadio).toBeVisible();

    // Verify "All" is selected by default
    await expect(homePage.countryAllRadio).toBeChecked();

    // Click USA filter
    await homePage.countryUSARadio.check();
    await expect(homePage.countryUSARadio).toBeChecked();

    // Wait for popular stations to reload
    await homePage.waitForPopularStationsLoaded();

    // Verify popular stations still displayed
    const stationCount = await homePage.popularStationItems.count();
    expect(stationCount).toBeGreaterThan(0);
  });
});
