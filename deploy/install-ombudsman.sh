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
# Fix apt_pkg issue (common on Ubuntu)
# ==============================================
fix_apt_pkg() {
    echo ""
    echo "=========================================="
    echo "Fixing apt_pkg if needed..."
    echo "=========================================="

    apt-get install --reinstall -y python3-apt 2>/dev/null || true
    print_status "python3-apt reinstalled"
}

# ==============================================
# Install system dependencies
# ==============================================
install_system_deps() {
    echo ""
    echo "=========================================="
    echo "Installing system dependencies..."
    echo "=========================================="

    fix_apt_pkg
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
    ENV_FILE="$BASE_DIR/ombudsman.env"

    cd "$FRONTEND_DIR"

    # Create frontend .env file from main config
    if [ -f "$ENV_FILE" ]; then
        # Extract VITE_API_URL from main config
        VITE_API_URL=$(grep "^VITE_API_URL=" "$ENV_FILE" | cut -d'=' -f2-)
        if [ -n "$VITE_API_URL" ]; then
            echo "VITE_API_URL=$VITE_API_URL" > .env
            chown "$REAL_USER:$REAL_USER" .env
            print_status "Frontend .env created with API URL: $VITE_API_URL"
        fi
    fi

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
# Setup SQL Server Auth Database
# ==============================================
setup_auth_db() {
    echo ""
    echo "=========================================="
    echo "Setting up authentication database..."
    echo "=========================================="

    ENV_FILE="$BASE_DIR/ombudsman.env"
    REAL_USER="${SUDO_USER:-$USER}"

    # Load env file
    if [ -f "$ENV_FILE" ]; then
        set -a
        source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
        set +a
    fi

    # Check if using SQL Server auth
    if [ "${AUTH_BACKEND:-sqlite}" = "sqlserver" ]; then
        if [ -n "$AUTH_DB_SERVER" ] && [ -n "$AUTH_DB_USER" ] && [ -n "$AUTH_DB_PASSWORD" ]; then
            echo "Creating auth tables in SQL Server..."
            cd "$BACKEND_DIR"
            sudo -u "$REAL_USER" \
                AUTH_DB_SERVER="$AUTH_DB_SERVER" \
                AUTH_DB_NAME="${AUTH_DB_NAME:-ovs_studio}" \
                AUTH_DB_USER="$AUTH_DB_USER" \
                AUTH_DB_PASSWORD="$AUTH_DB_PASSWORD" \
                ./venv/bin/python auth/setup_sql_server_auth.py

            # Create default admin user
            echo "Creating default admin user..."
            sudo -u "$REAL_USER" \
                AUTH_DB_SERVER="$AUTH_DB_SERVER" \
                AUTH_DB_NAME="${AUTH_DB_NAME:-ovs_studio}" \
                AUTH_DB_USER="$AUTH_DB_USER" \
                AUTH_DB_PASSWORD="$AUTH_DB_PASSWORD" \
                ./venv/bin/python -c "
from auth.sqlserver_auth_repository import SQLServerAuthRepository
from auth.models import UserCreate, UserRole
repo = SQLServerAuthRepository()
try:
    user = UserCreate(username='admin', email='admin@localhost', password='admin123', role=UserRole.ADMIN)
    repo.create_user(user)
    print('  Default admin user created (admin/admin123)')
except ValueError as e:
    print(f'  Admin user already exists')
except Exception as e:
    print(f'  Could not create admin user: {e}')
"
            print_status "SQL Server auth database configured"
        else
            print_warning "AUTH_BACKEND=sqlserver but credentials not set. Skipping auth DB setup."
            print_warning "Edit $ENV_FILE and run: ./start-ombudsman.sh setup-auth"
        fi
    else
        print_status "Using SQLite for authentication (default)"
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
    setup_auth_db

    echo ""
    echo "=========================================="
    echo -e "${GREEN}Installation Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit your config file (if not already done):"
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
    echo "Default login: admin / admin123"
    echo ""
}

main "$@"
