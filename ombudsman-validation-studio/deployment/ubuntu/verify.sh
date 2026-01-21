#!/bin/bash

# Ombudsman Validation Studio - Post-Installation Verification Script
# This script verifies that the installation completed successfully

set -e

echo "=================================================="
echo "Ombudsman Studio - Installation Verification"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check results
PASSED=0
FAILED=0
WARNINGS=0

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Function to print colored output
print_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "Verifying installation..."
echo ""

# 1. Check if Docker is installed
echo "[1/12] Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_pass "Docker installed: $DOCKER_VERSION"
else
    print_fail "Docker is not installed"
fi
echo ""

# 2. Check if Docker Compose is installed
echo "[2/12] Checking Docker Compose installation..."
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    print_pass "Docker Compose installed: $COMPOSE_VERSION"
else
    print_fail "Docker Compose is not installed"
fi
echo ""

# 3. Check if Docker daemon is running
echo "[3/12] Checking Docker service..."
if systemctl is-active --quiet docker; then
    print_pass "Docker service is running"
else
    print_fail "Docker service is not running"
    print_info "Try: sudo systemctl start docker"
fi
echo ""

# 4. Check if application directory exists
echo "[4/12] Checking application directory..."
APP_DIR="/opt/ombudsman-validation-studio"
if [ -d "$APP_DIR" ]; then
    print_pass "Application directory exists: $APP_DIR"
else
    print_fail "Application directory not found: $APP_DIR"
fi
echo ""

# 5. Check if .env file exists
echo "[5/12] Checking configuration file..."
if [ -f "$APP_DIR/.env" ]; then
    print_pass "Configuration file exists: $APP_DIR/.env"

    # Check if .env has been modified from template
    if grep -q "your-sqlserver-host" "$APP_DIR/.env"; then
        print_warn "Configuration file contains template values - needs updating"
        print_info "Edit with: sudo nano $APP_DIR/.env"
    else
        print_pass "Configuration file has been customized"
    fi
else
    print_fail "Configuration file not found: $APP_DIR/.env"
fi
echo ""

# 6. Check if docker-compose.yml exists
echo "[6/12] Checking Docker Compose configuration..."
if [ -f "$APP_DIR/docker-compose.yml" ]; then
    print_pass "Docker Compose configuration exists"
else
    print_fail "Docker Compose configuration not found"
fi
echo ""

# 7. Check if systemd service exists
echo "[7/12] Checking systemd service..."
if [ -f "/etc/systemd/system/ombudsman-studio.service" ]; then
    print_pass "Systemd service installed"

    if systemctl is-enabled --quiet ombudsman-studio; then
        print_pass "Auto-start is enabled"
    else
        print_warn "Auto-start is not enabled"
        print_info "Enable with: sudo systemctl enable ombudsman-studio"
    fi
else
    print_warn "Systemd service not found"
fi
echo ""

# 8. Check if containers are running
echo "[8/12] Checking Docker containers..."
cd $APP_DIR 2>/dev/null || true

if docker compose ps | grep -q "Up"; then
    print_pass "Docker containers are running"

    # Count running containers
    RUNNING=$(docker compose ps | grep "Up" | wc -l)
    print_info "$RUNNING container(s) running"

    # List containers
    docker compose ps --format "table {{.Name}}\t{{.Status}}" | tail -n +2 | while read line; do
        print_info "  $line"
    done
else
    print_warn "Docker containers are not running"
    print_info "Start with: cd $APP_DIR && docker compose up -d"
fi
echo ""

# 9. Check frontend accessibility
echo "[9/12] Checking frontend accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|301\|302"; then
    print_pass "Frontend is accessible on port 3000"
else
    print_fail "Frontend is not accessible on port 3000"
    print_info "Check logs: docker compose logs studio-frontend"
fi
echo ""

# 10. Check backend accessibility
echo "[10/12] Checking backend API..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    print_pass "Backend API is responding (health check passed)"
elif [ "$HTTP_CODE" = "404" ]; then
    print_warn "Backend is running but /health endpoint returned 404"
    print_info "Try: curl http://localhost:8000/docs"
else
    print_fail "Backend API is not accessible (HTTP $HTTP_CODE)"
    print_info "Check logs: docker compose logs studio-backend"
fi
echo ""

# 11. Check ports are listening
echo "[11/12] Checking network ports..."
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":3000 "; then
        print_pass "Port 3000 (frontend) is listening"
    else
        print_fail "Port 3000 (frontend) is not listening"
    fi

    if netstat -tuln | grep -q ":8000 "; then
        print_pass "Port 8000 (backend) is listening"
    else
        print_fail "Port 8000 (backend) is not listening"
    fi
elif command -v ss &> /dev/null; then
    if ss -tuln | grep -q ":3000 "; then
        print_pass "Port 3000 (frontend) is listening"
    else
        print_fail "Port 3000 (frontend) is not listening"
    fi

    if ss -tuln | grep -q ":8000 "; then
        print_pass "Port 8000 (backend) is listening"
    else
        print_fail "Port 8000 (backend) is not listening"
    fi
else
    print_warn "Network tools not available, skipping port check"
fi
echo ""

# 12. Check firewall status
echo "[12/12] Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        print_pass "UFW firewall is active"

        if ufw status | grep -q "3000.*ALLOW"; then
            print_pass "Port 3000 is allowed through firewall"
        else
            print_warn "Port 3000 is not allowed through firewall"
            print_info "Allow with: sudo ufw allow 3000/tcp"
        fi

        if ufw status | grep -q "8000.*ALLOW"; then
            print_pass "Port 8000 is allowed through firewall"
        else
            print_warn "Port 8000 is not allowed through firewall"
            print_info "Allow with: sudo ufw allow 8000/tcp"
        fi
    else
        print_warn "UFW firewall is not active"
        print_info "Enable with: sudo ufw enable"
    fi
else
    print_info "UFW firewall not installed (optional)"
fi
echo ""

# Summary
echo "=================================================="
echo "Verification Summary"
echo "=================================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC}   $FAILED"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Installation verified successfully!${NC}"
    echo ""
    echo "Access your application:"
    echo -e "  ${BLUE}Frontend:${NC} http://$LOCAL_IP:3000"
    echo -e "  ${BLUE}Backend API:${NC} http://$LOCAL_IP:8000"
    echo -e "  ${BLUE}API Docs:${NC} http://$LOCAL_IP:8000/docs"
    echo ""
    echo "Next steps:"
    echo "  1. Open http://$LOCAL_IP:3000 in your browser"
    echo "  2. Register a new user account"
    echo "  3. Start using Ombudsman Validation Studio!"
    echo ""
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Installation verified with warnings${NC}"
    echo ""
    echo "The application should work, but consider addressing warnings."
    echo ""
    echo "Access your application:"
    echo -e "  ${BLUE}Frontend:${NC} http://$LOCAL_IP:3000"
    echo -e "  ${BLUE}Backend API:${NC} http://$LOCAL_IP:8000"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Installation verification failed${NC}"
    echo ""
    echo "Please address the failed checks:"
    echo ""

    if [ ! -d "$APP_DIR" ]; then
        echo "  - Run installation script: sudo ./install.sh"
    fi

    if ! docker compose ps 2>/dev/null | grep -q "Up"; then
        echo "  - Start containers: cd $APP_DIR && docker compose up -d"
    fi

    echo "  - View logs: docker compose logs -f"
    echo "  - Check troubleshooting guide: ../TROUBLESHOOTING.md"
    echo ""
    exit 1
fi
