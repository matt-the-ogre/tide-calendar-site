/**
 * Test configuration and environment settings
 */

export interface TestConfig {
  baseUrl: string;
  timeout: {
    action: number;
    navigation: number;
    test: number;
  };
  retry: {
    count: number;
  };
  browsers: string[];
  viewport: {
    width: number;
    height: number;
  };
}

export const LOCAL_CONFIG: TestConfig = {
  baseUrl: 'http://localhost:5001',
  timeout: {
    action: 15000,
    navigation: 30000,
    test: 60000,
  },
  retry: {
    count: 1,
  },
  browsers: ['chromium'],
  viewport: {
    width: 1280,
    height: 720,
  },
};

export const PRODUCTION_CONFIG: TestConfig = {
  baseUrl: 'https://www.tidecalendar.xyz',
  timeout: {
    action: 20000,
    navigation: 45000,
    test: 90000,
  },
  retry: {
    count: 3,
  },
  browsers: ['chromium', 'firefox', 'webkit'],
  viewport: {
    width: 1280,
    height: 720,
  },
};

export const getTestConfig = (): TestConfig => {
  const environment = process.env.TEST_ENV || 'local';
  return environment === 'production' ? PRODUCTION_CONFIG : LOCAL_CONFIG;
};

export const TEST_ENDPOINTS = {
  HOME: '/',
  API_SEARCH_STATIONS: '/api/search_stations',
  API_POPULAR_STATIONS: '/api/popular_stations',
} as const;

export const SELECTORS = {
  // Form elements
  STATION_SEARCH: '#station_search',
  STATION_ID_HIDDEN: '#station_id',
  YEAR_SELECT: '#year',
  MONTH_SELECT: '#month',
  GENERATE_BUTTON: '#generate_btn',
  TIDE_FORM: '#tide_form',

  // Autocomplete
  AUTOCOMPLETE_DROPDOWN: '#autocomplete_dropdown',
  AUTOCOMPLETE_ITEM: '.autocomplete-item',
  AUTOCOMPLETE_ITEM_SELECTED: '.autocomplete-item.selected',

  // Error page
  ERROR_CONTAINER: '.container',
  ERROR_MESSAGE: '[data-error-message]',
  RETURN_HOME_BUTTON: 'a.btn',

  // General
  CONTAINER: '.container',
  MAIN_HEADING: 'h1',
  EXAMPLE_IMAGE: '.example-image img',
  FOOTER: 'footer',
  SOCIAL_ICONS: '.social-icons a',
} as const;

export const TEST_DATA = {
  VALID_STATION_ID: '9449639', // Point Roberts, WA
  INVALID_STATION_ID: '1234567',
  CURRENT_YEAR: new Date().getFullYear(),
  VALID_MONTHS: ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'],
  INVALID_YEARS: ['1999', '2031', 'abc'],
  INVALID_MONTHS: ['0', '13', 'abc'],

  SEARCH_QUERIES: {
    VALID: 'Point Roberts',
    PARTIAL: 'Point',
    INVALID: 'NonexistentPlace123',
    EMPTY: '',
    SPECIAL_CHARS: 'Test@#$%',
    SQL_INJECTION: "'; DROP TABLE stations; --",
    XSS_ATTEMPT: '<script>alert("xss")</script>',
  },

  POPULAR_STATION: {
    place_name: 'Point Roberts, WA',
    station_id: '9449639'
  },
} as const;

export const MOBILE_VIEWPORTS = {
  IPHONE_12: { width: 390, height: 844 },
  PIXEL_5: { width: 393, height: 851 },
  IPAD: { width: 768, height: 1024 },
  SAMSUNG_GALAXY: { width: 360, height: 640 },
} as const;

export const PERFORMANCE_THRESHOLDS = {
  PAGE_LOAD_TIME: 3000, // 3 seconds
  FORM_SUBMISSION_TIME: 5000, // 5 seconds
  API_RESPONSE_TIME: 2000, // 2 seconds
  AUTOCOMPLETE_RESPONSE_TIME: 1000, // 1 second
} as const;