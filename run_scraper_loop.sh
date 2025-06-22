#!/bin/bash
  while true; do
    cd /home/ec2-user/Analytics-Dashboard
    echo "Running scraper at $(date)"
    # Pass the RDS connection info explicitly to make sure it's used
    docker-compose exec -T -e DB_HOST=dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com \
                        -e DB_NAME=analytics \
                        -e DB_USER=dbuser \
                        -e DB_PASSWORD=Superman1262! \
                        web /usr/local/bin/python3 /app/ercot_scraper.py
    echo "Scraper completed at $(date)"
    sleep 900 
  done
