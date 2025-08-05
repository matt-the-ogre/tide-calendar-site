from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()

def init_db():
    conn = sqlite3.connect('tide_station_ids.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tide_station_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            lookup_count INTEGER NOT NULL,
            last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

from app import app

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
