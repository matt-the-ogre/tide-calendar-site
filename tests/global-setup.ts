import { chromium, FullConfig } from '@playwright/test';
import { getTestConfig } from './config/test-config';
import logging from './utils/logger';

async function globalSetup(config: FullConfig) {
  const testConfig = getTestConfig();
  const logger = logging.getLogger('global-setup');

  logger.info('Starting global setup');
  logger.info(`Testing against: ${testConfig.baseUrl}`);

  try {
    // Launch browser for setup
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    logger.info('Performing health check');

    // Health check - verify the application is running
    const response = await page.goto(testConfig.baseUrl);

    if (!response || !response.ok()) {
      throw new Error(`Application health check failed. Status: ${response?.status() || 'unknown'}`);
    }

    // Verify critical elements are present
    const title = await page.title();
    if (!title.includes('Tide Calendar')) {
      throw new Error(`Unexpected page title: ${title}`);
    }

    // Check for main form elements
    const formExists = await page.locator('#tide_form').count() > 0;
    if (!formExists) {
      throw new Error('Main form not found on homepage');
    }

    logger.info('Health check passed');

    // Clean up
    await context.close();
    await browser.close();

    logger.info('Global setup completed successfully');

  } catch (error) {
    logger.error('Global setup failed:', error);
    throw error;
  }
}

export default globalSetup;