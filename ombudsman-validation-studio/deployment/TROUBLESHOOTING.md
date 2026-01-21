# Ombudsman Validation Studio - Troubleshooting Guide

## Table of Contents
1. [Docker Issues](#docker-issues)
2. [Database Connection Issues](#database-connection-issues)
3. [Application Issues](#application-issues)
4. [Performance Issues](#performance-issues)
5. [Network Issues](#network-issues)
6. [Platform-Specific Issues](#platform-specific-issues)

---

## Docker Issues

### Issue: Docker command not found (Ubuntu)

**Symptoms:**
```
bash: docker: command not found
```

**Solution:**
```bash
# Verify Docker installation
which docker

# If not installed, reinstall
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, then test
docker --version
```

---

### Issue: Docker daemon not running (Ubuntu)

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
```bash
# Check Docker status
sudo systemctl status docker

# Start Docker
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Check if Docker is running
docker ps
```

---

### Issue: Docker Desktop not starting (Windows)

**Symptoms:**
- Docker Desktop icon shows error
- "Docker Desktop starting..." never completes
- WSL 2 errors

**Solutions:**

**Option 1: Enable WSL 2**
```powershell
# Run as Administrator
wsl --install
wsl --set-default-version 2

# Restart computer
Restart-Computer
```

**Option 2: Enable Hyper-V**
```powershell
# Run as Administrator
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Restart computer
Restart-Computer
```

**Option 3: Reset Docker Desktop**
1. Close Docker Desktop completely
2. Open Settings > Troubleshoot
3. Click "Reset to factory defaults"
4. Restart Docker Desktop

---

### Issue: Containers won't start

**Symptoms:**
```
Error response from daemon: driver failed programming external connectivity
```

**Solution:**
```bash
# Stop all containers
docker compose down

# Remove containers
docker compose rm -f

# Restart Docker
sudo systemctl restart docker  # Ubuntu
# OR restart Docker Desktop (Windows)

# Start containers again
docker compose up -d
```

---

### Issue: Port already in use

**Symptoms:**
```
Error starting userland proxy: listen tcp 0.0.0.0:3000: bind: address already in use
```

**Solution:**

**Ubuntu:**
```bash
# Find process using port 3000
sudo lsof -i :3000

# Kill the process
sudo kill -9 <PID>

# Or find and kill in one command
sudo kill -9 $(sudo lsof -t -i:3000)

# Start containers
docker compose up -d
```

**Windows:**
```powershell
# Find process using port 3000
netstat -ano | findstr :3000

# Kill the process
taskkill /PID <PID> /F

# Start containers
docker compose up -d
```

---

## Database Connection Issues

### Issue: Cannot connect to SQL Server

**Symptoms:**
```
[Microsoft][ODBC Driver 18 for SQL Server]Unable to open TCP socket
```

**Diagnostic Steps:**

**1. Check SQL Server is accessible:**

**Ubuntu:**
```bash
# Test connection
telnet sql-server-ip 1433

# If telnet not installed
sudo apt-get install telnet
```

**Windows:**
```powershell
# Test connection
Test-NetConnection -ComputerName sql-server-ip -Port 1433
```

**2. Verify credentials:**
```bash
# Check .env file
cat /opt/ombudsman-validation-studio/.env  # Ubuntu
type C:\OmbudsmanStudio\.env  # Windows
```

**3. Check SQL Server allows remote connections:**
```sql
-- On SQL Server
EXEC sp_configure 'remote access';
```

**4. Check firewall:**
```bash
# Ubuntu - check if port 1433 is open
sudo ufw status | grep 1433

# Windows - check firewall rule
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*SQL*"}
```

**Solutions:**

**Enable SQL Server remote connections:**
1. Open SQL Server Configuration Manager
2. SQL Server Network Configuration > Protocols
3. Enable TCP/IP
4. Restart SQL Server service

**Configure SQL Server firewall (Windows):**
```powershell
New-NetFirewallRule -DisplayName "SQL Server" `
    -Direction Inbound -LocalPort 1433 -Protocol TCP -Action Allow
```

**Update .env file:**
```bash
# Correct format
SQL_SERVER_HOST=192.168.1.100  # Use IP address, not hostname if DNS fails
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=YourPassword  # No special characters may need escaping
```

---

### Issue: SQL Server authentication failed

**Symptoms:**
```
Login failed for user 'sa'
```

**Solutions:**

**1. Enable SQL Server Authentication:**
```sql
-- On SQL Server, run as Administrator
USE master;
GO
EXEC xp_instance_regwrite
    N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'LoginMode', REG_DWORD, 2;
GO

-- Restart SQL Server service
```

**2. Reset SA password:**
```sql
ALTER LOGIN sa WITH PASSWORD = 'NewStrongPassword123!';
ALTER LOGIN sa ENABLE;
```

**3. Create new SQL login:**
```sql
CREATE LOGIN ombudsman_user WITH PASSWORD = 'StrongPassword123!';
CREATE USER ombudsman_user FOR LOGIN ombudsman_user;
GRANT CONNECT TO ombudsman_user;
-- Grant necessary database permissions
```

---

### Issue: Cannot connect to Snowflake

**Symptoms:**
```
250001: Could not connect to Snowflake backend
```

**Solutions:**

**1. Check Snowflake account identifier:**
```bash
# Format: <account_name>.<region>.<cloud>
# Example: xy12345.us-east-1.aws
SNOWFLAKE_ACCOUNT=xy12345.us-east-1.aws
```

**2. Verify network access:**
```bash
# Test Snowflake connectivity
curl https://<account>.snowflakecomputing.com

# Should return Snowflake's authentication page
```

**3. Check IP allowlist:**
- Log in to Snowflake web UI
- Account > Security > Network Policies
- Add VM's IP address to allowlist

---

## Application Issues

### Issue: Frontend shows blank page

**Symptoms:**
- Browser shows blank white page
- Console errors about failed to fetch

**Diagnostic Steps:**
```bash
# Check frontend container
docker compose logs studio-frontend

# Check if frontend is responding
curl http://localhost:3000

# Check browser console (F12)
```

**Solutions:**

**1. Clear browser cache:**
- Press Ctrl+Shift+Delete
- Clear cache and cookies
- Or try incognito/private mode

**2. Rebuild frontend:**
```bash
docker compose down
docker compose build studio-frontend --no-cache
docker compose up -d
```

**3. Check backend URL:**
- Frontend should connect to `http://vm-ip:8000`
- Update if using different hostname

---

### Issue: Backend API not responding

**Symptoms:**
```
Failed to fetch
ERR_CONNECTION_REFUSED
```

**Diagnostic Steps:**
```bash
# Check backend container
docker compose logs studio-backend

# Check if backend is running
docker compose ps

# Test backend directly
curl http://localhost:8000/health
```

**Solutions:**

**1. Check backend logs for errors:**
```bash
docker compose logs studio-backend --tail=100
```

**2. Restart backend:**
```bash
docker compose restart studio-backend
```

**3. Check database connection:**
```bash
# Backend won't start if can't connect to database
# Check .env file settings
```

---

### Issue: Login fails with "Unauthorized"

**Symptoms:**
- Login form shows "Invalid credentials"
- But credentials are correct

**Solutions:**

**1. Check if ovs_studio database exists:**
```sql
-- On SQL Server
SELECT name FROM sys.databases WHERE name = 'ovs_studio';
```

**2. Create database if missing:**
```sql
CREATE DATABASE ovs_studio;
```

**3. Check backend logs:**
```bash
docker compose logs studio-backend | grep -i error
```

**4. Reset admin user:**
```bash
# Connect to backend container
docker compose exec studio-backend bash

# Run Python shell
python3

# Reset admin password
from backend.auth.crud import reset_admin_password
reset_admin_password("newpassword123")
```

---

### Issue: "404 Not Found" errors

**Symptoms:**
- Pages show 404 errors
- API endpoints return 404

**Solutions:**

**1. Check routing in frontend:**
- Ensure React Router is properly configured
- Check browser URL matches routes

**2. Check backend routes:**
```bash
# View API docs
http://vm-ip:8000/docs

# Check available routes
docker compose exec studio-backend python3 -c "from backend.main import app; print([r.path for r in app.routes])"
```

---

## Performance Issues

### Issue: Application is slow

**Diagnostic Steps:**

**1. Check resource usage:**

**Ubuntu:**
```bash
# Check overall system
top
htop

# Check Docker stats
docker stats

# Check disk space
df -h

# Check memory
free -h
```

**Windows:**
```powershell
# Check Docker stats
docker stats

# Check system resources
Get-Counter '\Processor(_Total)\% Processor Time'
Get-Counter '\Memory\Available MBytes'
```

**2. Check database performance:**
```sql
-- On SQL Server
-- Check active queries
EXEC sp_who2;

-- Check wait stats
SELECT * FROM sys.dm_os_wait_stats
ORDER BY wait_time_ms DESC;
```

**Solutions:**

**1. Increase Docker resources:**

**Docker Desktop (Windows/Mac):**
- Settings > Resources
- Increase CPUs to 4+
- Increase Memory to 8GB+

**2. Optimize database:**
```sql
-- Update statistics
EXEC sp_updatestats;

-- Rebuild indexes
ALTER INDEX ALL ON your_table REBUILD;
```

**3. Enable caching:**
- Configure Redis for session caching (advanced)
- Enable browser caching

---

### Issue: High memory usage

**Solutions:**

**1. Restart containers:**
```bash
docker compose restart
```

**2. Prune unused Docker resources:**
```bash
# Remove unused containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove everything unused
docker system prune -a --volumes -f
```

**3. Limit container memory:**

Edit `docker-compose.yml`:
```yaml
services:
  studio-backend:
    deploy:
      resources:
        limits:
          memory: 2G
  studio-frontend:
    deploy:
      resources:
        limits:
          memory: 1G
```

---

## Network Issues

### Issue: Cannot access from other machines

**Symptoms:**
- Works on VM: `http://localhost:3000`
- Doesn't work from other machines: `http://vm-ip:3000`

**Solutions:**

**1. Check firewall:**

**Ubuntu:**
```bash
# Check firewall status
sudo ufw status

# Allow ports
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

**Windows:**
```powershell
# Check firewall
Get-NetFirewallRule | Where-Object {$_.LocalPort -eq 3000}

# Allow ports
New-NetFirewallRule -DisplayName "Ombudsman Frontend" `
    -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "Ombudsman Backend" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**2. Check Docker network settings:**
```bash
# Ensure containers bind to 0.0.0.0, not 127.0.0.1
docker compose ps
docker port studio-frontend
```

**3. Check VM network adapter:**
- Ensure VM network is in "Bridged" mode (not NAT)
- Or configure port forwarding in NAT settings

---

## Platform-Specific Issues

### Ubuntu Issues

#### Issue: Permission denied

**Symptoms:**
```
Got permission denied while trying to connect to Docker daemon socket
```

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in
exit

# Or apply group change immediately
newgrp docker

# Test
docker ps
```

---

#### Issue: Systemd service fails

**Symptoms:**
```
Failed to start ombudsman-studio.service
```

**Solutions:**
```bash
# Check service status
sudo systemctl status ombudsman-studio

# View service logs
sudo journalctl -u ombudsman-studio -n 50

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart ombudsman-studio
```

---

### Windows Issues

#### Issue: WSL 2 installation required

**Symptoms:**
```
Docker Desktop requires WSL 2
```

**Solution:**
```powershell
# Run as Administrator
wsl --install

# Restart computer
Restart-Computer

# After restart, set WSL 2 as default
wsl --set-default-version 2

# Install Ubuntu distribution (optional)
wsl --install -d Ubuntu
```

---

#### Issue: Windows Task Scheduler not running

**Symptoms:**
- Application doesn't start on boot

**Solution:**
```powershell
# Check task
Get-ScheduledTask -TaskName "OmbudsmanValidationStudio"

# View task history
Get-ScheduledTaskInfo -TaskName "OmbudsmanValidationStudio"

# Run task manually
Start-ScheduledTask -TaskName "OmbudsmanValidationStudio"

# Check if Docker Desktop is starting on boot
# Settings > General > "Start Docker Desktop when you log in"
```

---

## Getting Help

If you've tried the solutions above and still have issues:

### 1. Collect Diagnostic Information

**Ubuntu:**
```bash
# Save diagnostic info
{
    echo "=== System Info ==="
    uname -a
    echo "=== Docker Version ==="
    docker --version
    docker compose version
    echo "=== Docker Status ==="
    systemctl status docker
    echo "=== Container Status ==="
    docker compose ps
    echo "=== Recent Logs ==="
    docker compose logs --tail=50
    echo "=== Disk Space ==="
    df -h
    echo "=== Memory ==="
    free -h
} > diagnostic-info.txt
```

**Windows:**
```powershell
# Save diagnostic info
{
    "=== System Info ==="
    Get-ComputerInfo | Select-Object WindowsVersion, OsArchitecture
    "=== Docker Version ==="
    docker --version
    docker compose version
    "=== Container Status ==="
    docker compose ps
    "=== Recent Logs ==="
    docker compose logs --tail=50
} | Out-File diagnostic-info.txt
```

### 2. Submit Issue

Include the following in your issue report:
- Platform (Ubuntu/Windows Server version)
- Docker version
- Error messages (exact text)
- Steps to reproduce
- Diagnostic information file

### 3. Contact Support

- GitHub Issues: <your-repo-url>/issues
- Email: support@ombudsman.ai
- Documentation: <docs-url>

---

## Common Error Messages Reference

| Error Message | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Cannot connect to Docker daemon` | Docker not running | Start Docker: `sudo systemctl start docker` |
| `address already in use` | Port conflict | Find and kill process on port |
| `Login failed for user` | Wrong credentials | Check .env file |
| `Connection refused` | Service not running | Check with `docker compose ps` |
| `404 Not Found` | Wrong URL/route | Check API docs at /docs |
| `CORS error` | Cross-origin issue | Check backend CORS settings |
| `Out of memory` | Insufficient RAM | Increase Docker memory limit |
| `Disk quota exceeded` | Full disk | Run `docker system prune -a` |
| `Network timeout` | Firewall blocking | Check firewall rules |
| `Certificate error` | SSL/TLS issue | Check certificate configuration |
