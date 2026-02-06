#!/bin/bash
#
# Ombudsman Validation Studio - Installation Script
# Run this once to set up all prerequisites
#
# Usage: sudo ./install-ombudsman.sh
#        OMBUDSMAN_BASE_DIR=/custom/path sudo ./install-ombudsman.sh
#

set -e

# ==============================================
# Configuration - Auto-detect or use environment variable
# ==============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect BASE_DIR from script location (parent of deploy/)
# Can be overridden with OMBUDSMAN_BASE_DIR environment variable
if [ -n "$OMBUDSMAN_BASE_DIR" ]; then
    BASE_DIR="$OMBUDSMAN_BASE_DIR"
else
    BASE_DIR="$(dirname "$SCRIPT_DIR")"
fi

BACKEND_DIR="$BASE_DIR/ombudsman-validation-studio/backend"
FRONTEND_DIR="$BASE_DIR/ombudsman-validation-studio/frontend"
NODE_VERSION="20"
PYTHON_CMD=""  # Will be auto-detected

echo "=========================================="
echo "Installation Directory: $BASE_DIR"
echo "=========================================="

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
# Detect Python command (python3 or python)
# ==============================================
detect_python() {
    echo ""
    echo "=========================================="
    echo "Detecting Python installation..."
    echo "=========================================="

    # Check for python3 first (preferred)
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_status "Found python3: $PYTHON_VERSION"
    # Fall back to python
    elif command -v python &> /dev/null; then
        # Verify it's Python 3.x, not Python 2.x
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
        if [ "$PYTHON_MAJOR" -ge 3 ]; then
            PYTHON_CMD="python"
            print_status "Found python: $PYTHON_VERSION"
        else
            print_error "Python 2.x detected ($PYTHON_VERSION). Python 3.8+ is required."
            print_error "Please install Python 3: apt-get install python3 python3-pip python3-venv"
            exit 1
        fi
    else
        print_error "Python not found. Please install Python 3.8+:"
        print_error "  apt-get install python3 python3-pip python3-venv"
        exit 1
    fi

    # Verify minimum version (3.8+)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python $PYTHON_VERSION is too old. Python 3.8+ is required."
        exit 1
    fi

    print_status "Using Python command: $PYTHON_CMD (version $PYTHON_VERSION)"
    export PYTHON_CMD
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
# Install SOPS and age for secrets encryption
# ==============================================
install_sops() {
    echo ""
    echo "=========================================="
    echo "Installing SOPS and age for secrets..."
    echo "=========================================="

    # Install age
    if command -v age &> /dev/null; then
        print_status "age already installed: $(age --version)"
    else
        echo "Installing age..."
        # Try apt first (Ubuntu 22.04+)
        if apt-cache show age &> /dev/null 2>&1; then
            apt-get install -y age
        else
            # Download from GitHub releases
            AGE_VERSION="1.1.1"
            curl -LO "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
            tar -xzf "age-v${AGE_VERSION}-linux-amd64.tar.gz"
            mv age/age age/age-keygen /usr/local/bin/
            rm -rf age "age-v${AGE_VERSION}-linux-amd64.tar.gz"
        fi
        print_status "age installed"
    fi

    # Install SOPS
    if command -v sops &> /dev/null; then
        print_status "SOPS already installed: $(sops --version)"
    else
        echo "Installing SOPS..."
        SOPS_VERSION="3.8.1"
        curl -LO "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
        mv "sops-v${SOPS_VERSION}.linux.amd64" /usr/local/bin/sops
        chmod +x /usr/local/bin/sops
        print_status "SOPS installed"
    fi
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
    # This is critical for venv creation and npm install
    REAL_USER="${SUDO_USER:-$USER}"

    # Set ownership on entire base directory (needed for venv, npm, etc.)
    # This handles any directory structure without hardcoding names
    chown -R "$REAL_USER:$REAL_USER" "$BASE_DIR"
    print_status "Set ownership on $BASE_DIR"

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
        sudo -u "$REAL_USER" $PYTHON_CMD -m venv "$BACKEND_DIR/venv"
        print_status "Virtual environment created using $PYTHON_CMD"
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
# Interactive Setup Wizard
# ==============================================
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_password="$4"

    if [ "$is_password" = "true" ]; then
        echo -n "$prompt"
        read -s value
        echo ""
    else
        if [ -n "$default" ]; then
            read -p "$prompt [$default]: " value
        else
            read -p "$prompt: " value
        fi
    fi

    # Use default if empty
    if [ -z "$value" ]; then
        value="$default"
    fi

    eval "$var_name='$value'"
}

interactive_setup() {
    echo ""
    echo "=========================================="
    echo "       Configuration Wizard"
    echo "=========================================="
    echo ""
    echo "This wizard will help you configure the application."
    echo "Press Enter to accept default values shown in [brackets]."
    echo ""

    # -----------------------------------------
    # SQL Server (Source Database)
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── SQL Server (Source Database) ──${NC}"
    echo ""

    prompt_with_default "SQL Server host" "" "CFG_MSSQL_HOST"
    prompt_with_default "SQL Server port" "1433" "CFG_MSSQL_PORT"
    prompt_with_default "SQL Server database" "" "CFG_MSSQL_DATABASE"
    prompt_with_default "SQL Server username" "" "CFG_MSSQL_USER"
    prompt_with_default "SQL Server password" "" "CFG_MSSQL_PASSWORD" "true"

    # -----------------------------------------
    # Snowflake (Target Database)
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── Snowflake (Target Database) ──${NC}"
    echo ""

    prompt_with_default "Snowflake account (e.g., abc12345.us-east-1)" "" "CFG_SNOWFLAKE_ACCOUNT"
    prompt_with_default "Snowflake username" "" "CFG_SNOWFLAKE_USER"
    prompt_with_default "Snowflake warehouse" "COMPUTE_WH" "CFG_SNOWFLAKE_WAREHOUSE"
    prompt_with_default "Snowflake database" "" "CFG_SNOWFLAKE_DATABASE"
    prompt_with_default "Snowflake schema" "PUBLIC" "CFG_SNOWFLAKE_SCHEMA"
    prompt_with_default "Snowflake role (optional)" "" "CFG_SNOWFLAKE_ROLE"

    echo ""
    echo "Authentication method:"
    echo "  1) Password"
    echo "  2) PAT Token (Programmatic Access Token)"
    read -p "Select [1]: " sf_auth_choice
    sf_auth_choice="${sf_auth_choice:-1}"

    if [ "$sf_auth_choice" = "2" ]; then
        prompt_with_default "Snowflake PAT token" "" "CFG_SNOWFLAKE_TOKEN" "true"
        CFG_SNOWFLAKE_PASSWORD=""
    else
        prompt_with_default "Snowflake password" "" "CFG_SNOWFLAKE_PASSWORD" "true"
        CFG_SNOWFLAKE_TOKEN=""
    fi

    # -----------------------------------------
    # Authentication Backend
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── Application Authentication ──${NC}"
    echo ""
    echo "Where should user accounts be stored?"
    echo "  1) SQLite (local file, simple setup)"
    echo "  2) SQL Server (shared across instances)"
    read -p "Select [1]: " auth_choice
    auth_choice="${auth_choice:-1}"

    if [ "$auth_choice" = "2" ]; then
        CFG_AUTH_BACKEND="sqlserver"
        echo ""
        echo "SQL Server authentication database settings:"
        echo ""
        echo "Use same SQL Server credentials as source database?"
        echo "  Server: $CFG_MSSQL_HOST"
        echo "  User:   $CFG_MSSQL_USER"
        read -p "Reuse these credentials? (Y/n): " reuse_creds
        reuse_creds="${reuse_creds:-Y}"

        if [ "$reuse_creds" = "Y" ] || [ "$reuse_creds" = "y" ]; then
            CFG_AUTH_DB_SERVER="$CFG_MSSQL_HOST"
            CFG_AUTH_DB_USER="$CFG_MSSQL_USER"
            CFG_AUTH_DB_PASSWORD="$CFG_MSSQL_PASSWORD"
            echo ""
            prompt_with_default "Auth DB name" "ovs_studio" "CFG_AUTH_DB_NAME"
        else
            echo ""
            prompt_with_default "Auth DB server" "$CFG_MSSQL_HOST" "CFG_AUTH_DB_SERVER"
            prompt_with_default "Auth DB name" "ovs_studio" "CFG_AUTH_DB_NAME"
            prompt_with_default "Auth DB username" "$CFG_MSSQL_USER" "CFG_AUTH_DB_USER"
            prompt_with_default "Auth DB password" "" "CFG_AUTH_DB_PASSWORD" "true"
        fi
    else
        CFG_AUTH_BACKEND="sqlite"
        CFG_AUTH_DB_SERVER=""
        CFG_AUTH_DB_NAME=""
        CFG_AUTH_DB_USER=""
        CFG_AUTH_DB_PASSWORD=""
    fi

    # -----------------------------------------
    # LLM Provider (for AI schema mapping)
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── LLM Provider (AI Schema Mapping) ──${NC}"
    echo ""
    echo "Select LLM provider for AI-assisted schema mapping:"
    echo "  1) Ollama (local, free, no API key)"
    echo "  2) OpenAI"
    echo "  3) Azure OpenAI"
    echo "  4) Anthropic (Claude)"
    echo "  5) None (skip AI features)"
    read -p "Select [1]: " llm_choice
    llm_choice="${llm_choice:-1}"

    case "$llm_choice" in
        1)
            CFG_LLM_PROVIDER="ollama"
            prompt_with_default "Ollama URL" "http://localhost:11434" "CFG_OLLAMA_BASE_URL"
            prompt_with_default "Ollama model" "llama2" "CFG_OLLAMA_MODEL"
            ;;
        2)
            CFG_LLM_PROVIDER="openai"
            prompt_with_default "OpenAI API key" "" "CFG_OPENAI_API_KEY" "true"
            prompt_with_default "OpenAI model" "gpt-4o-mini" "CFG_OPENAI_MODEL"
            ;;
        3)
            CFG_LLM_PROVIDER="azure_openai"
            prompt_with_default "Azure OpenAI API key" "" "CFG_AZURE_OPENAI_API_KEY" "true"
            prompt_with_default "Azure OpenAI endpoint" "" "CFG_AZURE_OPENAI_ENDPOINT"
            prompt_with_default "Azure OpenAI deployment" "" "CFG_AZURE_OPENAI_DEPLOYMENT"
            prompt_with_default "Azure OpenAI API version" "2024-02-15-preview" "CFG_AZURE_OPENAI_API_VERSION"
            ;;
        4)
            CFG_LLM_PROVIDER="anthropic"
            prompt_with_default "Anthropic API key" "" "CFG_ANTHROPIC_API_KEY" "true"
            prompt_with_default "Anthropic model" "claude-3-5-sonnet-20241022" "CFG_ANTHROPIC_MODEL"
            ;;
        5)
            CFG_LLM_PROVIDER="ollama"
            CFG_OLLAMA_BASE_URL="http://localhost:11434"
            CFG_OLLAMA_MODEL="llama2"
            ;;
    esac

    # -----------------------------------------
    # Server Settings
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── Server Settings ──${NC}"
    echo ""
    prompt_with_default "Backend port" "8000" "CFG_BACKEND_PORT"
    prompt_with_default "Frontend port" "3000" "CFG_FRONTEND_PORT"

    # -----------------------------------------
    # Network/URL Configuration
    # -----------------------------------------
    echo ""
    echo -e "${GREEN}── Server Address (for API URLs) ──${NC}"
    echo ""
    echo "The frontend needs to know how to reach the backend API."
    echo "Select the address users will use to access this server:"
    echo ""

    # Detect available IPs
    declare -a IP_OPTIONS
    IP_OPTIONS+=("localhost")

    # Get hostname
    HOSTNAME_VAL=$(hostname 2>/dev/null)
    if [ -n "$HOSTNAME_VAL" ] && [ "$HOSTNAME_VAL" != "localhost" ]; then
        IP_OPTIONS+=("$HOSTNAME_VAL")
    fi

    # Get IP addresses (works on Linux and macOS)
    if command -v ip &> /dev/null; then
        # Linux
        while IFS= read -r ip; do
            [ -n "$ip" ] && IP_OPTIONS+=("$ip")
        done < <(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.')
    elif command -v ifconfig &> /dev/null; then
        # macOS / BSD
        while IFS= read -r ip; do
            [ -n "$ip" ] && IP_OPTIONS+=("$ip")
        done < <(ifconfig | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}')
    fi

    # Display options
    echo "Detected addresses:"
    for i in "${!IP_OPTIONS[@]}"; do
        idx=$((i + 1))
        ip="${IP_OPTIONS[$i]}"
        if [ "$ip" = "localhost" ]; then
            echo "  $idx) localhost (local development only)"
        elif [ "$ip" = "$HOSTNAME_VAL" ]; then
            echo "  $idx) $ip (hostname)"
        else
            echo "  $idx) $ip"
        fi
    done
    echo "  C) Enter custom hostname/IP"
    echo ""

    read -p "Select address [1]: " addr_choice
    addr_choice="${addr_choice:-1}"

    if [ "$addr_choice" = "C" ] || [ "$addr_choice" = "c" ]; then
        read -p "Enter hostname or IP: " CFG_SERVER_HOST
    elif [[ "$addr_choice" =~ ^[0-9]+$ ]] && [ "$addr_choice" -ge 1 ] && [ "$addr_choice" -le "${#IP_OPTIONS[@]}" ]; then
        CFG_SERVER_HOST="${IP_OPTIONS[$((addr_choice - 1))]}"
    else
        CFG_SERVER_HOST="localhost"
    fi

    # Build URLs
    CFG_VITE_API_URL="http://${CFG_SERVER_HOST}:${CFG_BACKEND_PORT}"
    CFG_CORS_ORIGINS="http://${CFG_SERVER_HOST}:${CFG_FRONTEND_PORT}"

    echo ""
    echo "URLs configured:"
    echo "  Backend API:  $CFG_VITE_API_URL"
    echo "  Frontend:     http://${CFG_SERVER_HOST}:${CFG_FRONTEND_PORT}"

    # Generate a random secret key
    CFG_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)

    # -----------------------------------------
    # Summary
    # -----------------------------------------
    echo ""
    echo "=========================================="
    echo "       Configuration Summary"
    echo "=========================================="
    echo ""
    echo "SQL Server:"
    echo "  Host: $CFG_MSSQL_HOST:$CFG_MSSQL_PORT"
    echo "  Database: $CFG_MSSQL_DATABASE"
    echo "  User: $CFG_MSSQL_USER"
    echo ""
    echo "Snowflake:"
    echo "  Account: $CFG_SNOWFLAKE_ACCOUNT"
    echo "  User: $CFG_SNOWFLAKE_USER"
    echo "  Warehouse: $CFG_SNOWFLAKE_WAREHOUSE"
    echo "  Database: $CFG_SNOWFLAKE_DATABASE"
    if [ -n "$CFG_SNOWFLAKE_TOKEN" ]; then
        echo "  Auth: PAT Token"
    else
        echo "  Auth: Password"
    fi
    echo ""
    echo "Authentication: $CFG_AUTH_BACKEND"
    echo "LLM Provider: $CFG_LLM_PROVIDER"
    echo ""
    echo "Server:"
    echo "  Address: $CFG_SERVER_HOST"
    echo "  Backend: http://${CFG_SERVER_HOST}:${CFG_BACKEND_PORT}"
    echo "  Frontend: http://${CFG_SERVER_HOST}:${CFG_FRONTEND_PORT}"
    echo ""

    read -p "Save this configuration? (Y/n): " confirm
    confirm="${confirm:-Y}"

    if [ "$confirm" != "Y" ] && [ "$confirm" != "y" ]; then
        echo "Configuration cancelled. You can edit manually: $BASE_DIR/ombudsman.env"
        return 1
    fi

    return 0
}

generate_env_file() {
    local ENV_FILE="$BASE_DIR/ombudsman.env"
    local REAL_USER="${SUDO_USER:-$USER}"

    cat > "$ENV_FILE" << EOF
# ============================================
# Ombudsman Validation Studio Configuration
# Generated by install wizard on $(date)
# ============================================

# ------------------------------------------
# SQL Server (Source Database)
# ------------------------------------------
MSSQL_HOST=$CFG_MSSQL_HOST
MSSQL_PORT=$CFG_MSSQL_PORT
MSSQL_DATABASE=$CFG_MSSQL_DATABASE
MSSQL_USER=$CFG_MSSQL_USER
MSSQL_PASSWORD=$CFG_MSSQL_PASSWORD

# ------------------------------------------
# Snowflake (Target Database)
# ------------------------------------------
SNOWFLAKE_ACCOUNT=$CFG_SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER=$CFG_SNOWFLAKE_USER
SNOWFLAKE_WAREHOUSE=$CFG_SNOWFLAKE_WAREHOUSE
SNOWFLAKE_DATABASE=$CFG_SNOWFLAKE_DATABASE
SNOWFLAKE_SCHEMA=$CFG_SNOWFLAKE_SCHEMA
SNOWFLAKE_ROLE=$CFG_SNOWFLAKE_ROLE
EOF

    # Add either password or token
    if [ -n "$CFG_SNOWFLAKE_TOKEN" ]; then
        cat >> "$ENV_FILE" << EOF
# Using PAT Token authentication
SNOWFLAKE_TOKEN=$CFG_SNOWFLAKE_TOKEN
# SNOWFLAKE_PASSWORD=
EOF
    else
        cat >> "$ENV_FILE" << EOF
SNOWFLAKE_PASSWORD=$CFG_SNOWFLAKE_PASSWORD
# SNOWFLAKE_TOKEN=  # Use instead of password for PAT auth
EOF
    fi

    cat >> "$ENV_FILE" << EOF

# ------------------------------------------
# Authentication Backend
# ------------------------------------------
AUTH_BACKEND=$CFG_AUTH_BACKEND
EOF

    if [ "$CFG_AUTH_BACKEND" = "sqlserver" ]; then
        cat >> "$ENV_FILE" << EOF
AUTH_DB_SERVER=$CFG_AUTH_DB_SERVER
AUTH_DB_NAME=$CFG_AUTH_DB_NAME
AUTH_DB_USER=$CFG_AUTH_DB_USER
AUTH_DB_PASSWORD=$CFG_AUTH_DB_PASSWORD
EOF
    else
        cat >> "$ENV_FILE" << EOF
# AUTH_DB_SERVER=
# AUTH_DB_NAME=ovs_studio
# AUTH_DB_USER=
# AUTH_DB_PASSWORD=
EOF
    fi

    cat >> "$ENV_FILE" << EOF

# ------------------------------------------
# LLM Provider (AI Schema Mapping)
# ------------------------------------------
LLM_PROVIDER=$CFG_LLM_PROVIDER
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2048
LLM_TIMEOUT=30

EOF

    case "$CFG_LLM_PROVIDER" in
        ollama)
            cat >> "$ENV_FILE" << EOF
# Ollama (local)
OLLAMA_BASE_URL=$CFG_OLLAMA_BASE_URL
OLLAMA_MODEL=$CFG_OLLAMA_MODEL
EOF
            ;;
        openai)
            cat >> "$ENV_FILE" << EOF
# OpenAI
OPENAI_API_KEY=$CFG_OPENAI_API_KEY
OPENAI_MODEL=$CFG_OPENAI_MODEL
EOF
            ;;
        azure_openai)
            cat >> "$ENV_FILE" << EOF
# Azure OpenAI
AZURE_OPENAI_API_KEY=$CFG_AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT=$CFG_AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT=$CFG_AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_VERSION=$CFG_AZURE_OPENAI_API_VERSION
EOF
            ;;
        anthropic)
            cat >> "$ENV_FILE" << EOF
# Anthropic
ANTHROPIC_API_KEY=$CFG_ANTHROPIC_API_KEY
ANTHROPIC_MODEL=$CFG_ANTHROPIC_MODEL
EOF
            ;;
    esac

    cat >> "$ENV_FILE" << EOF

# ------------------------------------------
# Server Settings
# ------------------------------------------
BACKEND_PORT=$CFG_BACKEND_PORT
FRONTEND_PORT=$CFG_FRONTEND_PORT
SECRET_KEY=$CFG_SECRET_KEY

# Server address (used for API URLs)
SERVER_HOST=$CFG_SERVER_HOST
VITE_API_URL=$CFG_VITE_API_URL
CORS_ORIGINS=$CFG_CORS_ORIGINS

# ------------------------------------------
# Paths (auto-configured)
# ------------------------------------------
# BASE_DIR=$BASE_DIR
# OMBUDSMAN_DATA_DIR=$BASE_DIR/data
# OMBUDSMAN_LOG_DIR=$BASE_DIR/logs
EOF

    chown "$REAL_USER:$REAL_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    print_status "Configuration saved to $ENV_FILE"
}

# ==============================================
# Setup config file
# ==============================================
setup_config() {
    echo ""
    echo "=========================================="
    echo "Setting up configuration..."
    echo "=========================================="

    ENV_FILE="$BASE_DIR/ombudsman.env"

    if [ -f "$ENV_FILE" ]; then
        print_status "Config file already exists at $ENV_FILE"
        read -p "Reconfigure? (y/N): " reconfigure
        if [ "$reconfigure" != "y" ] && [ "$reconfigure" != "Y" ]; then
            return
        fi
    fi

    # Run interactive setup
    if interactive_setup; then
        generate_env_file

        # Offer to encrypt
        echo ""
        if command -v sops &> /dev/null && command -v age &> /dev/null; then
            read -p "Encrypt configuration with SOPS? (Y/n): " encrypt_choice
            encrypt_choice="${encrypt_choice:-Y}"
            if [ "$encrypt_choice" = "Y" ] || [ "$encrypt_choice" = "y" ]; then
                SOPS_KEY_FILE="$BASE_DIR/.sops-age-key.txt"
                if [ ! -f "$SOPS_KEY_FILE" ]; then
                    echo "Generating encryption key..."
                    if ! age-keygen -o "$SOPS_KEY_FILE" 2>&1 | tee /tmp/age-keygen-output.txt; then
                        print_error "Failed to generate age key"
                        rm -f /tmp/age-keygen-output.txt
                        print_warning "Skipping encryption. Config saved as plaintext."
                        return
                    fi
                    chmod 600 "$SOPS_KEY_FILE"
                    AGE_PUBLIC_KEY=$(grep -i "public key:" /tmp/age-keygen-output.txt | cut -d: -f2 | tr -d ' ')
                    rm -f /tmp/age-keygen-output.txt

                    if [ -z "$AGE_PUBLIC_KEY" ]; then
                        print_error "Failed to extract public key from age-keygen output"
                        print_warning "Skipping encryption. Config saved as plaintext."
                        return
                    fi

                    # Create .sops.yaml config
                    cat > "$BASE_DIR/.sops.yaml" << EOF
creation_rules:
  # Match .env files for encryption
  - path_regex: .*\.env$
    age: $AGE_PUBLIC_KEY
  # Match .env.enc files for decryption
  - path_regex: .*\.env\.enc$
    age: $AGE_PUBLIC_KEY
EOF
                    print_status "Created SOPS config with age key"
                else
                    # Key exists, make sure .sops.yaml also exists
                    if [ ! -f "$BASE_DIR/.sops.yaml" ]; then
                        print_error "Key exists but .sops.yaml is missing"
                        print_warning "Run './start-ombudsman.sh init-secrets' to fix, then './start-ombudsman.sh encrypt-secrets'"
                        return
                    fi
                fi

                # Debug: show what we're using
                echo "Using key file: $SOPS_KEY_FILE"
                echo "Using config: $BASE_DIR/.sops.yaml"
                echo "Encrypting: $ENV_FILE"

                # Show the age public key being used
                echo "Age public key from config:"
                grep "age:" "$BASE_DIR/.sops.yaml" 2>/dev/null || echo "  (not found)"

                # Encrypt - keep stderr separate so we can see errors
                local sops_error
                sops_error=$(SOPS_AGE_KEY_FILE="$SOPS_KEY_FILE" sops --config "$BASE_DIR/.sops.yaml" --encrypt "$ENV_FILE" 2>&1 > "$ENV_FILE.enc.tmp")
                local sops_exit=$?

                if [ $sops_exit -eq 0 ]; then
                    # Verify the output is actually encrypted (contains ENC[ markers or sops_ metadata)
                    if grep -q "ENC\[" "$ENV_FILE.enc.tmp" 2>/dev/null || grep -q "^sops_" "$ENV_FILE.enc.tmp" 2>/dev/null; then
                        mv "$ENV_FILE.enc.tmp" "$ENV_FILE.enc"
                        print_status "Configuration encrypted to $ENV_FILE.enc"
                        print_warning "IMPORTANT: Back up your key: $SOPS_KEY_FILE"

                        read -p "Delete plaintext config file? (Y/n): " delete_plain
                        delete_plain="${delete_plain:-Y}"
                        if [ "$delete_plain" = "Y" ] || [ "$delete_plain" = "y" ]; then
                            rm "$ENV_FILE"
                            print_status "Plaintext config deleted"
                        fi
                    else
                        print_error "Encryption produced invalid output (no ENC[ or sops_ markers)"
                        echo "Output file contents:"
                        head -20 "$ENV_FILE.enc.tmp"
                        rm -f "$ENV_FILE.enc.tmp"
                        print_warning "Keeping plaintext config at $ENV_FILE"
                    fi
                else
                    print_error "SOPS encryption failed (exit code: $sops_exit)"
                    echo "SOPS error: $sops_error"
                    rm -f "$ENV_FILE.enc.tmp"
                    print_warning "Keeping plaintext config at $ENV_FILE"
                fi
            fi
        fi
    else
        # Fallback: copy template
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        cp "$SCRIPT_DIR/ombudsman.env" "$ENV_FILE"
        REAL_USER="${SUDO_USER:-$USER}"
        chown "$REAL_USER:$REAL_USER" "$ENV_FILE"
        print_warning "Using template. Edit $ENV_FILE with your credentials."
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

    # Load env file to get AUTH_BACKEND and credentials
    if [ -f "$ENV_FILE" ]; then
        set -a
        source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
        set +a
    fi

    # Use CFG_AUTH_BACKEND from wizard if AUTH_BACKEND wasn't loaded from env file
    AUTH_BACKEND="${AUTH_BACKEND:-${CFG_AUTH_BACKEND:-sqlite}}"

    # Check if using SQL Server auth
    if [ "$AUTH_BACKEND" = "sqlserver" ]; then
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
                AUTH_BACKEND="sqlserver" \
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
    if 'already exists' in str(e).lower():
        print(f'  Admin user already exists')
    else:
        print(f'  ValueError creating admin user: {e}')
except Exception as e:
    print(f'  Could not create admin user: {e}')
    import traceback
    traceback.print_exc()
"
            print_status "Auth database configured (SQL Server)"
        else
            print_warning "AUTH_BACKEND=sqlserver but credentials not set. Skipping auth DB setup."
            print_warning "Edit $ENV_FILE and run: ./start-ombudsman.sh setup-auth"
        fi
    else
        # SQLite authentication - create default admin user
        echo "Setting up SQLite authentication..."
        cd "$BACKEND_DIR"

        # Create default admin user for SQLite
        echo "Creating default admin user..."
        sudo -u "$REAL_USER" \
            AUTH_BACKEND="sqlite" \
            OMBUDSMAN_DATA_DIR="$BASE_DIR/data" \
            ./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from auth.sqlite_repository import SQLiteAuthRepository
from auth.models import UserCreate, UserRole
repo = SQLiteAuthRepository()
try:
    user = UserCreate(username='admin', email='admin@localhost', password='admin123', role=UserRole.ADMIN)
    repo.create_user(user)
    print('  Default admin user created (admin/admin123)')
except ValueError as e:
    if 'already exists' in str(e).lower():
        print(f'  Admin user already exists')
    else:
        print(f'  ValueError creating admin user: {e}')
except Exception as e:
    print(f'  Could not create admin user: {e}')
    import traceback
    traceback.print_exc()
"
        print_status "Auth database configured (SQLite)"
    fi
}

# ==============================================
# Setup systemd services for auto-start on boot
# ==============================================
setup_systemd_services() {
    echo ""
    echo "=========================================="
    echo "Setting up systemd services..."
    echo "=========================================="

    REAL_USER="${SUDO_USER:-$USER}"
    ENV_FILE="$BASE_DIR/ombudsman.env"

    # Get port configuration (from wizard vars, env file, or defaults)
    if [ -n "$CFG_BACKEND_PORT" ]; then
        SVC_BACKEND_PORT="$CFG_BACKEND_PORT"
    elif [ -f "$ENV_FILE" ]; then
        SVC_BACKEND_PORT=$(grep "^BACKEND_PORT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)
    fi
    SVC_BACKEND_PORT="${SVC_BACKEND_PORT:-8000}"

    if [ -n "$CFG_FRONTEND_PORT" ]; then
        SVC_FRONTEND_PORT="$CFG_FRONTEND_PORT"
    elif [ -f "$ENV_FILE" ]; then
        SVC_FRONTEND_PORT=$(grep "^FRONTEND_PORT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)
    fi
    SVC_FRONTEND_PORT="${SVC_FRONTEND_PORT:-3000}"

    print_status "Backend port: $SVC_BACKEND_PORT"
    print_status "Frontend port: $SVC_FRONTEND_PORT"

    # Create log directory
    mkdir -p "$BASE_DIR/logs"
    chown -R "$REAL_USER:$REAL_USER" "$BASE_DIR/logs"

    # Generate backend service file with dynamic paths and ports
    cat > /etc/systemd/system/ombudsman-backend.service << EOF
[Unit]
Description=Ombudsman Validation Studio - Backend
After=network.target

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BASE_DIR/ombudsman.env
Environment=OMBUDSMAN_BASE_DIR=$BASE_DIR
Environment=PYTHONPATH=$BACKEND_DIR:$BASE_DIR/ombudsman_core/src

ExecStart=$BACKEND_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $SVC_BACKEND_PORT --log-level info

Restart=always
RestartSec=5

StandardOutput=append:$BASE_DIR/logs/backend.log
StandardError=append:$BASE_DIR/logs/backend.log

[Install]
WantedBy=multi-user.target
EOF

    # Generate frontend service file with dynamic paths and ports
    cat > /etc/systemd/system/ombudsman-frontend.service << EOF
[Unit]
Description=Ombudsman Validation Studio - Frontend
After=network.target ombudsman-backend.service
Wants=ombudsman-backend.service

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$FRONTEND_DIR
EnvironmentFile=$BASE_DIR/ombudsman.env

ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port $SVC_FRONTEND_PORT --strictPort

Restart=always
RestartSec=5

StandardOutput=append:$BASE_DIR/logs/frontend.log
StandardError=append:$BASE_DIR/logs/frontend.log

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable services (auto-start on boot)
    systemctl enable ombudsman-backend
    systemctl enable ombudsman-frontend

    print_status "Systemd services installed and enabled"
    print_status "Services will auto-start on boot"
    print_status "Base directory: $BASE_DIR"
}

# ==============================================
# Main
# ==============================================
main() {
    # Check for --setup-only flag (reconfigure without reinstalling)
    SETUP_ONLY=false
    if [ "$1" = "--setup-only" ]; then
        SETUP_ONLY=true
    fi

    echo "=========================================="
    if [ "$SETUP_ONLY" = true ]; then
        echo "Ombudsman Validation Studio - Setup Wizard"
    else
        echo "Ombudsman Validation Studio Installer"
    fi
    echo "=========================================="

    check_sudo

    if [ "$SETUP_ONLY" = true ]; then
        # Just run config wizard, skip dependency installation
        setup_config
        setup_frontend      # Rebuild frontend with correct API URL
        setup_auth_db
        echo ""
        echo "=========================================="
        echo -e "${GREEN}Configuration Complete!${NC}"
        echo "=========================================="
        echo ""
        echo "Start the services:"
        echo "   sudo systemctl start ombudsman-backend ombudsman-frontend"
        echo "   # or: ./start-ombudsman.sh start"
        echo ""
        return
    fi

    install_system_deps
    detect_python
    install_nodejs
    install_odbc_drivers
    install_sops
    create_directories
    setup_python_venv
    setup_config           # Interactive wizard - collects VITE_API_URL
    setup_frontend         # Build frontend with correct API URL
    setup_auth_db
    setup_systemd_services

    echo ""
    echo "=========================================="
    echo -e "${GREEN}Installation Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Your application is configured and ready!"
    echo ""
    echo "Start the services:"
    echo "   sudo systemctl start ombudsman-backend ombudsman-frontend"
    echo ""
    echo "Access the application:"
    if [ -n "$CFG_SERVER_HOST" ]; then
        echo "   Frontend: http://${CFG_SERVER_HOST}:${CFG_FRONTEND_PORT:-3000}"
        echo "   Backend:  http://${CFG_SERVER_HOST}:${CFG_BACKEND_PORT:-8000}"
    else
        echo "   Frontend: http://your-server:3000"
        echo "   Backend:  http://your-server:8000"
    fi
    echo ""
    echo "Default login: admin / admin123"
    echo ""
    echo "=========================================="
    echo "Useful commands:"
    echo "=========================================="
    echo "  Start services:   sudo systemctl start ombudsman-backend ombudsman-frontend"
    echo "  Stop services:    sudo systemctl stop ombudsman-backend ombudsman-frontend"
    echo "  Restart services: sudo systemctl restart ombudsman-backend ombudsman-frontend"
    echo "  Check status:     sudo systemctl status ombudsman-backend"
    echo "  View logs:        sudo journalctl -u ombudsman-backend -f"
    echo "  Encrypt secrets:  ./start-ombudsman.sh encrypt-secrets"
    echo "  Edit secrets:     ./start-ombudsman.sh edit-secrets"
    echo ""
    echo "Services will auto-start on reboot."
    echo "For more help: cat $BASE_DIR/deploy/README.md"
    echo ""
}

main "$@"
