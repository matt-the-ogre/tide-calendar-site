import { defineConfig } from '@playwright/test';
import config from './playwright.config';

/**
 * Production configuration
 * Overrides base config for production testing
 */
export default defineConfig(config, {
  use: {
    ...config.use,
    baseURL: 'https://www.tidecalendar.xyz',
    // Longer timeouts for production network latency
    actionTimeout: 20000,
    navigationTimeout: 45000,
  },

  /* More retries for production stability */
  retries: 3,

  /* Run all browsers in production */
  projects: [
    {
      name: 'chromium',
      use: { ...config.projects[0].use },
    },
    {
      name: 'firefox',
      use: { ...config.projects[1].use },
    },
    {
      name: 'webkit',
      use: { ...config.projects[2].use },
    },
    {
      name: 'Mobile Chrome',
      use: { ...config.projects[3].use },
    },
    {
      name: 'Mobile Safari',
      use: { ...config.projects[4].use },
    },
  ],

  /* Production-specific reporter */
  reporter: [
    ['html', { outputFolder: 'playwright-report-prod' }],
    ['json', { outputFile: 'test-results/results-prod.json' }],
    ['junit', { outputFile: 'test-results/results-prod.xml' }],
  ],
});