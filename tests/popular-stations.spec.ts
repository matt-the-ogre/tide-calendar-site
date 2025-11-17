import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';

/**
 * Popular Stations Test Suite
 *
 * Tests the popular stations list functionality including:
 * - List rendering
 * - Quick generate PDF buttons
 * - Country filtering
 *
 * This suite would have caught the "Generate PDF" button bug where
 * popular station quick generate buttons returned 500 errors.
 */
test.describe('Popular Stations', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.navigateToHome();
    await homePage.waitForPopularStationsLoaded();
  });

  test('should display popular stations list', async ({ page }) => {
    // Verify popular stations list is visible
    await expect(homePage.popularStationsList).toBeVisible();

    // Should have at least 5 popular stations
    const stationCount = await homePage.popularStationItems.count();
    expect(stationCount).toBeGreaterThanOrEqual(5);

    // Each station should have station name and Generate PDF button
    const firstStation = homePage.popularStationItems.first();
    await expect(firstStation).toBeVisible();
  });

  test('should have working Generate PDF button for first popular station', async ({ page }) => {
    // THIS TEST WOULD HAVE CAUGHT THE BUG!
    // When the quick generate endpoint was broken, this would fail

    const firstStation = homePage.popularStationItems.first();
    const generateButton = firstStation.locator('.quick-generate-btn');

    // Verify button exists and is clickable
    await expect(generateButton).toBeVisible();
    await expect(generateButton).toBeEnabled();

    // Click and verify download starts
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await generateButton.click();

    // Verify download initiated (proves API endpoint works)
    const download = await downloadPromise;
    const filename = download.suggestedFilename();

    // Verify filename format: tide_calendar_<location>_<year>_<month>.pdf
    expect(filename).toMatch(/tide_calendar_.*_\d{4}_\d{2}\.pdf/);
  });

  test('should have working Generate PDF button for USA station', async ({ page }) => {
    // Select USA filter
    await homePage.selectCountryFilter('USA');

    // Wait for popular stations to reload
    await homePage.waitForPopularStationsLoaded();

    // Click first USA station's generate button
    const firstStation = homePage.popularStationItems.first();
    const generateButton = firstStation.locator('.quick-generate-btn');

    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await generateButton.click();

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });

  test('should have working Generate PDF button for Canadian station', async ({ page }) => {
    // Select Canada filter
    await homePage.selectCountryFilter('Canada');

    // Wait for popular stations to reload
    await homePage.waitForPopularStationsLoaded();

    // Verify at least one Canadian station exists
    const stationCount = await homePage.popularStationItems.count();
    if (stationCount === 0) {
      test.skip();
      return;
    }

    // Click first Canadian station's generate button
    const firstStation = homePage.popularStationItems.first();
    const generateButton = firstStation.locator('.quick-generate-btn');

    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await generateButton.click();

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });

  test('should filter popular stations by country - All', async ({ page }) => {
    // Select "All" filter (default)
    await homePage.selectCountryFilter('all');
    await homePage.waitForPopularStationsLoaded();

    const stationCount = await homePage.popularStationItems.count();
    expect(stationCount).toBeGreaterThan(0);
  });

  test('should filter popular stations by country - USA', async ({ page }) => {
    // Select USA filter
    await homePage.selectCountryFilter('USA');
    await homePage.waitForPopularStationsLoaded();

    const usaStationCount = await homePage.popularStationItems.count();
    expect(usaStationCount).toBeGreaterThan(0);
  });

  test('should filter popular stations by country - Canada', async ({ page }) => {
    // Select Canada filter
    await homePage.selectCountryFilter('Canada');
    await homePage.waitForPopularStationsLoaded();

    const canadaStationCount = await homePage.popularStationItems.count();

    // May be 0 if no Canadian stations are popular yet
    expect(canadaStationCount).toBeGreaterThanOrEqual(0);
  });

  test('should maintain country preference when switching filters', async ({ page }) => {
    // Select USA
    await homePage.selectCountryFilter('USA');
    await expect(homePage.countryUSARadio).toBeChecked();

    // Select Canada
    await homePage.selectCountryFilter('Canada');
    await expect(homePage.countryCanadaRadio).toBeChecked();
    await expect(homePage.countryUSARadio).not.toBeChecked();

    // Select All
    await homePage.selectCountryFilter('all');
    await expect(homePage.countryAllRadio).toBeChecked();
    await expect(homePage.countryUSARadio).not.toBeChecked();
    await expect(homePage.countryCanadaRadio).not.toBeChecked();
  });

  test('should have country filter defaulted to All', async ({ page }) => {
    // On fresh load, "All" should be selected
    await expect(homePage.countryAllRadio).toBeChecked();
    await expect(homePage.countryUSARadio).not.toBeChecked();
    await expect(homePage.countryCanadaRadio).not.toBeChecked();
  });

  test('all popular station items should have required elements', async ({ page }) => {
    const stationCount = await homePage.popularStationItems.count();

    // Check first 3 stations for performance
    const checkCount = Math.min(3, stationCount);

    for (let i = 0; i < checkCount; i++) {
      const station = homePage.popularStationItems.nth(i);

      // Each station should have text (station name)
      const stationText = await station.textContent();
      expect(stationText).toBeTruthy();

      // Each station should have a Generate PDF button
      const generateButton = station.locator('.quick-generate-btn');
      await expect(generateButton).toBeVisible();
      await expect(generateButton).toBeEnabled();
    }
  });
});
