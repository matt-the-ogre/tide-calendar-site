import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke test configuration
 * Minimal, fast configuration for CI smoke tests
 */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/smoke.spec.ts',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry once on CI */
  retries: process.env.CI ? 1 : 0,

  /* Use single worker on CI for consistency */
  workers: 1,

  /* Reporter to use */
  reporter: [
    ['html'],
    ['github'],
  ],

  /* Shared settings */
  use: {
    /* Base URL */
    baseURL: process.env.BASE_URL || 'https://www.tidecalendar.xyz',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot only on failure */
    screenshot: 'only-on-failure',

    /* No video for smoke tests (saves time) */
    video: 'off',

    /* Shorter timeouts for smoke tests */
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },

  /* Single project - chromium only */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Test timeouts - shorter for smoke tests */
  timeout: 20000,
  expect: {
    timeout: 5000
  },

  /* Output directory */
  outputDir: 'test-results/',
});
