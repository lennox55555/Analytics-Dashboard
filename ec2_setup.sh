#!/bin/bash

# EC2 setup script for Analytics Dashboard (Amazon Linux 2023)

# Update system packages
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.15.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Certbot for SSL certificates
sudo yum install -y certbot

# Clone the repository (replace with your actual repository URL)
# git clone https://github.com/yourusername/analytics-dashboard.git
# cd analytics-dashboard

# Create a self-signed certificate for initial testing
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=example.com"

# Set up the .env file
cat > .env << EOL
# Database Configuration
DB_HOST=db
DB_NAME=analytics
DB_USER=dbuser
DB_PASSWORD=$(openssl rand -base64 12)

# HTTPS Configuration
USE_HTTPS=true
SSL_CERT_FILE=certs/cert.pem
SSL_KEY_FILE=certs/key.pem

# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 12)
EOL

# Start the application
sudo docker-compose up -d

echo "Setup complete!"
echo "To generate proper SSL certificates, run: ./generate_certs.sh your-domain.com your-email@example.com"
echo "Then update the .env file to set USE_HTTPS=true and restart the containers with: docker-compose restart"