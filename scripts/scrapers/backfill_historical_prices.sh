#!/bin/bash

# One-time historical data backfill script
# This script loads the last 5 days + today of ERCOT price data

cd /home/ec2-user/Analytics-Dashboard

echo "Starting historical price data backfill at $(date)"
echo "This will load data for the last 6 days (5 days ago through today)"

# Load environment variables
source .env

# Run the price scraper with backfill flag
docker-compose -f config/docker-compose.yml exec -T web /usr/local/bin/python3 /app/scrapers/ercot_price_scraper.py --backfill

echo "Historical backfill completed at $(date)"
echo "You can now set up the regular 15-minute cron job for ongoing updates"
