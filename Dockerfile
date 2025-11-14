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

# Copy the application code
COPY app /app

# Expose the port the app runs on
EXPOSE 80

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
