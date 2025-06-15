# Analytics Dashboard

A comprehensive analytics dashboard solution built with FastAPI, PostgreSQL, and Grafana. This project deploys a complete analytics stack on AWS EC2, including a Python backend, PostgreSQL database, and Grafana for visualization.

## Architecture

- **FastAPI Backend**: Serves the web application, handles API endpoints, and proxies Grafana requests
- **PostgreSQL Database**: Stores application data and analytics information
- **Grafana**: Creates and displays interactive dashboards
- **Docker**: Containerizes all services for easy deployment
- **HTTPS**: Secured with Let's Encrypt SSL certificates

## Features

- Interactive stock price analytics dashboards
- RESTful API endpoints for data access
- Secure Grafana integration via proxy
- HTTPS support with Let's Encrypt
- Containerized deployment with Docker

## Deployment Guide

### Prerequisites

- AWS Account with EC2 permissions
- Registered domain with DNS management access (HostGator)
- Basic knowledge of AWS services

### Step 1: Launch EC2 Instance

1. Launch a t3.large EC2 instance with Ubuntu Server 20.04 LTS
2. Configure Security Group:
   - Allow HTTP (80) and HTTPS (443) from anywhere
   - Allow SSH (22) from your IP
3. Create and attach an Elastic IP to your instance

### Step 2: Set Up Domain DNS

1. In your HostGator account, create an A record pointing to your EC2 Elastic IP:
   - Type: A
   - Name: dashboard (or @ for root domain)
   - Value: Your EC2 Elastic IP
   - TTL: 3600 (or lower for faster propagation)

### Step 3: Deploy the Application

1. SSH into your EC2 instance:
   ```
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

2. Clone this repository:
   ```
   git clone https://github.com/yourusername/analytics-dashboard.git
   cd analytics-dashboard
   ```

3. Run the setup script:
   ```
   chmod +x ec2_setup.sh
   ./ec2_setup.sh
   ```

4. Generate SSL certificates:
   ```
   chmod +x generate_certs.sh
   ./generate_certs.sh yourdomain.com your@email.com
   ```

5. Update the environment variables if needed:
   ```
   nano .env
   ```

6. Restart the application:
   ```
   docker-compose down
   docker-compose up -d
   ```

## Database Schema

The application uses the following database schema:

- **apple_stock**: Raw stock data imported from CSV
  - date, open, high, low, close, volume

- **daily_metrics**: Calculated daily metrics
  - date, avg_price, volume_change_pct, price_change_pct

- **monthly_metrics**: Aggregated monthly metrics
  - month, avg_price, max_price, min_price, total_volume, volatility

## Dashboards

1. **Stock Overview**: Daily stock prices and trading volume
2. **Monthly Metrics**: Monthly price averages, volatility, and volume

## Development

### Local Development

1. Clone the repository
2. Install Docker and Docker Compose
3. Create a `.env` file with required variables
4. Run `docker-compose up -d`
5. Access the application at http://localhost

### Adding Custom Dashboards

1. Create JSON dashboard definitions in `grafana/provisioning/dashboards/`
2. Add dashboard to the provisioning list in `grafana/provisioning/dashboards/dashboards.yaml`
3. Restart Grafana container: `docker-compose restart grafana`

## Maintenance

### SSL Certificate Renewal

Let's Encrypt certificates expire every 90 days. To renew:

```
./generate_certs.sh yourdomain.com your@email.com
docker-compose restart web
```

### Backup and Restore

To backup the database:

```
docker exec analytics-dashboard_db_1 pg_dump -U dbuser analytics > backup.sql
```

To restore:

```
cat backup.sql | docker exec -i analytics-dashboard_db_1 psql -U dbuser analytics
```

## Troubleshooting

- **Grafana not loading**: Check the proxy configuration in `app.py`
- **Database connection issues**: Verify the `.env` file has the correct database credentials
- **HTTPS certificate problems**: Run the certificate generation script again and check permissions

## License

This project is licensed under the MIT License - see the LICENSE file for details.