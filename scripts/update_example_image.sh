#!/usr/bin/env bash
#
# Updates app/static/tide-calendar-example.webp with next month's calendar
# for Point Roberts, WA (station 9449639).
#
# Usage: ./scripts/update_example_image.sh
#
# Requirements: Python 3, pcal, ghostscript, imagemagick
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$PROJECT_ROOT/app"
STATIC_DIR="$APP_DIR/static"
OUTPUT_IMAGE="$STATIC_DIR/tide-calendar-example.webp"

STATION_ID="9449639"  # Point Roberts, WA
LOCATION_NAME="Point Roberts, WA"

# Calculate next month's year and month
NEXT_MONTH=$(date -v+1m +%m 2>/dev/null || date -d "+1 month" +%m)
NEXT_YEAR=$(date -v+1m +%Y 2>/dev/null || date -d "+1 month" +%Y)
# Remove leading zero for the app
MONTH_NUM=$((10#$NEXT_MONTH))

echo "Generating tide calendar for $LOCATION_NAME"
echo "  Station: $STATION_ID"
echo "  Month: $MONTH_NUM/$NEXT_YEAR"
echo ""

# Activate venv if present
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Generate the PDF directly via get_tides.py
echo "Generating PDF..."
cd "$PROJECT_ROOT"
PYTHONPATH="$APP_DIR" python "$APP_DIR/get_tides.py" \
    --station_id "$STATION_ID" \
    --year "$NEXT_YEAR" \
    --month "$MONTH_NUM" \
    --location_name "$LOCATION_NAME" \
    --skip_logging

# Find the generated PDF
PDF_DIR="${PDF_OUTPUT_DIR:-$APP_DIR/calendars}"
PDF_FILE="$PDF_DIR/tide_calendar_Point_Roberts_WA_${NEXT_YEAR}_$(printf '%02d' $MONTH_NUM).pdf"

if [ ! -s "$PDF_FILE" ]; then
    echo "ERROR: PDF was not generated at $PDF_FILE"
    ls -la "$PDF_DIR"/ 2>/dev/null || true
    exit 1
fi

echo "PDF generated: $PDF_FILE ($(wc -c < "$PDF_FILE" | tr -d ' ') bytes)"

# Convert PDF to WebP
echo "Converting PDF to WebP..."
magick -density 200 "${PDF_FILE}[0]" -quality 85 -resize 850x "$OUTPUT_IMAGE"

echo "Updated: $OUTPUT_IMAGE ($(wc -c < "$OUTPUT_IMAGE" | tr -d ' ') bytes)"

echo ""
echo "Done! Example image updated for $(date -v+1m +"%B %Y" 2>/dev/null || date -d '+1 month' +"%B %Y")."
