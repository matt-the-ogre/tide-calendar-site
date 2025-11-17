from dotenv import load_dotenv
import os
from app.database import init_database, import_stations_from_csv
from app.canadian_station_sync import import_canadian_stations_from_api

load_dotenv()

init_database()
import_stations_from_csv()
import_canadian_stations_from_api()

from app import app

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
