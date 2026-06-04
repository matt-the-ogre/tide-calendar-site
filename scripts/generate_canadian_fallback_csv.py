#!/usr/bin/env python3
"""
Regenerate app/canadian_tide_stations.csv — the offline fallback used only when the
CHS API is unreachable at container startup.

The committed fallback was a small, stale, hand-curated set with no alternative_name
column, so an API outage degraded the site to a fraction of its stations with no
common-name search. This script snapshots a full live import so the degraded mode
closely matches normal operation.

It is fast: fetch_canadian_stations_from_api() returns fully-normalized stations
(correct provinces from the baked province map, alternative names, formatted place
names) from a single bulk /stations call — no per-station /metadata calls. Province
accuracy therefore depends on app/canadian_station_provinces.csv being current; run
scripts/fetch_canadian_provinces.py first if needed.

Run: python3 scripts/generate_canadian_fallback_csv.py
"""

import csv
import logging
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

import canadian_station_sync as css  # noqa: E402  (needs APP_DIR on sys.path first)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OUTPUT = APP_DIR / 'canadian_tide_stations.csv'
# Keep the existing column order; append alternative_name (read by both CSV importers).
COLUMNS = ['station_id', 'place_name', 'province', 'latitude', 'longitude',
           'country', 'api_source', 'alternative_name']


def main():
    stations, source = css.fetch_canadian_stations_from_api()
    if not stations:
        raise SystemExit(f"CHS API fetch failed ({source}); fallback CSV left unchanged")

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for s in sorted(stations, key=lambda x: x['code']):
            writer.writerow([
                s['code'],
                s['place_name'],
                s['province'],
                s['latitude'],
                s['longitude'],
                'Canada',
                'CHS',
                s['alternativeName'] or '',
            ])

    logging.info(f"Wrote {len(stations)} stations to {OUTPUT} (source: {source})")


if __name__ == "__main__":
    main()
