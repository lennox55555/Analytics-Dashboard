# ERCOT Analytics Dashboard

A comprehensive real-time analytics platform for monitoring and analyzing the Electric Reliability Council of Texas (ERCOT) grid operations. This enterprise-grade solution combines advanced data processing, AI-powered visualization generation, and real-time monitoring capabilities to provide comprehensive insights into Texas's electrical grid performance.

## 🏗️ Architecture Overview

### Core Technologies

- **Backend**: FastAPI (Python) with asynchronous processing
- **Database**: PostgreSQL with RDS hosting on AWS
- **Visualization**: Grafana with custom dashboard provisioning
- **AI/ML**: AWS Bedrock (Claude 3 Sonnet) for intelligent visualization generation
- **Authentication**: JWT-based auth with session management
- **Containerization**: Docker Compose for orchestrated deployment
- **Security**: SSL/TLS with Let's Encrypt, API key management
- **Cloud Platform**: AWS (EC2, RDS, Bedrock)

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  FastAPI App    │───▶│    Grafana      │
│  (ERCOT APIs)   │    │   (Backend)     │    │ (Visualization) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   PostgreSQL    │    │  User Dashboard │
                    │   (AWS RDS)     │    │   (Frontend)    │
                    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  AWS Bedrock    │
                    │ (AI Generation) │
                    └─────────────────┘
```

## 🚀 Features

### Real-Time Grid Monitoring
- **Live Data Streams**: Continuous monitoring of ERCOT settlement prices, capacity, and reserves
- **Interactive Dashboards**: Customizable, real-time visualization of grid operations
- **Alert System**: Automated monitoring for emergency conditions and outages
- **Historical Analysis**: Time-series data analysis with configurable time ranges

### User Management & Personalization
- **Secure Authentication**: JWT-based authentication with bcrypt password hashing
- **Personal Dashboards**: Customizable dashboard layouts for each user
- **Role-Based Access**: Configurable permissions and access controls
- **Session Management**: Secure session handling with automatic expiration

### AI-Powered Analytics
- **Natural Language Queries**: Generate visualizations using plain English descriptions
- **Intelligent Chart Creation**: AI automatically selects appropriate chart types and data
- **Custom Dashboard Generation**: AI creates and deploys custom Grafana dashboards
- **Data Insights**: Automated analysis and recommendation system

### API Services
- **RESTful API**: Comprehensive API for data access and system integration
- **API Key Management**: Secure API access with usage tracking and rate limiting
- **Documentation**: Interactive API documentation with real-time testing
- **Webhook Support**: Event-driven notifications and integrations

## 🔒 Security, Scalability & Reliability

### Security Framework

**Authentication & Authorization**
- JWT tokens with configurable expiration (24-hour default)
- Bcrypt password hashing with salt rounds
- API key authentication with SHA-256 hashing
- Session management with IP and user-agent tracking
- CORS protection with configurable origins

**Data Protection**
- SSL/TLS encryption with Let's Encrypt certificates
- Environment variable-based configuration for sensitive data
- SQL injection protection through parameterized queries
- Rate limiting and usage monitoring for API endpoints
- Secure headers (X-Frame-Options, CSP, X-Content-Type-Options)

**Infrastructure Security**
- AWS security groups with minimal required access
- Database encryption at rest and in transit
- VPC isolation for database resources
- Regular security updates through containerized deployment

### Scalability Architecture

**Horizontal Scaling**
- Containerized architecture enabling easy horizontal scaling
- Stateless application design for load balancer compatibility
- Database connection pooling for efficient resource utilization
- Async/await patterns for non-blocking operations

**Performance Optimization**
- Database indexing on timestamp and foreign key columns
- Grafana panel caching for improved response times
- Efficient SQL queries with proper WHERE clauses and LIMIT statements
- Compressed JSON responses and optimized data structures

**Resource Management**
- Configurable worker processes and connection pools
- Memory-efficient data processing with streaming where possible
- Automatic cleanup of expired sessions and temporary data
- Monitoring and alerting for resource utilization

### Reliability & Monitoring

**High Availability**
- Health check endpoints for monitoring system status
- Database failover capabilities with RDS Multi-AZ
- Graceful error handling with proper HTTP status codes
- Automatic service restart capabilities with Docker

**Data Integrity**
- Transaction management for critical operations
- Data validation at multiple layers (API, database, frontend)
- Backup and restore procedures for PostgreSQL
- Audit logging for user actions and system events

**Monitoring & Observability**
- Comprehensive logging with structured format
- Real-time system health monitoring
- Performance metrics collection and analysis
- Error tracking and notification system

## 📊 Advanced Analytics

### Data Processing Pipeline

**Real-Time Data Ingestion**
- **ERCOT API Integration**: Automated data collection from ERCOT's public APIs
  - Settlement point prices (15-minute intervals)
  - System capacity and reserves (1-minute intervals)
  - Emergency alerts and system status updates
- **Data Validation**: Multi-layer validation ensuring data quality and consistency
- **ETL Processing**: Extract, Transform, Load pipeline with error handling and retry logic
- **Time Series Storage**: Optimized PostgreSQL schema for time-series data analysis

**Data Processing Components**
```python
# Key data processing modules
ercot_scraper.py          # Main data collection service
ercot_price_scraper.py    # Settlement price data processor
capacity_scraper.py       # System capacity monitoring
cleanup_to_15min.py       # Data aggregation and cleanup
```

**Data Quality Assurance**
- Duplicate detection and removal
- Missing data interpolation algorithms
- Anomaly detection for data validation
- Data lineage tracking and audit trails

### Visualization Components

**Dynamic Dashboard System**
- **Grafana Integration**: Seamless integration with Grafana for professional visualizations
- **Custom Panel Types**: Time series, bar charts, tables, and statistical panels
- **Real-Time Updates**: 30-second refresh cycles for live data monitoring
- **Responsive Design**: Mobile-friendly dashboard layouts

**AI-Powered Visualization Engine**
```python
# AI visualization core components
ai_visualization_core.py  # Main AI processing engine
grafana_api.py           # Grafana dashboard creation
bedrock_integration.py   # AWS Bedrock AI services
```

**Visualization Features**
- Automatic chart type selection based on data characteristics
- Smart color palettes and styling
- Interactive filtering and time range selection
- Export capabilities (PNG, PDF, CSV)

### Real-Time Monitoring

**Live Data Streaming**
- WebSocket connections for real-time data updates
- Server-Sent Events (SSE) for push notifications
- Configurable refresh intervals (30s to 5m)
- Automatic reconnection handling

**Alert System**
- Threshold-based alerting for critical metrics
- Emergency condition monitoring
- Email and webhook notifications
- Escalation procedures for unacknowledged alerts

**Performance Monitoring**
- API response time tracking
- Database query performance analysis
- System resource utilization monitoring
- User activity and engagement metrics

## 🔌 API Services

### Working API Service

**Comprehensive RESTful API**
- **Authentication Endpoints**: `/api/auth/login`, `/api/auth/register`, `/api/auth/me`
- **Data Access**: `/api/v1/settlement-prices`, `/api/v1/capacity-monitor`
- **Dashboard Management**: `/api/dashboard/settings`, `/api/dashboard/available-panels`
- **AI Services**: `/api/ai/visualizations`, `/api/ai/visualizations/clear`
- **Key Management**: `/api/keys` (CRUD operations for API keys)

**API Example Usage**
```bash
# Get settlement prices with API key
curl -H "X-API-Key: ercot_abc123..." \
     -H "X-API-Secret: secret456..." \
     "https://your-domain.com/api/v1/settlement-prices?start_date=2024-01-01&hub=houston&limit=100"

# Create AI visualization
curl -X POST \
     -H "Authorization: Bearer your-jwt-token" \
     -H "Content-Type: application/json" \
     -d '{"request_text": "Show me west hub prices over 24 hours", "visualization_type": "chart"}' \
     "https://your-domain.com/api/ai/visualizations"
```

### API Documentation

**Interactive Documentation**
- **Swagger/OpenAPI**: Auto-generated API documentation at `/api/docs`
- **Real-Time Testing**: Test API endpoints directly from documentation
- **Code Examples**: Sample requests in multiple programming languages
- **Response Schemas**: Detailed response format documentation

**Authentication Methods**
1. **JWT Bearer Tokens**: For user-based authentication
2. **API Keys**: For programmatic access with rate limiting
3. **Basic Auth**: Administrative access for system integration

### Security Measures

**API Protection**
- **Rate Limiting**: Configurable limits per hour/day per API key
- **Usage Tracking**: Detailed logging of API usage patterns
- **IP Allowlisting**: Optional IP-based access restrictions
- **Request Validation**: Schema validation for all API inputs

**API Key Management**
```python
# API key features
- Secure generation with cryptographic randomness
- SHA-256 hashing for storage
- Configurable expiration dates
- Usage analytics and monitoring
- Immediate revocation capabilities
```

### Usage Metrics

**Analytics Dashboard**
- API endpoint performance metrics
- Usage patterns and trends analysis
- Error rate monitoring and alerting
- User behavior analytics

**Monitoring Features**
- Real-time API usage dashboards
- Historical usage trend analysis
- Performance bottleneck identification
- Capacity planning recommendations

## 🤖 Development with AWS Bedrock

### Complete AI Application

**AWS Bedrock Integration**
- **Claude 3 Sonnet Model**: Advanced language model for natural language processing
- **Intelligent Data Analysis**: AI automatically understands user requests and selects appropriate data
- **SQL Generation**: Dynamic SQL query creation based on natural language input
- **Visualization Recommendations**: AI suggests optimal chart types and configurations

**AI System Architecture**
```python
class AIVisualizationProcessor:
    - BedrockAIClient: AWS Bedrock integration
    - DatabaseAnalyzer: Data source analysis
    - GrafanaAPI: Dashboard creation
    - SQLGenerator: Dynamic query generation
```

### Architecture Documentation

**AI Processing Flow**
1. **Request Analysis**: Natural language processing of user requests
2. **Data Source Selection**: Intelligent selection of relevant ERCOT data tables
3. **Query Generation**: Creation of optimized SQL queries
4. **Visualization Creation**: Automated Grafana dashboard generation
5. **Dashboard Integration**: Seamless addition to user's personal dashboard

**Technical Implementation**
```python
# Core AI components
ai_visualization_core.py:
  - Initialize AI system with database configuration
  - Process user requests through Bedrock
  - Generate working SQL queries
  - Create Grafana dashboards
  - Manage visualization lifecycle
```

### AI-Powered Card Creation

**Intelligent Visualization Generation**
- **Natural Language Input**: Users describe visualizations in plain English
- **Context Awareness**: AI understands ERCOT domain terminology and data relationships
- **Smart Defaults**: Automatic selection of appropriate time ranges, aggregations, and filters
- **Quality Assurance**: Validation of generated queries and visualizations

**AI Card Features**
```javascript
// Frontend AI integration
- Real-time visualization creation
- Preview of generated data
- Automatic dashboard integration
- User feedback and refinement
- Duplicate detection and prevention
```

**Example AI Interactions**
```
User: "Show me settlement prices for the west hub over the last 24 hours"
AI Response: Generated line chart with west hub price data, automatically added to dashboard

User: "Compare capacity reserves across all regions"
AI Response: Multi-series chart comparing reserve levels by region
```

### User Guide

**Getting Started with AI Features**
1. **Authentication**: Sign up or log in to access AI capabilities
2. **Request Creation**: Click the AI card and describe your visualization needs
3. **Review & Customize**: Preview generated visualizations before adding to dashboard
4. **Dashboard Management**: Organize and customize your AI-generated content

**Best Practices**
- Use specific terminology (hub names, time ranges, metrics)
- Start with simple requests and build complexity
- Leverage the AI's understanding of ERCOT data structures
- Combine AI-generated content with predefined dashboards

### Security Documentation

**AI System Security**
- **Input Sanitization**: All user requests are validated and sanitized
- **Query Validation**: Generated SQL queries are verified before execution
- **Access Control**: AI features require authenticated access
- **Audit Logging**: All AI interactions are logged for security and debugging

**Data Privacy**
- User requests are processed securely through AWS Bedrock
- No sensitive data is exposed to AI models
- Generated visualizations respect user permissions
- Automatic cleanup of temporary AI processing data

## 📋 Installation & Deployment

### Prerequisites

- **AWS Account**: EC2, RDS, and Bedrock access
- **Domain Name**: With DNS management capabilities
- **SSL Certificate**: Let's Encrypt integration included
- **System Requirements**: t3.large EC2 instance (minimum)

### Quick Start

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/analytics-dashboard.git
cd analytics-dashboard
```

2. **AWS Infrastructure Setup**
```bash
# Launch EC2 instance (t3.large recommended)
# Create RDS PostgreSQL instance
# Configure Security Groups (ports 22, 80, 443)
# Set up Elastic IP
```

3. **Environment Configuration**
```bash
# Set environment variables
export DB_HOST=your-rds-endpoint
export DB_PASSWORD=your-secure-password
export AWS_ACCESS_KEY_ID=your-aws-key
export AWS_SECRET_ACCESS_KEY=your-aws-secret
```

4. **Automated Deployment**
```bash
chmod +x ec2_setup.sh
./ec2_setup.sh

# Generate SSL certificates
chmod +x generate_certs.sh
./generate_certs.sh yourdomain.com your@email.com
```

5. **Launch Services**
```bash
docker-compose up -d
```

### Manual Configuration

**Database Setup**
```bash
# Initialize database schema
python setup_dashboard_db.py
python setup_auth_db.py
python setup_api_tables.py

# Load initial data
python import_data.py
```

**Grafana Configuration**
- Default credentials: admin/admin
- Automatic dashboard provisioning
- PostgreSQL datasource auto-configuration
- Custom panel templates included

## 🔧 Development

### Local Development Environment

**Prerequisites**
- Python 3.9+
- Docker & Docker Compose
- PostgreSQL client tools
- AWS CLI configured

**Setup**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Run development server
python app.py
```

**Development Features**
- Hot reloading with uvicorn
- Debug logging enabled
- Development database seeding
- Mock AWS services for testing

### Testing

**Test Suite**
```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run API tests
pytest tests/api/

# Performance testing
pytest tests/performance/
```

### Contributing

**Code Style**
- PEP 8 compliance required
- Type hints for all functions
- Comprehensive docstrings
- Unit test coverage >80%

**Pull Request Process**
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Update documentation
5. Submit pull request

## 📊 Monitoring & Maintenance

### System Monitoring

**Health Checks**
- Application health: `/health`
- Database connectivity verification
- External API availability checks
- SSL certificate expiration monitoring

**Maintenance Tasks**
```bash
# SSL certificate renewal (every 90 days)
./generate_certs.sh yourdomain.com your@email.com
docker-compose restart web

# Database backup
docker exec postgres_container pg_dump -U dbuser analytics > backup.sql

# Log rotation and cleanup
docker system prune -f
```

### Performance Optimization

**Database Tuning**
- Index optimization for time-series queries
- Connection pool configuration
- Query performance monitoring
- Automated vacuum and analyze

**Application Performance**
- Response time monitoring
- Memory usage optimization
- Cache implementation strategies
- Load balancing preparation

## 🛠️ Configuration

### Environment Variables

```bash
# Database Configuration
DB_HOST=dashboard-database-instance-1.cyo31ygmzfva.us-east-1.rds.amazonaws.com
DB_NAME=analytics
DB_USER=dbuser
DB_PASSWORD=your-secure-password

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1

# Application Settings
SECRET_KEY=your-jwt-secret-key
GRAFANA_URL=http://grafana:3000
GRAFANA_API_KEY=your-grafana-api-key

# Security Settings
CORS_ORIGINS=https://yourdomain.com
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Advanced Configuration

**Grafana Customization**
- Custom datasource configuration
- Dashboard template modification
- Plugin installation and configuration
- Theme and branding customization

**API Rate Limiting**
```python
# Configurable rate limits
RATE_LIMIT_PER_HOUR = 1000
RATE_LIMIT_PER_DAY = 10000
RATE_LIMIT_BURST = 50
```

## 📚 Additional Resources

### Documentation Links
- [ERCOT API Documentation](http://www.ercot.com/mktinfo/data_agg)
- [Grafana Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

### Support & Community
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Community support through GitHub Discussions
- **Documentation**: Comprehensive wiki with examples and tutorials
- **Updates**: Follow changelog for latest features and fixes

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for the Texas energy community**

This comprehensive analytics platform represents the cutting edge of grid monitoring technology, combining real-time data processing, AI-powered insights, and enterprise-grade security to provide unparalleled visibility into Texas's electrical grid operations.