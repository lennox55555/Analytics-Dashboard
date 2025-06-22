#!/bin/bash
cd /home/ec2-user/Analytics-Dashboard
source .env

while true; do
    echo "Running scraper at $(date)"
    docker-compose -f config/docker-compose.yml exec -T web /usr/local/bin/python3 /app/scrapers/ercot_scraper.py
    echo "Scraper completed at $(date)"
    sleep 900 
done
