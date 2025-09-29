import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';
import { SELECTORS } from '../config/test-config';

/**
 * Page Object Model for the error/tide station not found page
 */
export class ErrorPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  /**
   * Page elements
   */
  get errorContainer(): Locator {
    return this.page.locator(SELECTORS.ERROR_CONTAINER);
  }

  get errorMessage(): Locator {
    return this.page.locator('p').first();
  }

  get returnHomeButton(): Locator {
    return this.page.locator(SELECTORS.RETURN_HOME_BUTTON);
  }

  get instructionsSection(): Locator {
    return this.page.locator('.instructions');
  }

  get instructionsHeading(): Locator {
    return this.instructionsSection.locator('h2');
  }

  get instructionsList(): Locator {
    return this.instructionsSection.locator('ol');
  }

  get noaaLink(): Locator {
    return this.page.locator('a[href*="tidesandcurrents.noaa.gov"]');
  }

  get errorHeading(): Locator {
    return this.page.locator('h2:has-text("Error")');
  }

  /**
   * Actions
   */

  /**
   * Click the return home button
   */
  async clickReturnHome(): Promise<void> {
    this.logger.info('Clicking return home button');
    await this.returnHomeButton.click();
  }

  /**
   * Click the NOAA link
   */
  async clickNoaaLink(): Promise<void> {
    this.logger.info('Clicking NOAA stations link');
    await this.noaaLink.click();
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string> {
    return await this.errorMessage.textContent() || '';
  }

  /**
   * Get error message from data attribute
   */
  async getErrorMessageFromData(): Promise<string> {
    return await this.errorContainer.getAttribute('data-error-message') || '';
  }

  /**
   * Get instructions text
   */
  async getInstructionsText(): Promise<string> {
    return await this.instructionsSection.textContent() || '';
  }

  /**
   * Check if specific error type is displayed
   */
  async isErrorType(errorType: string): Promise<boolean> {
    const errorMessage = await this.getErrorMessage();
    const errorData = await this.getErrorMessageFromData();

    switch (errorType) {
      case 'station_not_found':
        return errorMessage.includes('not found') || errorData.includes('Could not find');
      case 'invalid_station_id':
        return errorMessage.includes('Station ID must') || errorData.includes('Station ID must');
      case 'invalid_month':
        return errorMessage.includes('Month must') || errorData.includes('Month must');
      case 'invalid_year':
        return errorMessage.includes('Year must') || errorData.includes('Year must');
      case 'no_station_selected':
        return errorMessage.includes('No station selected') || errorData.includes('No station selected');
      default:
        return false;
    }
  }

  /**
   * Wait for error page to load
   */
  async waitForErrorPage(): Promise<void> {
    await expect(this.errorHeading).toBeVisible();
    await expect(this.errorMessage).toBeVisible();
    await expect(this.returnHomeButton).toBeVisible();
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
   * Assert error page elements are visible
   */
  async assertErrorElementsVisible(): Promise<void> {
    await expect(this.mainHeading).toBeVisible();
    await expect(this.errorHeading).toBeVisible();
    await expect(this.errorMessage).toBeVisible();
    await expect(this.returnHomeButton).toBeVisible();
    await expect(this.instructionsSection).toBeVisible();
  }

  /**
   * Assert error message contains specific text
   */
  async assertErrorMessageContains(expectedText: string): Promise<void> {
    const errorMessage = await this.getErrorMessage();
    expect(errorMessage).toContain(expectedText);
  }

  /**
   * Assert return home button is functional
   */
  async assertReturnHomeButtonEnabled(): Promise<void> {
    await expect(this.returnHomeButton).toBeEnabled();
    await expect(this.returnHomeButton).toHaveAttribute('href', '/');
  }

  /**
   * Assert NOAA link opens in new tab
   */
  async assertNoaaLinkTarget(): Promise<void> {
    await expect(this.noaaLink).toHaveAttribute('target', '_blank');
    await expect(this.noaaLink).toHaveAttribute('href', /tidesandcurrents\.noaa\.gov/);
  }

  /**
   * Assert instructions are displayed
   */
  async assertInstructionsDisplayed(): Promise<void> {
    await expect(this.instructionsHeading).toBeVisible();
    await expect(this.instructionsHeading).toHaveText('How to Find Your Tide Station ID');
    await expect(this.instructionsList).toBeVisible();

    // Check that instructions list has steps
    const listItems = this.instructionsList.locator('li');
    const count = await listItems.count();
    expect(count).toBeGreaterThan(0);
  }

  /**
   * Assert footer is present
   */
  async assertFooterPresent(): Promise<void> {
    await expect(this.footer).toBeVisible();
    await expect(this.socialIcons).toHaveCount(4); // LinkedIn, Email, Twitter, GitHub
  }

  /**
   * Assert error type matches expected
   */
  async assertErrorType(expectedErrorType: string): Promise<void> {
    const isCorrectType = await this.isErrorType(expectedErrorType);
    expect(isCorrectType).toBe(true);
  }

  /**
   * Assert analytics tracking is present (data-error-message attribute)
   */
  async assertAnalyticsTracking(): Promise<void> {
    const errorData = await this.getErrorMessageFromData();
    expect(errorData).toBeTruthy();
    expect(errorData.length).toBeGreaterThan(0);
  }
}