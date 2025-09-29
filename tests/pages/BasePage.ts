import { Page, Locator } from '@playwright/test';
import { SELECTORS } from '../config/test-config';
import logging from '../utils/logger';

/**
 * Base page class with common functionality
 */
export class BasePage {
  protected page: Page;
  protected logger = logging.getLogger(this.constructor.name);

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to a specific path
   */
  async goto(path: string = '/'): Promise<void> {
    this.logger.info(`Navigating to: ${path}`);
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  /**
   * Wait for page to be fully loaded
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get page title
   */
  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  /**
   * Get page URL
   */
  getUrl(): string {
    return this.page.url();
  }

  /**
   * Take screenshot
   */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `test-results/${name}-${Date.now()}.png`,
      fullPage: true
    });
  }

  /**
   * Wait for element to be visible
   */
  async waitForElement(selector: string, timeout: number = 5000): Promise<Locator> {
    const element = this.page.locator(selector);
    await element.waitFor({ state: 'visible', timeout });
    return element;
  }

  /**
   * Check if element exists
   */
  async elementExists(selector: string): Promise<boolean> {
    const count = await this.page.locator(selector).count();
    return count > 0;
  }

  /**
   * Get element text content
   */
  async getElementText(selector: string): Promise<string> {
    const element = await this.waitForElement(selector);
    return await element.textContent() || '';
  }

  /**
   * Click element with retry logic
   */
  async clickElement(selector: string, options: { timeout?: number; force?: boolean } = {}): Promise<void> {
    this.logger.debug(`Clicking element: ${selector}`);
    const element = await this.waitForElement(selector, options.timeout);
    await element.click({ force: options.force });
  }

  /**
   * Fill input field
   */
  async fillInput(selector: string, value: string): Promise<void> {
    this.logger.debug(`Filling input ${selector} with: ${value}`);
    const element = await this.waitForElement(selector);
    await element.fill(value);
  }

  /**
   * Select option from dropdown
   */
  async selectOption(selector: string, value: string): Promise<void> {
    this.logger.debug(`Selecting option ${value} from: ${selector}`);
    const element = await this.waitForElement(selector);
    await element.selectOption(value);
  }

  /**
   * Get current viewport size
   */
  getViewportSize() {
    return this.page.viewportSize();
  }

  /**
   * Set viewport size
   */
  async setViewportSize(width: number, height: number): Promise<void> {
    await this.page.setViewportSize({ width, height });
  }

  /**
   * Check if page is mobile viewport
   */
  isMobileViewport(): boolean {
    const viewport = this.getViewportSize();
    return viewport ? viewport.width < 768 : false;
  }

  /**
   * Wait for network response
   */
  async waitForResponse(urlPattern: string | RegExp, timeout: number = 10000): Promise<void> {
    await this.page.waitForResponse(urlPattern, { timeout });
  }

  /**
   * Get all links on page
   */
  async getAllLinks(): Promise<Locator> {
    return this.page.locator('a');
  }

  /**
   * Check for JavaScript errors on page
   */
  async getConsoleErrors(): Promise<string[]> {
    const errors: string[] = [];
    this.page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    return errors;
  }

  /**
   * Common page elements
   */
  get container(): Locator {
    return this.page.locator(SELECTORS.CONTAINER);
  }

  get mainHeading(): Locator {
    return this.page.locator(SELECTORS.MAIN_HEADING);
  }

  get footer(): Locator {
    return this.page.locator(SELECTORS.FOOTER);
  }

  get socialIcons(): Locator {
    return this.page.locator(SELECTORS.SOCIAL_ICONS);
  }
}