# Ombudsman Validation Studio - Ubuntu Deployment

Complete deployment package for Ubuntu 20.04/22.04 LTS

## Quick Start

```bash
# 1. Copy deployment files to Ubuntu VM
scp -r deployment/ubuntu/ user@ubuntu-vm:~/

# 2. SSH into Ubuntu VM
ssh user@ubuntu-vm

# 3. Run pre-check (optional)
cd ~/ubuntu
sudo ./pre-check.sh

# 4. Run installation
sudo ./install.sh

# 5. Configure database
sudo nano /opt/ombudsman-validation-studio/.env

# 6. Start application
cd /opt/ombudsman-validation-studio
docker compose up -d

# 7. Verify installation
./verify.sh
```

## What's Included

```
ubuntu/
├── README.md           # This file
├── install.sh          # Main installation script
├── pre-check.sh        # Pre-installation system check
├── verify.sh           # Post-installation verification
├── uninstall.sh        # Uninstallation script
└── .env.example        # Configuration template
```

## System Requirements

### Minimum
- Ubuntu 20.04 LTS or 22.04 LTS
- 2 CPU cores
- 4 GB RAM
- 20 GB disk space
- Internet connection

### Recommended
- Ubuntu 22.04 LTS
- 4+ CPU cores
- 8+ GB RAM
- 50+ GB disk space
- 1 Gbps network

## Installation Steps

### Step 1: Pre-Installation Check

Run the pre-check script to verify system compatibility:

```bash
sudo ./pre-check.sh
```

This checks:
- Ubuntu version
- Available disk space
- Available memory
- Internet connectivity
- Required ports availability

### Step 2: Run Installation

```bash
sudo ./install.sh
```

The installer will:
1. Update system packages
2. Install Docker and Docker Compose
3. Set up application directory
4. Create configuration file
5. Configure auto-start service
6. Display access information

### Step 3: Configure Application

Edit the configuration file:

```bash
sudo nano /opt/ombudsman-validation-studio/.env
```

Update these critical settings:

```bash
# SQL Server - Replace with your values
SQL_SERVER_HOST=192.168.1.100
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=YourStrongPassword
SQL_SERVER_DATABASE=SampleDW

# OVS Studio Database
OVS_DB_HOST=192.168.1.100
OVS_DB_NAME=ovs_studio
OVS_DB_USER=sa
OVS_DB_PASSWORD=YourStrongPassword

# JWT Secret - Generate random string
JWT_SECRET_KEY=change-this-to-random-32-chars
```

**Generate a secure JWT secret:**
```bash
openssl rand -base64 32
```

### Step 4: Start Application

```bash
cd /opt/ombudsman-validation-studio
docker compose up -d
```

### Step 5: Verify Installation

```bash
./verify.sh
```

This checks:
- Docker is running
- Containers are healthy
- Frontend is accessible
- Backend is accessible
- Database connectivity

## Accessing the Application

After installation, access via:

- **Frontend**: http://your-ubuntu-ip:3000
- **Backend API**: http://your-ubuntu-ip:8000
- **API Documentation**: http://your-ubuntu-ip:8000/docs

## Managing the Application

### Using Docker Compose

```bash
# Start
cd /opt/ombudsman-validation-studio
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f studio-backend
docker compose logs -f studio-frontend
```

### Using Systemd Service

```bash
# Start
sudo systemctl start ombudsman-studio

# Stop
sudo systemctl stop ombudsman-studio

# Restart
sudo systemctl restart ombudsman-studio

# Status
sudo systemctl status ombudsman-studio

# View logs
sudo journalctl -u ombudsman-studio -f
```

## Firewall Configuration

Allow access to application ports:

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (if not already)
sudo ufw allow 22/tcp

# Allow application ports
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend

# Check status
sudo ufw status
```

## Updating the Application

```bash
# Stop application
cd /opt/ombudsman-validation-studio
docker compose down

# Backup current version
sudo cp -r /opt/ombudsman-validation-studio /opt/ombudsman-backup-$(date +%Y%m%d)

# Pull updates (if using git)
git pull origin main

# Rebuild containers
docker compose build --no-cache

# Start updated application
docker compose up -d

# Verify
docker compose ps
docker compose logs -f
```

## Backup and Restore

### Backup

```bash
# Backup entire application
sudo tar -czf ~/ombudsman-backup-$(date +%Y%m%d).tar.gz /opt/ombudsman-validation-studio

# Backup configuration only
sudo cp /opt/ombudsman-validation-studio/.env ~/ombudsman-env-backup-$(date +%Y%m%d)

# Backup database
# See database documentation for SQL Server backup
```

### Restore

```bash
# Stop application
sudo systemctl stop ombudsman-studio

# Restore from backup
sudo tar -xzf ~/ombudsman-backup-YYYYMMDD.tar.gz -C /

# Restore configuration
sudo cp ~/ombudsman-env-backup-YYYYMMDD /opt/ombudsman-validation-studio/.env

# Start application
sudo systemctl start ombudsman-studio
```

## Uninstalling

To completely remove the application:

```bash
./uninstall.sh
```

This will:
- Stop and remove containers
- Remove application directory
- Remove systemd service
- Optionally remove Docker

## Troubleshooting

### Check Docker Status

```bash
sudo systemctl status docker
docker --version
docker compose version
```

### Check Container Status

```bash
cd /opt/ombudsman-validation-studio
docker compose ps
docker compose logs
```

### Check Disk Space

```bash
df -h
docker system df
```

### Clean Up Docker Resources

```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove everything unused
docker system prune -a --volumes -f
```

### Common Issues

**Issue: Cannot connect to Docker daemon**
```bash
# Start Docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
```

**Issue: Port already in use**
```bash
# Find process using port
sudo lsof -i :3000

# Kill process
sudo kill -9 <PID>
```

**Issue: Out of disk space**
```bash
# Clean Docker resources
docker system prune -a --volumes -f

# Check space
df -h
```

## Monitoring

### View Resource Usage

```bash
# System resources
htop
# OR
top

# Docker stats
docker stats

# Disk usage
df -h
du -sh /opt/ombudsman-validation-studio
```

### View Logs

```bash
# Application logs
docker compose logs -f

# System logs
sudo journalctl -f

# Docker daemon logs
sudo journalctl -u docker -f
```

## Security Best Practices

1. **Firewall**: Only open required ports (3000, 8000)
2. **SSH**: Use key-based authentication, disable password login
3. **Updates**: Keep Ubuntu and Docker updated
4. **Passwords**: Use strong passwords in .env file
5. **JWT Secret**: Use cryptographically secure random string
6. **Backups**: Regular automated backups
7. **Monitoring**: Set up log monitoring
8. **SSL**: Configure HTTPS for production

## Performance Tuning

### Increase Docker Resources

Edit `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

### Optimize System

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install performance tools
sudo apt-get install -y htop iotop nethogs
```

## Support

- **Documentation**: See parent [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- **Troubleshooting**: See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Issues**: <your-repo-url>/issues

## Files and Locations

| Item | Location |
|------|----------|
| Application | `/opt/ombudsman-validation-studio` |
| Configuration | `/opt/ombudsman-validation-studio/.env` |
| Systemd Service | `/etc/systemd/system/ombudsman-studio.service` |
| Docker Compose | `/opt/ombudsman-validation-studio/docker-compose.yml` |
| Logs | `docker compose logs` or `journalctl -u ombudsman-studio` |

## Next Steps

1. ✅ Complete installation
2. ✅ Configure .env file
3. ✅ Start application
4. ✅ Verify installation
5. ✅ Configure firewall
6. ✅ Set up backups
7. ✅ Configure monitoring (optional)
8. ✅ Set up SSL/HTTPS (recommended for production)

---

**Installation successful?** Access your application at http://your-ubuntu-ip:3000
