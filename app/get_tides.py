"""Tide data download and PDF calendar generation pipeline.

Importable (app.calendar_service calls generate_calendar() in-process) and
runnable as a CLI (scripts/update_example_image.sh):

    python get_tides.py --station_id 9449639 --year 2024 --month 6
"""
import argparse
import logging
import os
import subprocess
import tempfile
import threading
from datetime import datetime

try:
    from app.database import log_station_lookup, get_station_info
    from app.tide_adapters import get_adapter_for_station
except ImportError:
    from database import log_station_lookup, get_station_info
    from tide_adapters import get_adapter_for_station

try:
    from app.sun_times import sun_times_for_month, format_sun_line, localize_and_filter_csv
except ImportError:
    from sun_times import sun_times_for_month, format_sun_line, localize_and_filter_csv

try:
    from app.tide_extremes import top_extreme_tides, format_extreme_rows
except ImportError:
    from tide_extremes import top_extreme_tides, format_extreme_rows

# Per-invocation timeout for each external tool (pcal, ps2pdf)
SUBPROCESS_TIMEOUT = 60

# Tides below this height (metres) are marked with an asterisk so pcal
# colour-codes the day
LOW_TIDE_THRESHOLD = 0.3


class TideDataError(Exception):
    """No usable tide predictions for the requested station/period."""


class CalendarGenerationError(Exception):
    """The pcal/ghostscript rendering pipeline failed."""


def download_tide_data(station_id, year, month):
    """Fetch tide predictions as CSV text via the appropriate API adapter.

    Returns the CSV string. Raises TideDataError when the station is unknown
    to both APIs or has no predictions for the period.
    """
    station_info = get_station_info(station_id)
    api_source = station_info.get('api_source') if station_info else None

    try:
        adapter = get_adapter_for_station(station_id, api_source)
    except ValueError as e:
        raise TideDataError(f"No adapter for station {station_id}: {e}") from e

    logging.info(f"Using {adapter.__class__.__name__} for station {station_id}")
    csv_data = adapter.get_predictions(station_id, year, month)

    if not csv_data:
        raise TideDataError(
            f"Failed to download data for station {station_id} ({year}-{month:02d})")

    lines = csv_data.splitlines()
    if len(lines) < 2:
        raise TideDataError(
            f"No predictions data found for station {station_id} in {year}-{month:02d}")
    if "No Predictions data was found." in lines[1]:
        raise TideDataError(
            f"No predictions data found for station {station_id} in {year}-{month:02d}")

    return csv_data


def _write_extreme_note(pcal_file, box, title, entries, empty_msg):
    """Write a stacked pcal note table into the given empty-cell box."""
    pcal_file.write(f"note/{box} all {title}\n")
    rows = format_extreme_rows(entries)
    if rows:
        for row in rows:
            pcal_file.write(f"note/{box} all {row}\n")
    else:
        pcal_file.write(f"note/{box} all {empty_msg}\n")


def convert_tide_data_to_pcal(csv_data, pcal_filename, location_name=None, station_id=None,
                              sun_times=None, high_tides=None, low_tides=None):
    """Convert tide CSV text to a pcal custom dates file.

    sun_times: optional {day:int -> ("HH:MM","HH:MM") | note str} from
    sun_times_for_month(); when present, a `Rise … Set …` line is written for
    each day BEFORE that day's tide lines so it sits at the top of the cell.
    """
    lines = csv_data.splitlines()

    with open(pcal_filename, 'w') as pcal_file:
        # Sun lines first so pcal places them above the tide events for each day.
        if sun_times:
            month_num = None
            for line in lines[1:]:
                if line.strip():
                    try:
                        month_num = int(line.strip().split(',')[0].split()[0].split('-')[1])
                        break
                    except (IndexError, ValueError):
                        continue
            if month_num is not None:
                for day in sorted(sun_times):
                    pcal_file.write(f"{month_num}/{day}  {format_sun_line(sun_times[day])}\n")

        valid_lines = 0
        skipped_lines = 0

        # lines[0] is the header
        for line_num, line in enumerate(lines[1:], start=2):
            if not line.strip():
                continue

            try:
                parts = line.strip().split(',')
                if len(parts) != 3:
                    logging.warning(f"Skipping line {line_num}: Expected 3 fields, got {len(parts)}: {line.strip()}")
                    skipped_lines += 1
                    continue

                date_time, prediction_str, tide_type = parts

                try:
                    prediction = round(float(prediction_str.strip()), 1)
                except ValueError:
                    logging.error(f"Line {line_num}: Could not convert prediction '{prediction_str}' to float. Line: {line.strip()}")
                    skipped_lines += 1
                    continue

                try:
                    date, time = date_time.strip().split()
                    year, month, day = date.split('-')
                except ValueError:
                    logging.error(f"Line {line_num}: Could not parse date/time '{date_time}'. Line: {line.strip()}")
                    skipped_lines += 1
                    continue

                tide_type = tide_type.strip().upper()
                if tide_type not in ['H', 'L']:
                    logging.warning(f"Line {line_num}: Invalid tide type '{tide_type}', defaulting to 'H'. Line: {line.strip()}")
                    tide_type = 'H'

                tide_type_full = "High" if tide_type == "H" else "Low"

                # Format the date for pcal (mm/dd); asterisk marks low tides
                # so pcal colour-codes the day
                pcal_date = f"{int(month)}/{int(day)}"
                if prediction < LOW_TIDE_THRESHOLD:
                    pcal_date += "*"

                pcal_file.write(f"{pcal_date}  {time} {tide_type_full} {prediction} m\n")
                valid_lines += 1

            except Exception as e:
                logging.error(f"Line {line_num}: Unexpected error parsing line: {e}. Line: {line.strip()}")
                skipped_lines += 1
                continue

        logging.info(f"Parsed {valid_lines} valid tide predictions, skipped {skipped_lines} malformed lines")

        if valid_lines == 0:
            raise TideDataError("No valid tide data found in API response")

        pcal_file.write("\n")

        # Daylight extreme-tide tables in unused cells (note/2, note/3).
        if high_tides is not None:
            _write_extreme_note(pcal_file, 2, "Top 5 High Tides (daylight)",
                                high_tides, "No daylight high tides")
        if low_tides is not None:
            _write_extreme_note(pcal_file, 3, "Top 5 Low Tides (daylight)",
                                low_tides, "No daylight low tides")

        # Tide station note shown on the calendar page
        if location_name:
            pcal_file.write(f"note/1 all Tide Station: {location_name}\n")
        else:
            pcal_file.write(f"note/1 all Tide Station ID: {station_id or 'unknown'}\n")


def _run_tool(cmd):
    """Run an external rendering tool with a timeout; raise on any failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=SUBPROCESS_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        raise CalendarGenerationError(f"{cmd[0]} timed out after {SUBPROCESS_TIMEOUT}s") from e
    except OSError as e:
        raise CalendarGenerationError(f"Could not run {cmd[0]}: {e}") from e
    if result.returncode != 0:
        raise CalendarGenerationError(
            f"{cmd[0]} exited {result.returncode}: {result.stderr.strip()[:500]}")
    return result


def generate_calendar(station_id, year, month, output_path, location_name=None):
    """Fetch tide data and render a PDF calendar at output_path. See module docs."""
    station_info = get_station_info(station_id) or {}
    api_source = station_info.get('api_source')
    iana_tz = station_info.get('timezone')
    lat = station_info.get('latitude')
    lng = station_info.get('longitude')

    # A CHS station with no timezone can't be localized: tide times would silently
    # stay in UTC and no sun line would be drawn. Surface it so it's diagnosable
    # (the fix is to re-run scripts/fetch_station_timezones.py for the new station).
    if (api_source or '').upper() == 'CHS' and not iana_tz:
        logging.warning(
            "CHS station %s has no timezone; tide times will render in UTC and "
            "no sunrise/sunset line will be shown", station_id)

    csv_data = download_tide_data(station_id, year, month)
    # CHS times are UTC -> convert to the station's local zone and trim to the
    # local month (NOAA passes through unchanged).
    csv_data = localize_and_filter_csv(csv_data, api_source, iana_tz, year, month)
    sun = sun_times_for_month(lat, lng, iana_tz, year, month)

    # Top-5 daylight high/low tables (only when we have a timezone AND coordinates
    # to define the daylight window; otherwise skip — omitting the tables rather
    # than showing a misleading "no daylight tides" cell, like the sun line).
    if iana_tz and lat is not None and lng is not None:
        high_tides, low_tides = top_extreme_tides(csv_data, lat, lng, iana_tz, year, month)
    else:
        high_tides, low_tides = None, None

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    tmp_pdf = f"{output_path}.tmp.{os.getpid()}.{threading.get_ident()}"

    try:
        with tempfile.TemporaryDirectory(prefix='tidecal-') as tmpdir:
            pcal_path = os.path.join(tmpdir, 'events.txt')
            ps_path = os.path.join(tmpdir, 'calendar.ps')

            convert_tide_data_to_pcal(csv_data, pcal_path,
                                      location_name=location_name,
                                      station_id=station_id,
                                      sun_times=sun,
                                      high_tides=high_tides,
                                      low_tides=low_tides)

            _run_tool(["pcal", "-f", pcal_path, "-o", ps_path,
                       "-s", "0.0:0.0:1.0", "-n", "Helvetica-Narrow/9",
                       "-m", "-C", "tidecalendar.xyz",
                       str(month), str(year)])
            _run_tool(["ps2pdf", ps_path, tmp_pdf])

            if not os.path.exists(tmp_pdf) or os.path.getsize(tmp_pdf) == 0:
                raise CalendarGenerationError("ps2pdf produced no output")
            os.replace(tmp_pdf, output_path)
    finally:
        if os.path.exists(tmp_pdf):
            os.remove(tmp_pdf)

    logging.info(f"PDF file created: {output_path}")
    return output_path


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate a tide calendar PDF.")
    parser.add_argument('--station_id', type=str, default='9449639', help='Station ID (default: 9449639)')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Year (default: current year)')
    parser.add_argument('--month', type=int, default=datetime.now().month, help='Month (default: current month)')
    parser.add_argument('--location_name', type=str, default=None, help='Human-readable location name for display')
    parser.add_argument('--skip_logging', action='store_true', help='Skip logging station lookup to database')
    args = parser.parse_args()

    if args.month < 1 or args.month > 12:
        logging.error("Month must be between 1 and 12")
        raise SystemExit(1)

    # Filename contract and output dir are owned by calendar_service; imported
    # lazily here to avoid a circular import (calendar_service imports us).
    try:
        from app.calendar_service import pdf_filename_for, PDF_OUTPUT_DIR
    except ImportError:
        from calendar_service import pdf_filename_for, PDF_OUTPUT_DIR

    output_path = os.path.join(
        PDF_OUTPUT_DIR,
        pdf_filename_for(args.location_name, args.station_id, args.year, args.month))

    try:
        generate_calendar(args.station_id, args.year, args.month, output_path,
                          location_name=args.location_name)
    except (TideDataError, CalendarGenerationError) as e:
        logging.error(f"Could not generate calendar: {e}")
        raise SystemExit(1)

    # Log AFTER successful generation so failed lookups never pollute the
    # popular stations list
    if not args.skip_logging:
        log_station_lookup(args.station_id)
        logging.info(f"Logged successful lookup for station {args.station_id}")


if __name__ == "__main__":
    main()
