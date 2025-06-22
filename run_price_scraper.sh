#!/bin/bash

# Regular price scraper runner script
# This script runs the ERCOT price scraper every 15 minutes for today's data only

# Set the PATH to include common directories
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

cd /home/ec2-user/Analytics-Dashboard

echo "Running price scraper at $(date)"

# Use full path to docker-compose
/usr/local/bin/docker-compose exec -T -e DB_HOST=dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com \
                    -e DB_NAME=analytics \
                    -e DB_USER=dbuser \
                    -e DB_PASSWORD=Superman1262! \
                    web /usr/local/bin/python3 /app/ercot_price_scraper.py

echo "Price scraper completed at $(date)"
