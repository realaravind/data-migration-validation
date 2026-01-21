# Ombudsman Validation Studio - VM Deployment

This directory contains everything you need to deploy Ombudsman Validation Studio on virtual machines using Docker.

## Quick Start

### Ubuntu VM
```bash
cd deployment/ubuntu
sudo ./install.sh
```

### Windows Server VM
```powershell
cd deployment\windows
.\install.ps1
```

## What's Included

```
deployment/
├── README.md                    # This file
├── DEPLOYMENT_GUIDE.md         # Comprehensive deployment guide
├── TROUBLESHOOTING.md          # Common issues and solutions
├── ubuntu/
│   └── install.sh              # Ubuntu automated installer
└── windows/
    └── install.ps1             # Windows automated installer
```

## Documentation

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete step-by-step installation instructions for both Ubuntu and Windows Server
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Solutions to common problems

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4 GB (Ubuntu) / 8 GB (Windows)
- **Disk**: 20 GB (Ubuntu) / 40 GB (Windows)
- **Network**: 1 Gbps

### Recommended for Production
- **CPU**: 4+ cores
- **RAM**: 8+ GB (Ubuntu) / 16+ GB (Windows)
- **Disk**: 50+ GB (Ubuntu) / 100+ GB (Windows)
- **Network**: 1 Gbps

## Installation Overview

Both installation scripts will:

1. ✅ Install Docker and Docker Compose
2. ✅ Set up application directory
3. ✅ Create configuration file (.env)
4. ✅ Configure auto-start on boot
5. ✅ Provide next steps and access information

## After Installation

### 1. Configure Database Connection

Edit the `.env` file:

**Ubuntu:**
```bash
sudo nano /opt/ombudsman-validation-studio/.env
```

**Windows:**
```powershell
notepad C:\OmbudsmanStudio\.env
```

Update these critical settings:
```bash
SQL_SERVER_HOST=your-sqlserver-ip
SQL_SERVER_PASSWORD=your-password
OVS_DB_HOST=your-sqlserver-ip
OVS_DB_PASSWORD=your-password
JWT_SECRET_KEY=<generate-random-32-char-string>
```

### 2. Start the Application

**Ubuntu:**
```bash
cd /opt/ombudsman-validation-studio
docker compose up -d
```

**Windows:**
```powershell
cd C:\OmbudsmanStudio
docker compose up -d
```

### 3. Access the Application

- **Frontend**: http://your-vm-ip:3000
- **Backend API**: http://your-vm-ip:8000
- **API Docs**: http://your-vm-ip:8000/docs

### 4. Create First User

1. Open the frontend in your browser
2. Click "Register" or "Create Account"
3. Fill in your details
4. Login with your credentials

## Managing the Application

### View Logs
```bash
docker compose logs -f
```

### Stop Application
```bash
docker compose down
```

### Restart Application
```bash
docker compose restart
```

### Update Application
```bash
docker compose down
git pull origin main
docker compose build
docker compose up -d
```

## Auto-Start Configuration

### Ubuntu (Systemd)
```bash
# Start on boot (already enabled by installer)
sudo systemctl enable ombudsman-studio

# Manual control
sudo systemctl start ombudsman-studio
sudo systemctl stop ombudsman-studio
sudo systemctl status ombudsman-studio
```

### Windows (Task Scheduler)
```powershell
# Already configured by installer

# Manual control
Start-ScheduledTask -TaskName "OmbudsmanValidationStudio"
Get-ScheduledTask -TaskName "OmbudsmanValidationStudio"
```

## Firewall Configuration

### Ubuntu
```bash
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
sudo ufw enable
```

### Windows
```powershell
# Already configured by installer

# Manual configuration
New-NetFirewallRule -DisplayName "Ombudsman Frontend" `
    -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "Ombudsman Backend" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

## Common Issues

### Docker not starting
- **Ubuntu**: `sudo systemctl start docker`
- **Windows**: Start Docker Desktop from Start Menu

### Port already in use
- **Ubuntu**: `sudo kill -9 $(sudo lsof -t -i:3000)`
- **Windows**: `netstat -ano | findstr :3000` then `taskkill /PID <PID> /F`

### Cannot connect to database
- Check `.env` file for correct credentials
- Verify SQL Server allows remote connections
- Check firewall allows port 1433

### More help
See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions.

## Security Best Practices

1. ✅ **Change default credentials** in `.env`
2. ✅ **Use strong JWT secret** (32+ random characters)
3. ✅ **Configure firewall** to restrict access
4. ✅ **Enable HTTPS** for production (see SSL guide)
5. ✅ **Regular backups** of `.env` and database
6. ✅ **Keep Docker updated**

## Backup and Restore

### Backup Configuration
**Ubuntu:**
```bash
sudo tar -czf ~/ombudsman-backup-$(date +%Y%m%d).tar.gz /opt/ombudsman-validation-studio
```

**Windows:**
```powershell
Compress-Archive -Path C:\OmbudsmanStudio\* -DestinationPath "C:\Backups\ombudsman-$(Get-Date -Format 'yyyyMMdd').zip"
```

### Backup Database
```sql
BACKUP DATABASE ovs_studio TO DISK = 'C:\Backups\ovs_studio.bak';
```

## Support

- 📖 **Documentation**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- 🔧 **Troubleshooting**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- 🐛 **Issues**: <your-github-repo>/issues
- 📧 **Email**: support@ombudsman.ai

## Architecture

```
┌─────────────────────────────────────────┐
│         Virtual Machine (VM)            │
│  ┌───────────────────────────────────┐  │
│  │         Docker Engine             │  │
│  │  ┌─────────────┐  ┌─────────────┐ │  │
│  │  │  Frontend   │  │   Backend   │ │  │
│  │  │  (React)    │  │  (FastAPI)  │ │  │
│  │  │  Port 3000  │  │  Port 8000  │ │  │
│  │  └─────────────┘  └─────────────┘ │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
               │         │
        ┌──────┴─────────┴──────┐
        │  External Databases   │
        │  - SQL Server         │
        │  - Snowflake          │
        └───────────────────────┘
```

## What's Next?

1. ✅ Complete installation
2. ✅ Configure database connection
3. ✅ Start application
4. ✅ Create first user
5. 📄 Review [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
6. 🔒 Set up SSL/HTTPS (recommended for production)
7. 📊 Configure monitoring (optional)
8. 🔄 Set up automated backups

## License

Copyright © 2025 Ombudsman.AI. All rights reserved.
