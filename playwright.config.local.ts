import { defineConfig } from '@playwright/test';
import config from './playwright.config';

/**
 * Local development configuration
 * Overrides base config for local testing
 */
export default defineConfig(config, {
  use: {
    ...config.use,
    baseURL: 'http://localhost:5001',
    // Slower timeout for local debugging
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  /* More retries for local flaky network */
  retries: 1,

  /* Run fewer workers locally to avoid resource issues */
  workers: 2,

  /* Enable UI mode for local development */
  reporter: [
    ['html'],
    ['list'],
  ],

  /* Local projects - focus on Chromium for faster feedback */
  projects: [
    {
      name: 'chromium',
      use: {
        ...config.projects[0].use,
        // Enable slow motion for debugging
        // slowMo: 1000,
      },
    },
    // Uncomment for cross-browser testing locally
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
  ],
});