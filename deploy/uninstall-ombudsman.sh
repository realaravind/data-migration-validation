#!/bin/bash
#
# Ombudsman Validation Studio - Uninstall Script
# Cleanly removes the installation
#
# Usage: sudo ./uninstall-ombudsman.sh
#

# ==============================================
# Auto-detect base directory from script location
# ==============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$OMBUDSMAN_BASE_DIR" ]; then
    BASE_DIR="$OMBUDSMAN_BASE_DIR"
else
    BASE_DIR="$(dirname "$SCRIPT_DIR")"
fi

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
# Check if running as root
# ==============================================
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run with sudo"
        echo "Usage: sudo ./uninstall-ombudsman.sh"
        exit 1
    fi
}

# ==============================================
# Stop services
# ==============================================
stop_services() {
    echo ""
    echo "Stopping services..."

    if systemctl is-active --quiet ombudsman-backend 2>/dev/null; then
        systemctl stop ombudsman-backend
        print_status "Stopped ombudsman-backend"
    else
        echo "  ombudsman-backend not running"
    fi

    if systemctl is-active --quiet ombudsman-frontend 2>/dev/null; then
        systemctl stop ombudsman-frontend
        print_status "Stopped ombudsman-frontend"
    else
        echo "  ombudsman-frontend not running"
    fi
}

# ==============================================
# Disable and remove systemd services
# ==============================================
remove_systemd_services() {
    echo ""
    echo "Removing systemd services..."

    # Disable services
    systemctl disable ombudsman-backend 2>/dev/null && print_status "Disabled ombudsman-backend"
    systemctl disable ombudsman-frontend 2>/dev/null && print_status "Disabled ombudsman-frontend"

    # Remove service files
    if [ -f /etc/systemd/system/ombudsman-backend.service ]; then
        rm -f /etc/systemd/system/ombudsman-backend.service
        print_status "Removed ombudsman-backend.service"
    fi

    if [ -f /etc/systemd/system/ombudsman-frontend.service ]; then
        rm -f /etc/systemd/system/ombudsman-frontend.service
        print_status "Removed ombudsman-frontend.service"
    fi

    # Reload systemd
    systemctl daemon-reload
    print_status "Reloaded systemd"
}

# ==============================================
# Remove data directory
# ==============================================
remove_data() {
    DATA_DIR="$BASE_DIR/data"

    if [ -d "$DATA_DIR" ]; then
        echo ""
        print_warning "Data directory found: $DATA_DIR"
        echo "This contains projects, pipelines, results, and authentication data."
        echo ""
        read -p "Delete data directory? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "$DATA_DIR"
            print_status "Removed data directory"
        else
            print_warning "Data directory preserved"
        fi
    fi
}

# ==============================================
# Remove logs
# ==============================================
remove_logs() {
    LOG_DIR="$BASE_DIR/logs"

    if [ -d "$LOG_DIR" ]; then
        echo ""
        read -p "Delete log files? (Y/n): " confirm
        confirm="${confirm:-Y}"
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "$LOG_DIR"
            print_status "Removed log directory"
        else
            print_warning "Log directory preserved"
        fi
    fi
}

# ==============================================
# Remove config and secrets
# ==============================================
remove_config() {
    echo ""
    echo "Configuration files:"

    [ -f "$BASE_DIR/ombudsman.env" ] && echo "  - $BASE_DIR/ombudsman.env"
    [ -f "$BASE_DIR/ombudsman.env.enc" ] && echo "  - $BASE_DIR/ombudsman.env.enc (encrypted)"
    [ -f "$BASE_DIR/.sops-age-key.txt" ] && echo "  - $BASE_DIR/.sops-age-key.txt (encryption key)"
    [ -f "$BASE_DIR/.sops.yaml" ] && echo "  - $BASE_DIR/.sops.yaml"

    echo ""
    print_warning "These contain your database credentials and encryption keys!"
    read -p "Delete configuration files? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -f "$BASE_DIR/ombudsman.env"
        rm -f "$BASE_DIR/ombudsman.env.enc"
        rm -f "$BASE_DIR/.sops-age-key.txt"
        rm -f "$BASE_DIR/.sops.yaml"
        print_status "Removed configuration files"
    else
        print_warning "Configuration files preserved"
    fi
}

# ==============================================
# Remove virtual environment
# ==============================================
remove_venv() {
    VENV_DIR="$BASE_DIR/ombudsman-validation-studio/backend/venv"

    if [ -d "$VENV_DIR" ]; then
        echo ""
        read -p "Delete Python virtual environment? (Y/n): " confirm
        confirm="${confirm:-Y}"
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "$VENV_DIR"
            print_status "Removed virtual environment"
        else
            print_warning "Virtual environment preserved"
        fi
    fi
}

# ==============================================
# Remove node_modules
# ==============================================
remove_node_modules() {
    NODE_DIR="$BASE_DIR/ombudsman-validation-studio/frontend/node_modules"

    if [ -d "$NODE_DIR" ]; then
        echo ""
        read -p "Delete node_modules? (Y/n): " confirm
        confirm="${confirm:-Y}"
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "$NODE_DIR"
            rm -rf "$BASE_DIR/ombudsman-validation-studio/frontend/dist"
            print_status "Removed node_modules and build artifacts"
        else
            print_warning "node_modules preserved"
        fi
    fi
}

# ==============================================
# Remove entire installation
# ==============================================
remove_installation() {
    echo ""
    echo "=========================================="
    print_warning "COMPLETE REMOVAL"
    echo "=========================================="
    echo ""
    echo "This will delete the entire installation directory:"
    echo "  $BASE_DIR"
    echo ""
    print_warning "This action cannot be undone!"
    echo ""
    read -p "Delete entire installation? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        # Extra confirmation for complete removal
        read -p "Are you sure? Type 'DELETE' to confirm: " final_confirm
        if [ "$final_confirm" = "DELETE" ]; then
            rm -rf "$BASE_DIR"
            print_status "Removed entire installation"
            echo ""
            echo "Uninstallation complete."
            exit 0
        else
            print_warning "Cancelled"
        fi
    else
        print_warning "Installation directory preserved"
    fi
}

# ==============================================
# Main
# ==============================================
main() {
    echo "=========================================="
    echo "Ombudsman Validation Studio - Uninstaller"
    echo "=========================================="
    echo ""
    echo "Installation directory: $BASE_DIR"
    echo ""

    check_sudo

    # Confirm before proceeding
    read -p "Proceed with uninstallation? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Cancelled."
        exit 0
    fi

    stop_services
    remove_systemd_services
    remove_venv
    remove_node_modules
    remove_logs
    remove_data
    remove_config
    remove_installation

    echo ""
    echo "=========================================="
    echo "Uninstallation Summary"
    echo "=========================================="
    echo ""
    echo "Removed:"
    echo "  - Systemd services"
    echo ""

    if [ -d "$BASE_DIR" ]; then
        echo "Preserved (in $BASE_DIR):"
        [ -d "$BASE_DIR/data" ] && echo "  - data/"
        [ -d "$BASE_DIR/logs" ] && echo "  - logs/"
        [ -f "$BASE_DIR/ombudsman.env" ] && echo "  - ombudsman.env"
        [ -f "$BASE_DIR/ombudsman.env.enc" ] && echo "  - ombudsman.env.enc"
        [ -f "$BASE_DIR/.sops-age-key.txt" ] && echo "  - .sops-age-key.txt"
        echo ""
        echo "To completely remove, run:"
        echo "  sudo rm -rf $BASE_DIR"
    fi

    echo ""
}

main "$@"
