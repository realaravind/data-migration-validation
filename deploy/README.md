# Ombudsman Validation Studio - Deployment Guide

## Quick Start

### 1. Install
```bash
sudo ./install-ombudsman.sh
```

### 2. Configure
```bash
nano /data/ombudsman/ombudsman.env
```

### 3. Start
```bash
sudo systemctl start ombudsman-backend ombudsman-frontend
```

### 4. Access
- Frontend: http://your-server:3000
- Backend API: http://your-server:8000
- Default login: `admin` / `admin123`

---

## Service Management

### Start/Stop/Restart
```bash
# Start both services
sudo systemctl start ombudsman-backend ombudsman-frontend

# Stop both services
sudo systemctl stop ombudsman-backend ombudsman-frontend

# Restart both services
sudo systemctl restart ombudsman-backend ombudsman-frontend

# Restart individual service
sudo systemctl restart ombudsman-backend
```

### Check Status
```bash
sudo systemctl status ombudsman-backend
sudo systemctl status ombudsman-frontend
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u ombudsman-backend -f
sudo journalctl -u ombudsman-frontend -f

# Or check log files directly
tail -f /data/ombudsman/logs/backend.log
tail -f /data/ombudsman/logs/frontend.log
```

### Enable/Disable Auto-Start
```bash
# Enable auto-start on boot (default after install)
sudo systemctl enable ombudsman-backend ombudsman-frontend

# Disable auto-start on boot
sudo systemctl disable ombudsman-backend ombudsman-frontend
```

---

## Configuration

All configuration is in `/data/ombudsman/ombudsman.env`:

### Database Connections
```bash
# SQL Server (source)
MSSQL_HOST=your-sql-server-host
MSSQL_PORT=1433
MSSQL_USER=your-username
MSSQL_PASSWORD=your-password
MSSQL_DATABASE=your-database

# Snowflake (target)
SNOWFLAKE_USER=your-user
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your-database

# Authentication: password OR token
SNOWFLAKE_PASSWORD=your-password
# SNOWFLAKE_TOKEN=your-pat-token  # Use instead of password
```

### LLM Provider (for AI schema mapping)
```bash
LLM_PROVIDER=ollama  # Options: ollama, openai, azure_openai, anthropic

# Ollama (default - local, no API key needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# OpenAI
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# Azure OpenAI
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

### Authentication Database
```bash
AUTH_BACKEND=sqlserver  # Options: sqlite, sqlserver

# SQL Server auth database
AUTH_DB_SERVER=your-sql-server-host
AUTH_DB_NAME=ovs_studio
AUTH_DB_USER=your-username
AUTH_DB_PASSWORD=your-password
```

---

## Directory Structure

```
/data/ombudsman/
├── ombudsman.env              # Main configuration file
├── deploy/                    # Deployment scripts
│   ├── install-ombudsman.sh   # Installation script
│   ├── start-ombudsman.sh     # Manual start/stop script
│   └── systemd/               # Systemd service files
├── ombudsman-validation-studio/
│   ├── backend/               # Python backend
│   │   └── venv/              # Python virtual environment
│   └── frontend/              # React frontend
├── ombudsman_core/            # Core library
├── data/                      # Application data
│   ├── projects/
│   ├── pipelines/
│   ├── results/
│   └── auth/
└── logs/                      # Log files
    ├── backend.log
    └── frontend.log
```

---

## Troubleshooting

### Services won't start
```bash
# Check for errors
sudo journalctl -u ombudsman-backend -n 50
sudo journalctl -u ombudsman-frontend -n 50

# Check if ports are in use
sudo lsof -i :8000
sudo lsof -i :3000
```

### Database connection issues
```bash
# Test SQL Server connection
cd /data/ombudsman/ombudsman-validation-studio/backend
./venv/bin/python -c "
import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-host,1433;DATABASE=your-db;UID=user;PWD=pass;TrustServerCertificate=yes;')
print('Connected!')
"
```

### Reset authentication database
```bash
cd /data/ombudsman/deploy
./start-ombudsman.sh setup-auth
```

### Rebuild frontend (after changing VITE_API_URL)
```bash
cd /data/ombudsman/deploy
./start-ombudsman.sh rebuild-frontend
sudo systemctl restart ombudsman-frontend
```

---

## Manual Start (without systemd)

If you prefer not to use systemd:
```bash
cd /data/ombudsman/deploy
./start-ombudsman.sh start    # Start services
./start-ombudsman.sh stop     # Stop services
./start-ombudsman.sh status   # Check status
./start-ombudsman.sh logs     # View logs
```

---

## Updating

```bash
cd /data/ombudsman
git pull

# Reinstall dependencies if needed
cd ombudsman-validation-studio/backend
./venv/bin/pip install -r requirements.txt

cd ../frontend
npm install
npm run build

# Restart services
sudo systemctl restart ombudsman-backend ombudsman-frontend
```
