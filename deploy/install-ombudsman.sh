#!/bin/bash
#
# Ombudsman Validation Studio - Installation Script
# Run this once to set up all prerequisites
#
# Usage: sudo ./install-ombudsman.sh
#

set -e

# ==============================================
# Configuration
# ==============================================
BASE_DIR="/data/ombudsman"
BACKEND_DIR="$BASE_DIR/ombudsman-validation-studio/backend"
FRONTEND_DIR="$BASE_DIR/ombudsman-validation-studio/frontend"
NODE_VERSION="20"

# ==============================================
# Colors for output
# ==============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ==============================================
# Check if running as root for system packages
# ==============================================
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run with sudo for system package installation"
        echo "Usage: sudo ./install-ombudsman.sh"
        exit 1
    fi
}

# ==============================================
# Install system dependencies
# ==============================================
install_system_deps() {
    echo ""
    echo "=========================================="
    echo "Installing system dependencies..."
    echo "=========================================="

    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        git \
        build-essential

    print_status "System dependencies installed"
}

# ==============================================
# Install Node.js
# ==============================================
install_nodejs() {
    echo ""
    echo "=========================================="
    echo "Installing Node.js v${NODE_VERSION}..."
    echo "=========================================="

    if command -v node &> /dev/null; then
        CURRENT_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$CURRENT_VERSION" -ge "$NODE_VERSION" ]; then
            print_status "Node.js $(node --version) already installed"
            return
        fi
    fi

    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    apt-get install -y nodejs

    print_status "Node.js $(node --version) installed"
    print_status "npm $(npm --version) installed"
}

# ==============================================
# Install ODBC drivers for SQL Server
# ==============================================
install_odbc_drivers() {
    echo ""
    echo "=========================================="
    echo "Installing ODBC drivers for SQL Server..."
    echo "=========================================="

    if odbcinst -q -d -n "ODBC Driver 18 for SQL Server" &> /dev/null; then
        print_status "ODBC Driver 18 already installed"
        return
    fi

    # Add Microsoft repo
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
    curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list

    apt-get update
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

    print_status "ODBC Driver 18 for SQL Server installed"
}

# ==============================================
# Create directory structure
# ==============================================
create_directories() {
    echo ""
    echo "=========================================="
    echo "Creating directory structure..."
    echo "=========================================="

    mkdir -p "$BASE_DIR/data"
    mkdir -p "$BASE_DIR/logs"
    mkdir -p "$BASE_DIR/data/projects"
    mkdir -p "$BASE_DIR/data/pipelines"
    mkdir -p "$BASE_DIR/data/results"
    mkdir -p "$BASE_DIR/data/batch_jobs"
    mkdir -p "$BASE_DIR/data/workloads"
    mkdir -p "$BASE_DIR/data/auth"

    # Set ownership to current user (not root)
    REAL_USER="${SUDO_USER:-$USER}"
    chown -R "$REAL_USER:$REAL_USER" "$BASE_DIR/data"
    chown -R "$REAL_USER:$REAL_USER" "$BASE_DIR/logs"

    print_status "Directories created"
}

# ==============================================
# Setup Python virtual environment
# ==============================================
setup_python_venv() {
    echo ""
    echo "=========================================="
    echo "Setting up Python virtual environment..."
    echo "=========================================="

    REAL_USER="${SUDO_USER:-$USER}"

    if [ ! -d "$BACKEND_DIR/venv" ]; then
        sudo -u "$REAL_USER" python3 -m venv "$BACKEND_DIR/venv"
        print_status "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi

    # Install Python dependencies
    sudo -u "$REAL_USER" "$BACKEND_DIR/venv/bin/pip" install --upgrade pip
    sudo -u "$REAL_USER" "$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

    print_status "Python dependencies installed"
}

# ==============================================
# Setup Frontend
# ==============================================
setup_frontend() {
    echo ""
    echo "=========================================="
    echo "Setting up frontend..."
    echo "=========================================="

    REAL_USER="${SUDO_USER:-$USER}"

    cd "$FRONTEND_DIR"

    # Install npm dependencies
    sudo -u "$REAL_USER" npm install
    print_status "Frontend dependencies installed"

    # Build frontend
    sudo -u "$REAL_USER" npm run build
    print_status "Frontend built"
}

# ==============================================
# Setup config file
# ==============================================
setup_config() {
    echo ""
    echo "=========================================="
    echo "Setting up configuration..."
    echo "=========================================="

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    ENV_FILE="$BASE_DIR/ombudsman.env"

    if [ ! -f "$ENV_FILE" ]; then
        cp "$SCRIPT_DIR/ombudsman.env" "$ENV_FILE"
        REAL_USER="${SUDO_USER:-$USER}"
        chown "$REAL_USER:$REAL_USER" "$ENV_FILE"
        print_status "Config file created at $ENV_FILE"
        print_warning "Remember to edit $ENV_FILE with your database credentials!"
    else
        print_status "Config file already exists at $ENV_FILE"
    fi
}

# ==============================================
# Main
# ==============================================
main() {
    echo "=========================================="
    echo "Ombudsman Validation Studio Installer"
    echo "=========================================="

    check_sudo
    install_system_deps
    install_nodejs
    install_odbc_drivers
    create_directories
    setup_python_venv
    setup_frontend
    setup_config

    echo ""
    echo "=========================================="
    echo -e "${GREEN}Installation Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit your config file:"
    echo "   nano $BASE_DIR/ombudsman.env"
    echo ""
    echo "2. Start the services:"
    echo "   cd $BASE_DIR/deploy"
    echo "   ./start-ombudsman.sh start"
    echo ""
    echo "3. Access the application:"
    echo "   Frontend: http://your-server:3000"
    echo "   Backend:  http://your-server:8000"
    echo ""
}

main "$@"
