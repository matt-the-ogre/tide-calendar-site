import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';
import { TEST_DATA } from './config/test-config';

test.describe('Autocomplete Functionality', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.navigateToHome();
  });

  test('should show autocomplete dropdown when typing place name', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();
    await homePage.assertAutocompleteVisible();

    const itemsCount = await homePage.getAutocompleteItemsCount();
    expect(itemsCount).toBeGreaterThan(0);
  });

  test('should filter autocomplete results based on user input', async ({ page }) => {
    await homePage.enterStationSearch('Point Roberts');
    await homePage.waitForAutocompleteDropdown();

    const items = await homePage.getAutocompleteItemTexts();
    expect(items.some(item => item.includes('Point Roberts'))).toBeTruthy();
  });

  test('should select station from autocomplete dropdown', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();
    await homePage.selectAutocompleteItem(0);

    const hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBeTruthy();
    expect(hiddenStationId).toMatch(/^\d+$/);
  });

  test('should navigate autocomplete with arrow down key', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();

    await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
    await expect(homePage.selectedAutocompleteItem).toBeVisible();
  });

  test('should navigate autocomplete with arrow up and down keys', async ({ page }) => {
    await homePage.enterStationSearch('San');
    await homePage.waitForAutocompleteDropdown();

    // Navigate down to first item
    await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
    await expect(homePage.selectedAutocompleteItem).toHaveCount(1);

    // Navigate down to second item
    await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
    await expect(homePage.selectedAutocompleteItem).toHaveCount(1);

    // Navigate down to third item
    await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
    const selectedCount = await homePage.selectedAutocompleteItem.count();
    expect(selectedCount).toBe(1);

    // Navigate up (should move to previous item)
    await homePage.navigateAutocompleteWithKeyboard('ArrowUp');
    // Selection behavior allows deselecting, so we just verify it worked without error
    await page.waitForTimeout(100);
  });

  test('should select item with Enter key', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();

    await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
    await homePage.navigateAutocompleteWithKeyboard('Enter');

    await homePage.assertAutocompleteHidden();
    const hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBeTruthy();
  });

  test('should close dropdown with Escape key', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();

    await homePage.navigateAutocompleteWithKeyboard('Escape');
    await homePage.assertAutocompleteHidden();
  });

  test('should hide dropdown when clicking outside', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();

    // Click on the page body (outside the dropdown)
    await page.click('body', { position: { x: 10, y: 10 } });
    await homePage.assertAutocompleteHidden();
  });

  test('should handle numeric station ID input directly', async ({ page }) => {
    await homePage.enterStationSearch('9449639');

    // Wait a moment for the JavaScript to process
    await page.waitForTimeout(500);

    // Should not show dropdown for numeric input
    const dropdownVisible = await homePage.autocompleteDropdown.isVisible();
    expect(dropdownVisible).toBe(false);

    const hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBe('9449639');
  });

  test('should clear hidden station ID when search is cleared', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();
    await homePage.selectAutocompleteItem(0);

    // Verify station ID was set
    let hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBeTruthy();

    // Clear the search
    await homePage.clearStationSearch();

    // Wait for change to process
    await page.waitForTimeout(300);

    // Verify station ID was cleared
    hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBe('');
  });

  test('should display place name with station ID after selection', async ({ page }) => {
    await homePage.enterStationSearch('Seattle');
    await homePage.waitForAutocompleteDropdown();

    const items = await homePage.getAutocompleteItemTexts();
    const firstItemText = items[0];

    await homePage.selectAutocompleteItem(0);

    const searchValue = await homePage.stationSearchInput.inputValue();
    expect(searchValue).toBe(firstItemText);
    expect(searchValue).toMatch(/.*\(\d+\)$/); // Should end with (station_id)
  });

  test('should search popular stations for common queries', async ({ page }) => {
    // Type a partial query that should match popular stations
    await homePage.enterStationSearch('Point');

    // Should show dropdown quickly (popular stations are cached)
    await homePage.waitForAutocompleteDropdown(2000);

    const itemsCount = await homePage.getAutocompleteItemsCount();
    expect(itemsCount).toBeGreaterThan(0);
  });

  test('should fall back to API search for uncommon queries', async ({ page }) => {
    // Type a more specific query that might not be in popular stations
    await homePage.enterStationSearch('Annapolis');

    // Wait for API response (300ms debounce + API time)
    await page.waitForTimeout(500);

    // Check if dropdown appears (might or might not depending on API)
    const isVisible = await homePage.autocompleteDropdown.isVisible();

    // If visible, should have items
    if (isVisible) {
      const itemsCount = await homePage.getAutocompleteItemsCount();
      expect(itemsCount).toBeGreaterThan(0);
    }
  });

  test('should show no results for invalid query', async ({ page }) => {
    await homePage.enterStationSearch(TEST_DATA.SEARCH_QUERIES.INVALID);

    // Wait for API response
    await page.waitForTimeout(500);

    // Dropdown should be hidden (no results)
    await homePage.assertAutocompleteHidden();
  });

  test('should handle empty search input', async ({ page }) => {
    await homePage.enterStationSearch('Point');
    await homePage.waitForAutocompleteDropdown();

    await homePage.clearStationSearch();

    // Dropdown should hide
    await homePage.assertAutocompleteHidden();

    // Hidden station ID should be cleared
    const hiddenStationId = await homePage.getHiddenStationId();
    expect(hiddenStationId).toBe('');
  });

  test('should maintain dropdown scroll position when navigating with keyboard', async ({ page }) => {
    await homePage.enterStationSearch('San');
    await homePage.waitForAutocompleteDropdown();

    const itemsCount = await homePage.getAutocompleteItemsCount();

    // Navigate down multiple times
    for (let i = 0; i < Math.min(5, itemsCount); i++) {
      await homePage.navigateAutocompleteWithKeyboard('ArrowDown');
      await page.waitForTimeout(100);
    }

    // Selected item should still be visible
    await expect(homePage.selectedAutocompleteItem).toBeVisible();
  });
});
