#!/bin/bash

# Ombudsman Validation Studio - Uninstallation Script
# This script removes the application and optionally Docker

set -e

echo "=========================================="
echo "Ombudsman Studio - Uninstallation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

APP_DIR="/opt/ombudsman-validation-studio"

echo -e "${YELLOW}WARNING: This will remove Ombudsman Validation Studio${NC}"
echo ""
echo "This script will:"
echo "  1. Stop all running containers"
echo "  2. Remove containers and images"
echo "  3. Remove application directory: $APP_DIR"
echo "  4. Remove systemd service"
echo "  5. Optionally remove Docker"
echo ""

read -p "Do you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""
echo "Starting uninstallation..."
echo ""

# Step 1: Stop systemd service
echo "[1/7] Stopping systemd service..."
if systemctl is-active --quiet ombudsman-studio; then
    systemctl stop ombudsman-studio
    echo -e "${GREEN}✓${NC} Service stopped"
else
    echo -e "${YELLOW}⚠${NC} Service not running"
fi

if systemctl is-enabled --quiet ombudsman-studio 2>/dev/null; then
    systemctl disable ombudsman-studio
    echo -e "${GREEN}✓${NC} Auto-start disabled"
fi
echo ""

# Step 2: Stop and remove Docker containers
echo "[2/7] Stopping and removing Docker containers..."
if [ -d "$APP_DIR" ] && [ -f "$APP_DIR/docker-compose.yml" ]; then
    cd $APP_DIR
    if docker compose ps -q 2>/dev/null | grep -q .; then
        docker compose down -v
        echo -e "${GREEN}✓${NC} Containers stopped and removed"
    else
        echo -e "${YELLOW}⚠${NC} No containers running"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker Compose file not found"
fi
echo ""

# Step 3: Remove Docker images
echo "[3/7] Removing Docker images..."
read -p "Remove Ombudsman Docker images? (yes/no): " REMOVE_IMAGES
if [ "$REMOVE_IMAGES" = "yes" ]; then
    # Remove images related to this application
    IMAGES=$(docker images | grep -E "ombudsman|studio" | awk '{print $3}')
    if [ ! -z "$IMAGES" ]; then
        echo "$IMAGES" | xargs docker rmi -f 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Docker images removed"
    else
        echo -e "${YELLOW}⚠${NC} No Ombudsman images found"
    fi
else
    echo -e "${YELLOW}⊘${NC} Skipping image removal"
fi
echo ""

# Step 4: Remove application directory
echo "[4/7] Removing application directory..."
read -p "Create backup before removal? (yes/no): " CREATE_BACKUP
if [ "$CREATE_BACKUP" = "yes" ] && [ -d "$APP_DIR" ]; then
    BACKUP_FILE="$HOME/ombudsman-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "$BACKUP_FILE" "$APP_DIR" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Backup created: $BACKUP_FILE"
fi

if [ -d "$APP_DIR" ]; then
    read -p "Remove application directory $APP_DIR? (yes/no): " REMOVE_DIR
    if [ "$REMOVE_DIR" = "yes" ]; then
        rm -rf "$APP_DIR"
        echo -e "${GREEN}✓${NC} Application directory removed"
    else
        echo -e "${YELLOW}⊘${NC} Application directory kept"
    fi
else
    echo -e "${YELLOW}⚠${NC} Application directory not found"
fi
echo ""

# Step 5: Remove systemd service
echo "[5/7] Removing systemd service..."
if [ -f "/etc/systemd/system/ombudsman-studio.service" ]; then
    rm -f "/etc/systemd/system/ombudsman-studio.service"
    systemctl daemon-reload
    echo -e "${GREEN}✓${NC} Systemd service removed"
else
    echo -e "${YELLOW}⚠${NC} Systemd service not found"
fi
echo ""

# Step 6: Remove firewall rules
echo "[6/7] Removing firewall rules..."
if command -v ufw &> /dev/null; then
    read -p "Remove firewall rules for ports 3000 and 8000? (yes/no): " REMOVE_FW
    if [ "$REMOVE_FW" = "yes" ]; then
        ufw delete allow 3000/tcp 2>/dev/null || true
        ufw delete allow 8000/tcp 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Firewall rules removed"
    else
        echo -e "${YELLOW}⊘${NC} Firewall rules kept"
    fi
else
    echo -e "${YELLOW}⚠${NC} UFW not installed"
fi
echo ""

# Step 7: Optionally remove Docker
echo "[7/7] Docker removal (optional)..."
echo ""
echo -e "${YELLOW}WARNING: This will remove Docker completely!${NC}"
echo "This will affect any other Docker containers you may have."
echo ""
read -p "Remove Docker completely? (yes/no): " REMOVE_DOCKER
if [ "$REMOVE_DOCKER" = "yes" ]; then
    echo ""
    echo "Stopping Docker service..."
    systemctl stop docker
    systemctl disable docker

    echo "Removing Docker packages..."
    apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || true

    echo "Removing Docker data..."
    rm -rf /var/lib/docker
    rm -rf /var/lib/containerd
    rm -rf /etc/docker

    echo "Removing Docker repository..."
    rm -f /etc/apt/sources.list.d/docker.list
    rm -f /etc/apt/keyrings/docker.gpg

    echo -e "${GREEN}✓${NC} Docker removed"
else
    echo -e "${YELLOW}⊘${NC} Docker kept (recommended if you use it for other projects)"
fi
echo ""

# Clean up package cache
echo "Cleaning up..."
apt-get autoremove -y 2>/dev/null || true
apt-get autoclean -y 2>/dev/null || true

echo ""
echo "=========================================="
echo "Uninstallation Complete"
echo "=========================================="
echo ""

if [ "$CREATE_BACKUP" = "yes" ] && [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}✓${NC} Backup saved to: $BACKUP_FILE"
fi

if [ "$REMOVE_DIR" = "yes" ]; then
    echo -e "${GREEN}✓${NC} Application removed"
else
    echo -e "${YELLOW}⚠${NC} Application directory still exists: $APP_DIR"
fi

if [ "$REMOVE_DOCKER" = "yes" ]; then
    echo -e "${GREEN}✓${NC} Docker removed"
else
    echo -e "${YELLOW}ℹ${NC} Docker is still installed"
    echo ""
    echo "To clean up Docker resources, run:"
    echo "  docker system prune -a --volumes -f"
fi

echo ""
echo "Thank you for using Ombudsman Validation Studio!"
echo ""
