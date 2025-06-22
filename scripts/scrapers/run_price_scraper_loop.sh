#!/bin/bash

# Price scraper loop - runs every 15 minutes
# This script continuously runs the ERCOT price scraper every 15 minutes

cd /home/ec2-user/Analytics-Dashboard
source .env

while true; do
    echo "Running price scraper at $(date)"
    docker-compose -f config/docker-compose.yml exec -T web /usr/local/bin/python3 /app/scrapers/ercot_price_scraper.py
    echo "Price scraper completed at $(date)"
    sleep 900  # 15 minutes
done