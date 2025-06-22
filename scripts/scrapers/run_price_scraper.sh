#!/bin/bash

# Regular price scraper runner script
# This script runs the ERCOT price scraper every 15 minutes for today's data only

# Set the PATH to include common directories
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

cd /home/ec2-user/Analytics-Dashboard

echo "Running price scraper at $(date)"

# Load environment variables
source .env

# Use full path to docker-compose from config directory
/usr/local/bin/docker-compose -f config/docker-compose.yml exec -T web /usr/local/bin/python3 /app/scrapers/ercot_price_scraper.py

echo "Price scraper completed at $(date)"
