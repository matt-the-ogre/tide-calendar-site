#!/usr/bin/env python3
"""
Generate the authoritative Canadian station -> province lookup.

The bulk CHS /stations list does NOT include a province, and the official station
name almost never carries one, so the app otherwise falls back to a longitude-based
guess that is wrong ~50% of the time. The authoritative `provinceCode` lives only in
the per-station /metadata endpoint. Fetching ~1,076 of those at container startup is
infeasible (CHS rate-limits hard), so this offline maintenance script precomputes the
map and writes it to app/canadian_station_provinces.csv, which is shipped and loaded
at runtime by canadian_station_sync.PROVINCE_BY_CODE.

Behaviour:
- Polite: ~1 request / RATE_DELAY seconds, with retry + exponential backoff.
- Resumable: existing rows in the output CSV are kept; only missing codes are fetched,
  and progress is checkpointed periodically — so a throttle/interrupt doesn't restart.

Run (occasionally, e.g. monthly, alongside validate_tide_stations.py):
    python3 scripts/fetch_canadian_provinces.py
Expected runtime: ~30-50 minutes for ~1,076 stations — CHS throttling slows it down
partway through (the rate drops as retries/backoff kick in). It is resumable and
checkpoints the CSV every 25 stations, so a slow run is normal — DON'T kill it; just
re-run later and it continues. Watch progress via the CSV row count.
"""

import argparse
import csv
import json
import logging
import os
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URLS = [
    "https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1",
    "https://api-iwls.dfo-mpo.gc.ca/api/v1",
]
HEADERS = {'User-Agent': 'TideCalendarSite/1.0 (province map maintenance script)'}
APP_DIR = Path(__file__).resolve().parent.parent / 'app'
OUTPUT = APP_DIR / 'canadian_station_provinces.csv'

RATE_DELAY = 0.7      # seconds between requests (CHS throttles aggressively)
MAX_RETRIES = 4
CHECKPOINT_EVERY = 25

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_station_list():
    """Return (stations, base_url) from the first reachable CHS endpoint."""
    for base in BASE_URLS:
        try:
            return _get(f"{base}/stations"), base
        except Exception as e:
            log.warning(f"Station list fetch from {base} failed: {e}")
    raise SystemExit("All CHS endpoints failed for the station list")


def fetch_province(base, station_id):
    """Fetch provinceCode for one station, with retry/backoff. Returns code or None."""
    url = f"{base}/stations/{station_id}/metadata"
    for attempt in range(MAX_RETRIES):
        try:
            return _get(url).get('provinceCode')
        except Exception:
            time.sleep(RATE_DELAY * (2 ** attempt))  # 0.7, 1.4, 2.8, 5.6
    return None


def load_existing():
    existing = {}
    if OUTPUT.exists():
        with open(OUTPUT, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                code, prov = (row.get('code') or '').strip(), (row.get('province') or '').strip()
                if code and prov:
                    existing[code] = prov
    return existing


def write_map(mapping):
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['code', 'province'])
        for code in sorted(mapping):
            w.writerow([code, mapping[code]])


def main():
    parser = argparse.ArgumentParser(description="Build the code->province map from CHS /metadata.")
    parser.add_argument('--limit', type=int, default=None, help='Only process the first N missing codes (for testing).')
    args = parser.parse_args()

    stations, base = fetch_station_list()
    targets = [s for s in stations
               if s.get('code') and s.get('officialName')
               and any(ts.get('code') == 'wlp-hilo' for ts in s.get('timeSeries', []))]
    by_code = {s['code']: s for s in targets}
    log.info(f"{len(targets)} calendar-capable stations from {base}")

    mapping = load_existing()
    missing = [c for c in by_code if c not in mapping]
    if args.limit:
        missing = missing[:args.limit]
    log.info(f"Already have {len(mapping)}; fetching {len(missing)} missing provinceCodes...")

    fetched = no_prov = failed = 0
    for i, code in enumerate(missing, 1):
        prov = fetch_province(base, by_code[code]['id'])
        if prov:
            mapping[code] = prov
            fetched += 1
        elif prov is None:
            # Could be a real None (no provinceCode) or exhausted retries; either way
            # leave it out so runtime falls back to inference for this code.
            no_prov += 1
        if i % CHECKPOINT_EVERY == 0:
            write_map(mapping)
            log.info(f"  checkpoint {i}/{len(missing)} (mapped={fetched}, no_province={no_prov})")
        time.sleep(RATE_DELAY)

    write_map(mapping)
    log.info(f"Done. Wrote {len(mapping)} rows to {OUTPUT} (fetched={fetched}, no_province/failed={no_prov + failed})")


if __name__ == "__main__":
    main()
