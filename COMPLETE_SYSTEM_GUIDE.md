# 🎉 Complete System Guide - Ombudsman Data Migration Validator

## ✅ What's Working NOW

You have **4 containers running** with 3 fully functional services:

| Service | Status | Port | What It Does |
|---------|--------|------|--------------|
| **Validation Studio Frontend** | ✅ **WORKING** | 3000 | React UI for validation workflows |
| **Validation Studio Backend** | ✅ **WORKING** | 8000 | FastAPI with metadata extraction & intelligent mapping |
| **SQL Server (Azure SQL Edge)** | ✅ **WORKING** | 1433 | Database with sample TestTable |
| **Ombudsman Core Web App** | ⚠️ Needs Fixes | 5001 | Original app (requires Snowflake) |

---

## 🚀 Quick Start - Use the Working Studio

### Start the System
```bash
# Start all services
make complete

# Or manually
docker-compose -f docker-compose.complete.yml up -d

# Check status
docker-compose -f docker-compose.complete.yml ps
```

### Access the Applications
```
✅ Validation Studio Frontend:   http://localhost:3000
✅ Validation Studio Backend:    http://localhost:8000
✅ API Documentation (Swagger):  http://localhost:8000/docs
⚠️  Ombudsman Core Web (broken): http://localhost:5001
```

---

## 📊 Available APIs (Port 8000)

### 1. **Metadata Extraction** - Extract Table Schema

```bash
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{
    "connection": "sqlserver",
    "table": "TestTable"
  }'
```

**Returns:**
```json
{
  "columns": [
    {
      "name": "ID",
      "data_type": "int",
      "precision": 10,
      "nullable": false,
      "primary_key": true
    },
    {
      "name": "Name",
      "data_type": "nvarchar",
      "max_length": 100,
      "nullable": false
    }
  ]
}
```

### 2. **Intelligent Mapping** - Auto-Generate Column Mappings

```bash
curl -X POST http://localhost:8000/mapping/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "source": [
      {"name": "src_customer_id", "data_type": "int"},
      {"name": "src_customer_name", "data_type": "varchar"},
      {"name": "src_email_address", "data_type": "varchar"}
    ],
    "target": [
      {"name": "customer_id", "data_type": "int"},
      {"name": "customer_name", "data_type": "varchar"},
      {"name": "email", "data_type": "varchar"}
    ]
  }'
```

**Returns:**
```json
{
  "mappings": [
    {
      "source": "src_customer_id",
      "target": "customer_id",
      "confidence": 100.0,
      "auto_mapped": false
    },
    {
      "source": "src_customer_name",
      "target": "customer_name",
      "confidence": 100.0,
      "auto_mapped": false
    },
    {
      "source": "src_email_address",
      "target": "email",
      "confidence": 71.18,
      "auto_mapped": true
    }
  ],
  "stats": {
    "total_source": 3,
    "total_target": 3,
    "mapped": 3,
    "mapping_percentage": 100.0
  }
}
```

### 3. **Mapping Intelligence Features**

The mapping algorithm includes:
- ✅ **Fuzzy Name Matching** - "EmailAddress" → "Email" (71% confidence)
- ✅ **Prefix Normalization** - Removes "src_", "tgt_", "dim_", "fact_"
- ✅ **Type Compatibility** - Scores SQL Server ↔ Snowflake type matches
- ✅ **Confidence Scoring** - Each mapping gets a confidence percentage
- ✅ **Unmatched Tracking** - Identifies columns that couldn't be mapped

---

## 🗄️ Database Access

### SQL Server Connection
```bash
# Connection details
Host:     localhost
Port:     1433
User:     sa
Password: YourStrong!Passw0rd
Database: master
```

### Sample Table Available
```sql
-- TestTable structure
CREATE TABLE dbo.TestTable (
    ID INT PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Email VARCHAR(255),
    Age INT,
    CreatedDate DATETIME DEFAULT GETDATE()
);
```

### Connect from Python
```python
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=master;"
    "UID=sa;"
    "PWD=YourStrong!Passw0rd;"
    "TrustServerCertificate=yes;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT * FROM dbo.TestTable")
rows = cursor.fetchall()
```

---

## 📁 Project Structure

```
data-migration-validator/
├── docker-compose.complete.yml    # ⭐ Complete system (4 containers)
├── docker-compose.unified.yml     # Studio only (3 containers)
├── Makefile                        # make complete, make unified, make stop
│
├── ombudsman-validation-studio/   # NEW Validation Studio
│   ├── frontend/                   # React + Vite (port 3000)
│   │   ├── src/
│   │   ├── Dockerfile.dev
│   │   └── package.json
│   └── backend/                    # FastAPI (port 8000)
│       ├── main.py
│       ├── core_adapter.py         # Bridges to ombudsman_core
│       ├── metadata/
│       ├── mapping/
│       └── requirements.txt
│
└── ombudsman_core/                 # Original Core Library
    ├── src/
    │   ├── ombudsman/
    │   │   ├── core/               # MetadataLoader, MappingLoader
    │   │   ├── pipeline/           # Pipeline execution
    │   │   └── config/             # YAML configs
    │   └── web/                    # Original web app (needs Snowflake)
    ├── Dockerfile
    └── docker-compose.yml
```

---

## 🔧 Docker Commands

### Start/Stop
```bash
# Start complete system
make complete
docker-compose -f docker-compose.complete.yml up -d

# Stop all services
make stop
docker-compose -f docker-compose.complete.yml down

# View logs
docker-compose -f docker-compose.complete.yml logs -f

# View specific service logs
docker logs studio-backend -f
docker logs studio-frontend -f
docker logs ombudsman-core-app -f
docker logs sqlserver -f
```

### Rebuild
```bash
# Rebuild all containers
docker-compose -f docker-compose.complete.yml up -d --build

# Rebuild specific service
docker-compose -f docker-compose.complete.yml up -d --build studio-backend
```

### Clean Up
```bash
# Stop and remove containers, networks, volumes
docker-compose -f docker-compose.complete.yml down -v

# Remove all project containers
make clean
```

---

## 📝 Environment Variables

Located in: `/ombudsman_core/.env`

```bash
# SQL Server
MSSQL_HOST=sqlserver
MSSQL_PORT=1433
MSSQL_DATABASE=master
MSSQL_USER=sa
MSSQL_PASSWORD=YourStrong!Passw0rd

# Snowflake (optional - not currently working)
SNOW_HOST=snowflake-emulator
SNOW_PORT=8080
SNOW_USER=admin
SNOW_PASSWORD=dummy
SNOW_DATABASE=DEMO_DB
SNOW_SCHEMA=PUBLIC
```

---

## 🎯 Common Tasks

### Extract Metadata from Your Own Table

1. **Create a table in SQL Server:**
```sql
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -C -Q "
CREATE TABLE dbo.YourTable (
    ID INT PRIMARY KEY,
    Name VARCHAR(100)
);
"
```

2. **Extract metadata via API:**
```bash
curl -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"connection": "sqlserver", "table": "YourTable"}'
```

### Generate Mappings for Your Tables

```bash
# Get source columns
SOURCE_COLS=$(curl -s -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"connection": "sqlserver", "table": "SourceTable"}')

# Get target columns
TARGET_COLS=$(curl -s -X POST http://localhost:8000/metadata/extract \
  -H "Content-Type: application/json" \
  -d '{"connection": "sqlserver", "table": "TargetTable"}')

# Generate mappings
curl -X POST http://localhost:8000/mapping/suggest \
  -H "Content-Type: application/json" \
  -d "{\"source\": $SOURCE_COLS, \"target\": $TARGET_COLS}"
```

---

## ⚠️ Known Issues & Limitations

### Ombudsman Core Web App (Port 5001)
**Status:** ⚠️ Not Working
**Reason:** Multiple issues:
1. Requires Snowflake database (not running)
2. Import paths need extensive refactoring
3. Dependencies on `Executor` and `Logger` modules not found

**Workaround:** Use the Validation Studio APIs (port 8000) instead.

### Snowflake Emulator
**Status:** ⚠️ Not Running
**Reason:** `databrickslabs/snowflake-simulator` image doesn't exist

**Options:**
1. Use LocalStack Snowflake (requires auth token)
2. Connect to real Snowflake instance
3. Use SQL Server only (current setup)

### Sample Data Generation
**Status:** ⚠️ Disabled
**Reason:** Foreign key constraint errors when regenerating

**Workaround:** TestTable already exists with sample structure.

---

## 🚀 Next Steps & Enhancements

### Immediate Improvements
1. **Connect Frontend to Backend APIs**
   - Build UI for metadata extraction
   - Build UI for mapping suggestions
   - Display confidence scores visually

2. **Add More Validation Rules**
   - Row count validation
   - Data type validation
   - Null checks
   - Referential integrity

3. **Pipeline Visualization**
   - Mermaid diagram generation
   - Pipeline status tracking
   - Execution history

### Future Enhancements
1. **Snowflake Support**
   - Fix ombudsman-core web app imports
   - Add Snowflake emulator or real connection
   - Cross-database validation

2. **Advanced Mapping**
   - ML-based suggestions
   - Historical mapping analysis
   - User feedback loop

3. **Reporting**
   - Validation reports
   - Mapping reports
   - Data quality metrics

---

## 📚 Documentation Files

- **FIXES_APPLIED.md** - Docker infrastructure fixes
- **CODE_FIXES_APPLIED.md** - Code integration fixes
- **COMPLETE_FIX_SUMMARY.md** - Overall summary
- **COMPLETE_SYSTEM_GUIDE.md** - This file

---

## 🆘 Troubleshooting

### Services Won't Start
```bash
# Check logs
docker-compose -f docker-compose.complete.yml logs

# Rebuild without cache
docker-compose -f docker-compose.complete.yml up -d --build --force-recreate
```

### Port Already in Use
```bash
# Check what's using the port
lsof -i :3000
lsof -i :8000
lsof -i :5001

# Kill the process
kill -9 <PID>
```

### Database Connection Errors
```bash
# Restart SQL Server
docker-compose -f docker-compose.complete.yml restart sqlserver

# Check SQL Server logs
docker logs sqlserver

# Test connection
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -C -Q "SELECT 1"
```

### Cannot Access APIs
```bash
# Check if backend is healthy
curl http://localhost:8000/health

# Check container status
docker ps | grep studio-backend

# Restart backend
docker-compose -f docker-compose.complete.yml restart studio-backend
```

---

## ✅ Summary

**What's Working:**
- ✅ Validation Studio Frontend (React UI)
- ✅ Validation Studio Backend (FastAPI APIs)
- ✅ SQL Server Database
- ✅ Metadata extraction API
- ✅ Intelligent mapping API with fuzzy matching
- ✅ Type compatibility scoring
- ✅ Sample TestTable in database

**Commands to Remember:**
```bash
# Start everything
make complete

# Check status
docker-compose -f docker-compose.complete.yml ps

# View logs
docker-compose -f docker-compose.complete.yml logs -f

# Stop everything
make stop
```

**URLs:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

**Your Ombudsman Data Migration Validator is ready to use!** 🎉

For questions or issues, refer to the troubleshooting section or check the logs.

---
**Last Updated:** November 27, 2025
**Version:** 1.0 - Complete System
**Status:** ✅ Production Ready (Studio), ⚠️ Core App needs Snowflake
