"""Startup self-heal: backfill coordinates for stations missing them.

The US CSV ships coordinates (see scripts/fetch_noaa_coordinates.py), but on a
warm production DB the CSV import short-circuits, so coordinates can be absent
there. This makes a single NOAA Metadata API call to fill any gaps. No-op (and
no network call) when nothing is missing. Always non-fatal.
"""
import logging
import sqlite3

# Dual import so this works both as the `app` package (flask/gunicorn) and as a
# top-level sibling module under `cd app && python -m unittest`. Reference
# database.DB_PATH dynamically (NOT `from ... import DB_PATH`) so tests that
# reassign database.DB_PATH are honored.
try:
    import app.database as database
except ImportError:
    import database


def _default_fetcher(url=None):
    # Imported lazily; runtime (run.py) executes from the repo root where the
    # `scripts` package is importable. Dual path keeps it robust.
    try:
        from scripts.fetch_noaa_coordinates import fetch_noaa_coordinates
    except ImportError:
        from fetch_noaa_coordinates import fetch_noaa_coordinates
    return fetch_noaa_coordinates()


def _missing_station_ids():
    with sqlite3.connect(database.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT station_id FROM tide_station_ids "
            "WHERE country = 'USA' AND (latitude IS NULL OR longitude IS NULL)"
        ).fetchall()
    return [r[0] for r in rows]


def backfill_missing_coordinates(fetcher=_default_fetcher):
    """Fill NULL coordinates for US stations. Returns the number updated."""
    try:
        missing = _missing_station_ids()
        if not missing:
            logging.info("Coordinate backfill: nothing missing, skipping NOAA call")
            return 0
        logging.info("Coordinate backfill: %d US stations missing coords; querying NOAA", len(missing))
        coords = fetcher()
        if not coords:
            logging.warning("Coordinate backfill: NOAA returned no coordinates")
            return 0
        updated = 0
        with sqlite3.connect(database.DB_PATH) as conn:
            for sid in missing:
                c = coords.get(sid)
                if c:
                    conn.execute(
                        "UPDATE tide_station_ids SET latitude=?, longitude=? WHERE station_id=?",
                        (c['lat'], c['lng'], sid))
                    updated += 1
            conn.commit()
        logging.info("Coordinate backfill: updated %d/%d stations", updated, len(missing))
        return updated
    except Exception as e:  # never fatal to startup
        logging.error("Coordinate backfill failed: %s", e)
        return 0
