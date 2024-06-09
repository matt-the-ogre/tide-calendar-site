#!/bin/bash

# Change to the project directory
cd /opt/tide-calendar

# Pull the latest changes from GitHub
git pull origin main

# Build and restart the Docker containers
docker-compose down
docker-compose up --build -d
