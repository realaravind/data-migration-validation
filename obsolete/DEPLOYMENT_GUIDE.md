# Ombudsman Validation Studio - Deployment Guide

**Version:** 2.0.0
**Last Updated:** December 3, 2025
**Status:** Production Ready

---

## 🎯 Overview

This guide covers deploying the Ombudsman Validation Studio to development, staging, and production environments.

---

## 📋 Prerequisites

### Required Software
- **Python:** 3.9 or higher
- **Docker:** 20.10+ (recommended for deployment)
- **Docker Compose:** 2.0+
- **SQL Server:** 2019+ or Azure SQL Database
- **Snowflake:** Account with appropriate permissions

### Optional (for advanced features)
- **AWS Account:** For AWS Secrets Manager
- **Azure Account:** For Azure Key Vault
- **HashiCorp Vault:** For enterprise secret management

---

## 🚀 Quick Start (Development)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd ombudsman-validation-studio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in `backend/` directory:

```env
# Application
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Database - SQL Server
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_SERVER_DATABASE=SampleDW
SQL_SERVER_USERNAME=sa
SQL_SERVER_PASSWORD=YourPassword123

# Database - Snowflake
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=YourPassword123
SNOWFLAKE_DATABASE=SAMPLEDW
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE=30
JWT_REFRESH_TOKEN_EXPIRE=7

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8000

# Features
ENABLE_AUTH=true
ENABLE_WEBSOCKETS=true
ENABLE_METRICS=true
```

### 3. Initialize Database

```bash
# Run authentication schema
sqlcmd -S localhost -d YourDB -U sa -P YourPassword -i backend/auth/schema.sql

# Verify tables created
sqlcmd -S localhost -d YourDB -U sa -P YourPassword -Q "SELECT name FROM sys.tables WHERE name LIKE 'Users' OR name LIKE 'RefreshTokens'"
```

### 4. Start the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the startup script
python main.py
```

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs

# Register first admin user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "SecureAdminPass123",
    "role": "admin",
    "full_name": "System Administrator"
  }'
```

---

## 🐳 Docker Deployment

### Option 1: Docker Compose (Recommended)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - SQL_SERVER_HOST=sql-server
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
    env_file:
      - .env.production
    volumes:
      - ./data:/data
      - ./logs:/logs
    depends_on:
      - sql-server
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped

  sql-server:
    image: mcr.microsoft.com/mssql/server:2019-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=YourStrong!Passw0rd
    ports:
      - "1433:1433"
    volumes:
      - sqlserver-data:/var/opt/mssql
    restart: unless-stopped

volumes:
  sqlserver-data:
```

**Deploy:**
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### Option 2: Individual Docker Container

**Dockerfile (backend/):**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /data /logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Build and Run:**
```bash
# Build
docker build -t ombudsman-backend:2.0.0 ./backend

# Run
docker run -d \
  --name ombudsman-backend \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  --env-file .env.production \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/logs \
  ombudsman-backend:2.0.0
```

---

## ☁️ Cloud Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)

1. **Push Image to ECR:**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag ombudsman-backend:2.0.0 <account-id>.dkr.ecr.us-east-1.amazonaws.com/ombudsman:2.0.0
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ombudsman:2.0.0
```

2. **Create ECS Task Definition:**
```json
{
  "family": "ombudsman-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/ombudsman:2.0.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DEBUG", "value": "false"}
      ],
      "secrets": [
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:ombudsman/jwt-secret"
        },
        {
          "name": "SQL_SERVER_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:ombudsman/sql-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ombudsman",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

3. **Configure Secrets Manager:**
```bash
# Create JWT secret
aws secretsmanager create-secret \
  --name ombudsman/jwt-secret \
  --secret-string "your-super-secret-jwt-key"

# Create database password
aws secretsmanager create-secret \
  --name ombudsman/sql-password \
  --secret-string "YourDatabasePassword"
```

4. **Deploy Service:**
```bash
aws ecs create-service \
  --cluster ombudsman-cluster \
  --service-name ombudsman-backend \
  --task-definition ombudsman-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Azure Deployment

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name ombudsman-rg --location eastus

# Create container
az container create \
  --resource-group ombudsman-rg \
  --name ombudsman-backend \
  --image <your-registry>.azurecr.io/ombudsman:2.0.0 \
  --cpu 2 \
  --memory 4 \
  --registry-login-server <your-registry>.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label ombudsman-api \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    DEBUG=false \
  --secure-environment-variables \
    JWT_SECRET_KEY=<secret> \
    SQL_SERVER_PASSWORD=<password>
```

#### Using Azure App Service

```bash
# Create App Service Plan
az appservice plan create \
  --name ombudsman-plan \
  --resource-group ombudsman-rg \
  --is-linux \
  --sku P1V2

# Create Web App
az webapp create \
  --resource-group ombudsman-rg \
  --plan ombudsman-plan \
  --name ombudsman-api \
  --deployment-container-image-name <your-registry>.azurecr.io/ombudsman:2.0.0

# Configure app settings
az webapp config appsettings set \
  --resource-group ombudsman-rg \
  --name ombudsman-api \
  --settings \
    ENVIRONMENT=production \
    DEBUG=false \
    WEBSITES_PORT=8000

# Configure secrets from Key Vault
az webapp config appsettings set \
  --resource-group ombudsman-rg \
  --name ombudsman-api \
  --settings \
    JWT_SECRET_KEY="@Microsoft.KeyVault(SecretUri=https://ombudsman-kv.vault.azure.net/secrets/jwt-secret/)"
```

---

## 🔐 Production Security Checklist

### Required Configuration

- [ ] Change default JWT secret key
- [ ] Use strong database passwords
- [ ] Enable SSL/TLS for databases
- [ ] Disable debug mode (`DEBUG=false`)
- [ ] Disable auto-reload (`RELOAD=false`)
- [ ] Use production-grade secret manager (AWS/Azure/Vault)
- [ ] Configure CORS to specific origins only
- [ ] Enable HTTPS for API endpoints
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Enable audit logging
- [ ] Set up monitoring and alerts

### Environment Variables Validation

```python
# Run validation
from config import get_config
from config.validation import validate_config

config = get_config()
result = validate_config(config)

if not result.is_valid():
    print("❌ Configuration errors:")
    for error in result.errors:
        print(f"  - {error}")
    exit(1)
else:
    print("✅ Configuration is valid")
```

---

## 📊 Monitoring & Logging

### Application Logs

Logs are written to `/logs` directory by default:

```bash
# View real-time logs
tail -f logs/application.log

# Search for errors
grep ERROR logs/application.log

# Filter by date
grep "2025-12-03" logs/application.log
```

### Health Checks

```bash
# Health endpoint
curl http://your-api.com/health

# Intelligent mapping health
curl http://your-api.com/mapping/intelligent/health

# Database connection status
curl http://your-api.com/connections/status
```

### Metrics Collection

Enable metrics in `.env`:
```env
ENABLE_METRICS=true
```

Metrics endpoints:
- `/metrics` - Prometheus format metrics
- `/mapping/intelligent/statistics` - Mapping statistics
- `/connections/pool/stats` - Connection pool metrics

---

## 🔄 Backup & Recovery

### Database Backup

```bash
# Backup authentication database
sqlcmd -S your-server -d YourDB -E -Q "BACKUP DATABASE YourDB TO DISK='backups/auth_backup.bak'"

# Backup configuration
cp -r config/ backups/config-$(date +%Y%m%d)/
cp .env.production backups/env-$(date +%Y%m%d)
```

### Pattern Backup

```bash
# Export learned mapping patterns
curl -X POST http://your-api.com/mapping/intelligent/export-patterns \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o backups/patterns-$(date +%Y%m%d).json
```

### Restore Patterns

```bash
# Import patterns
curl -X POST http://your-api.com/mapping/intelligent/import-patterns \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @backups/patterns-20251203.json
```

---

## 🧪 Testing Deployment

### Run Test Suite

```bash
# All tests
python3 -m pytest tests/ -v

# Unit tests only
python3 -m pytest tests/unit/ -v

# Integration tests
python3 -m pytest tests/integration/ -v

# With coverage
python3 -m pytest tests/ --cov=. --cov-report=html
```

### Smoke Tests

```bash
#!/bin/bash
# smoke-test.sh

API_URL="http://your-api.com"

# 1. Health check
echo "Testing health endpoint..."
curl -f $API_URL/health || exit 1

# 2. Authentication
echo "Testing authentication..."
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | jq -r '.access_token')

if [ -z "$TOKEN" ]; then
  echo "❌ Authentication failed"
  exit 1
fi
echo "✅ Authentication successful"

# 3. Protected endpoint
echo "Testing protected endpoint..."
curl -f -H "Authorization: Bearer $TOKEN" $API_URL/auth/me || exit 1
echo "✅ Protected endpoint accessible"

# 4. Intelligent mapping
echo "Testing intelligent mapping..."
curl -f -X POST $API_URL/mapping/intelligent/suggest \
  -H "Content-Type: application/json" \
  -d '{"source_columns":[{"name":"id"}],"target_columns":[{"name":"ID"}]}' \
  || exit 1
echo "✅ Intelligent mapping working"

echo "✅ All smoke tests passed!"
```

---

## 📚 Additional Resources

### Documentation
- API Documentation: `http://your-api.com/docs`
- Authentication Guide: `AUTHENTICATION_GUIDE.md`
- Intelligent Mapping Guide: `INTELLIGENT_MAPPING_GUIDE.md`
- Configuration Guide: `TASK_13_CONFIGURATION_SUMMARY.md`

### Support
- Issues: GitHub Issues
- Questions: Team Slack/Email
- Updates: Check releases for new versions

---

## 🎯 Post-Deployment Checklist

- [ ] Application starts without errors
- [ ] Health endpoint returns 200
- [ ] Database connections successful
- [ ] Admin user created and can login
- [ ] JWT tokens working
- [ ] Protected endpoints require authentication
- [ ] Intelligent mapping generating suggestions
- [ ] Configuration validation passes
- [ ] Secrets loaded from secret manager
- [ ] Logs being written correctly
- [ ] Metrics being collected
- [ ] Backups configured
- [ ] Monitoring alerts set up
- [ ] Documentation accessible
- [ ] Team trained on new features

---

## 🚨 Troubleshooting

### Common Issues

**Issue:** Application won't start
```bash
# Check logs
docker logs ombudsman-backend

# Verify environment variables
docker exec ombudsman-backend env | grep -E "(SQL|SNOWFLAKE|JWT)"

# Test configuration
docker exec ombudsman-backend python -c "from config import get_config; print(get_config())"
```

**Issue:** Database connection fails
```bash
# Test SQL Server connection
sqlcmd -S your-server -U your-user -P your-password -Q "SELECT 1"

# Test from container
docker exec ombudsman-backend python -c "
from sqlalchemy import create_engine
engine = create_engine('your-connection-string')
with engine.connect() as conn:
    print(conn.execute('SELECT 1').fetchone())
"
```

**Issue:** Authentication not working
```bash
# Check JWT secret is set
echo $JWT_SECRET_KEY

# Verify auth database tables exist
sqlcmd -S your-server -d YourDB -Q "SELECT name FROM sys.tables WHERE name LIKE '%User%' OR name LIKE '%Token%'"

# Test registration
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"Test123!","role":"user"}'
```

---

**Version:** 2.0.0
**Last Updated:** December 3, 2025
**Deployment Status:** Production Ready ✅
