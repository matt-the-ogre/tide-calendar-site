import { test, expect } from '@playwright/test';
import { HomePage } from './pages/HomePage';

/**
 * Station map: an embedded Leaflet/OpenStreetMap map of all selectable stations.
 * Clicking a pin's "Use this station" button fills the existing form; the country
 * filter re-fits the map. See app/static/js/station_map.js.
 */
test.describe('Station map', () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.navigateToHome();
  });

  test('renders the map with OSM tiles and station markers', async ({ page }) => {
    const map = page.locator('#station-map');
    await expect(map).toBeVisible();
    // Leaflet attaches a tile pane and loads tiles once initialized.
    await expect(map.locator('.leaflet-tile-pane')).toBeAttached();
    await expect(map.locator('.leaflet-tile').first()).toBeVisible();
    // markercluster renders cluster bubbles for the ~3,200 stations.
    await expect(map.locator('.marker-cluster').first()).toBeVisible();
    // OSM attribution must be present (tile usage policy).
    await expect(map.locator('.leaflet-control-attribution')).toContainText('OpenStreetMap');
  });

  test('serves a non-empty GeoJSON FeatureCollection', async ({ page }) => {
    const geo = await page.evaluate(async () => {
      const r = await fetch('/api/stations.geojson');
      return r.json();
    });
    expect(geo.type).toBe('FeatureCollection');
    expect(geo.features.length).toBeGreaterThan(1000);
    const f = geo.features[0];
    expect(f.geometry.type).toBe('Point');
    expect(Array.isArray(f.geometry.coordinates)).toBe(true);
    expect(typeof f.properties.station_id).toBe('string');
  });

  test('"use this station" fills the form', async ({ page }) => {
    // Wait for the map module to expose its fill hook (set during init).
    await page.waitForFunction(() => typeof (window as any)._tideMapFillForm === 'function');
    await page.evaluate(() => (window as any)._tideMapFillForm('9449639', 'Point Roberts, WA'));
    await expect(page.locator('#station_id')).toHaveValue('9449639');
    await expect(page.locator('#station_search')).toHaveValue('Point Roberts, WA (9449639)');
  });

  test('country filter re-fits the map without page errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await expect(page.locator('#station-map .leaflet-tile').first()).toBeVisible();
    // Radios are visually hidden pills — selectCountryFilter clicks the parent label.
    await homePage.selectCountryFilter('USA');
    await page.waitForTimeout(800);
    await homePage.selectCountryFilter('Canada');
    await page.waitForTimeout(800);
    expect(errors).toEqual([]);
  });
});
