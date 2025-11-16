import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';
import { SELECTORS, TEST_DATA } from '../config/test-config';

/**
 * Page Object Model for the home page
 */
export class HomePage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  /**
   * Page elements
   */
  get stationSearchInput(): Locator {
    return this.page.locator(SELECTORS.STATION_SEARCH);
  }

  get stationIdHidden(): Locator {
    return this.page.locator(SELECTORS.STATION_ID_HIDDEN);
  }

  get yearSelect(): Locator {
    return this.page.locator(SELECTORS.YEAR_SELECT);
  }

  get monthSelect(): Locator {
    return this.page.locator(SELECTORS.MONTH_SELECT);
  }

  get generateButton(): Locator {
    return this.page.locator(SELECTORS.GENERATE_BUTTON);
  }

  get tideForm(): Locator {
    return this.page.locator(SELECTORS.TIDE_FORM);
  }

  get autocompleteDropdown(): Locator {
    return this.page.locator(SELECTORS.AUTOCOMPLETE_DROPDOWN);
  }

  get autocompleteItems(): Locator {
    return this.page.locator(SELECTORS.AUTOCOMPLETE_ITEM);
  }

  get selectedAutocompleteItem(): Locator {
    return this.page.locator(SELECTORS.AUTOCOMPLETE_ITEM_SELECTED);
  }

  get exampleImage(): Locator {
    return this.page.locator(SELECTORS.EXAMPLE_IMAGE);
  }

  /**
   * Actions
   */

  /**
   * Navigate to home page
   */
  async navigateToHome(): Promise<void> {
    await this.goto('/');
    await this.waitForPageLoad();
  }

  /**
   * Enter station search text
   */
  async enterStationSearch(query: string): Promise<void> {
    this.logger.info(`Entering station search: ${query}`);
    await this.stationSearchInput.fill(query);
  }

  /**
   * Clear station search input
   */
  async clearStationSearch(): Promise<void> {
    await this.stationSearchInput.clear();
  }

  /**
   * Select year from dropdown
   */
  async selectYear(year: string): Promise<void> {
    this.logger.info(`Selecting year: ${year}`);
    await this.yearSelect.selectOption(year);
  }

  /**
   * Select month from dropdown
   */
  async selectMonth(month: string): Promise<void> {
    this.logger.info(`Selecting month: ${month}`);
    await this.monthSelect.selectOption(month);
  }

  /**
   * Click generate button
   */
  async clickGenerateButton(): Promise<void> {
    this.logger.info('Clicking generate button');
    await this.generateButton.click();
  }

  /**
   * Submit the form with valid data
   */
  async submitValidForm(options?: {
    stationId?: string;
    year?: string;
    month?: string;
  }): Promise<void> {
    const {
      stationId = TEST_DATA.VALID_STATION_ID,
      year = TEST_DATA.CURRENT_YEAR.toString(),
      month = '01'
    } = options || {};

    this.logger.info(`Submitting form with station: ${stationId}, year: ${year}, month: ${month}`);

    await this.enterStationSearch(stationId);
    await this.selectYear(year);
    await this.selectMonth(month);
    await this.clickGenerateButton();
  }

  /**
   * Wait for autocomplete dropdown to appear
   */
  async waitForAutocompleteDropdown(timeout: number = 5000): Promise<void> {
    await this.autocompleteDropdown.waitFor({ state: 'visible', timeout });
  }

  /**
   * Wait for autocomplete dropdown to hide
   */
  async waitForAutocompleteToHide(timeout: number = 5000): Promise<void> {
    await this.autocompleteDropdown.waitFor({ state: 'hidden', timeout });
  }

  /**
   * Get autocomplete items count
   */
  async getAutocompleteItemsCount(): Promise<number> {
    await this.waitForAutocompleteDropdown();
    return await this.autocompleteItems.count();
  }

  /**
   * Select autocomplete item by index
   */
  async selectAutocompleteItem(index: number): Promise<void> {
    await this.waitForAutocompleteDropdown();
    const items = this.autocompleteItems;
    const count = await items.count();

    if (index >= count) {
      throw new Error(`Autocomplete item index ${index} out of range (0-${count - 1})`);
    }

    await items.nth(index).click();
  }

  /**
   * Select autocomplete item by text content
   */
  async selectAutocompleteItemByText(text: string): Promise<void> {
    await this.waitForAutocompleteDropdown();
    const item = this.autocompleteItems.filter({ hasText: text });
    await item.first().click();
  }

  /**
   * Get autocomplete item texts
   */
  async getAutocompleteItemTexts(): Promise<string[]> {
    await this.waitForAutocompleteDropdown();
    const items = this.autocompleteItems;
    const count = await items.count();
    const texts: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) texts.push(text);
    }

    return texts;
  }

  /**
   * Navigate using keyboard in autocomplete
   */
  async navigateAutocompleteWithKeyboard(key: 'ArrowDown' | 'ArrowUp' | 'Enter' | 'Escape'): Promise<void> {
    await this.stationSearchInput.press(key);
  }

  /**
   * Get current year options from dropdown
   */
  async getYearOptions(): Promise<string[]> {
    const options = this.yearSelect.locator('option');
    const count = await options.count();
    const values: string[] = [];

    for (let i = 0; i < count; i++) {
      const value = await options.nth(i).getAttribute('value');
      if (value) values.push(value);
    }

    return values;
  }

  /**
   * Get current month options from dropdown
   */
  async getMonthOptions(): Promise<string[]> {
    const options = this.monthSelect.locator('option');
    const count = await options.count();
    const values: string[] = [];

    for (let i = 0; i < count; i++) {
      const value = await options.nth(i).getAttribute('value');
      if (value) values.push(value);
    }

    return values;
  }

  /**
   * Wait for year dropdown to be populated by JavaScript
   * This is a common wait pattern used across multiple tests
   */
  async waitForYearDropdownPopulated(timeout: number = 5000): Promise<void> {
    await this.page.waitForFunction(() => {
      const yearSelect = document.getElementById('year') as HTMLSelectElement;
      return yearSelect && yearSelect.options.length > 0;
    }, { timeout });
  }

  /**
   * Get the first available year option value
   */
  async getFirstYearOption(): Promise<string> {
    await this.waitForYearDropdownPopulated();
    const firstOption = this.yearSelect.locator('option').first();
    const value = await firstOption.getAttribute('value');
    if (!value) {
      throw new Error('No year options available');
    }
    return value;
  }

  /**
   * Get hidden station ID value
   */
  async getHiddenStationId(): Promise<string> {
    return await this.stationIdHidden.getAttribute('value') || '';
  }

  /**
   * Check if form is valid for submission
   */
  async isFormValid(): Promise<boolean> {
    const stationSearch = await this.stationSearchInput.inputValue();
    const year = await this.yearSelect.inputValue();
    const month = await this.monthSelect.inputValue();

    return Boolean(stationSearch && year && month);
  }

  /**
   * Assertions
   */

  /**
   * Assert page title
   */
  async assertPageTitle(): Promise<void> {
    const title = await this.getTitle();
    expect(title).toBe('Tide Calendar');
  }

  /**
   * Assert main elements are visible
   */
  async assertMainElementsVisible(): Promise<void> {
    await expect(this.mainHeading).toBeVisible();
    await expect(this.stationSearchInput).toBeVisible();
    await expect(this.yearSelect).toBeVisible();
    await expect(this.monthSelect).toBeVisible();
    await expect(this.generateButton).toBeVisible();
    await expect(this.exampleImage).toBeVisible();
  }

  /**
   * Assert form elements are enabled
   */
  async assertFormElementsEnabled(): Promise<void> {
    await expect(this.stationSearchInput).toBeEnabled();
    await expect(this.yearSelect).toBeEnabled();
    await expect(this.monthSelect).toBeEnabled();
    await expect(this.generateButton).toBeEnabled();
  }

  /**
   * Assert autocomplete dropdown is visible
   */
  async assertAutocompleteVisible(): Promise<void> {
    await expect(this.autocompleteDropdown).toBeVisible();
  }

  /**
   * Assert autocomplete dropdown is hidden
   */
  async assertAutocompleteHidden(): Promise<void> {
    await expect(this.autocompleteDropdown).toBeHidden();
  }

  /**
   * Assert station search has specific value
   */
  async assertStationSearchValue(expectedValue: string): Promise<void> {
    await expect(this.stationSearchInput).toHaveValue(expectedValue);
  }

  /**
   * Assert year dropdown has specific value
   */
  async assertYearValue(expectedValue: string): Promise<void> {
    await expect(this.yearSelect).toHaveValue(expectedValue);
  }

  /**
   * Assert month dropdown has specific value
   */
  async assertMonthValue(expectedValue: string): Promise<void> {
    await expect(this.monthSelect).toHaveValue(expectedValue);
  }
}