#!/bin/bash
  while true; do
    cd /home/ec2-user/Analytics-Dashboard
    echo "Running scraper at $(date)"
    docker-compose exec -T web /usr/local/bin/python3 /app/ercot_scraper.py
    echo "Scraper completed at $(date)"
    sleep 60 
  done