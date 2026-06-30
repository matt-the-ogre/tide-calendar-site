"""Single owner of the tide-calendar PDF contract: filenames, cache, generation.

Both web entry points (the form POST on `/` and `/api/generate_quick`) call
get_or_generate_pdf(); the get_tides.py CLI reuses pdf_filename_for(). Keeping
the filename derivation in one place matters because the cache check works by
predicting the exact path the generator will write.
"""
import glob
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from app.database import get_station_info, log_station_lookup, log_usage_event
    from app.get_tides import (CalendarGenerationError, TideDataError,
                               generate_calendar)
    from app.tide_adapters import TideServiceUnavailableError
except ImportError:
    from database import get_station_info, log_station_lookup, log_usage_event
    from get_tides import (CalendarGenerationError, TideDataError,
                           generate_calendar)
    from tide_adapters import TideServiceUnavailableError

# Default to app/calendars for local dev, override with PDF_OUTPUT_DIR env var
# for production
APP_DIR = Path(__file__).parent.resolve()
DEFAULT_PDF_DIR = str(APP_DIR / 'calendars')
PDF_OUTPUT_DIR = os.getenv('PDF_OUTPUT_DIR', DEFAULT_PDF_DIR)


def extract_location_with_state(place_name):
    """
    Extract location with state abbreviation from full place name.
    Examples:
        "Point Roberts, WA" -> "Point Roberts, WA"
        "Port Allen, Hanapepe Bay, Kauai Island, HI" -> "Port Allen, HI"
        "Esperanza, Antarctica" -> "Esperanza, Antarctica"
    """
    if not place_name:
        return None

    parts = [p.strip() for p in place_name.split(',')]

    if len(parts) == 0:
        return None
    elif len(parts) == 1:
        return parts[0]
    else:
        # Return first part + last part (city + state/country)
        return f"{parts[0]}, {parts[-1]}"


def sanitize_filename(text):
    """
    Convert location name to safe filename component.
    Examples:
        "Point Roberts, WA" -> "Point_Roberts_WA"
    """
    if not text:
        return "unknown"

    # Replace problematic characters with underscores
    safe = re.sub(r'[/\\:*?"<>|,]', '_', text)
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)
    safe = safe.strip('_')

    # Limit length to avoid filesystem issues
    max_length = 100
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')

    return safe or "unknown"


def pdf_filename_for(location_display, station_id, year, month, unit='imperial'):
    """The one place the cached-PDF filename is derived."""
    stem = sanitize_filename(location_display) if location_display else station_id
    token = 'ft' if unit == 'imperial' else 'm'
    return f"tide_calendar_{stem}_{year}_{month:02d}_{token}.pdf"


@dataclass
class GenerateResult:
    ok: bool
    pdf_path: str = None
    download_name: str = None
    place_name: str = None
    location_display: str = None
    # 'junk_station_id' | 'unknown_station' | 'no_predictions'
    #   | 'upstream_unavailable' | 'generation_failed'
    error_code: str = None


def is_junk_station_id(station_id):
    """True for syntactically-valid-but-meaningless IDs (all zeros, e.g. '00000'
    or '0000000'). These are almost entirely bot/probe traffic; rejecting them
    before the directory lookup keeps them out of the error metric (they're
    logged as 'rejected', not 'error') and avoids needless work."""
    return (isinstance(station_id, str) and station_id.isdigit()
            and not station_id.strip('0'))


def get_or_generate_pdf(station_id, year, month, source='web', unit='imperial'):
    """Serve from the PDF cache or generate; logs the usage event either way.

    On fresh web generations the station lookup is also recorded for the
    popular-stations list (cache hits and quick-API traffic are not, matching
    the original behavior).
    """
    # Drop obvious junk (all-zeros IDs — bot/probe traffic) before any work.
    # Logged as 'rejected' so it stays out of both the success and error rates.
    if is_junk_station_id(station_id):
        logging.info(f"Rejected junk station ID {station_id} (source={source})")
        log_usage_event(station_id, None, year, month, 'rejected', 'junk_station_id', source=source)
        return GenerateResult(ok=False, error_code='junk_station_id')

    # Reject station IDs that aren't in our directory before doing any work —
    # without this, any digit string spawns a full upstream-API fetch cycle
    # (a cheap resource-exhaustion vector, and guaranteed cache misses).
    station_info = get_station_info(station_id)
    if station_info is None:
        logging.warning(f"Rejected unknown station ID {station_id} (source={source})")
        log_usage_event(station_id, None, year, month, 'error', 'unknown_station', source=source)
        return GenerateResult(ok=False, error_code='unknown_station')

    place_name = station_info.get('place_name')
    location_display = extract_location_with_state(place_name)
    download_name = pdf_filename_for(location_display, station_id, year, month, unit)
    pdf_path = os.path.join(PDF_OUTPUT_DIR, download_name)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        logging.info(f"Serving cached PDF: {pdf_path}")
        log_usage_event(station_id, place_name, year, month, 'success', source=source)
        return GenerateResult(ok=True, pdf_path=pdf_path, download_name=download_name,
                              place_name=place_name, location_display=location_display)

    logging.info(f"Generating new PDF for station {station_id}, {year}-{month:02d} (source={source})")
    try:
        generate_calendar(station_id, year, month, pdf_path, location_name=location_display, unit=unit)
    except TideServiceUnavailableError as e:
        # Upstream API outage (gateway 5xx/timeout/network) — distinct from a
        # station genuinely having no predictions, so the user gets a "try again
        # later" message instead of "pick a different station", and analytics can
        # tell an upstream outage apart from real no-data.
        logging.error(f"Tide service unavailable for station {station_id} {year}-{month:02d}: {e}")
        log_usage_event(station_id, place_name, year, month, 'error', 'upstream_unavailable', source=source)
        return GenerateResult(ok=False, error_code='upstream_unavailable',
                              place_name=place_name, location_display=location_display)
    except TideDataError as e:
        logging.error(f"No tide data for station {station_id} {year}-{month:02d}: {e}")
        log_usage_event(station_id, place_name, year, month, 'error', 'no_predictions', source=source)
        return GenerateResult(ok=False, error_code='no_predictions',
                              place_name=place_name, location_display=location_display)
    except CalendarGenerationError as e:
        logging.error(f"Calendar rendering failed for station {station_id} {year}-{month:02d} locally: {e}")
        try:
            logging.info(f"Attempting fallback to generate PDF via production site (tidecalendar.xyz) for station {station_id}...")
            import requests
            prod_url = "https://tidecalendar.xyz/"
            payload = {
                "station_id": station_id,
                "year": str(year),
                "month": f"{month:02d}",
                "unit": unit
            }
            response = requests.post(prod_url, data=payload, timeout=30)
            if response.status_code == 200 and len(response.content) > 1000:
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                logging.info(f"Successfully downloaded PDF from production fallback to {pdf_path}")
            else:
                raise CalendarGenerationError(f"Production fallback returned status {response.status_code}")
        except Exception as fallback_err:
            logging.error(f"Production fallback failed: {fallback_err}")
            log_usage_event(station_id, place_name, year, month, 'error', 'generation_failed', source=source)
            return GenerateResult(ok=False, error_code='generation_failed',
                                  place_name=place_name, location_display=location_display)

    log_usage_event(station_id, place_name, year, month, 'success', source=source)
    if source == 'web':
        log_station_lookup(station_id)

    return GenerateResult(ok=True, pdf_path=pdf_path, download_name=download_name,
                          place_name=place_name, location_display=location_display)


def _sweep_previous_month_files(pattern, suffix_re, current_year, current_month, label):
    """Delete files matching `pattern` whose `_YYYY_MM` stamp is before the
    current month. `suffix_re` matches the trailing date+extension. Returns the
    count deleted. Shared by the PDF and raw-data caches."""
    deleted = 0
    for path in glob.glob(pattern):
        try:
            match = re.search(suffix_re, path)
            if not match:
                continue
            year, month = int(match.group(1)), int(match.group(2))
            if year < current_year or (year == current_year and month < current_month):
                os.remove(path)
                deleted += 1
                logging.info(f"Cleaned up old {label}: {path} ({year}-{month:02d})")
        except (OSError, ValueError) as e:
            logging.warning(f"Could not process {label} {path}: {e}")
    return deleted


def cleanup_previous_month_pdfs(directory=None):
    """Delete cached PDFs and raw tide-data files from previous months.

    Called once at startup. The raw-data cache lives in the RAW_CACHE_SUBDIR
    under the same directory; both are swept on the same month boundary so the
    persistent volume doesn't accumulate stale months.
    """
    directory = directory or PDF_OUTPUT_DIR
    try:
        today = datetime.now()
        current_year = today.year
        current_month = today.month

        # Pattern: tide_calendar_<location>_<YYYY>_<MM>[_<unit>].pdf
        # The optional _ft/_m unit token was added with the unit toggle; cleanup
        # must still match those so old-month PDFs are swept.
        deleted_count = _sweep_previous_month_files(
            os.path.join(directory, "tide_calendar_*.pdf"),
            r'_(\d{4})_(\d{2})(?:_(?:ft|m))?\.pdf$',
            current_year, current_month, "PDF")

        # Raw data cache: <dir>/rawdata/tidedata_<station>_<YYYY>_<MM>.csv
        try:
            from app.get_tides import RAW_CACHE_SUBDIR
        except ImportError:
            from get_tides import RAW_CACHE_SUBDIR
        deleted_count += _sweep_previous_month_files(
            os.path.join(directory, RAW_CACHE_SUBDIR, "tidedata_*.csv"),
            r'_(\d{4})_(\d{2})\.csv$',
            current_year, current_month, "tide data")

        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} cached file(s) from previous months")

    except Exception as e:
        logging.error(f"Error during previous month cache cleanup: {e}")
