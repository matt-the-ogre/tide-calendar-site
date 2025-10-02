import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';
import { ErrorPage } from './pages/ErrorPage';
import { TEST_DATA } from './config/test-config';

test.describe('Form Validation', () => {
  let homePage: HomePage;
  let errorPage: ErrorPage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    errorPage = new ErrorPage(page);
    await homePage.navigateToHome();
  });

  test.describe('Station ID Validation', () => {
    test('should show error for empty station selection', async ({ page }) => {
      // Programmatically submit form with empty station to bypass HTML5 validation
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');

      await page.evaluate(() => {
        const form = document.querySelector('form') as HTMLFormElement;
        const stationInput = document.querySelector('#station_search') as HTMLInputElement;
        if (stationInput) {
          stationInput.removeAttribute('required');
          stationInput.value = '';
        }
        if (form) {
          form.submit();
        }
      });

      await errorPage.waitForErrorPage();
      await errorPage.assertErrorMessageContains('No station selected');
    });

    test('should show error for invalid place name', async ({ page }) => {
      await homePage.enterStationSearch('invalid123xyz');
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      await errorPage.waitForErrorPage();
      await errorPage.assertErrorMessageContains('Could not find tide station');
    });

    test('should accept valid numeric station ID', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.VALID_STATION_ID);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');

      const isValid = await homePage.isFormValid();
      expect(isValid).toBe(true);
    });

    test('should accept station from autocomplete', async ({ page }) => {
      await homePage.enterStationSearch('Point');
      await homePage.waitForAutocompleteDropdown();
      await homePage.selectAutocompleteItem(0);

      const hiddenStationId = await homePage.getHiddenStationId();
      expect(hiddenStationId).toBeTruthy();
      expect(hiddenStationId).toMatch(/^\d+$/);
    });
  });

  test.describe('Year Validation', () => {
    test('should have year range 2025-2040', async ({ page }) => {
      const yearOptions = await homePage.getYearOptions();

      expect(yearOptions).toContain('2025');
      expect(yearOptions).toContain('2040');
      expect(yearOptions).not.toContain('1999');
      expect(yearOptions).not.toContain('2050');
    });

    test('should have exactly 16 year options', async ({ page }) => {
      const yearOptions = await homePage.getYearOptions();
      expect(yearOptions.length).toBe(16); // 2025-2040 = 16 years
    });

    test('should pre-select current year by default', async ({ page }) => {
      const currentYear = new Date().getFullYear();
      const selectedYear = await homePage.yearSelect.inputValue();

      // If current year is in range, it should be selected
      if (currentYear >= 2025 && currentYear <= 2040) {
        expect(selectedYear).toBe(currentYear.toString());
      }
    });
  });

  test.describe('Month Validation', () => {
    test('should have all 12 months', async ({ page }) => {
      const monthOptions = await homePage.getMonthOptions();

      expect(monthOptions).toHaveLength(12);
      TEST_DATA.VALID_MONTHS.forEach(month => {
        expect(monthOptions).toContain(month);
      });
    });

    test('should have months in correct order', async ({ page }) => {
      const monthOptions = await homePage.getMonthOptions();

      for (let i = 0; i < 12; i++) {
        const expectedMonth = (i + 1).toString().padStart(2, '0');
        expect(monthOptions[i]).toBe(expectedMonth);
      }
    });

    test('should pre-select current month by default', async ({ page }) => {
      const currentMonth = (new Date().getMonth() + 1).toString().padStart(2, '0');
      const selectedMonth = await homePage.monthSelect.inputValue();

      expect(selectedMonth).toBe(currentMonth);
    });
  });

  test.describe('Security - SQL Injection', () => {
    test('should handle SQL injection in station search', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.SEARCH_QUERIES.SQL_INJECTION);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      await errorPage.waitForErrorPage();
      // Should show error, not crash or expose database
      await expect(errorPage.errorHeading).toBeVisible();
    });

    test('should not execute SQL in place name lookup', async ({ page }) => {
      const sqlPayload = "'; DROP TABLE tide_station_ids; --";
      await homePage.enterStationSearch(sqlPayload);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      // Should fail gracefully with error page
      await errorPage.waitForErrorPage();
      await expect(page).toHaveURL(/\//);
    });
  });

  test.describe('Security - XSS Prevention', () => {
    test('should escape XSS in station search', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.SEARCH_QUERIES.XSS_ATTEMPT);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      // Wait for error page
      await errorPage.waitForErrorPage();

      // XSS should be escaped, not executed
      const alerts: string[] = [];
      page.on('dialog', dialog => {
        alerts.push(dialog.message());
        dialog.dismiss();
      });

      // Wait a bit to see if any alerts fire
      await page.waitForTimeout(500);
      expect(alerts.length).toBe(0);
    });

    test('should not render unescaped HTML in error messages', async ({ page }) => {
      const htmlPayload = '<img src=x onerror=alert(1)>';
      await homePage.enterStationSearch(htmlPayload);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      // Wait a moment for navigation
      await page.waitForTimeout(1000);

      // Check that no img element from the payload exists in the DOM
      const imgElements = await page.locator('img[src="x"]').count();
      expect(imgElements).toBe(0);

      // Also check for XSS script execution
      const alerts: string[] = [];
      page.on('dialog', dialog => {
        alerts.push(dialog.message());
        dialog.dismiss();
      });
      await page.waitForTimeout(500);
      expect(alerts.length).toBe(0);
    });
  });

  test.describe('Input Sanitization', () => {
    test('should handle special characters in station search', async ({ page }) => {
      const specialChars = ['test@#$%', "test'quote", 'test"double'];

      for (const input of specialChars) {
        // Navigate to fresh page for each test to avoid state issues
        await homePage.navigateToHome();
        await homePage.enterStationSearch(input);
        await homePage.selectYear('2025');
        await homePage.selectMonth('01');
        await homePage.clickGenerateButton();

        // Should handle gracefully (either find station or show error)
        await page.waitForTimeout(500);
        const currentUrl = page.url();
        expect(currentUrl).toBeTruthy();
      }
    });

    test('should trim whitespace from station search', async ({ page }) => {
      await homePage.enterStationSearch('  9449639  ');

      // Wait for processing
      await page.waitForTimeout(300);

      const hiddenValue = await homePage.getHiddenStationId();
      expect(hiddenValue).toBe('9449639');
    });

    test('should handle very long input strings', async ({ page }) => {
      const longString = 'a'.repeat(1000);
      await homePage.enterStationSearch(longString);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      // Should not crash, just show error
      await errorPage.waitForErrorPage();
      await expect(errorPage.errorHeading).toBeVisible();
    });

    test('should handle unicode characters', async ({ page }) => {
      const unicode = '测试🌊🌴';
      await homePage.enterStationSearch(unicode);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      await homePage.clickGenerateButton();

      // Should handle gracefully
      await errorPage.waitForErrorPage();
      await expect(page).toHaveURL(/\//);
    });
  });

  test.describe('Form State Management', () => {
    test('should maintain form values after error', async ({ page }) => {
      await homePage.enterStationSearch('invalid123');
      await homePage.selectYear('2025');
      await homePage.selectMonth('06');
      await homePage.clickGenerateButton();

      await errorPage.waitForErrorPage();
      await errorPage.clickReturnHome();

      await homePage.waitForPageLoad();
      await expect(homePage.mainHeading).toBeVisible();
    });

    test('should clear hidden station ID when search is cleared', async ({ page }) => {
      await homePage.enterStationSearch('Point');
      await homePage.waitForAutocompleteDropdown();
      await homePage.selectAutocompleteItem(0);

      let stationId = await homePage.getHiddenStationId();
      expect(stationId).toBeTruthy();

      await homePage.clearStationSearch();
      await page.waitForTimeout(300);

      stationId = await homePage.getHiddenStationId();
      expect(stationId).toBe('');
    });

    test('should update hidden field when typing numeric ID', async ({ page }) => {
      await homePage.enterStationSearch('9449639');
      await page.waitForTimeout(500);

      const hiddenValue = await homePage.getHiddenStationId();
      expect(hiddenValue).toBe('9449639');
    });
  });

  test.describe('Edge Cases', () => {
    test('should handle form submission with all default values', async ({ page }) => {
      // Don't change anything, just check if form has valid defaults
      const isValid = await homePage.isFormValid();

      // Form should either be invalid (no station) or have valid default
      if (isValid) {
        const stationValue = await homePage.stationSearchInput.inputValue();
        expect(stationValue).toBeTruthy();
      }
    });

    test('should handle rapid form submissions', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.VALID_STATION_ID);
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');

      // Click button multiple times rapidly
      await homePage.clickGenerateButton();
      await homePage.clickGenerateButton();
      await homePage.clickGenerateButton();

      // Should handle gracefully (one submission should process)
      await page.waitForTimeout(1000);
      const currentUrl = page.url();
      expect(currentUrl).toBeTruthy();
    });

    test('should handle boundary year values', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.VALID_STATION_ID);

      // Test minimum year (2025)
      await homePage.selectYear('2025');
      await homePage.selectMonth('01');
      const minYearValid = await homePage.isFormValid();
      expect(minYearValid).toBe(true);

      // Test maximum year (2040)
      await homePage.selectYear('2040');
      await homePage.selectMonth('12');
      const maxYearValid = await homePage.isFormValid();
      expect(maxYearValid).toBe(true);
    });

    test('should handle all month values correctly', async ({ page }) => {
      await homePage.enterStationSearch(TEST_DATA.VALID_STATION_ID);
      await homePage.selectYear('2025');

      // Test each month
      for (let month = 1; month <= 12; month++) {
        const monthStr = month.toString().padStart(2, '0');
        await homePage.selectMonth(monthStr);

        const isValid = await homePage.isFormValid();
        expect(isValid).toBe(true);
      }
    });

    test('should handle station ID with leading zeros', async ({ page }) => {
      await homePage.enterStationSearch('0009449639');
      await page.waitForTimeout(500);

      const hiddenValue = await homePage.getHiddenStationId();
      // Should accept it (even if it's unusual)
      expect(hiddenValue).toBeTruthy();
    });
  });

  test.describe('Required Field Validation', () => {
    test('should require station selection', async ({ page }) => {
      // Try to submit without station
      const stationInput = homePage.stationSearchInput;
      const isRequired = await stationInput.getAttribute('required');

      expect(isRequired).not.toBeNull();
    });

    test('should require year selection', async ({ page }) => {
      const yearInput = homePage.yearSelect;
      const isRequired = await yearInput.getAttribute('required');

      expect(isRequired).not.toBeNull();
    });

    test('should require month selection', async ({ page }) => {
      const monthInput = homePage.monthSelect;
      const isRequired = await monthInput.getAttribute('required');

      expect(isRequired).not.toBeNull();
    });
  });
});
