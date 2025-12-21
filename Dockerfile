# Use the official Python image from the Docker Hub
FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_RUN_PORT=80

# Create and set the working directory
WORKDIR /app

# Create persistent data directory
RUN mkdir -p /data

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pcal \
    ghostscript && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only runtime application files (not dev tools, tests, or generated files)
# Core Python application files
COPY app/__init__.py /app/
COPY app/run.py /app/
COPY app/routes.py /app/
COPY app/get_tides.py /app/
COPY app/database.py /app/
COPY app/tide_adapters.py /app/
COPY app/canadian_station_sync.py /app/

# Templates and static assets
COPY app/templates/ /app/templates/
COPY app/static/ /app/static/

# Required CSV data files (imported at startup)
COPY app/tide_stations_new.csv /app/
COPY app/canadian_tide_stations.csv /app/

# Expose the port the app runs on
EXPOSE 80

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
