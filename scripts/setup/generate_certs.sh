#!/bin/bash

# This script generates SSL certificates using Let's Encrypt

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <domain> <email>"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

# Create certs directory if it doesn't exist
mkdir -p certs

# Run certbot to get certificates
sudo certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --domains $DOMAIN \
    --preferred-challenges http

# Copy certificates to our certs directory
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem certs/key.pem

# Fix permissions
sudo chown $USER:$USER certs/cert.pem certs/key.pem

echo "Certificates generated and copied to certs/ directory"