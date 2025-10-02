import { defineConfig } from '@playwright/test';
import baseConfig from './playwright.config';

/**
 * Configuration for production testing
 */
export default defineConfig({
  ...baseConfig,
  use: {
    ...baseConfig.use,
    baseURL: 'https://www.tidecalendar.xyz',
  },
  // No webServer for production - we test the live site
  webServer: undefined,
});
