# Ombudsman Validation Studio - Deployment Guide

**Version:** 2.0.0
**Date:** December 4, 2025
**Status:** Production Ready

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [Deployment Methods](#deployment-methods)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Quick Start

### One-Command Deployment

```bash
# Navigate to the project directory
cd ombudsman-validation-studio

# Run the deployment script
./deploy.sh
```

The script will:
- ✅ Check Docker status
- ✅ Verify environment configuration
- ✅ Build images if needed
- ✅ Create data directories
- ✅ Start backend service
- ✅ Verify health checks

---

## Prerequisites

### Required Software

1. **Docker Desktop**
   - Version: 20.10+ or later
   - Download: https://www.docker.com/products/docker-desktop
   - Status: Must be running

2. **Docker Compose**
   - Version: 2.0+ (included with Docker Desktop)
   - Verify: `docker-compose --version`

3. **Database Connections** (Optional for initial deployment)
   - SQL Server (for source database)
   - Snowflake (for target database)

### System Requirements

- **CPU:** 2+ cores recommended
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 2GB free space for images
- **Network:** Internet for pulling base images

---

## Configuration

### Step 1: Environment Variables

Create or update `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### Required Variables:

#### SQL Server Configuration
```bash
MSSQL_HOST=host.docker.internal
MSSQL_PORT=1433
MSSQL_USER=sa
MSSQL_PASSWORD=YourPassword123!
MSSQL_DATABASE=SampleDW

# OR use connection string directly
SQLSERVER_CONN_STR="DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=SampleDW;UID=sa;PWD=YourPassword123!;TrustServerCertificate=yes;"
```

#### Snowflake Configuration
```bash
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_DATABASE=SAMPLEDW
SNOWFLAKE_SCHEMA=PUBLIC
```

#### Storage Paths (Auto-configured in Docker)
```bash
MAPPING_INTELLIGENCE_DIR=/data/mapping_intelligence
QUERY_HISTORY_DIR=/data/query_history
PIPELINE_RUNS_DIR=/data/pipeline_runs
CONFIG_BACKUPS_DIR=/data/config_backups
AUTH_DATA_DIR=/data/auth
```

### Step 2: Data Directories

Data directories are automatically created by the deployment script. Manual creation:

```bash
mkdir -p backend/data/{mapping_intelligence,query_history,pipeline_runs,config_backups,auth}
```

---

## Deployment Methods

### Method 1: Automated Script (Recommended)

```bash
./deploy.sh
```

**What it does:**
1. Checks Docker status
2. Verifies environment configuration
3. Stops existing containers
4. Builds/updates images
5. Creates data directories
6. Starts backend service
7. Performs health checks
8. Displays access information

### Method 2: Docker Compose (Manual)

#### Backend Only
```bash
# Build the image
docker-compose build studio-backend

# Start the service
docker-compose up -d studio-backend

# View logs
docker-compose logs -f studio-backend
```

#### Full Stack (Backend + Frontend)
```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Method 3: Development Mode

For development with hot reload:

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up -d

# This enables:
# - Hot reload on code changes
# - Volume mounts for live editing
# - Detailed logging
```

---

## Verification

### Step 1: Check Service Status

```bash
# View running containers
docker-compose ps

# Expected output:
# NAME                                        STATUS
# ombudsman-validation-studio-studio-backend-1   Up 2 minutes
```

### Step 2: Health Check

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok"}
```

### Step 3: API Documentation

Open in browser:
- **Health Check:** http://localhost:8000/health
- **API Docs (Swagger):** http://localhost:8000/docs
- **Feature List:** http://localhost:8000/features
- **Root Endpoint:** http://localhost:8000/

### Step 4: Test Key Endpoints

```bash
# Test metadata extraction endpoint
curl -X GET http://localhost:8000/features

# Should return list of all available features
```

### Step 5: View Logs

```bash
# View recent logs
docker-compose logs --tail=100 studio-backend

# Follow logs in real-time
docker-compose logs -f studio-backend
```

---

## Troubleshooting

### Issue 1: Docker Not Running

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
1. Start Docker Desktop application
2. Wait for Docker to fully start (icon in system tray)
3. Verify: `docker info`
4. Retry deployment

### Issue 2: Port Already in Use

**Error:** `port is already allocated`

**Solution:**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Use different external port
```

### Issue 3: Backend Won't Start

**Error:** Container exits immediately

**Solution:**
```bash
# View detailed logs
docker-compose logs studio-backend

# Check for:
# - Database connection errors
# - Missing environment variables
# - Python import errors

# Rebuild image
docker-compose build --no-cache studio-backend
docker-compose up -d studio-backend
```

### Issue 4: Cannot Connect to Database

**Error:** `Connection refused` or `Login failed`

**Solution:**
1. Verify database is running
2. Check `.env` credentials
3. For SQL Server on host machine:
   - Use `host.docker.internal` as hostname
   - Ensure SQL Server allows remote connections
4. For Snowflake:
   - Verify account identifier format
   - Check user permissions

### Issue 5: Data Not Persisting

**Error:** Data lost after container restart

**Solution:**
1. Check volume mounts in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./backend/data:/data
   ```
2. Verify data directories exist on host
3. Check file permissions:
   ```bash
   chmod -R 755 backend/data
   ```

### Issue 6: Out of Memory

**Error:** `Container killed` or `Out of memory`

**Solution:**
1. Increase Docker memory limit:
   - Docker Desktop → Settings → Resources → Memory
   - Recommended: 4GB minimum
2. Check memory usage:
   ```bash
   docker stats
   ```

---

## Maintenance

### Viewing Logs

```bash
# View all logs
docker-compose logs

# View backend logs only
docker-compose logs studio-backend

# Follow logs (real-time)
docker-compose logs -f studio-backend

# Last 100 lines
docker-compose logs --tail=100 studio-backend

# Since specific time
docker-compose logs --since 2h studio-backend
```

### Restarting Services

```bash
# Restart backend
docker-compose restart studio-backend

# Restart all services
docker-compose restart

# Stop and start (recreates containers)
docker-compose down
docker-compose up -d
```

### Updating Application

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose build --no-cache

# Restart services
docker-compose down
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

### Cleaning Up

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove images
docker rmi ombudsman-validation-studio-studio-backend

# Remove all unused Docker resources
docker system prune -a
```

### Database Backups

Backup data directories regularly:

```bash
# Backup all data
tar -czf backup-$(date +%Y%m%d).tar.gz backend/data/

# Restore from backup
tar -xzf backup-20251204.tar.gz
```

### Monitoring

```bash
# Check resource usage
docker stats

# Check container health
docker inspect --format='{{.State.Health.Status}}' ombudsman-validation-studio-studio-backend-1

# View container details
docker inspect ombudsman-validation-studio-studio-backend-1
```

---

## Production Deployment

### Security Checklist

- [ ] Change default passwords in `.env`
- [ ] Use `.env` file (never commit to git)
- [ ] Enable HTTPS/SSL if exposing externally
- [ ] Set up firewall rules
- [ ] Use strong authentication credentials
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### Performance Optimization

1. **Resource Limits:**
   ```yaml
   # Add to docker-compose.yml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
       reservations:
         memory: 2G
   ```

2. **Connection Pooling:**
   - Already configured in application
   - Adjust in `.env` if needed:
     ```bash
     DB_POOL_SIZE=10
     DB_MAX_OVERFLOW=20
     ```

3. **Caching:**
   - Redis integration (optional)
   - Query result caching enabled

### High Availability

For production environments:

1. **Load Balancing:**
   - Run multiple backend instances
   - Use nginx or HAProxy

2. **Database Replication:**
   - Read replicas for SQL Server
   - Snowflake auto-scales

3. **Health Monitoring:**
   - Set up Prometheus/Grafana
   - Configure alerts

---

## Quick Reference

### Common Commands

```bash
# Start services
./deploy.sh                                    # Automated deployment
docker-compose up -d                           # Manual start

# Stop services
docker-compose down                            # Stop and remove
docker-compose stop                            # Stop only

# View status
docker-compose ps                              # Container status
docker-compose logs -f                         # Live logs
curl http://localhost:8000/health             # Health check

# Update and restart
docker-compose build --no-cache               # Rebuild images
docker-compose up -d --force-recreate         # Recreate containers

# Troubleshooting
docker-compose logs --tail=100 studio-backend # Recent logs
docker stats                                   # Resource usage
docker-compose restart studio-backend         # Restart service
```

### Port Reference

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| Frontend (if deployed) | 3000 | http://localhost:3000 |

### File Locations

| Item | Location |
|------|----------|
| Configuration | `.env` |
| Docker Compose | `docker-compose.yml` |
| Backend Code | `backend/` |
| Data Storage | `backend/data/` |
| Logs | `docker-compose logs` |

---

## Support

### Getting Help

1. **Documentation:**
   - API Docs: http://localhost:8000/docs
   - Feature List: http://localhost:8000/features

2. **Logs:**
   ```bash
   docker-compose logs -f studio-backend
   ```

3. **Health Check:**
   ```bash
   curl -v http://localhost:8000/health
   ```

### Reporting Issues

When reporting issues, include:
- Docker version: `docker --version`
- Compose version: `docker-compose --version`
- OS and version
- Error messages from logs
- Steps to reproduce

---

## Next Steps

After successful deployment:

1. ✅ **Test Endpoints:** Visit http://localhost:8000/docs
2. ✅ **Configure Databases:** Update `.env` with real credentials
3. ✅ **Run Sample Validation:** Test with sample data
4. ✅ **Set Up Monitoring:** Configure health checks
5. ✅ **Review Logs:** Check for any warnings

---

**Deployment Guide Version:** 2.0.0
**Last Updated:** December 4, 2025
**Status:** ✅ Production Ready
