# Playwright Testing TODO List

## Completed ✅

1. **Autocomplete Tests** - DONE
   - 16 scenarios × 5 browsers = 80 tests
   - Tests dropdown visibility, filtering, selection, keyboard navigation
   - Commit: 98ec895

2. **API Endpoint Tests** - DONE
   - 25 scenarios × 5 browsers = 125 tests
   - Tests /api/search_stations and /api/popular_stations
   - Security testing for SQL injection and XSS
   - Commit: 80f15ad

3. **Form Validation Tests** - DONE
   - 29 scenarios × 5 browsers = 145 tests
   - Station ID, year/month validation, security, input sanitization
   - Commit: 300401d

**Total Tests Passing: 350 tests (70 scenarios × 5 browsers)**

---

## Remaining Work 🚧

### 4. End-to-End Workflow Tests
**Priority: High**

Create comprehensive E2E tests for the complete user journey:

**Test Scenarios:**
- Complete flow: search → select → generate → download PDF
- PDF generation verification (file exists, non-empty, correct naming)
- Error recovery flows (invalid input → error page → return home)
- Multi-step workflows with different station types
- Cookie persistence (last_place_name)
- PDF cleanup verification (old files removed)

**Estimated:** 10-15 scenarios × 5 browsers = 50-75 tests

**File:** `tests/e2e-workflow.spec.ts`

---

### 5. Accessibility Tests
**Priority: Medium**

Ensure WCAG 2.1 compliance and keyboard navigation:

**Test Scenarios:**
- Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- Screen reader compatibility (ARIA labels, roles, descriptions)
- Focus management (visible focus indicators, logical tab order)
- Color contrast validation
- Form label associations
- Error message announcements
- Skip links and landmarks

**Estimated:** 8-12 scenarios × 5 browsers = 40-60 tests

**File:** `tests/accessibility.spec.ts`

**Tools to use:**
- `@axe-core/playwright` for automated accessibility auditing
- Manual keyboard navigation tests
- Focus trap verification

---

### 6. Performance Tests
**Priority: Low**

Measure and validate application performance:

**Test Scenarios:**
- Page load time (<2 seconds)
- API response times (<500ms)
- Autocomplete debounce effectiveness
- PDF generation time (<5 seconds)
- Memory leak detection (repeated operations)
- Network request optimization (caching, compression)

**Estimated:** 6-10 scenarios × 3 browsers (desktop only) = 18-30 tests

**File:** `tests/performance.spec.ts`

**Metrics to track:**
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time to Interactive (TTI)
- API call duration
- PDF generation duration

---

## Additional Recommendations

### 7. Visual Regression Testing (Optional)
- Screenshot comparison for UI consistency
- Responsive design validation across viewports
- Cross-browser visual parity

**Tool:** `@playwright/test` built-in screenshot comparison

---

### 8. Mobile-Specific Tests (Optional)
- Touch interactions
- Mobile viewport layouts
- Mobile keyboard behavior
- Orientation changes

---

## Test Execution Commands

```bash
# Run all tests
npx playwright test

# Run specific test suite
npx playwright test tests/e2e-workflow.spec.ts
npx playwright test tests/accessibility.spec.ts
npx playwright test tests/performance.spec.ts

# Run tests for specific browser
npx playwright test --project=chromium
npx playwright test --project=webkit

# Run with UI mode (debugging)
npx playwright test --ui

# Generate HTML report
npx playwright show-report
```

---

## Current Test Statistics

- **Total Test Files:** 4 (basic, autocomplete, api, form-validation)
- **Total Test Scenarios:** 70
- **Total Tests (all browsers):** 350
- **Pass Rate:** 100%
- **Browsers Tested:** Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari

---

## Notes

- All tests use Page Object Model (POM) pattern
- Test configuration in `playwright.config.ts`
- Page objects in `tests/pages/`
- Test data in `tests/config/test-config.ts`
- Global setup/teardown in `tests/global-setup.ts` and `tests/global-teardown.ts`

---

Last Updated: 2025-10-02
