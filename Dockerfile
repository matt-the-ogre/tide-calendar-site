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

# # Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY app /app

# Install system dependencies
RUN apt-get update && \
apt-get install -y --no-install-recommends \
pcal \
ghostscript && \
rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to the container
COPY requirements.txt /app

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 80

# Command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
