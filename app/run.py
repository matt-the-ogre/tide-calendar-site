from dotenv import load_dotenv
import os
import logging
from app.database import init_database, import_stations_from_csv
from app.canadian_station_sync import import_canadian_stations_from_api
from app.station_coordinates import backfill_missing_coordinates
from app.calendar_service import cleanup_previous_month_pdfs

# Configure logging for startup messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

load_dotenv()

init_database()
import_stations_from_csv()
import_canadian_stations_from_api()
backfill_missing_coordinates()
# Old cached PDFs only go stale once a month; sweeping at startup keeps the
# request path free of directory scans (containers redeploy on every push).
cleanup_previous_month_pdfs()

from app import app

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
