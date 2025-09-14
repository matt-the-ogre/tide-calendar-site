from dotenv import load_dotenv
import os
from app.database import init_database

load_dotenv()

init_database()

from app import app

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)
