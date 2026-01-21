# Ombudsman Validation Studio - VM Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Ubuntu VM Deployment](#ubuntu-vm-deployment)
4. [Windows Server VM Deployment](#windows-server-vm-deployment)
5. [Post-Installation Configuration](#post-installation-configuration)
6. [Managing the Application](#managing-the-application)
7. [Backup and Restore](#backup-and-restore)
8. [Security Best Practices](#security-best-practices)

---

## Overview

This guide covers deploying Ombudsman Validation Studio on virtual machines using Docker. This deployment model provides:

- **Easy Installation**: Automated scripts for both Ubuntu and Windows Server
- **Consistent Environment**: Docker ensures consistency across platforms
- **Auto-Start**: Application starts automatically when VM boots
- **Simple Updates**: Update containers without reinstalling
- **Portability**: Easy to migrate between VMs

### Architecture

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
│              ▲         ▲                │
│              │         │                │
└──────────────┼─────────┼────────────────┘
               │         │
        ┌──────┴─────────┴──────┐
        │  External Databases   │
        │  - SQL Server         │
        │  - Snowflake          │
        └───────────────────────┘
```

---

## System Requirements

### Ubuntu VM Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 20.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk Space | 20 GB | 50+ GB |
| Network | 1 Gbps | 1 Gbps |

### Windows Server VM Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows Server 2019 | Windows Server 2022 |
| CPU | 2 cores | 4+ cores |
| RAM | 8 GB | 16+ GB |
| Disk Space | 40 GB | 100+ GB |
| Network | 1 Gbps | 1 Gbps |

### Network Requirements

**Required Outbound Ports:**
- Port 443 (HTTPS) - For downloading Docker and dependencies
- SQL Server port (usually 1433) - For database connections
- Snowflake port (443) - For Snowflake connections

**Required Inbound Ports:**
- Port 3000 - Frontend web interface
- Port 8000 - Backend API

---

## Ubuntu VM Deployment

### Quick Start

1. **Download the installer:**
```bash
cd ~
git clone <your-repo-url> ombudsman-validation-studio
# Or download and extract the deployment package
```

2. **Run the installation script:**
```bash
cd ombudsman-validation-studio/deployment/ubuntu
sudo ./install.sh
```

3. **Edit configuration:**
```bash
sudo nano /opt/ombudsman-validation-studio/.env
```

4. **Start the application:**
```bash
cd /opt/ombudsman-validation-studio
docker compose up -d
```

### Detailed Installation Steps

#### Step 1: Prepare the VM

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install curl if not present
sudo apt-get install curl -y
```

#### Step 2: Transfer Application Files

**Option A: Using Git**
```bash
cd ~
git clone <your-repo-url> ombudsman-validation-studio
```

**Option B: Using SCP**
```bash
# From your local machine
scp -r ./ombudsman-validation-studio user@vm-ip:~/
```

**Option C: Using SFTP**
```bash
sftp user@vm-ip
put -r ./ombudsman-validation-studio
```

#### Step 3: Run Installation Script

```bash
cd ~/ombudsman-validation-studio/deployment/ubuntu
chmod +x install.sh
sudo ./install.sh
```

The script will:
1. Update system packages
2. Install prerequisites (curl, git, etc.)
3. Install Docker Engine
4. Install Docker Compose
5. Set up application directory at `/opt/ombudsman-validation-studio`
6. Create .env configuration file
7. Create systemd service for auto-start

#### Step 4: Configure Database Connections

Edit the `.env` file:
```bash
sudo nano /opt/ombudsman-validation-studio/.env
```

Update the following values:
```bash
# SQL Server Configuration
SQL_SERVER_HOST=your-sqlserver-hostname-or-ip
SQL_SERVER_PORT=1433
SQL_SERVER_USER=your-username
SQL_SERVER_PASSWORD=your-password
SQL_SERVER_DATABASE=SampleDW

# OVS Studio Database
OVS_DB_HOST=your-sqlserver-hostname-or-ip
OVS_DB_NAME=ovs_studio
OVS_DB_USER=your-username
OVS_DB_PASSWORD=your-password

# JWT Secret (generate a random string)
JWT_SECRET_KEY=<generate-a-random-32-character-string>
```

#### Step 5: Start the Application

**Option A: Using Docker Compose**
```bash
cd /opt/ombudsman-validation-studio
docker compose up -d
```

**Option B: Using Systemd Service**
```bash
sudo systemctl start ombudsman-studio
```

#### Step 6: Verify Installation

```bash
# Check container status
docker compose ps

# View logs
docker compose logs -f

# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000
```

### Ubuntu Auto-Start Configuration

The installation script creates a systemd service that automatically starts the application on boot.

**Service Commands:**
```bash
# Start application
sudo systemctl start ombudsman-studio

# Stop application
sudo systemctl stop ombudsman-studio

# Restart application
sudo systemctl restart ombudsman-studio

# Check status
sudo systemctl status ombudsman-studio

# Enable auto-start (already enabled by installer)
sudo systemctl enable ombudsman-studio

# Disable auto-start
sudo systemctl disable ombudsman-studio
```

---

## Windows Server VM Deployment

### Quick Start

1. **Download the deployment package** to the Windows Server

2. **Open PowerShell as Administrator**

3. **Navigate to deployment folder:**
```powershell
cd C:\path\to\ombudsman-validation-studio\deployment\windows
```

4. **Run the installation script:**
```powershell
.\install.ps1
```

5. **Edit configuration:**
```powershell
notepad C:\OmbudsmanStudio\.env
```

6. **Start the application:**
```powershell
cd C:\OmbudsmanStudio
docker compose up -d
```

### Detailed Installation Steps

#### Step 1: Prepare Windows Server

1. **Enable Windows Features:**
   - Open Server Manager
   - Add Roles and Features
   - Enable Hyper-V (if using Docker Desktop)
   - Or enable Windows Subsystem for Linux (WSL 2)

2. **Set Execution Policy:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Step 2: Transfer Application Files

**Option A: Using Git**
```powershell
# Install Git if not present (done by script)
cd C:\
git clone <your-repo-url> ombudsman-validation-studio
```

**Option B: Using RDP**
- Copy files via Remote Desktop clipboard
- Or use mapped drives

**Option C: Using Network Share**
```powershell
# Map network drive
net use Z: \\server\share

# Copy files
Copy-Item Z:\ombudsman-validation-studio C:\ -Recurse
```

#### Step 3: Run Installation Script

1. **Right-click PowerShell** and select **"Run as Administrator"**

2. **Navigate to deployment folder:**
```powershell
cd C:\ombudsman-validation-studio\deployment\windows
```

3. **Run the installer:**
```powershell
.\install.ps1
```

The script will:
1. Install Chocolatey package manager
2. Install Docker Desktop
3. Install Git
4. Create application directory at `C:\OmbudsmanStudio`
5. Copy application files
6. Create `.env` configuration file
7. Create Windows Task Scheduler job for auto-start

**Note:** The script may require a restart after installing Docker Desktop. After restart, run the script again.

#### Step 4: Configure Database Connections

Edit the `.env` file:
```powershell
notepad C:\OmbudsmanStudio\.env
```

Update the same values as shown in the Ubuntu section.

#### Step 5: Start Docker Desktop

1. Open Docker Desktop from Start Menu
2. Wait for Docker to start (icon turns green in system tray)
3. Accept license agreement if prompted

#### Step 6: Start the Application

```powershell
cd C:\OmbudsmanStudio
docker compose up -d
```

#### Step 7: Verify Installation

```powershell
# Check container status
docker compose ps

# View logs
docker compose logs -f

# Test backend
Invoke-WebRequest -Uri http://localhost:8000/health

# Open frontend in browser
Start-Process http://localhost:3000
```

### Windows Auto-Start Configuration

The installation script creates a Windows Task Scheduler job that automatically starts the application on boot.

**Task Scheduler Commands:**
```powershell
# Start the scheduled task manually
Start-ScheduledTask -TaskName "OmbudsmanValidationStudio"

# View task status
Get-ScheduledTask -TaskName "OmbudsmanValidationStudio"

# Disable auto-start
Disable-ScheduledTask -TaskName "OmbudsmanValidationStudio"

# Enable auto-start
Enable-ScheduledTask -TaskName "OmbudsmanValidationStudio"
```

---

## Post-Installation Configuration

### 1. Create OVS Studio Database

The application requires a database for user authentication and project management.

**On SQL Server:**
```sql
CREATE DATABASE ovs_studio;
GO

USE ovs_studio;
GO

-- The application will create tables automatically on first run
```

### 2. Configure Firewall

**Ubuntu:**
```bash
# Allow frontend port
sudo ufw allow 3000/tcp

# Allow backend port
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
```

**Windows Server:**
```powershell
# Allow frontend port
New-NetFirewallRule -DisplayName "Ombudsman Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# Allow backend port
New-NetFirewallRule -DisplayName "Ombudsman Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 3. Configure SSL/HTTPS (Optional but Recommended)

See the [SSL_CONFIGURATION.md](./SSL_CONFIGURATION.md) guide for detailed instructions.

### 4. Create First User

Access the application at `http://vm-ip:3000` and register the first user.

---

## Managing the Application

### Starting the Application

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

### Stopping the Application

**Ubuntu:**
```bash
cd /opt/ombudsman-validation-studio
docker compose down
```

**Windows:**
```powershell
cd C:\OmbudsmanStudio
docker compose down
```

### Viewing Logs

**Ubuntu:**
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f studio-backend

# Frontend only
docker compose logs -f studio-frontend
```

**Windows:**
```powershell
# All services
docker compose logs -f

# Backend only
docker compose logs -f studio-backend

# Frontend only
docker compose logs -f studio-frontend
```

### Restarting Services

**Ubuntu:**
```bash
# Restart all
docker compose restart

# Restart backend only
docker compose restart studio-backend

# Restart frontend only
docker compose restart studio-frontend
```

**Windows:**
```powershell
# Same commands as Ubuntu
docker compose restart
```

### Updating the Application

1. **Stop the application:**
```bash
docker compose down
```

2. **Pull latest changes:**
```bash
git pull origin main
```

3. **Rebuild containers:**
```bash
docker compose build
```

4. **Start updated application:**
```bash
docker compose up -d
```

---

## Backup and Restore

### Backing Up Configuration

**Ubuntu:**
```bash
# Backup .env file
sudo cp /opt/ombudsman-validation-studio/.env ~/ombudsman-backup-.env-$(date +%Y%m%d)

# Backup entire directory
sudo tar -czf ~/ombudsman-backup-$(date +%Y%m%d).tar.gz /opt/ombudsman-validation-studio
```

**Windows:**
```powershell
# Backup .env file
Copy-Item C:\OmbudsmanStudio\.env "C:\Backups\ombudsman-.env-$(Get-Date -Format 'yyyyMMdd')"

# Backup entire directory
Compress-Archive -Path C:\OmbudsmanStudio\* -DestinationPath "C:\Backups\ombudsman-$(Get-Date -Format 'yyyyMMdd').zip"
```

### Backing Up Database

```sql
-- On SQL Server
BACKUP DATABASE ovs_studio
TO DISK = 'C:\Backups\ovs_studio.bak'
WITH INIT;
```

### Restoring

1. **Stop the application**
2. **Restore .env file**
3. **Restore application files**
4. **Restore database**
5. **Start the application**

---

## Security Best Practices

### 1. Change Default Credentials

- Update `JWT_SECRET_KEY` in `.env` with a strong random string
- Use strong database passwords
- Change default application admin password after first login

### 2. Network Security

- Use firewall to restrict access to ports 3000 and 8000
- Consider using a VPN for remote access
- Implement SSL/TLS for HTTPS

### 3. Regular Updates

```bash
# Update Docker
# Ubuntu
sudo apt-get update && sudo apt-get upgrade docker-ce docker-ce-cli

# Update application
git pull origin main
docker compose build
docker compose up -d
```

### 4. Monitor Logs

```bash
# Check for errors
docker compose logs --tail=100 | grep -i error

# Monitor in real-time
docker compose logs -f
```

### 5. Backup Regularly

- Schedule automatic backups of `.env` file
- Schedule automatic database backups
- Store backups offsite

---

## Next Steps

1. Review the [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) guide
2. Configure [SSL/HTTPS](./SSL_CONFIGURATION.md) for production use
3. Set up [monitoring and alerting](./MONITORING.md)
4. Review [performance tuning](./PERFORMANCE_TUNING.md) options

---

## Support

For issues or questions:
- Check the [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) guide
- View logs: `docker compose logs -f`
- GitHub Issues: <your-repo-url>/issues
- Email: support@ombudsman.ai
