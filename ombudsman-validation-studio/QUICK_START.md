# Ombudsman Validation Studio - Quick Start

**Version:** 2.0.0
**Status:** ✅ Ready for Deployment

---

## 🚀 3-Step Quick Start

### Step 1: Start Docker Desktop

**Mac:**
- Open "Docker Desktop" from Applications
- Wait for Docker icon in menu bar to stabilize
- Verify: Green light/whale icon indicates running

**Windows:**
- Launch Docker Desktop from Start Menu
- Wait for "Docker Desktop is running" notification

**Linux:**
```bash
sudo systemctl start docker
```

---

### Step 2: Deploy Backend

Navigate to project and run deployment script:

```bash
cd ombudsman-validation-studio
./deploy.sh
```

**What happens:**
- ✅ Checks Docker status
- ✅ Verifies configuration
- ✅ Creates data directories
- ✅ Starts backend service
- ✅ Performs health checks

**Expected output:**
```
==================================================
Ombudsman Validation Studio - Deployment Script
==================================================

✓ Docker is running
✓ Environment file found
✓ Stopped existing containers
✓ Backend image exists
✓ Data directories created
✓ Backend container started
✓ Backend is healthy and responding

==================================================
✓ Deployment Complete!
==================================================

Backend API:
  - URL: http://localhost:8000
  - Health: http://localhost:8000/health
  - API Docs: http://localhost:8000/docs
```

---

### Step 3: Verify Deployment

**Option A: Browser**
- Open: http://localhost:8000/docs
- You should see Swagger UI with all API endpoints

**Option B: Command Line**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## 🎯 Quick Access

### API Endpoints

| Endpoint | URL | Description |
|----------|-----|-------------|
| Health Check | http://localhost:8000/health | Service status |
| API Documentation | http://localhost:8000/docs | Interactive API docs |
| Feature List | http://localhost:8000/features | All available features |
| Root | http://localhost:8000/ | API information |

---

## 🔧 Common Commands

### Service Management

```bash
# Start services
./deploy.sh

# Stop services
docker-compose down

# Restart services
docker-compose restart studio-backend

# View logs
docker-compose logs -f studio-backend

# Check status
docker-compose ps
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Get all features
curl http://localhost:8000/features

# View API docs
open http://localhost:8000/docs  # Mac
xdg-open http://localhost:8000/docs  # Linux
start http://localhost:8000/docs  # Windows
```

---

## 🆘 Quick Troubleshooting

### Issue: "Docker is not running"
**Solution:** Start Docker Desktop and wait ~30 seconds

### Issue: "Port 8000 already in use"
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
```

### Issue: "Backend won't start"
```bash
# View detailed logs
docker-compose logs studio-backend

# Rebuild and restart
docker-compose build studio-backend
docker-compose up -d studio-backend
```

### Issue: "Cannot connect to database"
- Check `.env` file has correct credentials
- Verify databases are running and accessible

---

## 📚 Key Features

### 1. Metadata Extraction
Extract schemas from SQL Server and Snowflake databases.

```bash
# Test endpoint
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"database": "source", "tables": ["Customers"]}'
```

### 2. Intelligent Mapping
AI-powered column mapping with fuzzy matching.

```bash
# Get suggestions
curl -X POST http://localhost:8000/mapping/suggest \
  -H "Content-Type: application/json" \
  -d '{"source_columns": [...], "target_columns": [...]}'
```

### 3. Custom Query Validation
Validate business queries between databases.

```bash
# See examples
curl http://localhost:8000/custom-queries/examples
```

### 4. Result Comparison (Task 6 - Latest Feature!)
Advanced result comparison with row-level diffing.

```bash
# Compare results
curl -X POST http://localhost:8000/custom-queries/results/compare \
  -H "Content-Type: application/json" \
  -d '{
    "sql_results": [...],
    "snow_results": [...],
    "comparison_type": "rowset",
    "key_columns": ["id"]
  }'
```

---

## 🎓 Next Steps

### After Deployment:

1. **Explore API Documentation:**
   - Visit: http://localhost:8000/docs
   - Try out endpoints interactively

2. **Configure Databases:**
   - Edit `.env` with your SQL Server credentials
   - Edit `.env` with your Snowflake credentials
   - Restart: `docker-compose restart studio-backend`

3. **Run Sample Validation:**
   - Use sample data generator
   - Execute validation pipeline
   - View results

4. **Review Features:**
   - Check: http://localhost:8000/features
   - Read detailed guides in documentation

---

## 📖 Documentation

- **Deployment Guide:** `DEPLOYMENT_GUIDE.md` (comprehensive)
- **Status Report:** `DEPLOYMENT_STATUS.md` (current status)
- **Task 6 Guide:** `CUSTOM_QUERY_RESULTS_GUIDE.md` (result handling)
- **Technical Summary:** `CONVERSATION_TECHNICAL_SUMMARY.md` (implementation details)

---

## ✅ Deployment Checklist

- [ ] Docker Desktop running
- [ ] Run `./deploy.sh`
- [ ] Health check passes: http://localhost:8000/health
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] Update `.env` with real credentials (optional)
- [ ] Test key endpoints

---

## 🎉 Success!

Once you see:
```
✓ Backend is healthy and responding
```

Your Ombudsman Validation Studio is **LIVE** and ready to use!

**Access the API:** http://localhost:8000/docs

---

**Quick Start Version:** 1.0
**Date:** December 4, 2025
**Status:** ✅ Ready
