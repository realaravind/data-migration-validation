#!/bin/bash

# Ombudsman Validation Studio - Pre-Installation Check Script
# This script verifies that the Ubuntu system meets requirements before installation

set -e

echo "=========================================="
echo "Ombudsman Studio - Pre-Installation Check"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check results
PASSED=0
FAILED=0
WARNINGS=0

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
    echo -e "  $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_fail "This script must be run as root (use sudo)"
    exit 1
fi

echo "Checking system requirements..."
echo ""

# 1. Check Ubuntu Version
echo "[1/10] Checking Ubuntu version..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then
        VERSION_NUM=$(echo $VERSION_ID | cut -d. -f1)
        if [ "$VERSION_NUM" -ge 20 ]; then
            print_pass "Ubuntu $VERSION_ID detected"
        else
            print_fail "Ubuntu $VERSION_ID is too old (need 20.04+)"
        fi
    else
        print_fail "This is not Ubuntu ($ID detected)"
    fi
else
    print_fail "Cannot detect operating system"
fi
echo ""

# 2. Check CPU cores
echo "[2/10] Checking CPU cores..."
CPU_CORES=$(nproc)
if [ "$CPU_CORES" -ge 4 ]; then
    print_pass "$CPU_CORES CPU cores detected (recommended)"
elif [ "$CPU_CORES" -ge 2 ]; then
    print_warn "$CPU_CORES CPU cores detected (minimum met, 4+ recommended)"
else
    print_fail "$CPU_CORES CPU core(s) detected (need at least 2)"
fi
echo ""

# 3. Check available RAM
echo "[3/10] Checking available RAM..."
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -ge 8 ]; then
    print_pass "${TOTAL_RAM}GB RAM detected (recommended)"
elif [ "$TOTAL_RAM" -ge 4 ]; then
    print_warn "${TOTAL_RAM}GB RAM detected (minimum met, 8GB+ recommended)"
else
    print_fail "${TOTAL_RAM}GB RAM detected (need at least 4GB)"
fi
echo ""

# 4. Check available disk space
echo "[4/10] Checking available disk space..."
DISK_SPACE=$(df / | awk 'NR==2 {print int($4/1024/1024)}')
if [ "$DISK_SPACE" -ge 50 ]; then
    print_pass "${DISK_SPACE}GB free disk space (recommended)"
elif [ "$DISK_SPACE" -ge 20 ]; then
    print_warn "${DISK_SPACE}GB free disk space (minimum met, 50GB+ recommended)"
else
    print_fail "${DISK_SPACE}GB free disk space (need at least 20GB)"
fi
echo ""

# 5. Check internet connectivity
echo "[5/10] Checking internet connectivity..."
if ping -c 1 google.com &> /dev/null || ping -c 1 8.8.8.8 &> /dev/null; then
    print_pass "Internet connection available"
else
    print_fail "No internet connection (required for Docker installation)"
fi
echo ""

# 6. Check DNS resolution
echo "[6/10] Checking DNS resolution..."
if nslookup google.com &> /dev/null; then
    print_pass "DNS resolution working"
else
    print_warn "DNS resolution may have issues"
fi
echo ""

# 7. Check required ports availability
echo "[7/10] Checking required ports..."
check_port() {
    PORT=$1
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_fail "Port $PORT is already in use"
        print_info "Process using port: $(lsof -Pi :$PORT -sTCP:LISTEN | tail -n 1)"
    else
        print_pass "Port $PORT is available"
    fi
}

# Check if lsof is installed
if ! command -v lsof &> /dev/null; then
    print_warn "lsof not installed, skipping port check"
else
    check_port 3000  # Frontend
    check_port 8000  # Backend
fi
echo ""

# 8. Check if Docker is already installed
echo "[8/10] Checking existing Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+')
    print_warn "Docker $DOCKER_VERSION already installed (will be skipped)"

    # Check if Docker is running
    if systemctl is-active --quiet docker; then
        print_pass "Docker service is running"
    else
        print_warn "Docker service is not running"
    fi
else
    print_pass "Docker not installed (will be installed)"
fi
echo ""

# 9. Check system architecture
echo "[9/10] Checking system architecture..."
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    print_pass "x86_64 architecture detected"
elif [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
    print_pass "ARM64 architecture detected"
else
    print_warn "Unusual architecture detected: $ARCH"
fi
echo ""

# 10. Check for required package manager
echo "[10/10] Checking package manager..."
if command -v apt-get &> /dev/null; then
    print_pass "apt-get package manager available"
else
    print_fail "apt-get not found (required for installation)"
fi
echo ""

# Summary
echo "=========================================="
echo "Pre-Installation Check Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC}   $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ System meets requirements!${NC}"
    echo ""
    echo "You can proceed with installation:"
    echo "  sudo ./install.sh"
    echo ""
    exit 0
elif [ $FAILED -le 2 ] && [ $WARNINGS -ge 1 ]; then
    echo -e "${YELLOW}⚠ System meets minimum requirements with warnings${NC}"
    echo ""
    echo "You can proceed, but consider addressing warnings for better performance."
    echo "  sudo ./install.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ System does not meet requirements${NC}"
    echo ""
    echo "Please address the failed checks before installation."
    echo ""
    exit 1
fi
