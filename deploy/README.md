# Ombudsman Validation Studio - Deployment Guide

## Quick Start

### 1. Clone/Copy to your desired location
```bash
# Example: Install to /opt/ombudsman
cd /opt
git clone <repository-url> ombudsman
cd ombudsman/deploy
```

### 2. Install (one command does everything)
```bash
sudo ./install-ombudsman.sh
```
The script auto-detects the installation directory from where it's run.

### 3. Configure
```bash
# Edit config file in the installation directory
nano ../ombudsman.env
```

### 4. Start
```bash
sudo systemctl start ombudsman-backend ombudsman-frontend
```

### 5. Access
- Frontend: http://your-server:3000
- Backend API: http://your-server:8000
- Default login: `admin` / `admin123`

---

## Custom Installation Path

The installation path is **automatically detected** from where you run the scripts. No hardcoded paths.

### Examples
```bash
# Install to /opt/ombudsman
cd /opt/ombudsman/deploy
sudo ./install-ombudsman.sh

# Install to /home/user/apps/ombudsman
cd /home/user/apps/ombudsman/deploy
sudo ./install-ombudsman.sh

# Install to /data/ombudsman (traditional path)
cd /data/ombudsman/deploy
sudo ./install-ombudsman.sh
```

### Override with Environment Variable
```bash
# Force a specific base directory
OMBUDSMAN_BASE_DIR=/custom/path sudo ./install-ombudsman.sh
OMBUDSMAN_BASE_DIR=/custom/path ./start-ombudsman.sh start
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OMBUDSMAN_BASE_DIR` | Base installation directory | Auto-detected from script location |
| `OMBUDSMAN_ENV_FILE` | Path to config file | `$BASE_DIR/ombudsman.env` |
| `OMBUDSMAN_DATA_DIR` | Path to data directory | `$BASE_DIR/data` |
| `OMBUDSMAN_LOG_DIR` | Path to log directory | `$BASE_DIR/logs` |

---

## What the Install Script Does

The install script automatically handles everything in one run:

| Step | Action |
|------|--------|
| 1 | Install system dependencies (python3, pip, venv, curl, git, build-essential) |
| 2 | Auto-detect Python command (python3 or python, verifies 3.8+) |
| 3 | Install Node.js v20 |
| 4 | Install ODBC Driver 18 for SQL Server |
| 5 | Install SOPS and age (for secrets encryption) |
| 6 | Create directory structure (`$BASE_DIR/data`, `logs`, etc.) |
| 7 | Create Python virtual environment |
| 8 | Install Python dependencies from requirements.txt |
| 9 | Install frontend npm dependencies |
| 10 | Build frontend for production |
| 11 | Copy configuration template to `$BASE_DIR/ombudsman.env` |
| 12 | Setup authentication database (if SQL Server auth configured) |
| 13 | Install systemd service files |
| 14 | Enable auto-start on boot |

After installation completes, you only need to:
1. Edit the config file with your database credentials
2. Start the services with `systemctl`

Services will automatically restart on system reboot.

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
tail -f $BASE_DIR/logs/backend.log
tail -f $BASE_DIR/logs/frontend.log
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

All configuration is in `$BASE_DIR/ombudsman.env`:

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

## Secrets Encryption (SOPS)

The config file contains sensitive credentials. Use SOPS encryption to secure them.

### Initial Setup (New Installations)
```bash
cd $BASE_DIR/deploy

# 1. Initialize encryption (generates age key)
./start-ombudsman.sh init-secrets

# 2. Edit your config with credentials
nano $BASE_DIR/ombudsman.env

# 3. Encrypt the config file
./start-ombudsman.sh encrypt-secrets

# 4. (Optional) Delete plaintext file
rm $BASE_DIR/ombudsman.env
```

### Encrypting Existing Deployments
```bash
cd $BASE_DIR/deploy

# 1. Update to get SOPS support
sudo ./start-ombudsman.sh update

# 2. Install SOPS and age (if not installed by update)
#    On Ubuntu 22.04+:
sudo apt-get install -y age
#    For SOPS, download from GitHub:
curl -LO https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

# 3. Initialize encryption key
./start-ombudsman.sh init-secrets

# 4. Encrypt your existing config
./start-ombudsman.sh encrypt-secrets

# 5. Verify services still work
sudo systemctl restart ombudsman-backend ombudsman-frontend
sudo systemctl status ombudsman-backend

# 6. Once verified, delete plaintext file
rm $BASE_DIR/ombudsman.env

# 7. IMPORTANT - Backup your key!
cp $BASE_DIR/.sops-age-key.txt ~/sops-key-backup.txt
```

### How It Works
- Uses [SOPS](https://github.com/getsops/sops) with [age](https://github.com/FiloSottile/age) encryption
- Encrypted file: `$BASE_DIR/ombudsman.env.enc`
- Encryption key: `$BASE_DIR/.sops-age-key.txt`
- Services automatically decrypt at startup

### Managing Secrets
```bash
# Edit encrypted config (auto decrypt/re-encrypt)
./start-ombudsman.sh edit-secrets

# Decrypt to plaintext (for backup/migration)
./start-ombudsman.sh decrypt-secrets

# Re-encrypt after changes
./start-ombudsman.sh encrypt-secrets
```

### Key Backup
**IMPORTANT:** Back up your encryption key securely!
```bash
# The key file location
$BASE_DIR/.sops-age-key.txt

# Copy to secure location
cp $BASE_DIR/.sops-age-key.txt /secure/backup/location/
```

Without this key, you cannot decrypt your secrets.

---

## Directory Structure

```
$BASE_DIR/                     # e.g., /opt/ombudsman, /data/ombudsman, etc.
├── ombudsman.env              # Configuration file (plaintext)
├── ombudsman.env.enc          # Configuration file (encrypted, if using SOPS)
├── .sops-age-key.txt          # Encryption key (keep secure!)
├── .sops.yaml                 # SOPS configuration
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
cd $BASE_DIR/ombudsman-validation-studio/backend
./venv/bin/python -c "
import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-host,1433;DATABASE=your-db;UID=user;PWD=pass;TrustServerCertificate=yes;')
print('Connected!')
"
```

### Reset authentication database
```bash
cd $BASE_DIR/deploy
./start-ombudsman.sh setup-auth
```

### Rebuild frontend (after changing VITE_API_URL)
```bash
cd $BASE_DIR/deploy
./start-ombudsman.sh rebuild-frontend
sudo systemctl restart ombudsman-frontend
```

---

## Manual Start (without systemd)

If you prefer not to use systemd:
```bash
cd $BASE_DIR/deploy
./start-ombudsman.sh start    # Start services
./start-ombudsman.sh stop     # Stop services
./start-ombudsman.sh status   # Check status
./start-ombudsman.sh logs     # View logs
```

---

## Updating

### One-command update (recommended)
```bash
cd $BASE_DIR/deploy
sudo ./start-ombudsman.sh update
```

This automatically:
1. Stops services
2. Pulls latest code from git
3. Updates Python dependencies
4. Updates npm dependencies
5. Fixes any security vulnerabilities
6. Rebuilds frontend
7. Restarts services

### Manual update
```bash
cd $BASE_DIR
git pull

cd ombudsman-validation-studio/backend
./venv/bin/pip install -r requirements.txt

cd ../frontend
npm install
npm audit fix
npm run build

sudo systemctl restart ombudsman-backend ombudsman-frontend
```
