import { defineConfig } from '@playwright/test';
import baseConfig from './playwright.config';

/**
 * Configuration for local testing
 */
export default defineConfig({
  ...baseConfig,
  use: {
    ...baseConfig.use,
    baseURL: 'http://localhost:5001',
  },
  webServer: {
    command: 'cd app && python3 -m flask run --host 0.0.0.0 --port 5001',
    url: 'http://localhost:5001',
    reuseExistingServer: !process.env.CI,
  },
});
