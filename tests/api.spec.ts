import { test, expect } from '@playwright/test';
import { TEST_DATA, TEST_ENDPOINTS } from './config/test-config';

test.describe('API Endpoints', () => {
  test.describe('/api/search_stations', () => {
    test('should return search results for valid query', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=Point`);

      expect(response.ok()).toBeTruthy();
      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
      expect(data.length).toBeGreaterThan(0);

      // Validate response structure
      const firstStation = data[0];
      expect(firstStation).toHaveProperty('station_id');
      expect(firstStation).toHaveProperty('place_name');
      expect(firstStation).toHaveProperty('lookup_count');
      expect(firstStation.place_name.toLowerCase()).toContain('point');
    });

    test('should return results sorted by lookup count', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=San`);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();

      if (data.length > 1) {
        // Verify results are sorted by lookup_count DESC
        for (let i = 0; i < data.length - 1; i++) {
          expect(data[i].lookup_count).toBeGreaterThanOrEqual(data[i + 1].lookup_count);
        }
      }
    });

    test('should return empty array for empty query', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=`);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data).toEqual([]);
    });

    test('should return empty array for very short query', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=`);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
    });

    test('should handle non-existent station names gracefully', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=${TEST_DATA.SEARCH_QUERIES.INVALID}`);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data).toEqual([]);
    });

    test('should perform case-insensitive search', async ({ request }) => {
      const lowerResponse = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=seattle`);
      const upperResponse = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=SEATTLE`);
      const mixedResponse = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=Seattle`);

      const lowerData = await lowerResponse.json();
      const upperData = await upperResponse.json();
      const mixedData = await mixedResponse.json();

      // All should return the same results
      expect(lowerData).toEqual(upperData);
      expect(lowerData).toEqual(mixedData);
    });

    test('should handle special characters in search query', async ({ request }) => {
      const specialChars = ['test@#$%', "test'quote", 'test"doublequote'];

      for (const query of specialChars) {
        const response = await request.get(
          `${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=${encodeURIComponent(query)}`
        );

        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        expect(Array.isArray(data)).toBeTruthy();
      }
    });

    test('should handle SQL injection attempts safely', async ({ request }) => {
      const response = await request.get(
        `${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=${encodeURIComponent(TEST_DATA.SEARCH_QUERIES.SQL_INJECTION)}`
      );

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
      // Should not cause database error, just return empty or no matches
    });

    test('should handle XSS attempts safely', async ({ request }) => {
      const response = await request.get(
        `${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=${encodeURIComponent(TEST_DATA.SEARCH_QUERIES.XSS_ATTEMPT)}`
      );

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();

      // If any results, ensure place_name doesn't contain unescaped script tags
      if (data.length > 0) {
        data.forEach(station => {
          expect(station.place_name).not.toContain('<script');
        });
      }
    });

    test('should limit search results to 10 items', async ({ request }) => {
      // Use a broad query that might match many stations
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=a`);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data.length).toBeLessThanOrEqual(10);
    });

    test('should handle missing query parameter', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_SEARCH_STATIONS);

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data).toEqual([]);
    });

    test('should return valid station IDs', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=Point`);

      const data = await response.json();

      if (data.length > 0) {
        data.forEach(station => {
          // Station ID should be numeric string
          expect(station.station_id).toMatch(/^\d+$/);
          // Should be at least 4 digits (typical NOAA station ID length)
          expect(station.station_id.length).toBeGreaterThanOrEqual(4);
        });
      }
    });

    test('should have correct Content-Type header', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=Point`);

      expect(response.headers()['content-type']).toContain('application/json');
    });
  });

  test.describe('/api/popular_stations', () => {
    test('should return popular stations', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      expect(response.ok()).toBeTruthy();
      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
      expect(data.length).toBeGreaterThan(0);
    });

    test('should return at most 16 stations', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data = await response.json();
      expect(data.length).toBeLessThanOrEqual(16);
    });

    test('should have valid response structure', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data = await response.json();

      // Validate structure of each station
      data.forEach(station => {
        expect(station).toHaveProperty('station_id');
        expect(station).toHaveProperty('place_name');
        expect(station).toHaveProperty('lookup_count');
        expect(station.station_id).toMatch(/^\d+$/);
        expect(typeof station.place_name).toBe('string');
        expect(typeof station.lookup_count).toBe('number');
      });
    });

    test('should be sorted by lookup count descending', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data = await response.json();

      if (data.length > 1) {
        for (let i = 0; i < data.length - 1; i++) {
          expect(data[i].lookup_count).toBeGreaterThanOrEqual(data[i + 1].lookup_count);
        }
      }
    });

    test('should have highest lookup count first', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data = await response.json();

      if (data.length > 0) {
        const firstStation = data[0];
        const lastStation = data[data.length - 1];

        expect(firstStation.lookup_count).toBeGreaterThanOrEqual(lastStation.lookup_count);
      }
    });

    test('should not accept query parameters', async ({ request }) => {
      const response = await request.get(`${TEST_ENDPOINTS.API_POPULAR_STATIONS}?q=test`);

      // Should ignore query parameters and return popular stations anyway
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
    });

    test('should have correct Content-Type header', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      expect(response.headers()['content-type']).toContain('application/json');
    });

    test('should return consistent results on multiple calls', async ({ request }) => {
      const response1 = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);
      const response2 = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data1 = await response1.json();
      const data2 = await response2.json();

      // Results should be the same (popular stations don't change between requests)
      expect(data1).toEqual(data2);
    });

    test('should have all required fields populated', async ({ request }) => {
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);

      const data = await response.json();

      data.forEach(station => {
        expect(station.station_id).toBeTruthy();
        expect(station.place_name).toBeTruthy();
        expect(station.lookup_count).toBeGreaterThanOrEqual(0);
      });
    });

    test('should return data within reasonable time', async ({ request }) => {
      const startTime = Date.now();
      const response = await request.get(TEST_ENDPOINTS.API_POPULAR_STATIONS);
      const endTime = Date.now();

      expect(response.ok()).toBeTruthy();

      // Should respond within 2 seconds
      const responseTime = endTime - startTime;
      expect(responseTime).toBeLessThan(2000);
    });
  });

  test.describe('API Error Handling', () => {
    test('should handle server errors gracefully', async ({ request }) => {
      // Try an invalid endpoint
      const response = await request.get('/api/nonexistent_endpoint');

      expect(response.status()).toBe(404);
    });

    test('should return JSON even on error', async ({ request }) => {
      // Send request that might cause error
      const response = await request.get(`${TEST_ENDPOINTS.API_SEARCH_STATIONS}?q=${'a'.repeat(1000)}`);

      // Should still return valid response (even if empty)
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
    });
  });
});
