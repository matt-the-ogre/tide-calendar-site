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
    from app.database import (get_place_name_by_station_id, log_station_lookup,
                              log_usage_event)
    from app.get_tides import (CalendarGenerationError, TideDataError,
                               generate_calendar)
except ImportError:
    from database import (get_place_name_by_station_id, log_station_lookup,
                          log_usage_event)
    from get_tides import (CalendarGenerationError, TideDataError,
                           generate_calendar)

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


def pdf_filename_for(location_display, station_id, year, month):
    """The one place the cached-PDF filename is derived."""
    stem = sanitize_filename(location_display) if location_display else station_id
    return f"tide_calendar_{stem}_{year}_{month:02d}.pdf"


@dataclass
class GenerateResult:
    ok: bool
    pdf_path: str = None
    download_name: str = None
    place_name: str = None
    location_display: str = None
    error_code: str = None  # 'no_predictions' | 'generation_failed'


def get_or_generate_pdf(station_id, year, month, source='web'):
    """Serve from the PDF cache or generate; logs the usage event either way.

    On fresh web generations the station lookup is also recorded for the
    popular-stations list (cache hits and quick-API traffic are not, matching
    the original behavior).
    """
    place_name = get_place_name_by_station_id(station_id)
    location_display = extract_location_with_state(place_name)
    download_name = pdf_filename_for(location_display, station_id, year, month)
    pdf_path = os.path.join(PDF_OUTPUT_DIR, download_name)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        logging.info(f"Serving cached PDF: {pdf_path}")
        log_usage_event(station_id, place_name, year, month, 'success', source=source)
        return GenerateResult(ok=True, pdf_path=pdf_path, download_name=download_name,
                              place_name=place_name, location_display=location_display)

    logging.info(f"Generating new PDF for station {station_id}, {year}-{month:02d} (source={source})")
    try:
        generate_calendar(station_id, year, month, pdf_path, location_name=location_display)
    except TideDataError as e:
        logging.error(f"No tide data for station {station_id} {year}-{month:02d}: {e}")
        log_usage_event(station_id, place_name, year, month, 'error', 'no_predictions', source=source)
        return GenerateResult(ok=False, error_code='no_predictions',
                              place_name=place_name, location_display=location_display)
    except CalendarGenerationError as e:
        logging.error(f"Calendar rendering failed for station {station_id} {year}-{month:02d}: {e}")
        log_usage_event(station_id, place_name, year, month, 'error', 'generation_failed', source=source)
        return GenerateResult(ok=False, error_code='generation_failed',
                              place_name=place_name, location_display=location_display)

    log_usage_event(station_id, place_name, year, month, 'success', source=source)
    if source == 'web':
        log_station_lookup(station_id)

    return GenerateResult(ok=True, pdf_path=pdf_path, download_name=download_name,
                          place_name=place_name, location_display=location_display)


def cleanup_previous_month_pdfs(directory=None):
    """Delete cached PDFs from previous months. Called once at startup."""
    directory = directory or PDF_OUTPUT_DIR
    try:
        today = datetime.now()
        current_year = today.year
        current_month = today.month

        pdf_pattern = os.path.join(directory, "tide_calendar_*.pdf")
        deleted_count = 0

        for pdf_file in glob.glob(pdf_pattern):
            try:
                # Pattern: tide_calendar_<location>_<YYYY>_<MM>.pdf
                match = re.search(r'_(\d{4})_(\d{2})\.pdf$', pdf_file)
                if match:
                    pdf_year = int(match.group(1))
                    pdf_month = int(match.group(2))

                    if pdf_year < current_year or (pdf_year == current_year and pdf_month < current_month):
                        os.remove(pdf_file)
                        deleted_count += 1
                        logging.info(f"Cleaned up old PDF: {pdf_file} ({pdf_year}-{pdf_month:02d})")
            except (OSError, ValueError) as e:
                logging.warning(f"Could not process PDF {pdf_file}: {e}")

        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} PDF(s) from previous months")

    except Exception as e:
        logging.error(f"Error during previous month PDF cleanup: {e}")
