# Playwright Test Suite for Tide Calendar Application

This comprehensive test suite provides automated testing for the Tide Calendar Flask web application using Playwright with TypeScript.

## 📋 Overview

The test suite covers:
- **Form validation** - Input validation, edge cases, security tests
- **PDF generation** - End-to-end workflow testing
- **Autocomplete functionality** - Search, keyboard navigation, performance
- **Error handling** - Error pages, navigation, user feedback
- **Mobile responsiveness** - Cross-device compatibility, touch interactions
- **Performance testing** - Load times, API response times, resource optimization

## 🏗️ Test Architecture

```
tests/
├── config/
│   └── test-config.ts           # Environment and test data configuration
├── pages/
│   ├── BasePage.ts             # Base page object with common functionality
│   ├── HomePage.ts             # Home page interactions and assertions
│   └── ErrorPage.ts            # Error page interactions and assertions
├── utils/
│   └── logger.ts               # Centralized logging utility
├── fixtures/                   # Test data and mock responses
├── *.spec.ts                   # Test specification files
├── global-setup.ts             # Global test setup and health checks
└── global-teardown.ts          # Global test cleanup
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18.0.0 or higher
- npm or yarn package manager
- Running Flask application (local or production)

### Installation

```bash
# Install dependencies
npm install

# Install Playwright browsers
npm run test:install

# Install system dependencies (if needed)
npm run test:install-deps
```

### Environment Configuration

Set environment variables for different test environments:

```bash
# Local testing (default)
export BASE_URL=http://localhost:5001
export TEST_ENV=local

# Production testing
export BASE_URL=https://www.tidecalendar.xyz
export TEST_ENV=production
```

## 🧪 Running Tests

### Basic Test Execution

```bash
# Run all tests
npm test

# Run tests for specific environment
npm run test:local      # Local development server
npm run test:prod       # Production environment

# Run with browser UI visible
npm run test:headed

# Run in debug mode
npm run test:debug

# Run with interactive UI
npm run test:ui
```

### Specific Test Categories

```bash
# Run specific test files
npx playwright test form-validation.spec.ts
npx playwright test pdf-generation.spec.ts
npx playwright test autocomplete.spec.ts
npx playwright test error-handling.spec.ts
npx playwright test mobile-responsive.spec.ts
npx playwright test performance.spec.ts

# Run tests matching a pattern
npx playwright test --grep "autocomplete"
npx playwright test --grep "mobile"
```

### Cross-Browser Testing

```bash
# Run on specific browsers
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Run on mobile devices
npx playwright test --project="Mobile Chrome"
npx playwright test --project="Mobile Safari"
```

## 📊 Test Reports

```bash
# Generate and view HTML report
npm run test:report

# View test results
npx playwright show-report
```

Reports include:
- Test execution status and timing
- Screenshots on failure
- Video recordings of failed tests
- Performance metrics and traces

## 🎯 Test Categories

### 1. Form Validation Tests (`form-validation.spec.ts`)

**Coverage:**
- Required field validation
- Station ID format validation (numeric, non-existent)
- Year/month dropdown validation
- Security testing (SQL injection, XSS attempts)
- Input edge cases (special characters, unicode, max length)
- HTML5 form validation
- Client-side JavaScript validation

**Key Test Cases:**
```typescript
// Example validation tests
test('should show error when station search is empty')
test('should handle SQL injection attempt')
test('should validate required HTML5 attributes')
test('should handle unicode characters')
```

### 2. PDF Generation Tests (`pdf-generation.spec.ts`)

**Coverage:**
- Successful PDF generation with valid station ID (9449639)
- PDF download verification
- File size and content validation
- Error handling for failed generation
- Different year/month combinations
- Network timeout handling

**Key Test Cases:**
```typescript
// Example PDF tests
test('should generate PDF for valid station ID')
test('should handle PDF generation timeout')
test('should validate PDF file size and format')
```

### 3. Autocomplete Tests (`autocomplete.spec.ts`)

**Coverage:**
- Dropdown visibility and hiding
- Keyboard navigation (arrow keys, Enter, Escape)
- Mouse/touch selection
- Popular stations vs API search
- Performance and response times
- Error handling and edge cases
- Debouncing and rapid typing

**Key Test Cases:**
```typescript
// Example autocomplete tests
test('should show autocomplete dropdown when typing station name')
test('should navigate autocomplete items with arrow keys')
test('should respond quickly to search queries')
test('should handle rapid typing efficiently')
```

### 4. Error Handling Tests (`error-handling.spec.ts`)

**Coverage:**
- Error page display for various error types
- Return home button functionality
- Error message validation and security
- Analytics tracking for errors
- Accessibility compliance
- Browser history handling
- Content and styling consistency

**Key Test Cases:**
```typescript
// Example error handling tests
test('should show error page for invalid station ID')
test('should track analytics for error events')
test('should return to home page when clicking return home button')
test('should be keyboard navigable')
```

### 5. Mobile Responsiveness Tests (`mobile-responsive.spec.ts`)

**Coverage:**
- Multiple device viewports (iPhone, Pixel, iPad, etc.)
- Touch interactions and gestures
- Responsive layout and element sizing
- Mobile-specific features (keyboard, select dropdowns)
- Viewport rotation simulation
- Cross-browser mobile compatibility
- Touch target size validation

**Key Test Cases:**
```typescript
// Example mobile tests
test('should display home page elements properly on mobile')
test('should handle touch interactions')
test('should have adequate touch target sizes')
test('should work consistently across mobile devices')
```

### 6. Performance Tests (`performance.spec.ts`)

**Coverage:**
- Page load times and Core Web Vitals
- API response times and concurrent requests
- Form interaction responsiveness
- Autocomplete performance and debouncing
- Resource loading optimization
- Memory usage and cleanup
- Network simulation

**Key Test Cases:**
```typescript
// Example performance tests
test('should load home page within acceptable time')
test('should respond quickly to API requests')
test('should show autocomplete suggestions quickly')
test('should not have memory leaks during interactions')
```

## ⚙️ Configuration

### Test Configuration (`config/test-config.ts`)

The test configuration provides:
- Environment-specific settings (local vs production)
- Test data constants and selectors
- Performance thresholds
- Mobile viewport definitions
- API endpoints and expected responses

### Key Configuration Sections:

```typescript
// Environment configs
export const LOCAL_CONFIG: TestConfig = {
  baseUrl: 'http://localhost:5001',
  timeout: { action: 15000, navigation: 30000, test: 60000 },
  retry: { count: 1 },
  browsers: ['chromium']
};

export const PRODUCTION_CONFIG: TestConfig = {
  baseUrl: 'https://www.tidecalendar.xyz',
  timeout: { action: 20000, navigation: 45000, test: 90000 },
  retry: { count: 3 },
  browsers: ['chromium', 'firefox', 'webkit']
};

// Test data
export const TEST_DATA = {
  VALID_STATION_ID: '9449639', // Point Roberts, WA
  INVALID_STATION_ID: '1234567',
  SEARCH_QUERIES: {
    SQL_INJECTION: "'; DROP TABLE stations; --",
    XSS_ATTEMPT: '<script>alert("xss")</script>'
  }
};

// Performance thresholds
export const PERFORMANCE_THRESHOLDS = {
  PAGE_LOAD_TIME: 3000,
  API_RESPONSE_TIME: 2000,
  AUTOCOMPLETE_RESPONSE_TIME: 1000
};
```

## 🔧 Page Object Model

### Base Page (`pages/BasePage.ts`)
Common functionality shared across all pages:
- Navigation helpers
- Logging integration
- Element waiting utilities
- Screenshot capabilities

### Home Page (`pages/HomePage.ts`)
Encapsulates home page interactions:
- Form field interactions
- Autocomplete handling
- Validation checks
- Assertion helpers

### Error Page (`pages/ErrorPage.ts`)
Handles error page functionality:
- Error type detection
- Navigation testing
- Message validation
- Analytics verification

## 📈 Continuous Integration

### GitHub Actions Setup

Create `.github/workflows/playwright.yml`:

```yaml
name: Playwright Tests
on:
  push:
    branches: [ main, development ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    timeout-minutes: 60
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-node@v4
      with:
        node-version: lts/*

    - name: Install dependencies
      run: npm ci

    - name: Install Playwright Browsers
      run: npx playwright install --with-deps

    - name: Start Flask Application
      run: |
        cd app
        pip install -r requirements.txt
        flask run --host 0.0.0.0 --port 5001 &
        sleep 10 # Wait for app to start

    - name: Run Playwright tests
      run: npm test
      env:
        BASE_URL: http://localhost:5001

    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: playwright-report
        path: playwright-report/
        retention-days: 30
```

### Docker Testing

Create `Dockerfile.test`:

```dockerfile
FROM mcr.microsoft.com/playwright:v1.40.0-focal

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["npm", "test"]
```

Build and run tests in Docker:

```bash
docker build -f Dockerfile.test -t tide-calendar-tests .
docker run -e BASE_URL=https://www.tidecalendar.xyz tide-calendar-tests
```

## 🐛 Debugging Tests

### Local Debugging

```bash
# Run in debug mode with browser visible
npm run test:debug

# Run single test in debug mode
npx playwright test form-validation.spec.ts --debug

# Generate trace files for analysis
npx playwright test --trace on
```

### Analyzing Failures

1. **Screenshots**: Automatic screenshots on test failures
2. **Videos**: Video recordings of test execution
3. **Traces**: Detailed execution traces with DOM snapshots
4. **Logs**: Structured logging with configurable levels

### Common Issues and Solutions

**Test Timeouts:**
```bash
# Increase timeouts for slower environments
npx playwright test --timeout=60000
```

**Element Not Found:**
```typescript
// Use proper waiting strategies
await page.waitForSelector('#element', { state: 'visible' });
await expect(locator).toBeVisible();
```

**Flaky Tests:**
```typescript
// Add proper wait conditions
await page.waitForLoadState('networkidle');
await page.waitForFunction(() => window.dataLoaded === true);
```

## 📋 Test Maintenance

### Regular Maintenance Tasks

1. **Update Test Data**: Keep station IDs and test data current
2. **Review Performance Thresholds**: Adjust based on application changes
3. **Update Browser Versions**: Keep Playwright browsers updated
4. **Monitor Test Stability**: Address flaky tests promptly
5. **Review Test Coverage**: Ensure new features are tested

### Test Data Management

```typescript
// Update test-config.ts regularly
export const TEST_DATA = {
  VALID_STATION_ID: '9449639', // Verify this station is still active
  CURRENT_YEAR: new Date().getFullYear(), // Auto-updates
  // Add new test cases as needed
};
```

### Adding New Tests

1. **Create test file**: Follow naming convention `*.spec.ts`
2. **Import required modules**: Use existing page objects and config
3. **Write descriptive test names**: Clearly indicate what is being tested
4. **Add proper logging**: Use the logger utility for debugging
5. **Update documentation**: Include new tests in this README

## 🔐 Security Testing

The test suite includes security-focused tests:

- **Input Sanitization**: SQL injection and XSS prevention
- **Error Message Security**: No sensitive information exposure
- **CSRF Protection**: Form submission security
- **Content Security**: Proper encoding and escaping

## 🎯 Best Practices

### Test Writing Guidelines

1. **Independent Tests**: Each test should be self-contained
2. **Descriptive Names**: Test names should explain what is being tested
3. **Proper Cleanup**: Use beforeEach/afterEach for test isolation
4. **Avoid Hard Waits**: Use proper wait conditions instead of fixed timeouts
5. **Mock External Dependencies**: Use request interception for reliability

### Performance Considerations

1. **Parallel Execution**: Tests run in parallel for speed
2. **Selective Testing**: Use test.describe.configure for critical paths
3. **Resource Management**: Proper browser context cleanup
4. **Test Data Optimization**: Minimize test data size and complexity

## 📞 Support and Contributing

### Getting Help

- Review test output and logs for failure analysis
- Check browser console for JavaScript errors
- Use Playwright trace viewer for detailed debugging
- Consult Playwright documentation for advanced features

### Contributing

1. Follow existing code patterns and conventions
2. Add appropriate logging and error handling
3. Update documentation for new features
4. Ensure tests are stable and not flaky
5. Add performance benchmarks for new functionality

## 📄 License

This test suite is part of the Tide Calendar project and follows the same licensing terms.