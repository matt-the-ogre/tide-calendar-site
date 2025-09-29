import { FullConfig } from '@playwright/test';
import logging from './utils/logger';

async function globalTeardown(config: FullConfig) {
  const logger = logging.getLogger('global-teardown');

  logger.info('Starting global teardown');

  try {
    // Cleanup test artifacts if needed
    // For example, remove downloaded PDFs in test environment

    // Log test completion
    logger.info('Test suite execution completed');

  } catch (error) {
    logger.error('Global teardown error:', error);
  }

  logger.info('Global teardown completed');
}

export default globalTeardown;