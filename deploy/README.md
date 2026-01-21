# Ombudsman Validation Studio - Linux Deployment Guide

This guide covers deploying Ombudsman Validation Studio on Ubuntu 24.04 LTS with Nginx, SSL, and Ollama.

## Architecture

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    Ubuntu 24.04                      │
                    │                                                     │
┌─────────┐        │  ┌─────────┐     ┌─────────────────┐               │
│ Browser │───────▶│  │  Nginx  │────▶│ Frontend (3000) │               │
│         │  HTTPS │  │ :80/443 │     │   React/serve   │               │
└─────────┘        │  │         │     └─────────────────┘               │
                    │  │         │                                       │
                    │  │         │     ┌─────────────────┐               │
                    │  │  /api/* │────▶│ Backend (8000)  │               │
                    │  │         │     │ FastAPI/uvicorn │               │
                    │  └─────────┘     │                 │               │
                    │                  │     ▼           │               │
                    │                  │  ┌──────────┐   │               │
                    │                  │  │ Ollama   │   │               │
                    │                  │  │ :11434   │   │               │
                    │                  │  └──────────┘   │               │
                    │                  └─────────────────┘               │
                    └─────────────────────────────────────────────────────┘
```

## Prerequisites

- Ubuntu 24.04 LTS server
- Domain name pointing to your server's IP
- Root or sudo access
- Open ports: 80 (HTTP), 443 (HTTPS)

## Quick Start

### 1. Install Dependencies

```bash
# Clone or copy the repository to your server
cd /path/to/data-migration-validator

# Run the dependency installation script
sudo ./deploy/install-dependencies.sh
```

This installs:
- Python 3.11
- Node.js 20.x
- Microsoft ODBC Driver 18 for SQL Server
- Nginx
- Certbot (Let's Encrypt)
- Ollama (for AI-powered schema mapping)

### 2. Deploy the Application

```bash
sudo ./deploy/deploy.sh your-domain.com your-email@example.com
```

This will:
1. Copy application code to `/opt/ombudsman/`
2. Set up Python virtual environment
3. Build the React frontend
4. Create data directories
5. Install systemd services
6. Configure Nginx with SSL
7. Obtain Let's Encrypt certificate
8. Start all services

### 3. Configure Environment

Edit the environment file with your database credentials:

```bash
sudo nano /opt/ombudsman/.env
```

Key settings to configure:
- `MSSQL_HOST`, `MSSQL_USER`, `MSSQL_PASSWORD` - SQL Server connection
- `SNOWFLAKE_*` - Snowflake connection settings
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`

After editing, restart the backend:

```bash
sudo systemctl restart ombudsman-backend
```

## File Locations

| Purpose | Path |
|---------|------|
| Application code | `/opt/ombudsman/` |
| Backend | `/opt/ombudsman/backend/` |
| Frontend | `/opt/ombudsman/frontend/` |
| Core library | `/opt/ombudsman/core/` |
| Configuration | `/opt/ombudsman/.env` |
| Data storage | `/var/lib/ombudsman/data/` |
| Logs | `/var/log/ombudsman/` |
| Nginx config | `/etc/nginx/sites-available/ombudsman` |

## Service Management

### View Service Status

```bash
# All services
sudo systemctl status ombudsman-backend ombudsman-frontend ollama nginx

# Individual service
sudo systemctl status ombudsman-backend
```

### View Logs

```bash
# Backend logs (journald)
sudo journalctl -u ombudsman-backend -f

# Frontend logs
sudo journalctl -u ombudsman-frontend -f

# Application logs
sudo tail -f /var/log/ombudsman/backend.log
sudo tail -f /var/log/ombudsman/backend-error.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart backend
sudo systemctl restart ombudsman-backend

# Restart frontend
sudo systemctl restart ombudsman-frontend

# Restart all
sudo systemctl restart ombudsman-backend ombudsman-frontend nginx
```

## Ollama Management

```bash
# Check Ollama status
sudo systemctl status ollama

# Pull a different model
ollama pull mistral

# List available models
ollama list

# Change model in .env
# Edit /opt/ombudsman/.env and set OLLAMA_MODEL=mistral
```

## SSL Certificate Renewal

Certificates auto-renew via cron. To manually renew:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

## Updating the Application

```bash
# Stop services
sudo systemctl stop ombudsman-backend ombudsman-frontend

# Pull latest code
cd /path/to/data-migration-validator
git pull

# Re-run deployment (preserves data and config)
sudo ./deploy/deploy.sh your-domain.com

# Or manually update:
# Backend
sudo cp -r ombudsman-validation-studio/backend/* /opt/ombudsman/backend/
sudo -u ombudsman /opt/ombudsman/backend/venv/bin/pip install -r /opt/ombudsman/backend/requirements.txt

# Frontend
cd ombudsman-validation-studio/frontend
npm ci && npm run build
sudo cp -r dist/* /opt/ombudsman/frontend/dist/

# Restart
sudo systemctl start ombudsman-backend ombudsman-frontend
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
sudo journalctl -u ombudsman-backend -n 50

# Test manually
sudo -u ombudsman /opt/ombudsman/backend/venv/bin/python -c "import main"

# Check Python path
sudo -u ombudsman bash -c 'source /opt/ombudsman/backend/venv/bin/activate && python -c "import sys; print(sys.path)"'
```

### Database connection issues

```bash
# Test SQL Server connection
/opt/mssql-tools18/bin/sqlcmd -S your-host -U your-user -P your-password -Q "SELECT 1"

# Check ODBC drivers
odbcinst -q -d
```

### Nginx 502 Bad Gateway

```bash
# Check if backend is running
sudo systemctl status ombudsman-backend

# Check if backend is listening
sudo ss -tlnp | grep 8000

# Test backend directly
curl http://127.0.0.1:8000/health
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Check Nginx SSL config
sudo nginx -t
```

## Security Recommendations

1. **Firewall**: Only allow ports 80, 443, and SSH
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Database**: Use strong passwords and restrict network access

3. **Secrets**: Generate strong SECRET_KEY
   ```bash
   openssl rand -hex 32
   ```

4. **Updates**: Keep system updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Backup

### Backup Data

```bash
# Create backup
sudo tar -czvf ombudsman-backup-$(date +%Y%m%d).tar.gz \
    /var/lib/ombudsman/data \
    /opt/ombudsman/.env
```

### Restore Data

```bash
# Stop services
sudo systemctl stop ombudsman-backend ombudsman-frontend

# Restore
sudo tar -xzvf ombudsman-backup-YYYYMMDD.tar.gz -C /

# Start services
sudo systemctl start ombudsman-backend ombudsman-frontend
```
